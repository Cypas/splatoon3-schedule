from typing import Sequence

from .result import RequestContext, ServiceResult
from .dto import ScheduleQuery


class ScheduleApplicationService:
    """对战日程查询应用服务。"""

    def __init__(self, file_storage=None):
        self.file_storage = file_storage

    async def get_stages(
        self,
        context: RequestContext,
        num_list: Sequence[int] | None = None,
        contest_match: str | None = None,
        rule_match: str | None = None,
        trigger_word: str = "图",
        cache_key: str | None = None,
        query: ScheduleQuery | None = None,
    ) -> ServiceResult:
        from ..image.image import get_save_temp_image, get_stages_image

        if query is not None:
            num_list, contest_match, rule_match = query.numbers, query.contest, query.rule
        numbers = list(num_list) if num_list is not None else [0]
        is_cache, image_data = await get_save_temp_image(
            cache_key or trigger_word,
            get_stages_image,
            numbers,
            contest_match,
            rule_match,
        )
        if image_data is None:
            return ServiceResult(status="completed", data={"cached": is_cache})
        if isinstance(image_data, str):
            return ServiceResult(
                status="failed",
                message=image_data,
                data={"cached": is_cache},
                code="SCHEDULE_RENDER_FAILED",
            )
        storage_result = self.file_storage.upload_image(
            image_data,
            context.client_id or context.user_id,
        ) if self.file_storage is not None else None
        image_url = storage_result.get("file_url") if storage_result else None
        return ServiceResult(
            status="completed",
            data={
                "cached": is_cache,
                "storage": "cos" if image_url else "none",
            },
            image_data=image_data,
            image_url=image_url,
        )
