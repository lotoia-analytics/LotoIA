"""Gerador estrutural ML 15D — pool mínimo de candidatos conformes (M-ML-072)."""

from __future__ import annotations

import os
from collections import Counter
from random import Random
from typing import Any, Mapping, Sequence

from lotoia.ml.structural_policy_15d import (
    CORE_NUMBERS,
    DISCOURAGED_NUMBERS,
    POLICY_VERSION,
    build_structural_policy_15d_memory,
    resolve_previous_contest_numbers,
    validate_game_structural_policy_15d,
)
from lotoia.ml.supervised_output_calibration import analyze_pool_structural_issues
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-072"
CALIBRATION_VERSION = "M-ML-072-v1"
POOL_ORIGIN_LABEL = "ML_STRUCTURAL_15D_POOL"
ENV_STRUCTURAL_15D_POOL_ENABLED = "LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED"
MIN_COMPLIANT_POOL_SIZE = 100
MIN_POOL_COMPLIANCE_RATE = 0.90


def resolve_structural_pool_target(
    *, requested_count: int, min_compliant: int | None = None
) -> int:
    """Escala pool conforme ao lote solicitado — evita material insuficiente para anti-clone."""
    requested = max(int(requested_count or 0), 1)
    floor = max(int(min_compliant or MIN_COMPLIANT_POOL_SIZE), MIN_COMPLIANT_POOL_SIZE)
    return max(floor, requested * 3, requested + 75)


REFERENCE_CONTEST_WINDOW = 10
MAX_PREFIX_SUFFIX_SHARE = (
    0.21  # Frequência histórica do triplet dominante (últimos 300 concursos: 21,0%)
)
MIN_DEZENA_COVERAGE_RATIO = 0.18
NEAR_CLONE_OVERLAP_15D = 14


