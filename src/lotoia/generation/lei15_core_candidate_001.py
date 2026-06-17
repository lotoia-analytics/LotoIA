"""Lei 15 Core Candidate 001 / CDX — nucleus corrections N-C1..N-C6 (shadow_test)."""

from __future__ import annotations

import logging
from random import Random
from typing import TYPE_CHECKING

from lotoia.generation.lei15_core_structural_payload import (
    apply_core_traceability_payload,
    apply_structural_bias_penalty_to_score,
    prefix3,
)
from lotoia.statistics.historical_intelligence import (
    GENERATION_PROFILE_RATIOS,
    PROFILE_CHAOTIC,
    PROFILE_HYBRID,
    PROFILE_RECURRENT,
    profile_quota,
)

if TYPE_CHECKING:
    from lotoia.governance.lei15_core_candidate_001 import CoreCandidate001Config

logger = logging.getLogger(__name__)

_PREFIX_TRIPLET = (1, 2, 3)
_HIGH_SUFFIX = {22, 23, 24, 25}


def _cap_high_suffix_from_hot(selected: set[int], hot_numbers: list[int], *, max_high: int) -> None:
    high_in_sel = [n for n in selected if n in _HIGH_SUFFIX]
    if len(high_in_sel) <= max_high:
        return
    hot_high = [n for n in hot_numbers if n in _HIGH_SUFFIX and n in selected]
    for drop in hot_high[max_high:]:
        selected.discard(drop)


def _generate_candidate_profile_candidate(
    random: Random,
    profile_type: str,
    history: list[object],
    *,
    config: "CoreCandidate001Config",
) -> dict[str, object]:
    from lotoia.generator.basic_generator import _build_game

    last_numbers = set(history[-1].numbers) if history else set()
    hot_numbers: list[int] = []
    if history:
        counts = {number: 0 for number in range(1, 26)}
        for draw in history[-30:]:
            for number in draw.numbers:
                counts[number] += 1
        hot_numbers = [
            number for number, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:12]
        ]

    if profile_type == PROFILE_RECURRENT and history and hot_numbers:
        max_ov = config.max_last_draw_overlap if config.cap_last_draw_overlap else 10
        low = 7 if config.cap_last_draw_overlap else 8
        high = min(max_ov, len(last_numbers))
        high = max(low, high)
        selected = set(random.sample(sorted(last_numbers), random.randint(low, high)))
        available_hot = [number for number in hot_numbers if number not in selected]
        if available_hot:
            need = 15 - len(selected)
            picked_hot = random.sample(available_hot, min(len(available_hot), need))
            selected.update(picked_hot)
        if config.suffix_hot_cap:
            _cap_high_suffix_from_hot(selected, hot_numbers, max_high=config.max_high_suffix_digits)
        while len(selected) < 15:
            selected.add(random.randint(1, 25))
        if config.block_prefix_triplet_123 and prefix3(list(selected)) == _PREFIX_TRIPLET:
            for drop in _PREFIX_TRIPLET:
                if drop in selected:
                    selected.remove(drop)
                    break
            while len(selected) < 15:
                n = random.randint(1, 25)
                if n not in _PREFIX_TRIPLET:
                    selected.add(n)
        game = _build_game(list(selected))
        apply_core_traceability_payload(game, profile_origin=PROFILE_RECURRENT)
        return game

    if profile_type == PROFILE_CHAOTIC:
        start = random.randint(1, 20)
        selected = set(range(start, min(26, start + random.randint(5, 7))))
        selected.update(random.choice([range(1, 6), range(6, 11), range(11, 16), range(16, 21), range(21, 26)]))
        while len(selected) < 15:
            selected.add(random.randint(1, 25))
        game = _build_game(list(selected))
        apply_core_traceability_payload(game, profile_origin=PROFILE_CHAOTIC)
        return game

    selected: set[int] = set()
    if history:
        if profile_type == PROFILE_HYBRID and config.hybrid_reduced_inheritance:
            lo, hi = config.hybrid_inherit_min, config.hybrid_inherit_max
        else:
            lo, hi = 6, min(9, len(last_numbers))
        hi = max(lo, min(hi, len(last_numbers)))
        selected.update(random.sample(sorted(last_numbers), random.randint(lo, hi)))
    if profile_type == PROFILE_HYBRID and config.blind_spot_injection:
        spots = [d for d in config.blind_spot_digits if d not in selected]
        random.shuffle(spots)
        for digit in spots[: config.blind_spot_slots]:
            selected.add(digit)
    while len(selected) < 15:
        selected.add(random.randint(1, 25))
    game = _build_game(list(selected))
    apply_core_traceability_payload(game, profile_origin=PROFILE_HYBRID)
    return game


