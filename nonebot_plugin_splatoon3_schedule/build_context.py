import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    from .utils.translation import dict_weapon_special, dict_weapon_sub
    from .weapon_matcher import WeaponCandidate, normalize_weapon_text
except ImportError:
    import ast

    source = (Path(__file__).resolve().parent / "utils" / "translation.py").read_text("utf-8")
    dictionaries = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"dict_weapon_special", "dict_weapon_sub"}:
                dictionaries[name] = ast.literal_eval(node.value)
    dict_weapon_special = dictionaries["dict_weapon_special"]
    dict_weapon_sub = dictionaries["dict_weapon_sub"]
    from weapon_matcher import WeaponCandidate, normalize_weapon_text


ContextKey = tuple[str, str, str, str]
ReplyStatus = Literal["selected", "ambiguous", "invalid", "exited", "expired", "failed", "missing"]
ENTITY_ALIASES: dict[str, set[str]] = {}
for synonyms in (dict_weapon_sub, dict_weapon_special):
    for synonym, canonical_name in synonyms.items():
        ENTITY_ALIASES.setdefault(normalize_weapon_text(synonym), set()).add(canonical_name)


@dataclass
class BuildQueryContext:
    candidates: tuple[WeaponCandidate, ...]
    mode: str | None
    started_at: float
    reply_count: int = 0


@dataclass(frozen=True)
class BuildContextReply:
    status: ReplyStatus
    build_id: int | None = None
    mode: str | None = None
    candidates: tuple[WeaponCandidate, ...] = field(default_factory=tuple)


def format_candidate_list(candidates: tuple[WeaponCandidate, ...]) -> str:
    return "\n".join(
        f"{index}. {candidate.zh_name}｜{candidate.sub_name}｜{candidate.special_name}"
        for index, candidate in enumerate(candidates, 1)
    )


def format_candidate_prompt(
    candidates: tuple[WeaponCandidate, ...], title: str, initial: bool = False
) -> str:
    time_text = "120 秒内" if initial else "原提示的 120 秒内"
    return (
        f"{title}\n{format_candidate_list(candidates)}\n"
        f"请在{time_text}回复编号、副武器、大招或“退出”。"
    )


class BuildContextStore:
    timeout_seconds = 120
    max_replies = 2

    def __init__(self):
        self._contexts: dict[ContextKey, BuildQueryContext] = {}

    def has(self, key: ContextKey) -> bool:
        return key in self._contexts

    def get(self, key: ContextKey) -> BuildQueryContext | None:
        return self._contexts.get(key)

    def clear(self, key: ContextKey) -> None:
        self._contexts.pop(key, None)

    def set(
        self,
        key: ContextKey,
        candidates: tuple[WeaponCandidate, ...],
        mode: str | None,
        now: float | None = None,
    ) -> BuildQueryContext:
        context = BuildQueryContext(candidates, mode, time.monotonic() if now is None else now)
        self._contexts[key] = context
        return context

    def reply(self, key: ContextKey, text: str, now: float | None = None) -> BuildContextReply:
        context = self._contexts.get(key)
        if context is None:
            return BuildContextReply("missing")
        current_time = time.monotonic() if now is None else now
        if current_time - context.started_at >= self.timeout_seconds:
            self.clear(key)
            return BuildContextReply("expired")
        normalized = normalize_weapon_text(text)
        if normalized == "退出":
            self.clear(key)
            return BuildContextReply("exited")
        context.reply_count += 1
        stripped = unicodedata.normalize("NFKC", text).strip()
        if re.fullmatch(r"[0-9]+", stripped):
            index = int(stripped) - 1
            if 0 <= index < len(context.candidates):
                candidate = context.candidates[index]
                self.clear(key)
                return BuildContextReply("selected", candidate.build_id, context.mode)
        else:
            canonical_names = ENTITY_ALIASES.get(normalized, set())
            filtered = tuple(
                candidate
                for candidate in context.candidates
                if candidate.sub_name in canonical_names or candidate.special_name in canonical_names
            )
            if len(filtered) == 1:
                self.clear(key)
                return BuildContextReply("selected", filtered[0].build_id, context.mode)
            if len(filtered) > 1:
                context.candidates = filtered
                if context.reply_count < self.max_replies:
                    return BuildContextReply("ambiguous", mode=context.mode, candidates=filtered)
        if context.reply_count >= self.max_replies:
            self.clear(key)
            return BuildContextReply("failed")
        return BuildContextReply("invalid", mode=context.mode, candidates=context.candidates)


build_context_store = BuildContextStore()
