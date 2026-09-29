from typing import Sequence

from .result import RequestContext, ServiceResult
from .dto import ScheduleQuery


class ScheduleApplicationService:
    """对战日程查询应用服务。"""

    def __init__(self, file_storage=None):
        self.file_storage = file_storage

    async def get_upcoming_special_events(
        self, context: RequestContext
    ) -> ServiceResult:
        """Return special-event reminders for today and the next two days."""
        import asyncio

        from ..data.data_source import get_newest_event_or_coop

        notice = await asyncio.to_thread(get_newest_event_or_coop)
        message = notice or "近期没有活动比赛、团队打工、Big Run或随机金工安排"
        return ServiceResult(
            status="completed",
            message=message,
            data={
                "has_events": bool(notice),
                "notice": notice,
                "range_days": 3,
            },
        )

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

    async def get_gear(self, context: RequestContext) -> ServiceResult:
        """Capture the gear shop using the same mobile view as NoneBot."""
        from ..data.playwright_handler import ErrorImage, get_screenshot

        screenshot = await get_screenshot(
            shot_url="https://splatoon3.ink/gear",
            mode="mobile",
        )
        fallback_message = None
        if isinstance(screenshot, ErrorImage):
            fallback_message = screenshot.error_message
            image_data = screenshot.image
        else:
            image_data = screenshot
        storage_result = self.file_storage.upload_image(
            image_data, context.client_id or context.user_id
        ) if self.file_storage else None
        image_url = storage_result.get("file_url") if storage_result else None
        return ServiceResult(
            status="completed",
            data={
                "operation": "gear_shop",
                "cached": False,
                "fallback_screenshot": bool(fallback_message),
            },
            image_data=image_data,
            image_url=image_url,
            warnings=[fallback_message] if fallback_message else [],
        )

    async def get_random_weapons(
        self,
        context: RequestContext,
        filters: Sequence[str] | None = None,
        fully_random: bool = False,
    ) -> ServiceResult:
        """Generate two teams using the same filters as NoneBot's random command."""
        from ..data import db_image
        from ..image import image_to_bytes
        from ..image.image import get_random_weapon_image

        if db_image.get_weapon_info("", "", "", "") is None:
            return ServiceResult(
                status="failed",
                message="武器数据尚未初始化，请先更新武器数据",
                code="WEAPON_DATA_UNAVAILABLE",
            )
        normalized_filters = [str(value).strip() for value in (filters or [])]
        normalized_filters = [value for value in normalized_filters if value][:4]
        command = "随机武器完全随机" if fully_random else "随机武器"
        if normalized_filters and not fully_random:
            command += " " + " ".join(normalized_filters)
        try:
            image_data = image_to_bytes(await get_random_weapon_image(command))
        except Exception as exc:
            return ServiceResult(
                status="failed",
                message=f"随机武器生成失败: {exc}",
                code="RANDOM_WEAPON_RENDER_FAILED",
            )
        storage_result = self.file_storage.upload_image(
            image_data, context.client_id or context.user_id
        ) if self.file_storage else None
        image_url = storage_result.get("file_url") if storage_result else None
        return ServiceResult(
            status="completed",
            data={
                "operation": "random_weapons",
                "cached": False,
                "filters": normalized_filters,
                "fully_random": fully_random,
            },
            image_data=image_data,
            image_url=image_url,
        )

    async def get_build(self, context: RequestContext, weapon_query: str, mode: str = "全部") -> ServiceResult:
        from .weapon_match import match_weapon_async
        from ..image.image import get_build_image

        public_to_internal = {
            "涂地": "TW",
            "区域": "SZ",
            "塔楼": "TC",
            "鱼虎": "RM",
            "蛤蜊": "CB",
            "全部": "全部",
        }
        internal_to_public = {value: key for key, value in public_to_internal.items()}
        normalized_mode = str(mode).strip()
        if normalized_mode.upper() in internal_to_public:
            normalized_mode = normalized_mode.upper()
            public_mode = internal_to_public[normalized_mode]
            internal_mode = normalized_mode
        elif normalized_mode in public_to_internal:
            public_mode = normalized_mode
            internal_mode = public_to_internal[normalized_mode]
        else:
            return ServiceResult(
                status="failed",
                message="不支持的配装模式",
                code="INVALID_BUILD_MODE",
                data={"mode": mode, "allowed_modes": list(public_to_internal)},
            )
        match = await match_weapon_async(weapon_query)
        if match.status != "matched":
            return ServiceResult(status="failed", message="未能唯一匹配武器", code="WEAPON_NOT_MATCHED",
                                  data={"match_status": match.status, "candidates": [c.zh_name for c in match.candidates]})
        build = match.matched
        if build is None:
            return ServiceResult(status="failed", message="未能唯一匹配武器", code="WEAPON_NOT_MATCHED",
                                  data={"match_status": match.status, "candidates": [c.zh_name for c in match.candidates]})
        trigger_prefix = "mcp_" if context.provider == "mcp" else ""
        result = await self.get_rendered(
            context,
            "weapon_build",
            f"{trigger_prefix}配装_{build.zh_name}_{public_mode}",
            get_build_image,
            build.sendou_name,
            internal_mode,
        )
        result.data.update({"weapon": build.zh_name, "mode": public_mode})
        return result
