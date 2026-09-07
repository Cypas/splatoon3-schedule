import uuid
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

from ...application import RequestContext, normalize_schedule_query, build_schedule_cache_key
from ...application.schedule_service import ScheduleApplicationService
from ...infrastructure.file_storage import CosFileStorage


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
