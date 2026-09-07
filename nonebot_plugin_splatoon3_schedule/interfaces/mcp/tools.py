import uuid
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from ...application import RequestContext, normalize_schedule_query, build_schedule_cache_key
from ...application.schedule_service import ScheduleApplicationService
from ...infrastructure.file_storage import CosFileStorage
from ...image.image import get_coop_stages_image, get_festival_image, get_events_image


CONTEST_VALUES = ("涂地", "挑战", "开放", "X段")
RULE_VALUES = ("区域", "蛤蜊", "塔楼", "鱼虎")


mcp = FastMCP(
    "splatoon3-schedule",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["xyy2.ayano.top", "xyy2.ayano.top:*"],
        allowed_origins=["https://xyy2.ayano.top"],
    ),
)
schedule_service = ScheduleApplicationService(file_storage=CosFileStorage())


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


@mcp.tool(name="get_splatoon3_coop_schedule")
async def get_splatoon3_coop_schedule(
    all_schedules: Annotated[bool, Field(description="Show all Salmon Run rotations. Corresponds to NoneBot '/打工' (false) or '/全部打工' (true). Default: false.")]=False,
) -> dict:
    """Get the Salmon Run (Co-op) schedule image."""
    return await _render_tool("coop_schedule", "mcp_coop_all" if all_schedules else "mcp_coop", get_coop_stages_image, all_schedules)


@mcp.tool(name="get_splatoon3_festival_schedule")
async def get_splatoon3_festival_schedule() -> dict:
    """Get current and upcoming Splatfests; corresponds to NoneBot '/祭典' and takes no parameters."""
    return await _render_tool("festival_schedule", "mcp_festival", get_festival_image)


@mcp.tool(name="get_splatoon3_event_schedule")
async def get_splatoon3_event_schedule() -> dict:
    """Get current and upcoming challenge events; corresponds to NoneBot '/活动' and takes no parameters."""
    return await _render_tool("event_schedule", "mcp_events", get_events_image)


@mcp.tool(name="get_splatoon3_weapon_build")
async def get_splatoon3_weapon_build(
    weapon: Annotated[str, Field(description="Weapon official name, Chinese name, English name, alias, or sticker/variant name. Same matching rules as NoneBot '/配装 <weapon>'; examples: '/配装 小绿' and '/配装 贴牌碳刷 塔楼'.", min_length=1, max_length=40)],
    mode: Annotated[str, Field(description="Optional mode suffix from NoneBot '/配装 <weapon> <mode>'. Supported: 涂地, 区域, 塔楼, 鱼虎, 蛤蜊, 全部.", json_schema_extra={"enum": ["涂地", "区域", "塔楼", "鱼虎", "蛤蜊", "全部"]})] = "全部",
) -> dict:
    """Get Sendou.ink build recommendations; ambiguous names return candidates."""
    result = await schedule_service.get_build(RequestContext(request_id=str(uuid.uuid4()), provider="mcp"), weapon, mode)
    return {"status": result.status, "message": result.message, "data": result.data,
            "image_url": result.image_url, "code": result.code, "warnings": result.warnings}