def _attach_candidate_scores(
    game: dict[str, object],
    history: list[object],
    profile_type: str,
    *,
    config: "CoreCandidate001Config",
) -> dict[str, object]:
    from lotoia.generator.basic_generator import _attach_scores

    apply_core_traceability_payload(game, profile_origin=profile_type)
    _attach_scores(game, history=history, profile_type=profile_type)
    apply_core_traceability_payload(game, profile_origin=profile_type)

    if config.adjusted_recurrence_scoring:
        intel = game.get("historical_intelligence")
        if isinstance(intel, dict):
            recurrence = float(intel.get("recurrence_score", 0) or 0)
            current = float(game.get("profile_score", 0) or 0)
            dampen = recurrence * 0.40 * (1.0 - config.recurrence_weight_scale)
            game["profile_score"] = round(max(0.0, current - dampen), 2)
            intel["candidate_nc6_applied"] = True

    apply_structural_bias_penalty_to_score(
        game,
        weight=config.structural_bias_weight,
        enabled=config.structural_bias_penalty,
    )

    meta = dict(game.get("core_candidate_metadata") or {})
    meta.update(
        {
            "variant": config.variant,
            "n_c1_overlap_cap": config.cap_last_draw_overlap,
            "n_c2_suffix_hot_cap": config.suffix_hot_cap,
            "n_c3_hybrid_blind_spot": config.blind_spot_injection,
            "n_c4_pool_quota": config.pool_sampling_by_quota,
            "n_c5_no_relabel": config.disable_profile_relabeling,
            "n_c6_recurrence_adjust": config.adjusted_recurrence_scoring,
            "structural_bias_penalty": game.get("structural_bias_penalty", 0),
        }
    )
    game["core_candidate_metadata"] = meta
    game["core_candidate_001_applied"] = True
    apply_core_traceability_payload(
        game,
        profile_origin=str(game.get("perfil_origem_real") or profile_type),
        relabeling_applied=False,
        relabeling_reason=None,
    )
    return game


def _pick_profile_for_quota(profile_counts: dict[str, int], profile_targets: dict[str, int]) -> str:
    profiles = list(GENERATION_PROFILE_RATIOS)
    return min(profiles, key=lambda p: profile_counts.get(p, 0) / max(profile_targets.get(p, 0), 1))


