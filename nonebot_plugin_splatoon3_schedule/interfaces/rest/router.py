from fastapi import APIRouter, Query

from ...application import RequestContext, normalize_schedule_query, build_schedule_cache_key
from ..mcp.tools import CONTEST_VALUES, RULE_VALUES
from ...application.schedule_service import ScheduleApplicationService
from ...infrastructure.file_storage import CosFileStorage


router = APIRouter(
    prefix="/schedule",
    tags=["Splatoon 3 日程"],
)
schedule_service = ScheduleApplicationService(file_storage=CosFileStorage())


@router.get("/stages")
async def get_stages(
    numbers: list[int] | None = Query(default=None),
    contest: str | None = None,
    rule: str | None = None,
) -> dict:
    """获取对战日程，并返回图片 URL。"""
    query = normalize_schedule_query(numbers, contest, rule,
                                     contest_values=CONTEST_VALUES,
                                     rule_values=RULE_VALUES)
    result = await schedule_service.get_stages(
        context=RequestContext(
            request_id="rest-schedule",
            provider="rest",
        ),
        query=query,
        trigger_word="图",
        cache_key=build_schedule_cache_key("rest", query),
    )
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }
