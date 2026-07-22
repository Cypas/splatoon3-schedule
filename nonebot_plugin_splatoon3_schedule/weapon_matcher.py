import atexit
import asyncio
import sqlite3
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein
from zhconv import convert

try:
    from .utils.translation import dict_weapon_class, dict_weapon_special, dict_weapon_sub
except ImportError:
    import ast

    source = (Path(__file__).resolve().parent / "utils" / "translation.py").read_text("utf-8")
    dictionaries = {}
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"dict_weapon_class", "dict_weapon_special", "dict_weapon_sub"}:
                dictionaries[name] = ast.literal_eval(node.value)
    dict_weapon_class = dictionaries["dict_weapon_class"]
    dict_weapon_special = dictionaries["dict_weapon_special"]
    dict_weapon_sub = dictionaries["dict_weapon_sub"]

try:
    from nonebot import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


MatchStatus = Literal["matched", "ambiguous", "conflict", "not_found"]
RESOURCE_DIR = Path(__file__).resolve().parent / "resource"
DEFAULT_DB_PATH = RESOURCE_DIR / "db" / "image.db"
DEFAULT_MODEL_DIR = RESOURCE_DIR / "weapon_match" / "model"
DEFAULT_QDRANT_DIR = RESOURCE_DIR / "weapon_match" / "qdrant"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
COLLECTION_NAME = "splatoon3_weapons"
EXTRA_ALIASES = {
    "mint-decavitator": ("牙膏", "牙膏刀", "白牙膏"),
    "charcoal-decavitator": ("牙膏", "牙膏刀", "黑牙膏"),
}


@dataclass(frozen=True)
class WeaponCandidate:
    build_id: int
    zh_name: str
    sendou_name: str
    sub_name: str
    special_name: str
    group_id: int
    tag: int
    score: float = 0.0
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    entity_score: float = 0.0


@dataclass(frozen=True)
class MatchResult:
    status: MatchStatus
    query: str
    normalized_query: str
    matched: WeaponCandidate | None = None
    candidates: tuple[WeaponCandidate, ...] = field(default_factory=tuple)
    requested_tag: int | None = None