def build_candidate_pool(
    pool_size: int,
    *,
    seed: int,
    history: list[object],
    config: "CoreCandidate001Config",
) -> list[dict[str, object]]:
    from lotoia.generator.basic_generator import _is_valid_game, _normalization_pressure_level
    from lotoia.statistics.generation_trace import record_discarded_game

    games: list[dict[str, object]] = []
    seen: set[tuple[int, ...]] = set()
    profile_counts = {profile: 0 for profile in GENERATION_PROFILE_RATIOS}
    profile_targets = profile_quota(pool_size) if config.pool_sampling_by_quota else None
    max_attempts = pool_size * 1500
    attempts = 0

    while len(games) < pool_size and attempts < max_attempts:
        attempts += 1
        if profile_targets is not None:
            profile_type = _pick_profile_for_quota(profile_counts, profile_targets)
        else:
            profiles = list(GENERATION_PROFILE_RATIOS)
            profile_type = profiles[attempts % len(profiles)]

        candidate = _generate_candidate_profile_candidate(
            Random((attempts * 7919) + pool_size + seed),
            profile_type,
            history,
            config=config,
        )
        if not _is_valid_game(candidate, profile_type=profile_type):
            record_discarded_game(
                "normalize_distribution",
                candidate["numbers"],
                reason="candidate rejected by normalization filter",
                metrics={"pressure_level": _normalization_pressure_level()},
                history=history,
                profile_type=profile_type,
            )
            continue
        game = _attach_candidate_scores(candidate, history, profile_type, config=config)
        key = tuple(game["numbers"])
        if key in seen:
            continue
        seen.add(key)
        games.append(game)
        origin = str(game.get("perfil_origem_real") or profile_type)
        profile_counts[origin] = profile_counts.get(origin, 0) + 1

    if len(games) < pool_size:
        raise RuntimeError(
            f"[CoreCandidate001] pool incompleto {len(games)}/{pool_size} variant={config.variant}"
        )

    logger.info(
        "[CoreCandidate001/CDX] pool=%d variant=%s profiles_real=%s",
        len(games),
        config.variant,
        profile_counts,
    )
    return games


def tag_gp_candidate_metadata(games: list[dict], *, config: "CoreCandidate001Config") -> None:
    for game in games:
        game["core_candidate_001_applied"] = True
        origin = str(game.get("perfil_origem_real") or game.get("profile_type") or "")
        apply_core_traceability_payload(
            game,
            profile_origin=origin,
            relabeling_applied=bool(game.get("relabeling_applied")),
            relabeling_reason=game.get("relabeling_reason"),
        )
        meta = dict(game.get("core_candidate_metadata") or {})
        meta.setdefault("variant", config.variant)
        meta["gp_compose_no_relabel"] = config.disable_profile_relabeling
        game["core_candidate_metadata"] = meta


def audit_profile_pattern_frequencies(games: list[dict]) -> dict[str, dict[str, float]]:
    """Audit R-03/R-04 internal pattern rates."""
    from collections import Counter

    buckets: dict[str, list[dict]] = {"recorrente": [], "hibrido": [], "caotico": [], "all": list(games)}
    for g in games:
        origin = str(g.get("perfil_origem_real") or g.get("profile_type") or "")
        if origin in buckets:
            buckets[origin].append(g)

    def _rates(items: list[dict]) -> dict[str, float]:
        if not items:
            return {}
        n = len(items)
        c_p3 = Counter(str(g.get("prefix_signature", "")) for g in items)
        c_s3 = Counter(str(g.get("suffix_signature", "")) for g in items)
        return {
            "count": n,
            "prefix_01_02_03_pct": c_p3.get("01-02-03", 0) / n * 100,
            "prefix_01_02_pct": sum(1 for g in items if "01-02" in (g.get("core_traceability") or {}).get("prefix_pairs", [])) / n * 100,
            "prefix_02_03_pct": sum(1 for g in items if "02-03" in (g.get("core_traceability") or {}).get("prefix_pairs", [])) / n * 100,
            "suffix_22_24_25_pct": c_s3.get("22-24-25", 0) / n * 100,
            "suffix_22_24_pct": sum(1 for g in items if "22-24" in (g.get("core_traceability") or {}).get("suffix_pairs", [])) / n * 100,
            "suffix_24_25_pct": sum(1 for g in items if "24-25" in (g.get("core_traceability") or {}).get("suffix_pairs", [])) / n * 100,
            "suffix_22_25_pct": sum(1 for g in items if "22-25" in (g.get("core_traceability") or {}).get("suffix_pairs", [])) / n * 100,
            "avg_bias_score": sum(float(g.get("structural_bias_score", 0) or 0) for g in items) / n,
        }

    return {k: _rates(v) for k, v in buckets.items() if v}
