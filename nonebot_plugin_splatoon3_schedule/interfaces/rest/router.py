from fastapi import APIRouter, Query

from ...application import RequestContext
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
    result = await schedule_service.get_stages(
        context=RequestContext(
            request_id="rest-schedule",
            provider="rest",
        ),
        num_list=numbers or [0],
        contest_match=contest,
        rule_match=rule,
        trigger_word="图",
        cache_key="rest_"
        + ",".join(
            [
                *(map(str, numbers or [0])),
                contest or "",
                rule or "",
            ]
        ),
    )
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }
