"""Core Realignment V4 PATTERN PROTECTED — V1 signature patterns, not exact cards."""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lotoia.governance.lei15_core_realignment_v4 import CoreRealignmentV4Config

logger = logging.getLogger(__name__)

_COMPOSE_POOL_CAP = 600


def _prefix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[:n])


def _suffix(numbers: list[int], n: int) -> tuple[int, ...]:
    return tuple(sorted(numbers)[-n:])


def _format_prefix(p: tuple[int, ...]) -> str:
    return "-".join(f"{d:02d}" for d in p)


def _base_score(g: dict) -> float:
    final = g.get("final_score")
    final_value = final.get("final_score", 0) if isinstance(final, dict) else final
    return float(g.get("profile_score", 0) or 0) * 100.0 + float(final_value or 0)


def _max_overlap(numbers: list[int], selected: list[dict]) -> int:
    num_set = set(numbers)
    return max((len(num_set & set(item["numbers"])) for item in selected), default=0)


def compute_pattern_score(
    game: dict,
    *,
    config: "CoreRealignmentV4Config",
) -> tuple[float, dict[str, Any]]:
    """Score V1 combinatorial signature — patterns only, never exact-card lookup."""
    numbers = game["numbers"]
    num_set = set(numbers)
    p3 = _prefix(numbers, 3)
    s3 = _suffix(numbers, 3)
    signals: dict[str, Any] = {
        "strong_suffix": s3 in config.strong_suffixes,
        "strong_prefix": p3 in config.strong_prefixes,
        "middle_block_hits": 0,
        "high_close_24_25": 24 in num_set and 25 in num_set,
        "preferred_profile": False,
    }
    score = 0.0
    if signals["strong_suffix"]:
        score += 30.0
    if signals["strong_prefix"]:
        score += 20.0
    middle_hits = sum(1 for d in config.middle_block_digits if d in num_set)
    signals["middle_block_hits"] = middle_hits
    score += middle_hits * 5.0
    if signals["high_close_24_25"]:
        score += 10.0
    profile = str(game.get("profile_type") or "").strip().lower()
    if profile in config.preferred_profiles:
        signals["preferred_profile"] = True
        score += 5.0
    return round(score, 3), signals


def filter_pool_soft_v4(
    pool: list[dict],
    *,
    config: "CoreRealignmentV4Config",
) -> tuple[list[dict], bool]:
    if not pool:
        return pool, False

    total = len(pool)
    cap_per_prefix3 = max(2, int(total * config.max_pool_prefix3_ratio))

    groups: dict[tuple[int, ...], list[dict]] = {}
    for game in pool:
        key = _prefix(game["numbers"], 3)
        groups.setdefault(key, []).append(game)

    needs_filter = any(len(group) > cap_per_prefix3 for group in groups.values())
    if not needs_filter:
        return pool, True

    filtered: list[dict] = []
    for group_games in groups.values():
        sorted_group = sorted(group_games, key=_base_score, reverse=True)
        filtered.extend(sorted_group[:cap_per_prefix3])

    if len(filtered) < config.min_pool_size_after_filter:
        logger.info(
            "[CoreRealignV4] pre-filter skipped: %d -> %d (min=%d)",
            total,
            len(filtered),
            config.min_pool_size_after_filter,
        )
        return pool, True

    logger.info(
        "[CoreRealignV4] pre-filter: %d -> %d (cap=%d)",
        total,
        len(filtered),
        cap_per_prefix3,
    )
    return filtered, True


def _tag_v4_game(
    game: dict,
    *,
    config: "CoreRealignmentV4Config",
    pre_filter_applied: bool,
    protected_v1_pattern: bool,
    pattern_score: float,
    pattern_signals: dict[str, Any],
    completion_pass: bool = False,
) -> dict:
    numbers = game["numbers"]
    tagged = dict(game)
    existing_meta = dict(tagged.get("realignment_metadata") or {})
    existing_meta.update(
        {
            "realignment_tag": config.realignment_tag,
            "evidence_epoch": config.evidence_epoch,
            "mode": config.mode,
            "v1_applied": True,
            "v2_applied": False,
            "v3_applied": False,
            "v3_1_applied": False,
            "v4_applied": True,
            "pool_pre_filter_applied": pre_filter_applied,
            "protected_v1_pattern": protected_v1_pattern,
            "pattern_score": pattern_score,
            "pattern_signals": pattern_signals,
            "v4_completion_pass": completion_pass,
            "prefix_3": _format_prefix(_prefix(numbers, 3)),
            "prefix_4": _format_prefix(_prefix(numbers, 4)),
            "suffix_3": _format_prefix(_suffix(numbers, 3)),
            "suffix_4": _format_prefix(_suffix(numbers, 4)),
        }
    )
    tagged["realignment_metadata"] = existing_meta
    tagged["realignment_applied"] = True
    tagged["core_realignment_v4_applied"] = True
    return tagged


