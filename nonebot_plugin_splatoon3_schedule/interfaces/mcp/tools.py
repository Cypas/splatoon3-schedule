import uuid
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from ...application import RequestContext, normalize_schedule_query, build_schedule_cache_key
from ...application.schedule_service import ScheduleApplicationService
from ...config import plugin_config
from ...infrastructure.file_storage import CosFileStorage
from ...image.image import get_coop_stages_image, get_festival_image, get_events_image


CONTEST_VALUES = ("涂地", "挑战", "开放", "X段")
RULE_VALUES = ("区域", "蛤蜊", "塔楼", "鱼虎")


mcp = FastMCP(
    "splatoon3-schedule",
    transport_security=TransportSecuritySettings(
        # Host 由外部 Nginx 等反向代理校验；这里关闭 MCP 内置的 Host/Origin
        # 联合校验，Origin 白名单由 server.py 的外层中间件单独处理。
        enable_dns_rebinding_protection=False,
    ),
)
schedule_service = ScheduleApplicationService(file_storage=CosFileStorage())


def _service_result_dict(result) -> dict:
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }


@mcp.tool(name="get_splatoon3_schedule")
async def get_splatoon3_schedule(
    numbers: Annotated[
        list[int] | None,
        Field(
            description="Optional schedule indexes from 0 to 11. 0 is current and 1 is next. Omit to query index 0.",
            min_length=1,
        ),
    ] = None,
    contest: Annotated[
        str | None,
        Field(
            description="Optional battle queue type. Allowed values: 涂地, 挑战, 开放, X段. Omit to include all queue types.",
            json_schema_extra={"enum": list(CONTEST_VALUES)},
        ),
    ] = None,
    rule: Annotated[
        str | None,
        Field(
            description="Optional battle rule. Allowed values: 区域, 蛤蜊, 塔楼, 鱼虎. Omit to include all rules.",
            json_schema_extra={"enum": list(RULE_VALUES)},
        ),
    ] = None,
) -> dict:
    """Get the Splatoon 3 (喷三) battle schedule and its COS image URL. All parameters are optional; invalid input falls back to indexes 0 and 1."""
    query = normalize_schedule_query(numbers, contest, rule,
                                     contest_values=CONTEST_VALUES,
                                     rule_values=RULE_VALUES)
    result = await schedule_service.get_stages(
        context=RequestContext(
            request_id=str(uuid.uuid4()),
            provider="mcp",
        ),
        query=query,
        trigger_word="图",
        cache_key=build_schedule_cache_key("mcp", query),
    )
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }


async def _render_tool(operation: str, trigger: str, func, *args) -> dict:
    result = await schedule_service.get_rendered(RequestContext(request_id=str(uuid.uuid4()), provider="mcp"), operation, trigger, func, *args)
    return {"status": result.status, "message": result.message, "data": result.data,
            "image_url": result.image_url, "code": result.code, "warnings": result.warnings}


@mcp.tool(name="get_splatoon3_upcoming_special_events")
async def get_splatoon3_upcoming_special_events() -> dict:
    """Get special-event reminders for today and the next two days, including challenge events, Eggstra Work, Big Run, and golden random Salmon Run rotations. No parameters are required."""
    result = await schedule_service.get_upcoming_special_events(
        RequestContext(request_id=str(uuid.uuid4()), provider="mcp")
    )
    return _service_result_dict(result)


@mcp.tool(name="get_splatoon3_coop_schedule")
async def get_splatoon3_coop_schedule(
    all_schedules: Annotated[bool, Field(description="Whether to show all available Salmon Run rotations. When false, only the current rotation is shown. Default: false.")]=False,
) -> dict:
    """Get the Salmon Run (Co-op) schedule image."""
    return await _render_tool("coop_schedule", "mcp_coop_all" if all_schedules else "mcp_coop", get_coop_stages_image, all_schedules)


@mcp.tool(name="get_splatoon3_festival_schedule")
async def get_splatoon3_festival_schedule() -> dict:
    """Get an image of current and upcoming Splatfests. No parameters are required."""
    return await _render_tool("festival_schedule", "mcp_festival", get_festival_image)


@mcp.tool(name="get_splatoon3_event_schedule")
async def get_splatoon3_event_schedule() -> dict:
    """Get an image of current and upcoming challenge events. No parameters are required."""
    return await _render_tool("event_schedule", "mcp_events", get_events_image)


@mcp.tool(name="get_splatoon3_gear_shop")
async def get_splatoon3_gear_shop() -> dict:
    """Get an image of the current gear available in the Splatoon3.ink gear shop. No parameters are required."""
    result = await schedule_service.get_gear(
        RequestContext(request_id=str(uuid.uuid4()), provider="mcp")
    )
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }


@mcp.tool(name="get_splatoon3_random_weapons")
async def get_splatoon3_random_weapons(
    filters: Annotated[
        list[str] | None,
        Field(
            description="Optional constraints for the four weapon positions. Supply at most four entries; each may be a weapon class, sub weapon, special weapon, or common alias. Examples: ['小枪', '刷', '狙', '泡'] or ['nice弹']. Missing positions are filled using balanced random weapon classes.",
            max_length=4,
        ),
    ] = None,
    fully_random: Annotated[
        bool,
        Field(description="Whether to use unrestricted random selection instead of balanced weapon classes. When true, filters are ignored. Default: false."),
    ] = False,
) -> dict:
    """Generate a fresh random-weapon image for two private-battle teams."""
    result = await schedule_service.get_random_weapons(
        RequestContext(request_id=str(uuid.uuid4()), provider="mcp"),
        filters=filters,
        fully_random=fully_random,
    )
    return {
        "status": result.status,
        "message": result.message,
        "data": result.data,
        "image_url": result.image_url,
        "code": result.code,
        "warnings": result.warnings,
    }


@mcp.tool(name="get_splatoon3_weapon_build")
async def get_splatoon3_weapon_build(
    weapon: Annotated[str, Field(description="Weapon official name, Chinese name, English name, common alias, or sticker/variant name. Examples: '小绿' or '贴牌碳刷'.", min_length=1, max_length=40)],
    mode: Annotated[str, Field(description="Optional battle-mode filter for build recommendations. Supported: 涂地, 区域, 塔楼, 鱼虎, 蛤蜊, 全部.", json_schema_extra={"enum": ["涂地", "区域", "塔楼", "鱼虎", "蛤蜊", "全部"]})] = "全部",
) -> dict:
    """Get Sendou.ink build recommendations; ambiguous names return candidates."""
    result = await schedule_service.get_build(RequestContext(request_id=str(uuid.uuid4()), provider="mcp"), weapon, mode)
    return {"status": result.status, "message": result.message, "data": result.data,
            "image_url": result.image_url, "code": result.code, "warnings": result.warnings}
