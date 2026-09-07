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

    async def get_rendered(self, context: RequestContext, operation: str, trigger: str, func, *args) -> ServiceResult:
        """Render any schedule-related image and expose it as a platform-neutral result."""
        from ..image.image import get_save_temp_image
        is_cache, image_data = await get_save_temp_image(trigger, func, *args)
        if image_data is None:
            return ServiceResult(status="completed", data={"cached": is_cache})
        if isinstance(image_data, str):
            return ServiceResult(status="failed", message=image_data, code="RENDER_FAILED")
        storage_result = self.file_storage.upload_image(image_data, context.client_id or context.user_id) if self.file_storage else None
        image_url = storage_result.get("file_url") if storage_result else None
        return ServiceResult(status="completed", data={"operation": operation, "cached": is_cache}, image_data=image_data, image_url=image_url)

    async def get_build(self, context: RequestContext, weapon_query: str, mode: str = "全部") -> ServiceResult:
        from ..weapon_match import match_weapon_async
        match = await match_weapon_async(weapon_query)
        if match.status != "matched":
            return ServiceResult(status="failed", message="未能唯一匹配武器", code="WEAPON_NOT_MATCHED",
                                  data={"match_status": match.status, "candidates": [c.zh_name for c in match.candidates]})
        build = match.matched
        if build is None:
            return ServiceResult(status="failed", message="未能唯一匹配武器", code="WEAPON_NOT_MATCHED")
        result = await self.get_rendered(context, "weapon_build", f"配装_{build.zh_name}_{mode}",
                                          __import__("nonebot_plugin_splatoon3_schedule.image.image", fromlist=["get_build_image"]).get_build_image,
                                          build.sendou_name, mode)
        result.data.update({"weapon": build.zh_name, "mode": mode})
        return result