def normalize_weapon_text(text: str) -> str:
    text = convert(unicodedata.normalize("NFKC", text), "zh-cn").casefold()
    return "".join(char for char in text if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def _parse_query(query: str) -> tuple[str, int | None]:
    query = convert(unicodedata.normalize("NFKC", query), "zh-cn")
    requested_tag = None
    for marker, tag in (("新贴牌", 2), ("彩牌", 2), ("贴牌", 1), ("原版", 0), ("无印", 0)):
        if marker in query:
            if requested_tag is not None and requested_tag != tag:
                return normalize_weapon_text(query), -1
            requested_tag = tag
            query = query.replace(marker, "")
    return normalize_weapon_text(query), requested_tag


def _candidate(row: dict, **scores: float) -> WeaponCandidate:
    return WeaponCandidate(
        build_id=row["build_id"],
        zh_name=row["zh_name"],
        sendou_name=row["sendou_name"],
        sub_name=row["sub_name"],
        special_name=row["special_name"],
        group_id=row["group_id"],
        tag=row["tag"],
        **scores,
    )


class WeaponMatcher:
    _executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="weapon-match")
    _semantic_lock = threading.Lock()
    _model = None
    _qdrant = None
    _semantic_failed = False

    def __init__(
        self,
        db_path: Path | str = DEFAULT_DB_PATH,
        model_dir: Path | str = DEFAULT_MODEL_DIR,
        qdrant_dir: Path | str = DEFAULT_QDRANT_DIR,
    ):
        self.db_path = Path(db_path)
        self.model_dir = Path(model_dir)
        self.qdrant_dir = Path(qdrant_dir)
        self._catalog_lock = threading.Lock()
        self._aliases = None
        self._alias_map = None
        self._entities = None

    def _load_catalog(self) -> tuple[list[dict], dict[str, list[dict]], list[dict]]:
        if self._aliases is not None:
            return self._aliases, self._alias_map, self._entities
        with self._catalog_lock:
            if self._aliases is not None:
                return self._aliases, self._alias_map, self._entities
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT b.id build_id, b.zh_name, b.keywords, b.sendou_name,
                       b.group_id, b.is_deco tag, w.zh_sub_name sub_name,
                       w.zh_special_name special_name, w.zh_weapon_class weapon_class
                FROM BUILDS b
                JOIN WEAPON_INFO w
                  ON REPLACE(b.zh_name, ' ', '') = REPLACE(w.zh_name, ' ', '')
                ORDER BY b.id
                """
            ).fetchall()
            build_count = conn.execute("SELECT COUNT(*) FROM BUILDS").fetchone()[0]
            conn.close()
            if len(rows) != build_count:
                raise ValueError(f"BUILDS 与 WEAPON_INFO 未完整关联: {len(rows)}/{build_count}")
            aliases = []
            alias_map: dict[str, list[dict]] = {}
            for source in rows:
                base = dict(source)
                raw_aliases = [value for value in (source["keywords"] or "").split("|") if value]
                raw_aliases.extend((source["zh_name"], *EXTRA_ALIASES.get(source["sendou_name"], ())))
                seen = set()
                for alias in raw_aliases:
                    normalized = normalize_weapon_text(alias)
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    row = {**base, "alias": alias, "normalized_alias": normalized}
                    aliases.append(row)
                    alias_map.setdefault(normalized, []).append(row)
            entities = []
            for entity_type, synonyms in (
                ("sub", dict_weapon_sub),
                ("special", dict_weapon_special),
                ("class", dict_weapon_class),
            ):
                for synonym, canonical in synonyms.items():
                    entities.append(
                        {
                            "entity_type": entity_type,
                            "canonical_name": canonical,
                            "normalized_synonym": normalize_weapon_text(synonym),
                        }
                    )
            self._aliases, self._alias_map, self._entities = aliases, alias_map, entities
            return aliases, alias_map, entities

    def _exact(self, query: str, normalized: str, requested_tag: int | None) -> MatchResult | None:
        if requested_tag == -1:
            return MatchResult("conflict", query, normalized, requested_tag=requested_tag)
        try:
            rows = self._load_catalog()[1].get(normalized, [])
        except (sqlite3.Error, ValueError) as exc:
            logger.warning(f"武器数据不可用，无法执行本地匹配: {exc}")
            return MatchResult("not_found", query, normalized, requested_tag=requested_tag)
        if not rows:
            return None
        candidates = tuple(_candidate(row, score=1.0, lexical_score=1.0) for row in rows)
        if requested_tag is not None:
            tagged = [candidate for candidate in candidates if candidate.tag == requested_tag]
            if len(tagged) == 1:
                return MatchResult("matched", query, normalized, tagged[0], candidates, requested_tag)
            return MatchResult("conflict", query, normalized, candidates=candidates[:3], requested_tag=requested_tag)
        if len({candidate.group_id for candidate in candidates}) > 1:
            return MatchResult("conflict", query, normalized, candidates=candidates[:3])
        matched = next((candidate for candidate in candidates if candidate.tag == 0), candidates[0])
        return MatchResult("matched", query, normalized, matched, candidates)

    def _semantic_scores(self, query: str) -> dict[int, float]:
        if WeaponMatcher._semantic_failed:
            return {}
        with WeaponMatcher._semantic_lock:
            try:
                if WeaponMatcher._model is None or WeaponMatcher._qdrant is None:
                    if not self.qdrant_dir.exists() or not self.model_dir.exists():
                        raise FileNotFoundError("本地模型或 Qdrant 索引不存在")
                    from fastembed import TextEmbedding
                    from qdrant_client import QdrantClient

                    WeaponMatcher._model = TextEmbedding(
                        model_name=MODEL_NAME,
                        specific_model_path=str(self.model_dir),
                        local_files_only=True,
                        threads=2,
                    )
                    WeaponMatcher._qdrant = QdrantClient(path=str(self.qdrant_dir))
                vector = next(WeaponMatcher._model.query_embed([query])).tolist()
                points = WeaponMatcher._qdrant.query_points(
                    collection_name=COLLECTION_NAME,
                    query=vector,
                    limit=8,
                    with_payload=True,
                ).points
                return {int(point.payload["build_id"]): float(point.score) for point in points}
            except Exception as exc:
                WeaponMatcher._semantic_failed = True
                logger.warning(f"武器语义索引不可用，已降级为词面匹配: {exc}")
                return {}

    def _non_exact(self, query: str, normalized: str, requested_tag: int | None) -> MatchResult:
        try:
            aliases, _, entity_rows = self._load_catalog()
        except (sqlite3.Error, ValueError) as exc:
            logger.warning(f"武器匹配数据不可用: {exc}")
            return MatchResult("not_found", query, normalized, requested_tag=requested_tag)
        detected: dict[str, set[str]] = {}
        for row in entity_rows:
            synonym = row["normalized_synonym"]
            if len(synonym) >= 2 and synonym in normalized:
                detected.setdefault(row["entity_type"], set()).add(row["canonical_name"])
        rows_by_build: dict[int, dict] = {}
        lexical: dict[int, float] = {}
        typo = set()
        for row in aliases:
            alias = row["normalized_alias"]
            ratio = fuzz.ratio(normalized, alias) / 100
            partial = fuzz.partial_ratio(normalized, alias) / 100
            if len(alias) <= 2 and len(normalized) > len(alias) and not detected:
                partial = min(partial, 0.55)
            score = max(ratio, partial * 0.96)
            distance = Levenshtein.distance(normalized, alias, score_cutoff=2)
            if min(len(normalized), len(alias)) >= 3 and distance == 1:
                score = max(score, 0.92)
                typo.add(row["build_id"])
            build_id = row["build_id"]
            rows_by_build[build_id] = row
            lexical[build_id] = max(lexical.get(build_id, 0.0), score)
        semantic = self._semantic_scores(query)
        ranked = []
        for build_id, row in rows_by_build.items():
            entity_matches = 0
            for entity_type, names in detected.items():
                field_name = {"sub": "sub_name", "special": "special_name", "class": "weapon_class"}[entity_type]
                if row[field_name] in names:
                    entity_matches += 1
            entity_score = entity_matches / len(detected) if detected else 0.0
            lexical_score = lexical[build_id]
            semantic_score = semantic.get(build_id, 0.0)
            score = (
                lexical_score * 0.68 + semantic_score * 0.22 + entity_score * 0.1
                if semantic
                else lexical_score * 0.82 + entity_score * 0.18
            )
            if requested_tag is not None and row["tag"] == requested_tag:
                score += 0.025
            ranked.append(
                _candidate(
                    row,
                    score=min(score, 1.0),
                    lexical_score=lexical_score,
                    semantic_score=semantic_score,
                    entity_score=entity_score,
                )
            )
        ranked.sort(key=lambda candidate: (-candidate.score, candidate.build_id))
        if not ranked or ranked[0].score < 0.45:
            return MatchResult("not_found", query, normalized, candidates=tuple(ranked[:3]), requested_tag=requested_tag)
        group_scores = {}
        group_members = {}
        for candidate in ranked:
            group_scores[candidate.group_id] = max(group_scores.get(candidate.group_id, 0.0), candidate.score)
            group_members.setdefault(candidate.group_id, []).append(candidate)
        ordered_groups = sorted(group_scores, key=lambda group_id: (-group_scores[group_id], group_id))
        members = group_members[ordered_groups[0]]
        best = members[0]
        if requested_tag is not None:
            tagged = next((candidate for candidate in members if candidate.tag == requested_tag), None)
            if tagged is None or best.lexical_score - tagged.lexical_score >= 0.12:
                return MatchResult("conflict", query, normalized, candidates=tuple(ranked[:3]), requested_tag=requested_tag)
            best = tagged
        else:
            original = next((candidate for candidate in members if candidate.tag == 0), None)
            if original and best.score - original.score < 0.04:
                best = original
        gap = best.score - group_scores[ordered_groups[1]] if len(ordered_groups) > 1 else best.score
        evidence = (
            best.lexical_score >= 0.72
            or best.build_id in typo
            or best.entity_score == 1.0 and best.semantic_score >= 0.7
            or best.semantic_score >= 0.88
        )
        threshold = 0.72 if best.build_id in typo else 0.78
        if len(normalized) > 2 and best.score >= threshold and gap >= 0.055 and evidence:
            return MatchResult("matched", query, normalized, best, tuple(ranked[:3]), requested_tag)
        return MatchResult("ambiguous", query, normalized, candidates=tuple(ranked[:3]), requested_tag=requested_tag)

    def match_weapon(self, query: str) -> MatchResult:
        normalized, requested_tag = _parse_query(query)
        if not normalized:
            return MatchResult("not_found", query, normalized, requested_tag=requested_tag)
        exact = self._exact(query, normalized, requested_tag)
        return exact if exact is not None else self._non_exact(query, normalized, requested_tag)

    async def match_weapon_async(self, query: str) -> MatchResult:
        normalized, requested_tag = _parse_query(query)
        if not normalized:
            return MatchResult("not_found", query, normalized, requested_tag=requested_tag)
        exact = self._exact(query, normalized, requested_tag)
        if exact is not None:
            return exact
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._non_exact, query, normalized, requested_tag)


weapon_matcher = WeaponMatcher()


def match_weapon(query: str) -> MatchResult:
    return weapon_matcher.match_weapon(query)


async def match_weapon_async(query: str) -> MatchResult:
    return await weapon_matcher.match_weapon_async(query)


def close_weapon_matcher() -> None:
    with WeaponMatcher._semantic_lock:
        if WeaponMatcher._qdrant is not None:
            WeaponMatcher._qdrant.close()
        WeaponMatcher._qdrant = None
        WeaponMatcher._model = None


atexit.register(close_weapon_matcher)
