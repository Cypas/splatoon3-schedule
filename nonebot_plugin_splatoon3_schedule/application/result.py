from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RequestContext:
    request_id: str = ""
    provider: str = ""
    client_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    parent_source_id: str | None = None


@dataclass
class ServiceResult:
    status: str
    message: str = ""
    data: dict[str, Any] | None = None
    image_data: bytes | None = None
    image_url: str | None = None
    image_path: str | None = None
    file_url: str | None = None
    warnings: list[str] | None = None
    code: str | None = None

    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {}
        if self.warnings is None:
            self.warnings = []