def _compose_faixa_b_diversity(
    pool: list[dict],
    *,
    count: int,
    config: "CoreRealignmentV4Config",
    game_size: int,
    selected: list[dict],
    selected_keys: set[tuple[int, ...]],
    pre_filter_applied: bool,
) -> list[dict]:
    if count < 1:
        return []

    def _concentration_penalty(count_struct: int, gp_size: int, max_ratio: float, weight: float) -> float:
        if gp_size < 1:
            return 0.0
        projected = (count_struct + 1) / (gp_size + 1)
        excess = max(0.0, projected - max_ratio)
        return round(excess * weight, 3)

    def _coverage_bonus(numbers: list[int]) -> float:
        present = sum(1 for digit in config.target_coverage_digits if digit in set(numbers))
        return round(min(present * config.coverage_bonus_per_digit, config.max_coverage_bonus), 3)

    def _overlap_penalty(numbers: list[int], current: list[dict]) -> float:
        if not current:
            return 0.0
        max_ov = _max_overlap(numbers, current)
        allowed = max(0, game_size - config.overlap_slack)
        excess = max(0, max_ov - allowed)
        return round(excess * config.overlap_penalty_per_digit, 3)

    effective_pool = sorted(pool, key=_base_score, reverse=True)
    if len(effective_pool) > _COMPOSE_POOL_CAP:
        effective_pool = effective_pool[:_COMPOSE_POOL_CAP]

    prefix3_counts = Counter(_prefix(item["numbers"], 3) for item in selected)
    prefix4_counts = Counter(_prefix(item["numbers"], 4) for item in selected)
    suffix3_counts = Counter(_suffix(item["numbers"], 3) for item in selected)
    suffix4_counts = Counter(_suffix(item["numbers"], 4) for item in selected)
    remaining = [game for game in effective_pool if tuple(game["numbers"]) not in selected_keys]

    picked: list[dict] = []
    while len(picked) < count and remaining:
        gp_size = len(selected) + len(picked)
        enforce = gp_size >= config.min_gp_for_concentration_check
        best_game: dict | None = None
        best_score = float("-inf")
        best_pat_score = 0.0
        best_pat_signals: dict[str, Any] = {}

        for game in remaining:
            numbers = game["numbers"]
            key = tuple(numbers)
            if key in selected_keys:
                continue
            total_penalty = 0.0
            if enforce:
                p3 = _prefix(numbers, 3)
                p4 = _prefix(numbers, 4)
                s3 = _suffix(numbers, 3)
                s4 = _suffix(numbers, 4)
                total_penalty += _concentration_penalty(
                    prefix3_counts[p3],
                    gp_size,
                    config.max_prefix3_ratio,
                    config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    prefix4_counts[p4],
                    gp_size,
                    config.max_prefix4_ratio,
                    config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    suffix3_counts[s3],
                    gp_size,
                    config.max_suffix3_ratio,
                    config.concentration_penalty_weight,
                )
                total_penalty += _concentration_penalty(
                    suffix4_counts[s4],
                    gp_size,
                    config.max_suffix4_ratio,
                    config.concentration_penalty_weight,
                )
            pat_score, pat_signals = compute_pattern_score(game, config=config)
            bonus = _coverage_bonus(numbers)
            overlap = _overlap_penalty(numbers, selected + picked)
            score = (bonus - total_penalty - overlap) + _base_score(game) * config.base_score_weight
            if score > best_score:
                best_score = score
                best_game = game
                best_pat_score = pat_score
                best_pat_signals = pat_signals

        if best_game is None:
            break

        tagged = _tag_v4_game(
            best_game,
            config=config,
            pre_filter_applied=pre_filter_applied,
            protected_v1_pattern=False,
            pattern_score=best_pat_score,
            pattern_signals=best_pat_signals,
        )
        picked.append(tagged)
        numbers = best_game["numbers"]
        key = tuple(numbers)
        selected_keys.add(key)
        prefix3_counts[_prefix(numbers, 3)] += 1
        prefix4_counts[_prefix(numbers, 4)] += 1
        suffix3_counts[_suffix(numbers, 3)] += 1
        suffix4_counts[_suffix(numbers, 4)] += 1
        remaining = [game for game in remaining if tuple(game["numbers"]) not in selected_keys]

    if len(picked) < count:
        for game in effective_pool:
            if len(picked) >= count:
                break
            key = tuple(game["numbers"])
            if key in selected_keys:
                continue
            pat_score, pat_signals = compute_pattern_score(game, config=config)
            picked.append(
                _tag_v4_game(
                    game,
                    config=config,
                    pre_filter_applied=pre_filter_applied,
                    protected_v1_pattern=False,
                    pattern_score=pat_score,
                    pattern_signals=pat_signals,
                    completion_pass=True,
                )
            )
            selected_keys.add(key)

    return picked


