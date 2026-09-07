from contextlib import asynccontextmanager
from typing import AsyncIterator

from .tools import mcp

MCP_PATH = "/schedule"
_mcp_app = mcp.streamable_http_app()


class _TrailingSlashCompatibleApp:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].endswith("/mcp/"):
            scope = dict(scope)
            scope["path"] = scope["path"][:-1]
            scope["raw_path"] = scope["raw_path"].rstrip(b"/")
        await self.app(scope, receive, send)


mcp_http_app = _TrailingSlashCompatibleApp(_mcp_app)


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
