import asyncio
import json
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncIterator

from ...config import plugin_config
from .tools import mcp

MCP_PATH = "/schedule"
_mcp_app = mcp.streamable_http_app()


class _IpSlidingWindowLimiter:
    def __init__(self, limit: int = 15, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def allow(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            if now - self._last_cleanup >= self.window_seconds:
                self._requests = {
                    ip: timestamps
                    for ip, timestamps in self._requests.items()
                    if timestamps and timestamps[-1] > cutoff
                }
                self._last_cleanup = now
            timestamps = self._requests.setdefault(client_ip, deque())
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                return False
            timestamps.append(now)
            return True


def _get_client_ip(scope) -> str:
    headers = dict(scope.get("headers", []))
    for header_name in (b"cf-connecting-ip", b"x-forwarded-for"):
        value = headers.get(header_name)
        if value:
            return value.decode("latin-1").split(",", 1)[0].strip()
    client = scope.get("client")
    return str(client[0]) if client else "unknown"


class _RateLimitedApp:
    def __init__(self, app, limit: int = 15, window_seconds: int = 60):
        self.app = app
        self.limiter = _IpSlidingWindowLimiter(limit, window_seconds)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            client_ip = _get_client_ip(scope)
            if not await self.limiter.allow(client_ip):
                payload = json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32000,
                            "message": "请求频率过高，请稍后再试",
                        },
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
                await send(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            (b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(payload)).encode("ascii")),
                            (b"retry-after", str(self.limiter.window_seconds).encode("ascii")),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": payload})
                return
        await self.app(scope, receive, send)


class _TrailingSlashCompatibleApp:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].endswith("/mcp/"):
            scope = dict(scope)
            scope["path"] = scope["path"][:-1]
            scope["raw_path"] = scope["raw_path"].rstrip(b"/")
        await self.app(scope, receive, send)


class _OriginRestrictedApp:
    """只校验 Origin，不校验 Host（Host 由外部反向代理负责）。"""

    def __init__(self, app, allowed_origins: list[str]):
        self.app = app
        self.allowed_origins = tuple(allowed_origins)

    def _is_allowed(self, origin: str) -> bool:
        if not self.allowed_origins:
            return True
        if origin in self.allowed_origins:
            return True
        for allowed in self.allowed_origins:
            if allowed.endswith(":*") and origin.startswith(allowed[:-2] + ":"):
                return True
        return False

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin")
            if origin:
                origin = origin.decode("latin-1")
                if not self._is_allowed(origin):
                    payload = b"Invalid Origin header"
                    await send(
                        {
                            "type": "http.response.start",
                            "status": 403,
                            "headers": [
                                (b"content-type", b"text/plain; charset=utf-8"),
                                (b"content-length", str(len(payload)).encode("ascii")),
                            ],
                        }
                    )
                    await send({"type": "http.response.body", "body": payload})
                    return
        await self.app(scope, receive, send)


mcp_http_app = _RateLimitedApp(
    _OriginRestrictedApp(
        _TrailingSlashCompatibleApp(_mcp_app),
        list(plugin_config.splatoon3_mcp_allowed_origins),
    )
)


def install_mcp_lifespan(host_app) -> None:
    """将 MCP 会话管理器接入实际运行的宿主 ASGI 应用生命周期。"""
    original_lifespan = host_app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application) -> AsyncIterator[None]:
        async with original_lifespan(application):
            async with mcp.session_manager.run():
                yield

    host_app.router.lifespan_context = lifespan


__all__ = ["MCP_PATH", "mcp", "mcp_http_app", "install_mcp_lifespan"]
