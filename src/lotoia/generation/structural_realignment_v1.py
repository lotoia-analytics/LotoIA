"""Structural Realignment V1 — GP-level diversity enforcement.

PURPOSE
-------
Reduce structural bias detected in EPOCH_001:
  - Over-concentration of prefix_3 01-02-03 (50–63 % of GP games)
  - Over-concentration of suffix_3 22-24-25 (53–66 % of GP games)
  - Recurrently missing digits: 16, 06, 17, 23, 20, 08, 10, 04
  - GP redundancy (mean similarity 0.80–0.84)

CONSTRAINTS (immutable)
-----------------------
  - Does NOT modify game.numbers — Law 15 is untouched.
  - Does NOT replace structural-statistical analysis.
  - Does NOT produce games without full traceability.
  - All scoring is additive / advisory; never a hard block.
  - Shadow mode: enriches metadata without changing selection.

INTEGRATION
-----------
  Called from lotoia.generator.basic_generator.generate_best_games
  when LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1 != "off".
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lotoia.governance.law15_structural_realignment_v1 import StructuralRealignmentConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structural helpers
# ---------------------------------------------------------------------------

def _prefix(numbers: list[int], n: int) -> tuple[int, ...]:
    sorted_nums = sorted(numbers)
    return tuple(sorted_nums[:n])


def _suffix(numbers: list[int], n: int) -> tuple[int, ...]:
    sorted_nums = sorted(numbers)
    return tuple(sorted_nums[-n:])


def _format_prefix(nums: tuple[int, ...]) -> str:
    return "-".join(f"{x:02d}" for x in nums)


def _max_overlap(numbers: list[int], selected: list[dict]) -> int:
    num_set = set(numbers)
    return max((len(num_set & set(g["numbers"])) for g in selected), default=0)


# ---------------------------------------------------------------------------
# Per-game scoring
# ---------------------------------------------------------------------------

def _concentration_penalty(
    count: int,
    gp_size: int,
    max_ratio: float,
    weight: float,
) -> float:
    """Penalty when this game would push a structure above max_ratio."""
    if gp_size < 1:
        return 0.0
    projected_ratio = (count + 1) / (gp_size + 1)
    excess = max(0.0, projected_ratio - max_ratio)
    return round(excess * weight, 3)


def _coverage_bonus(
    numbers: list[int],
    target_digits: tuple[int, ...],
    bonus_per_digit: float,
    max_bonus: float,
) -> float:
    num_set = set(numbers)
    present = sum(1 for d in target_digits if d in num_set)
    return round(min(present * bonus_per_digit, max_bonus), 3)


def _overlap_penalty(
    numbers: list[int],
    selected: list[dict],
    game_size: int,
    overlap_slack: int,
    penalty_per_digit: float,
) -> float:
    """Penalty for near-duplicate games already in the GP."""
    if not selected:
        return 0.0
    max_ov = _max_overlap(numbers, selected)
    allowed = max(0, game_size - overlap_slack)
    excess = max(0, max_ov - allowed)
    return round(excess * penalty_per_digit, 3)


def score_for_gp_diversity(
    game: dict,
    selected: list[dict],
    *,
    prefix3_counts: Counter,
    prefix4_counts: Counter,
    suffix3_counts: Counter,
    suffix4_counts: Counter,
    gp_target_size: int,
    config: "StructuralRealignmentConfig",
    game_size: int = 15,
) -> dict:
    """Compute structural diversity contribution for one candidate game.

    Returns a dict with penalty/bonus breakdown — does NOT mutate game.
    """
    numbers = game["numbers"]
    current_gp_size = len(selected)

    p3 = _prefix(numbers, 3)
    p4 = _prefix(numbers, 4)
    s3 = _suffix(numbers, 3)
    s4 = _suffix(numbers, 4)

    penalty_p3 = _concentration_penalty(
        prefix3_counts[p3], current_gp_size,
        config.max_prefix3_ratio, config.concentration_penalty_weight,
    )
    penalty_p4 = _concentration_penalty(
        prefix4_counts[p4], current_gp_size,
        config.max_prefix4_ratio, config.concentration_penalty_weight,
    )
    penalty_s3 = _concentration_penalty(
        suffix3_counts[s3], current_gp_size,
        config.max_suffix3_ratio, config.concentration_penalty_weight,
    )
    penalty_s4 = _concentration_penalty(
        suffix4_counts[s4], current_gp_size,
        config.max_suffix4_ratio, config.concentration_penalty_weight,
    )

    bonus = _coverage_bonus(
        numbers,
        config.target_coverage_digits,
        config.coverage_bonus_per_digit,
        config.max_coverage_bonus,
    )

    ov_penalty = _overlap_penalty(
        numbers, selected, game_size,
        config.overlap_slack, config.overlap_penalty_per_digit,
    )

    total_penalty = penalty_p3 + penalty_p4 + penalty_s3 + penalty_s4 + ov_penalty
    net_delta = round(bonus - total_penalty, 3)

    return {
        "realignment_tag": config.realignment_tag,
        "evidence_epoch": config.evidence_epoch,
        "prefix_3": _format_prefix(p3),
        "prefix_4": _format_prefix(p4),
        "suffix_3": _format_prefix(s3),
        "suffix_4": _format_prefix(s4),
        "penalty_prefix3": penalty_p3,
        "penalty_prefix4": penalty_p4,
        "penalty_suffix3": penalty_s3,
        "penalty_suffix4": penalty_s4,
        "bonus_coverage": bonus,
        "penalty_overlap": ov_penalty,
        "total_penalty": total_penalty,
        "net_score_delta": net_delta,
    }


# ---------------------------------------------------------------------------
# Pool scoring (shadow_test mode)
# ---------------------------------------------------------------------------

def apply_gp_realignment_scoring(
    games: list[dict],
    config: "StructuralRealignmentConfig",
    *,
    game_size: int = 15,
) -> list[dict]:
    """Tag each game in the pool with realignment metadata.

    Called in both shadow_test and active modes.
    Does NOT reorder the list — that is done by compose_diverse_gp in active mode.
    Does NOT mutate game['numbers'] or any existing score field.
    """
    if not games:
        return games

    annotated = []
    for game in games:
        # Shallow copy to avoid mutating the original
        enriched = dict(game)
        # Compute a point-in-time score assuming no other games selected yet
        # (full GP-aware scoring happens in compose_diverse_gp)
        numbers = enriched.get("numbers") or []
        p3 = _prefix(numbers, 3)
        p4 = _prefix(numbers, 4)
        s3 = _suffix(numbers, 3)
        s4 = _suffix(numbers, 4)
        bonus = _coverage_bonus(
            numbers,
            config.target_coverage_digits,
            config.coverage_bonus_per_digit,
            config.max_coverage_bonus,
        )
        enriched["realignment_metadata"] = {
            "realignment_tag": config.realignment_tag,
            "evidence_epoch": config.evidence_epoch,
            "mode": config.mode,
            "prefix_3": _format_prefix(p3),
            "prefix_4": _format_prefix(p4),
            "suffix_3": _format_prefix(s3),
            "suffix_4": _format_prefix(s4),
            "coverage_bonus": bonus,
            "target_coverage_digits": list(config.target_coverage_digits),
        }
        annotated.append(enriched)

    logger.debug(
        "[RealignmentV1] pool=%d game_size=%d mode=%s",
        len(annotated), game_size, config.mode,
    )
    return annotated


# ---------------------------------------------------------------------------
# GP composition with structural diversity (active mode)
# ---------------------------------------------------------------------------

def compose_diverse_gp(
    pool: list[dict],
    count: int,
    config: "StructuralRealignmentConfig",
    *,
    game_size: int = 15,
) -> list[dict]:
    """Greedy GP composition that enforces structural diversity.

    Replaces _compose_profiled_games when realignment mode is 'active'.
    Selects games by maximising: base_score + coverage_bonus - concentration_penalties.
    Profile quotas are NOT respected here; the caller should blend if needed.

    Does NOT mutate game numbers or any Law-15 rule.
    Every selected game carries full realignment_metadata.
    """
    if count < 1 or not pool:
        return []

    # Normalise base scores for sorting (profile_score dominates)
    def _base_score(g: dict) -> float:
        return (
            float(g.get("profile_score", 0)) * 100.0
            + float(g.get("final_score", {}).get("final_score", 0))
        )

    selected: list[dict] = []
    selected_keys: set[tuple[int, ...]] = set()
    prefix3_counts: Counter = Counter()
    prefix4_counts: Counter = Counter()
    suffix3_counts: Counter = Counter()
    suffix4_counts: Counter = Counter()

    remaining = [g for g in pool if g]

    while len(selected) < count and remaining:
        best_game: dict | None = None
        best_combined: float = float("-inf")
        best_realign: dict | None = None

        for candidate in remaining:
            key = tuple(candidate.get("numbers") or [])
            if key in selected_keys:
                continue

            realign = score_for_gp_diversity(
                candidate,
                selected,
                prefix3_counts=prefix3_counts,
                prefix4_counts=prefix4_counts,
                suffix3_counts=suffix3_counts,
                suffix4_counts=suffix4_counts,
                gp_target_size=count,
                config=config,
                game_size=game_size,
            )

            combined = _base_score(candidate) + realign["net_score_delta"]

            if combined > best_combined:
                best_combined = combined
                best_game = candidate
                best_realign = realign

        if best_game is None:
            break

        enriched = dict(best_game)
        enriched["realignment_metadata"] = {
            **best_realign,  # type: ignore[arg-type]
            "mode": config.mode,
            "combined_score": round(best_combined, 4),
            "gp_slot": len(selected),
        }
        key = tuple(enriched.get("numbers") or [])
        selected.append(enriched)
        selected_keys.add(key)

        numbers = enriched.get("numbers") or []
        prefix3_counts[_prefix(numbers, 3)] += 1
        prefix4_counts[_prefix(numbers, 4)] += 1
        suffix3_counts[_suffix(numbers, 3)] += 1
        suffix4_counts[_suffix(numbers, 4)] += 1
        remaining = [g for g in remaining if tuple(g.get("numbers") or []) not in selected_keys]

    logger.info(
        "[RealignmentV1] compose_diverse_gp: requested=%d selected=%d game_size=%d",
        count, len(selected), game_size,
    )
    return selected[:count]


# ---------------------------------------------------------------------------
# GP-level metrics (for reporting and dashboard)
# ---------------------------------------------------------------------------

def compute_gp_realignment_metrics(games: list[dict], *, game_size: int = 15) -> dict:
    """Compute structural diversity metrics for a finalised GP.

    Returns a dict ready to be stored in context_json / reconciliation payload.
    Does NOT read from the DB; operates only on the in-memory game list.
    """
    if not games:
        return {"available": False, "reason": "empty_games"}

    prefix3_c: Counter = Counter()
    prefix4_c: Counter = Counter()
    suffix3_c: Counter = Counter()
    suffix4_c: Counter = Counter()
    digit_presence: Counter = Counter()
    overlap_pairs = 0
    n = len(games)

    for game in games:
        nums = sorted(game.get("numbers") or [])
        if not nums:
            continue
        prefix3_c[_format_prefix(_prefix(nums, 3))] += 1
        prefix4_c[_format_prefix(_prefix(nums, 4))] += 1
        suffix3_c[_format_prefix(_suffix(nums, 3))] += 1
        suffix4_c[_format_prefix(_suffix(nums, 4))] += 1
        for d in nums:
            digit_presence[d] += 1

    # Overlap count
    for i in range(n):
        nums_i = set(games[i].get("numbers") or [])
        for j in range(i + 1, n):
            if len(nums_i & set(games[j].get("numbers") or [])) >= game_size - 2:
                overlap_pairs += 1

    top_p3 = prefix3_c.most_common(1)
    top_p4 = prefix4_c.most_common(1)
    top_s3 = suffix3_c.most_common(1)
    top_s4 = suffix4_c.most_common(1)

    most_absent = sorted(
        [(d, n - digit_presence.get(d, 0)) for d in range(1, 26) if digit_presence.get(d, 0) < n * 0.5],
        key=lambda x: -x[1],
    )[:8]

    return {
        "available": True,
        "gp_size": n,
        "game_size": game_size,
        "top_prefix3": top_p3[0][0] if top_p3 else None,
        "top_prefix3_count": top_p3[0][1] if top_p3 else 0,
        "top_prefix3_ratio": round(top_p3[0][1] / n, 3) if top_p3 else 0.0,
        "top_prefix4": top_p4[0][0] if top_p4 else None,
        "top_prefix4_count": top_p4[0][1] if top_p4 else 0,
        "top_prefix4_ratio": round(top_p4[0][1] / n, 3) if top_p4 else 0.0,
        "top_suffix3": top_s3[0][0] if top_s3 else None,
        "top_suffix3_count": top_s3[0][1] if top_s3 else 0,
        "top_suffix3_ratio": round(top_s3[0][1] / n, 3) if top_s3 else 0.0,
        "top_suffix4": top_s4[0][0] if top_s4 else None,
        "top_suffix4_count": top_s4[0][1] if top_s4 else 0,
        "top_suffix4_ratio": round(top_s4[0][1] / n, 3) if top_s4 else 0.0,
        "most_absent_digits": most_absent,
        "near_duplicate_pairs": overlap_pairs,
        "realignment_tag": "REALIGNMENT_V1",
        "evidence_epoch": "EPOCH_001",
    }