def compose_gp_v4(
    pool: list[dict],
    count: int,
    config: "CoreRealignmentV4Config",
    *,
    game_size: int = 15,
) -> tuple[list[dict], bool]:
    """Compose GP with Faixa A (pattern-protected, no structural penalty) + Faixa B."""
    if count < 1 or not pool:
        return [], False

    pool, pre_filter_applied = filter_pool_soft_v4(pool, config=config)

    scored: list[tuple[float, float, dict, dict[str, Any]]] = []
    for game in pool:
        pat_score, pat_signals = compute_pattern_score(game, config=config)
        scored.append((pat_score, _base_score(game), game, pat_signals))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

    pattern_slots = max(1, int(round(count * config.pattern_protected_ratio)))
    selected: list[dict] = []
    selected_keys: set[tuple[int, ...]] = set()

    for pat_score, _, game, pat_signals in scored:
        if len(selected) >= pattern_slots:
            break
        if pat_score < config.min_pattern_score_faixa_a:
            continue
        key = tuple(game["numbers"])
        if key in selected_keys:
            continue
        selected.append(
            _tag_v4_game(
                game,
                config=config,
                pre_filter_applied=pre_filter_applied,
                protected_v1_pattern=True,
                pattern_score=pat_score,
                pattern_signals=pat_signals,
            )
        )
        selected_keys.add(key)

    if len(selected) < pattern_slots:
        for pat_score, _, game, pat_signals in scored:
            if len(selected) >= pattern_slots:
                break
            key = tuple(game["numbers"])
            if key in selected_keys:
                continue
            selected.append(
                _tag_v4_game(
                    game,
                    config=config,
                    pre_filter_applied=pre_filter_applied,
                    protected_v1_pattern=True,
                    pattern_score=pat_score,
                    pattern_signals=pat_signals,
                    completion_pass=True,
                )
            )
            selected_keys.add(key)

    remainder_count = count - len(selected)
    if remainder_count > 0:
        remainder = _compose_faixa_b_diversity(
            pool,
            count=remainder_count,
            config=config,
            game_size=game_size,
            selected=selected,
            selected_keys=selected_keys,
            pre_filter_applied=pre_filter_applied,
        )
        selected.extend(remainder)

    if len(selected) < count:
        for _, _, game, pat_signals in scored:
            if len(selected) >= count:
                break
            key = tuple(game["numbers"])
            if key in selected_keys:
                continue
            pat_score, _ = compute_pattern_score(game, config=config)
            selected.append(
                _tag_v4_game(
                    game,
                    config=config,
                    pre_filter_applied=pre_filter_applied,
                    protected_v1_pattern=False,
                    pattern_score=pat_score,
                    pattern_signals=pat_signals,
                    completion_pass=True,
                )
            )
            selected_keys.add(key)

    protected_count = sum(
        1 for game in selected if (game.get("realignment_metadata") or {}).get("protected_v1_pattern")
    )
    logger.info(
        "[CoreRealignV4] composed %d/%d faixa_a=%d target_a=%d pool=%d pre_filter=%s",
        len(selected),
        count,
        protected_count,
        pattern_slots,
        len(pool),
        pre_filter_applied,
    )
    return selected, False