def is_structural_15d_pool_enabled() -> bool:
    raw = os.getenv(ENV_STRUCTURAL_15D_POOL_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _game_signature(game: Mapping[str, Any]) -> tuple[int, ...]:
    return tuple(sorted(resolve_cartao_final_from_game(dict(game))))


def _parity_targets() -> list[tuple[int, int]]:
    return [(7, 8), (8, 7)]


def _generate_compliant_card(
    rng: Random,
    previous_numbers: set[int],
    *,
    policy: Mapping[str, Any],
) -> list[int] | None:
    """Gera cartão 15D conforme repetição, paridade e sequência.

    ``core_numbers``/``discouraged_numbers`` orientam preferência de composição apenas;
    a aprovação final usa ``validate_game_structural_policy_15d`` (regras reais, M-ML-079).
    """
    if len(previous_numbers) < 10:
        return None
    core_numbers = {int(value) for value in policy.get("core_numbers") or CORE_NUMBERS}
    discouraged = {
        int(value) for value in policy.get("discouraged_numbers") or DISCOURAGED_NUMBERS
    }

    for _ in range(1200):
        repeat_n = rng.randint(7, 10)
        parity = rng.choice(_parity_targets())
        repeated = set(rng.sample(sorted(previous_numbers), repeat_n))
        odd_in_base = sum(1 for number in repeated if number % 2 == 1)
        even_in_base = repeat_n - odd_in_base
        odd_need = parity[0] - odd_in_base
        even_need = parity[1] - even_in_base
        if odd_need < 0 or even_need < 0:
            continue
        remaining = 15 - repeat_n
        if odd_need + even_need != remaining:
            continue

        available_odd = [number for number in range(1, 26, 2) if number not in repeated]
        available_even = [
            number for number in range(2, 26, 2) if number not in repeated
        ]
        if odd_need > len(available_odd) or even_need > len(available_even):
            continue

        preferred_odd = [number for number in available_odd if number in core_numbers]
        preferred_even = [number for number in available_even if number in core_numbers]
        safe_odd = [number for number in available_odd if number not in discouraged]
        safe_even = [number for number in available_even if number not in discouraged]

        pick_odd = _pick_with_preference(
            rng, available_odd, preferred_odd, safe_odd, odd_need
        )
        pick_even = _pick_with_preference(
            rng, available_even, preferred_even, safe_even, even_need
        )
        if pick_odd is None or pick_even is None:
            continue

        card = sorted(set(repeated) | set(pick_odd) | set(pick_even))
        if len(card) != 15:
            continue
        validation = validate_game_structural_policy_15d(
            card,
            previous_contest_numbers=sorted(previous_numbers),
            policy=policy,
        )
        if validation.get("approved"):
            return card
    return None


def _pick_with_preference(
    rng: Random,
    available: list[int],
    preferred: list[int],
    safe: list[int],
    count: int,
) -> list[int] | None:
    if count == 0:
        return []
    pool = preferred or safe or available
    if len(pool) < count and len(available) < count:
        return None
    if len(pool) >= count:
        return rng.sample(pool, count)
    chosen = list(pool)
    rest = [number for number in available if number not in chosen]
    if len(chosen) + len(rest) < count:
        return None
    chosen.extend(rng.sample(rest, count - len(chosen)))
    return chosen


def _extract_recent_contests(
    history: Sequence[Any] | None, *, window: int = REFERENCE_CONTEST_WINDOW
) -> list[list[int]]:
    contests: list[list[int]] = []
    for draw in list(history or [])[-window:]:
        numbers = getattr(draw, "numbers", None)
        if numbers:
            contests.append(sorted(int(number) for number in numbers))
            continue
        if isinstance(draw, Mapping):
            raw = draw.get("numbers") or draw.get("dezenas") or []
            contests.append(
                sorted(int(number) for number in raw if 1 <= int(number) <= 25)
            )
    return [row for row in contests if len(row) == 15]


def _evaluate_pool_against_recent_contests(
    games: Sequence[Mapping[str, Any]],
    *,
    history: Sequence[Any] | None,
    window: int = REFERENCE_CONTEST_WINDOW,
) -> dict[str, Any]:
    contests = _extract_recent_contests(history, window=window)
    if not contests or not games:
        return {
            "available": False,
            "reference_contest_window": window,
            "reference_contests_count": len(contests),
        }
    hit_scores: list[float] = []
    for game in games:
        card = set(_game_signature(game))
        if not card:
            continue
        hits = [len(card & set(contest)) for contest in contests]
        hit_scores.append(sum(hits) / len(hits))
    return {
        "available": True,
        "reference_contest_window": window,
        "reference_contests_count": len(contests),
        "reference_contest_numbers": [contest for contest in contests],
        "avg_hits_per_contest": round(sum(hit_scores) / len(hit_scores), 4)
        if hit_scores
        else 0.0,
    }


def _pool_diversity_metrics(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cards = [_game_signature(game) for game in games if _game_signature(game)]
    pool_size = len(cards)
    if pool_size == 0:
        return {"pool_size": 0, "diversity_score": 0.0}
    prefix3 = Counter(
        format_dezena_group(compute_prefix(list(card), 3)) for card in cards
    )
    suffix3 = Counter(
        format_dezena_group(compute_suffix(list(card), 3)) for card in cards
    )
    number_presence = Counter(number for card in cards for number in card)
    prefix_limit = max(3, int(pool_size * MAX_PREFIX_SUFFIX_SHARE))
    suffix_limit = max(3, int(pool_size * MAX_PREFIX_SUFFIX_SHARE))
    min_expected = max(1, int(pool_size * MIN_DEZENA_COVERAGE_RATIO))
    near_clone_pairs = 0
    for index, left in enumerate(cards):
        for right in cards[index + 1 :]:
            if len(set(left) & set(right)) >= NEAR_CLONE_OVERLAP_15D:
                near_clone_pairs += 1
    return {
        "pool_size": pool_size,
        "top_prefix3": prefix3.most_common(1)[0] if prefix3 else ("", 0),
        "top_suffix3": suffix3.most_common(1)[0] if suffix3 else ("", 0),
        "prefix_dominant": any(
            count >= prefix_limit for _, count in prefix3.most_common(3)
        ),
        "suffix_dominant": any(
            count >= suffix_limit for _, count in suffix3.most_common(3)
        ),
        "subcovered_dezenas": [
            number
            for number in range(1, 26)
            if number_presence.get(number, 0) < min_expected
        ],
        "near_clone_pairs": near_clone_pairs,
        "diversity_score": round(
            1.0 - (near_clone_pairs / max(pool_size * (pool_size - 1) / 2, 1)),
            4,
        ),
    }


def _structural_pool_score(
    game: Mapping[str, Any],
    *,
    selected_cards: list[list[int]],
    policy: Mapping[str, Any],
) -> float:
    card = list(_game_signature(game))
    if not card:
        return 0.0
    score = float(game.get("profile_score", 0) or 0)
    card_set = set(card)
    core_present = len(
        card_set & {int(value) for value in policy.get("core_numbers") or CORE_NUMBERS}
    )
    discouraged_present = len(
        card_set
        & {
            int(value)
            for value in policy.get("discouraged_numbers") or DISCOURAGED_NUMBERS
        }
    )
    score += core_present * 0.35
    score -= max(0, discouraged_present - 3) * 0.45
    if selected_cards:
        overlaps = [len(card_set & set(other)) for other in selected_cards]
        if overlaps:
            score -= max(overlaps) * 0.25
    prefix = format_dezena_group(compute_prefix(card, 3))
    suffix = format_dezena_group(compute_suffix(card, 3))
    prefix_counts = Counter(
        format_dezena_group(compute_prefix(row, 3)) for row in selected_cards
    )
    suffix_counts = Counter(
        format_dezena_group(compute_suffix(row, 3)) for row in selected_cards
    )
    if prefix_counts.get(prefix, 0) >= max(
        2, int(len(selected_cards) * MAX_PREFIX_SUFFIX_SHARE)
    ):
        score -= 0.8
    if suffix_counts.get(suffix, 0) >= max(
        2, int(len(selected_cards) * MAX_PREFIX_SUFFIX_SHARE)
    ):
        score -= 0.8
    return score


def _select_diverse_compliant_pool(
    compliant_games: list[dict[str, Any]],
    *,
    target_size: int,
    policy: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if len(compliant_games) <= target_size:
        return list(compliant_games)
    ranked = sorted(
        compliant_games,
        key=lambda row: float(row.get("profile_score", 0) or 0),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    selected_cards: list[list[int]] = []
    for game in ranked:
        card = list(_game_signature(game))
        if not card:
            continue
        if any(
            len(set(card) & set(other)) >= NEAR_CLONE_OVERLAP_15D
            for other in selected_cards
        ):
            continue
        adjusted = dict(game)
        adjusted["structural_pool_score"] = round(
            _structural_pool_score(game, selected_cards=selected_cards, policy=policy),
            4,
        )
        selected.append(adjusted)
        selected_cards.append(card)
        if len(selected) >= target_size:
            break
    if len(selected) < target_size:
        for game in ranked:
            if game in selected:
                continue
            selected.append(dict(game))
            if len(selected) >= target_size:
                break
    selected.sort(
        key=lambda row: (
            -float(row.get("structural_pool_score", row.get("profile_score", 0)) or 0),
            tuple(row.get("numbers") or ()),
        )
    )
    return selected


def build_ml_structural_15d_pool(
    raw_pool: Sequence[Mapping[str, Any]],
    *,
    history: Sequence[Any] | None,
    min_compliant: int = MIN_COMPLIANT_POOL_SIZE,
    seed: int | None = None,
    policy: Mapping[str, Any] | None = None,
    calibration_plan: Mapping[str, Any] | None = None,
    module_params: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Gera/expande pool estrutural 15D com mínimo de candidatos conformes."""
    empty_bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "pool_origin": POOL_ORIGIN_LABEL,
        "structural_pool_applied": False,
    }
    if not is_structural_15d_pool_enabled():
        return [dict(game) for game in raw_pool], empty_bundle

    resolved_policy = dict(policy or build_structural_policy_15d_memory())
    previous_numbers = set(resolve_previous_contest_numbers(history))
    rng = Random(abs(int(seed or 0)) % 1_000_003 + 17)
    metrics_before = _pool_diversity_metrics(raw_pool)
    diagnostics_before = analyze_pool_structural_issues(list(raw_pool), game_size=15)

    compliant: list[dict[str, Any]] = []
    non_compliant: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for game in raw_pool:
        signature = _game_signature(game)
        if not signature or signature in seen:
            continue
        seen.add(signature)
        validation = validate_game_structural_policy_15d(
            list(signature),
            previous_contest_numbers=sorted(previous_numbers),
            policy=resolved_policy,
        )
        enriched = dict(game)
        enriched["structural_policy_15d_validation"] = validation
        enriched["pool_origin"] = POOL_ORIGIN_LABEL
        enriched["structural_pool_generated"] = False
        if validation.get("approved"):
            compliant.append(enriched)
        else:
            non_compliant.append(enriched)

    generated_count = 0
    max_attempts = max(min_compliant * 40, 4000)
    attempts = 0
    while len(compliant) < min_compliant and attempts < max_attempts:
        attempts += 1
        card = _generate_compliant_card(rng, previous_numbers, policy=resolved_policy)
        if not card:
            continue
        signature = tuple(card)
        if signature in seen:
            continue
        seen.add(signature)
        from lotoia.generator.basic_generator import _attach_scores, _build_game

        game = _build_game(card)
        _attach_scores(game, history=list(history or []), profile_type="recorrente")
        validation = validate_game_structural_policy_15d(
            card,
            previous_contest_numbers=sorted(previous_numbers),
            policy=resolved_policy,
        )
        if not validation.get("approved"):
            continue
        enriched = dict(game)
        enriched["structural_policy_15d_validation"] = validation
        enriched["pool_origin"] = POOL_ORIGIN_LABEL
        enriched["structural_pool_generated"] = True
        compliant.append(enriched)
        generated_count += 1

    target_pool_size = max(min_compliant, len(compliant))
    selected_compliant = _select_diverse_compliant_pool(
        compliant,
        target_size=target_pool_size,
        policy=resolved_policy,
    )
    if len(selected_compliant) >= min_compliant:
        pool = selected_compliant
    else:
        compliant_signatures = {_game_signature(row) for row in selected_compliant}
        fallback_tail = [
            dict(game)
            for game in non_compliant
            if _game_signature(game) not in compliant_signatures
        ][: max(0, min_compliant // 5)]
        pool = selected_compliant + fallback_tail

    compliant_in_pool = sum(
        1
        for game in pool
        if (game.get("structural_policy_15d_validation") or {}).get("approved")
    )
    compliance_rate = compliant_in_pool / max(len(pool), 1)
    metrics_after = _pool_diversity_metrics(pool)
    diagnostics_after = analyze_pool_structural_issues(pool, game_size=15)
    confronto = _evaluate_pool_against_recent_contests(pool, history=history)

    bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "pool_origin": POOL_ORIGIN_LABEL,
        "structural_pool_applied": True,
        "structural_pool_size": len(pool),
        "structural_compliant_pool_size": len(selected_compliant),
        "structural_generated_count": generated_count,
        "compliance_rate": round(compliance_rate, 4),
        "min_compliant_required": int(min_compliant),
        "min_compliance_rate_required": MIN_POOL_COMPLIANCE_RATE,
        "compliance_met": compliance_rate >= MIN_POOL_COMPLIANCE_RATE
        and len(selected_compliant) >= min_compliant,
        "policy_version": POLICY_VERSION,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "diagnostics_before": {
            "issue_count": diagnostics_before.get("issue_count"),
            "diversity_score": round(
                1.0
                - float(
                    (diagnostics_before.get("redundancy") or {}).get(
                        "similaridade_media_entre_jogos", 0
                    )
                    or 0
                ),
                4,
            ),
        },
        "diagnostics_after": {
            "issue_count": diagnostics_after.get("issue_count"),
            "diversity_score": round(
                1.0
                - float(
                    (diagnostics_after.get("redundancy") or {}).get(
                        "similaridade_media_entre_jogos", 0
                    )
                    or 0
                ),
                4,
            ),
        },
        "reference_contest_window": REFERENCE_CONTEST_WINDOW,
        "confronto_recent_contests": confronto,
        "raw_pool_size": len(list(raw_pool)),
        "raw_compliant_count": len(compliant) - generated_count,
    }
    if module_params or calibration_plan:
        from lotoia.ml.authorized_ml_calibration_plan import (
            extract_module_operational_params,
        )

        ops = extract_module_operational_params(calibration_plan)
        mp = dict(module_params or ops.get("modules", {}).get("M-ML-072") or {})
        subcovered = {
            int(str(value).lstrip("0") or "0")
            for value in list(mp.get("dezenas_subcobertas") or [])
            if str(value).strip().isdigit()
        }
        missing_boost = float(mp.get("missing_numbers_boost", 1.0) or 1.0)
        actions: list[str] = []
        if mp:
            for game in pool:
                numbers = set(resolve_cartao_final_from_game(dict(game)))
                boost = 0.0
                for number in subcovered:
                    if number in numbers:
                        boost += 0.35 * missing_boost
                if boost:
                    game["profile_score"] = round(
                        float(game.get("profile_score", 0) or 0) + boost,
                        4,
                    )
                    game["ml_calibration_boost"] = round(boost, 4)
                    actions.append(f"reforco_subcoberta_{len(numbers & subcovered)}")
            bundle["calibration_plan_applied"] = bool(ops.get("applied"))
            bundle["calibration_operational_trace"] = list(ops.get("trace") or [])
            bundle["calibration_module_params"] = mp
            bundle["calibration_actions"] = actions
    return pool, bundle


def build_structural_15d_pool_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    return {
        "mission_id": str(source.get("mission_id") or MISSION_ID),
        "pool_origin": str(source.get("pool_origin") or POOL_ORIGIN_LABEL),
        "structural_pool_applied": bool(source.get("structural_pool_applied")),
        "structural_pool_size": int(source.get("structural_pool_size", 0) or 0),
        "structural_compliant_pool_size": int(
            source.get("structural_compliant_pool_size", 0) or 0
        ),
        "compliance_rate": float(source.get("compliance_rate", 0.0) or 0.0),
        "compliance_met": bool(source.get("compliance_met")),
        "structural_generated_count": int(
            source.get("structural_generated_count", 0) or 0
        ),
        "reference_contest_window": int(
            source.get("reference_contest_window", REFERENCE_CONTEST_WINDOW)
            or REFERENCE_CONTEST_WINDOW
        ),
        "confronto_recent_contests": dict(
            source.get("confronto_recent_contests") or {}
        ),
        "metrics_before": dict(source.get("metrics_before") or {}),
        "metrics_after": dict(source.get("metrics_after") or {}),
        "calibration_plan_applied": bool(source.get("calibration_plan_applied")),
        "calibration_operational_trace": list(
            source.get("calibration_operational_trace") or []
        ),
        "calibration_module_params": dict(
            source.get("calibration_module_params") or {}
        ),
    }
