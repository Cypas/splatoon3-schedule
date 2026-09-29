from dataclasses import dataclass
from collections.abc import Sequence

CONTEST_VALUES = ("涂地", "挑战", "开放", "X段")
RULE_VALUES = ("区域", "蛤蜊", "塔楼", "鱼虎")


@dataclass(frozen=True)
class ScheduleQuery:
    numbers: tuple[int, ...] = (0,)
    contest: str | None = None
    rule: str | None = None


def normalize_schedule_query(
    numbers: Sequence[int] | None = None,
    contest: str | None = None,
    rule: str | None = None,
    *,
    contest_values: Sequence[str] = (),
    rule_values: Sequence[str] = (),
) -> ScheduleQuery:
    """Normalize public-entry parameters using the MCP/REST shared contract."""
    nums = tuple(numbers) if numbers is not None else (0,)
    valid = bool(nums) and all(isinstance(n, int) and 0 <= n <= 11 for n in nums)
    valid = valid and (contest is None or not contest_values or contest in contest_values)
    valid = valid and (rule is None or not rule_values or rule in rule_values)
    if not valid:
        return ScheduleQuery((0, 1), None, None)
    return ScheduleQuery(nums, contest, rule)


def build_schedule_cache_key(provider: str, query: ScheduleQuery) -> str:
    """Build a platform-neutral, human-readable image cache key.

    MCP-generated images use an explicit prefix so cache entries can be traced
    back to the tool interface while retaining their business meaning.
    """
    numbers = "".join(str(number) for number in query.numbers)
    prefix = "mcp_" if provider == "mcp" else ""
    return f"{prefix}{numbers}{query.contest or ''}{query.rule or ''}图"
