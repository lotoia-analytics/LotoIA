"""Core Realignment V2 — Two-layer GP structural diversity enforcement.

Layer 1: Pool Pre-Filter
  Caps the number of candidates per prefix_3 before greedy composition so
  the algorithm has materially diverse candidates even when profiles Recurrent
  and Hybrid produce a biased pool from the last draw.

Layer 2: Tighter Greedy Composition
  Reuses compose_diverse_gp from V1 but with tighter thresholds from
  CoreRealignmentV2Config (max_prefix3_ratio=0.15, etc.).

ADM Authorization: ADR-044 / MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lotoia.governance.lei15_15a_core_realignment_v2 import CoreRealignmentV2Config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prefix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[:n])


def _suffix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[-n:])


def _format_prefix(p: tuple[int, ...]) -> str:
    return "-".join(f"{d:02d}" for d in p)


def _max_overlap(numbers: list[int], selected: list[dict]) -> int:
    num_set = set(numbers)
    return max((len(num_set & set(g["numbers"])) for g in selected), default=0)


# ---------------------------------------------------------------------------
# Layer 1 — Pool Pre-Filter
# ---------------------------------------------------------------------------

def filter_pool_for_prefix_diversity(
    pool: list[dict],
    *,
    config: "CoreRealignmentV2Config",
) -> tuple[list[dict], bool, bool]:
    """Cap candidates per prefix_3 so the pool is prefix-diverse.

    Returns (pool, pre_filter_applied, fallback_to_v1).

    pre_filter_applied=False and fallback_to_v1=False  → pool unchanged, proceed V2.
    pre_filter_applied=True  and fallback_to_v1=False  → filtered pool, proceed V2.
    pre_filter_applied=False and fallback_to_v1=True   → pool unchanged, caller MUST
        use V1 compose_diverse_gp (ADR-044 safety rule).
    """
    if not pool:
        return pool, False, False

    total = len(pool)
    cap_per_prefix3 = max(1, int(total * config.max_pool_prefix3_ratio))

    # Group by prefix_3
    groups: dict[tuple[int, ...], list[dict]] = {}
    for game in pool:
        key = _prefix(game["numbers"], 3)
        groups.setdefault(key, []).append(game)

    # Check whether any group exceeds the cap
    needs_filter = any(len(g) > cap_per_prefix3 for g in groups.values())
    if not needs_filter:
        return pool, True, False

    # Apply cap: keep top-N by base_score within each group
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
        logger.warning(
            "[CoreRealignV2] pool pós-filtro %d → %d abaixo do mínimo=%d — "
            "fallback obrigatório para V1",
            total, len(filtered), config.min_pool_size_after_filter,
        )
        return pool, False, True

    logger.info(
        "[CoreRealignV2] pool pre-filter: %d → %d candidates "
        "(cap_per_prefix3=%d, groups=%d)",
        total, len(filtered), cap_per_prefix3, len(groups),
    )
    return filtered, True, False


# ---------------------------------------------------------------------------
# Layer 2 — Greedy GP composition (reuses V1 algo, V2 config)
# ---------------------------------------------------------------------------

_COMPOSE_POOL_CAP_V2 = 600  # max candidates evaluated in each greedy step


def compose_gp_v2(
    pool: list[dict],
    count: int,
    config: "CoreRealignmentV2Config",
    *,
    game_size: int = 15,
    pre_filter_applied: bool = False,
) -> tuple[list[dict], bool]:
    """Two-layer greedy GP composition.

    Returns (selected_games, fallback_to_v1).
    When fallback_to_v1=True, selected_games is empty and caller MUST use V1.
    """
    if count < 1 or not pool:
        return [], False

    # Layer 1 — apply pool pre-filter if not already done
    fallback_to_v1 = False
    if not pre_filter_applied:
        pool, pre_filter_applied, fallback_to_v1 = filter_pool_for_prefix_diversity(pool, config=config)
        if fallback_to_v1:
            return [], True

    # Scoring helpers
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

    # Cap pool to _COMPOSE_POOL_CAP_V2 keeping top-scoring candidates
    effective_pool = sorted(pool, key=_base_score, reverse=True)
    if len(effective_pool) > _COMPOSE_POOL_CAP_V2:
        effective_pool = effective_pool[:_COMPOSE_POOL_CAP_V2]

    selected: list[dict] = []
    selected_keys: set[tuple[int, ...]] = set()
    prefix3_counts: Counter = Counter()
    prefix4_counts: Counter = Counter()
    suffix3_counts: Counter = Counter()
    suffix4_counts: Counter = Counter()

    remaining = [g for g in effective_pool if g]

    while len(selected) < count and remaining:
        gp_size = len(selected)
        enforce_concentration = gp_size >= config.min_gp_for_concentration_check

        best_game: dict | None = None
        best_score = float("-inf")

        for game in remaining:
            numbers = game["numbers"]
            key = tuple(numbers)
            if key in selected_keys:
                continue

            # Layer 2 — structural penalty/bonus
            p3 = _prefix(numbers, 3)
            p4 = _prefix(numbers, 4)
            s3 = _suffix(numbers, 3)
            s4 = _suffix(numbers, 4)

            total_penalty = 0.0
            if enforce_concentration:
                total_penalty += _concentration_penalty(prefix3_counts[p3], gp_size, config.max_prefix3_ratio, config.concentration_penalty_weight)
                total_penalty += _concentration_penalty(prefix4_counts[p4], gp_size, config.max_prefix4_ratio, config.concentration_penalty_weight)
                total_penalty += _concentration_penalty(suffix3_counts[s3], gp_size, config.max_suffix3_ratio, config.concentration_penalty_weight)
                total_penalty += _concentration_penalty(suffix4_counts[s4], gp_size, config.max_suffix4_ratio, config.concentration_penalty_weight)

            bonus = _coverage_bonus(numbers)
            ov_pen = _overlap_penalty(numbers, selected)
            net_delta = bonus - total_penalty - ov_pen

            # Combined score: structural diversity delta + base score (scaled down)
            score = net_delta + _base_score(game) * 0.001

            if score > best_score:
                best_score = score
                best_game = game

        if best_game is None:
            break

        numbers = best_game["numbers"]
        p3 = _prefix(numbers, 3)
        p4 = _prefix(numbers, 4)
        s3 = _suffix(numbers, 3)
        s4 = _suffix(numbers, 4)

        # Tag the game with V2 metadata
        tagged = dict(best_game)
        existing_meta = dict(tagged.get("realignment_metadata") or {})
        existing_meta.update({
            "realignment_tag": config.realignment_tag,
            "evidence_epoch": config.evidence_epoch,
            "mode": config.mode,
            "v1_applied": True,
            "v2_applied": True,
            "pool_pre_filter_applied": pre_filter_applied,
            "v2_fallback_to_v1": False,
            "prefix_3": _format_prefix(p3),
            "prefix_4": _format_prefix(p4),
            "suffix_3": _format_prefix(s3),
            "suffix_4": _format_prefix(s4),
        })
        tagged["realignment_metadata"] = existing_meta
        tagged["realignment_applied"] = True
        tagged["core_realignment_v2_applied"] = True

        selected.append(tagged)
        selected_keys.add(tuple(numbers))
        prefix3_counts[p3] += 1
        prefix4_counts[p4] += 1
        suffix3_counts[s3] += 1
        suffix4_counts[s4] += 1

        remaining = [g for g in remaining if tuple(g["numbers"]) not in selected_keys]

    if len(selected) < count:
        logger.warning(
            "[CoreRealignV2] greedy pass %d/%d — completion pass (sem penalidade estrutural)",
            len(selected), count,
        )
        for game in effective_pool:
            if len(selected) >= count:
                break
            numbers = game["numbers"]
            key = tuple(numbers)
            if key in selected_keys:
                continue
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
                "v2_applied": True,
                "pool_pre_filter_applied": pre_filter_applied,
                "v2_fallback_to_v1": False,
                "v2_completion_pass": True,
                "prefix_3": _format_prefix(p3),
                "prefix_4": _format_prefix(p4),
                "suffix_3": _format_prefix(s3),
                "suffix_4": _format_prefix(s4),
            })
            tagged["realignment_metadata"] = existing_meta
            tagged["realignment_applied"] = True
            tagged["core_realignment_v2_applied"] = True
            selected.append(tagged)
            selected_keys.add(key)
            prefix3_counts[p3] += 1
            prefix4_counts[p4] += 1
            suffix3_counts[s3] += 1
            suffix4_counts[s4] += 1

    logger.info(
        "[CoreRealignV2] composed %d / %d games (pool=%d, pre_filter=%s)",
        len(selected), count, len(pool), pre_filter_applied,
    )
    return selected, False


# ---------------------------------------------------------------------------
# Pool tagging (shadow_test mode metadata)
# ---------------------------------------------------------------------------

def apply_v2_pool_tagging(
    games: list[dict],
    config: "CoreRealignmentV2Config",
    *,
    game_size: int = 15,
) -> list[dict]:
    """Tag pool games with V2 metadata without altering selection.

    Used in shadow_test mode before compose_gp_v2 to annotate all candidates.
    """
    if not games:
        return games

    annotated = []
    for game in games:
        enriched = dict(game)
        numbers = enriched.get("numbers") or []
        p3 = _prefix(numbers, 3)
        p4 = _prefix(numbers, 4)
        s3 = _suffix(numbers, 3)
        s4 = _suffix(numbers, 4)
        coverage = sum(1 for d in config.target_coverage_digits if d in set(numbers))
        existing_meta = dict(enriched.get("realignment_metadata") or {})
        existing_meta.update({
            "realignment_tag": config.realignment_tag,
            "evidence_epoch": config.evidence_epoch,
            "mode": config.mode,
            "v2_applied": False,
            "pool_pre_filter_applied": False,
            "prefix_3": _format_prefix(p3),
            "prefix_4": _format_prefix(p4),
            "suffix_3": _format_prefix(s3),
            "suffix_4": _format_prefix(s4),
            "coverage_digits_present": coverage,
            "target_coverage_digits": list(config.target_coverage_digits),
        })
        enriched["realignment_metadata"] = existing_meta
        annotated.append(enriched)
    return annotated


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_v2_gp_metrics(selected: list[dict]) -> dict:
    """Compute V2 structural metrics for the composed GP."""
    if not selected:
        return {}

    prefix3_counter: Counter = Counter()
    suffix3_counter: Counter = Counter()
    prefix4_counter: Counter = Counter()
    suffix4_counter: Counter = Counter()
    v2_applied_count = 0
    pre_filter_count = 0

    for game in selected:
        nums = game["numbers"]
        prefix3_counter[_format_prefix(_prefix(nums, 3))] += 1
        suffix3_counter[_format_prefix(_suffix(nums, 3))] += 1
        prefix4_counter[_format_prefix(_prefix(nums, 4))] += 1
        suffix4_counter[_format_prefix(_suffix(nums, 4))] += 1
        meta = game.get("realignment_metadata") or {}
        if meta.get("v2_applied"):
            v2_applied_count += 1
        if meta.get("pool_pre_filter_applied"):
            pre_filter_count += 1

    gp_size = len(selected)
    return {
        "gp_size": gp_size,
        "top_prefix3": prefix3_counter.most_common(3),
        "top_suffix3": suffix3_counter.most_common(3),
        "top_prefix4": prefix4_counter.most_common(3),
        "top_suffix4": suffix4_counter.most_common(3),
        "v2_applied_count": v2_applied_count,
        "pre_filter_applied_count": pre_filter_count,
        "unique_prefix3": len(prefix3_counter),
        "unique_suffix3": len(suffix3_counter),
        "top_prefix3_ratio": prefix3_counter.most_common(1)[0][1] / gp_size if prefix3_counter else 0.0,
        "top_suffix3_ratio": suffix3_counter.most_common(1)[0][1] / gp_size if suffix3_counter else 0.0,
    }
