"""Core Realignment V3 BALANCED — hits-first structural balance.

ADR-045: soft pool pre-filter + V1-adjacent compose thresholds.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lotoia.governance.lei15_15a_core_realignment_v3 import CoreRealignmentV3Config

logger = logging.getLogger(__name__)

_COMPOSE_POOL_CAP = 600


def _prefix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[:n])


def _suffix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[-n:])


def _format_prefix(p: tuple[int, ...]) -> str:
    return "-".join(f"{d:02d}" for d in p)


def _max_overlap(numbers: list[int], selected: list[dict]) -> int:
    num_set = set(numbers)
    return max((len(num_set & set(g["numbers"])) for g in selected), default=0)


def filter_pool_soft(
    pool: list[dict],
    *,
    config: "CoreRealignmentV3Config",
) -> tuple[list[dict], bool, bool]:
    """Soft cap per prefix_3. Skips filter (does not fallback) if pool too small."""
    if not pool:
        return pool, False, False

    total = len(pool)
    cap_per_prefix3 = max(2, int(total * config.max_pool_prefix3_ratio))

    groups: dict[tuple[int, ...], list[dict]] = {}
    for game in pool:
        key = _prefix(game["numbers"], 3)
        groups.setdefault(key, []).append(game)

    needs_filter = any(len(g) > cap_per_prefix3 for g in groups.values())
    if not needs_filter:
        return pool, True, False

    def _base_score(g: dict) -> float:
        return (
            float(g.get("profile_score", 0)) * 100.0
            + float(g.get("final_score", {}).get("final_score", 0))
        )

    filtered: list[dict] = []
    for group_games in groups.values():
        sorted_group = sorted(group_games, key=_base_score, reverse=True)
        filtered.extend(sorted_group[:cap_per_prefix3])

    if len(filtered) < config.min_pool_size_after_filter:
        logger.info(
            "[CoreRealignV3] soft pre-filter skipped: %d → %d (min=%d)",
            total, len(filtered), config.min_pool_size_after_filter,
        )
        return pool, True, False

    logger.info(
        "[CoreRealignV3] soft pre-filter: %d → %d (cap=%d, groups=%d)",
        total, len(filtered), cap_per_prefix3, len(groups),
    )
    return filtered, True, False


def _tag_v3_game(
    game: dict,
    *,
    config: "CoreRealignmentV3Config",
    pre_filter_applied: bool,
    completion_pass: bool = False,
) -> dict:
    numbers = game["numbers"]
    p3 = _prefix(numbers, 3)
    p4 = _prefix(numbers, 4)
    s3 = _suffix(numbers, 3)
    s4 = _suffix(numbers, 4)
    tagged = dict(game)
    existing_meta = dict(tagged.get("realignment_metadata") or {})
    existing_meta.update({
        "realignment_tag": config.realignment_tag,
        "evidence_epoch": config.evidence_epoch,
        "mode": config.mode,
        "v1_applied": True,
        "v2_applied": False,
        "v3_applied": True,
        "pool_pre_filter_applied": pre_filter_applied,
        "v3_fallback_to_v1": False,
        "v3_completion_pass": completion_pass,
        "prefix_3": _format_prefix(p3),
        "prefix_4": _format_prefix(p4),
        "suffix_3": _format_prefix(s3),
        "suffix_4": _format_prefix(s4),
    })
    tagged["realignment_metadata"] = existing_meta
    tagged["realignment_applied"] = True
    tagged["core_realignment_v3_applied"] = True
    return tagged


def compose_gp_v3(
    pool: list[dict],
    count: int,
    config: "CoreRealignmentV3Config",
    *,
    game_size: int = 15,
    pre_filter_applied: bool = False,
) -> tuple[list[dict], bool]:
    if count < 1 or not pool:
        return [], False

    if not pre_filter_applied:
        pool, pre_filter_applied, _ = filter_pool_soft(pool, config=config)

    def _concentration_penalty(count_struct: int, gp_size: int, max_ratio: float, weight: float) -> float:
        if gp_size < 1:
            return 0.0
        projected = (count_struct + 1) / (gp_size + 1)
        excess = max(0.0, projected - max_ratio)
        return round(excess * weight, 3)

    def _coverage_bonus(numbers: list[int]) -> float:
        present = sum(1 for d in config.target_coverage_digits if d in set(numbers))
        return round(min(present * config.coverage_bonus_per_digit, config.max_coverage_bonus), 3)

    def _overlap_penalty(numbers: list[int], selected: list[dict]) -> float:
        if not selected:
            return 0.0
        max_ov = _max_overlap(numbers, selected)
        allowed = max(0, game_size - config.overlap_slack)
        excess = max(0, max_ov - allowed)
        return round(excess * config.overlap_penalty_per_digit, 3)

    def _base_score(g: dict) -> float:
        return (
            float(g.get("profile_score", 0)) * 100.0
            + float(g.get("final_score", {}).get("final_score", 0))
        )

    effective_pool = sorted(pool, key=_base_score, reverse=True)
    if len(effective_pool) > _COMPOSE_POOL_CAP:
        effective_pool = effective_pool[:_COMPOSE_POOL_CAP]

    selected: list[dict] = []
    selected_keys: set[tuple[int, ...]] = set()
    prefix3_counts: Counter = Counter()
    prefix4_counts: Counter = Counter()
    suffix3_counts: Counter = Counter()
    suffix4_counts: Counter = Counter()
    remaining = list(effective_pool)

    while len(selected) < count and remaining:
        gp_size = len(selected)
        enforce = gp_size >= config.min_gp_for_concentration_check
        best_game: dict | None = None
        best_score = float("-inf")

        for game in remaining:
            numbers = game["numbers"]
            key = tuple(numbers)
            if key in selected_keys:
                continue
            p3 = _prefix(numbers, 3)
            p4 = _prefix(numbers, 4)
            s3 = _suffix(numbers, 3)
            s4 = _suffix(numbers, 4)
            total_penalty = 0.0
            if enforce:
                total_penalty += _concentration_penalty(
                    prefix3_counts[p3], gp_size, config.max_prefix3_ratio, config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    prefix4_counts[p4], gp_size, config.max_prefix4_ratio, config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    suffix3_counts[s3], gp_size, config.max_suffix3_ratio, config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    suffix4_counts[s4], gp_size, config.max_suffix4_ratio, config.concentration_penalty_weight,
                )
            bonus = _coverage_bonus(numbers)
            ov_pen = _overlap_penalty(numbers, selected)
            score = (bonus - total_penalty - ov_pen) + _base_score(game) * config.base_score_weight
            if score > best_score:
                best_score = score
                best_game = game

        if best_game is None:
            break

        numbers = best_game["numbers"]
        tagged = _tag_v3_game(best_game, config=config, pre_filter_applied=pre_filter_applied)
        selected.append(tagged)
        key = tuple(numbers)
        selected_keys.add(key)
        prefix3_counts[_prefix(numbers, 3)] += 1
        prefix4_counts[_prefix(numbers, 4)] += 1
        suffix3_counts[_suffix(numbers, 3)] += 1
        suffix4_counts[_suffix(numbers, 4)] += 1
        remaining = [g for g in remaining if tuple(g["numbers"]) not in selected_keys]

    if len(selected) < count:
        logger.warning(
            "[CoreRealignV3] greedy %d/%d — completion pass",
            len(selected), count,
        )
        for game in effective_pool:
            if len(selected) >= count:
                break
            key = tuple(game["numbers"])
            if key in selected_keys:
                continue
            selected.append(
                _tag_v3_game(game, config=config, pre_filter_applied=pre_filter_applied, completion_pass=True)
            )
            selected_keys.add(key)

    logger.info(
        "[CoreRealignV3] composed %d/%d (pool=%d, pre_filter=%s)",
        len(selected), count, len(pool), pre_filter_applied,
    )
    return selected, False
