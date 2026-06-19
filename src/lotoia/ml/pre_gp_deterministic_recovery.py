"""Recuperação determinística pré-GP — M-ML-074.

Loop operacional antes de expor bloqueio M-ML-073 ao usuário.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Callable, Mapping, Sequence

from lotoia.governance.institutional_agent_routing_matrix import enrich_hierarchy_bundle
from lotoia.ml.ml_operational_hierarchy import (
    STAGE_CONFORMITY,
    STAGE_COVERAGE,
    STAGE_DIVERSITY,
    _filter_near_clone_games,
    _pool_candidate_slice,
    execute_ml_operational_hierarchy,
    resolve_failed_hierarchy_stage,
)
from lotoia.ml.pre_final_pool_ml_calibration import _game_signature, _metric_snapshot
from lotoia.ml.structural_policy_15d import is_structural_policy_15d_format
from lotoia.ml.structural_pool_15d_generator import build_ml_structural_15d_pool
from lotoia.ml.supervised_output_calibration import analyze_pool_structural_issues
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-ML-074"
RECOVERY_VERSION = "M-ML-074-v1"
ENV_PRE_GP_RECOVERY_ATTEMPTS = "LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS"
ENV_PRE_GP_RECOVERY_ENABLED = "LOTOIA_ML_PRE_GP_RECOVERY_ENABLED"
DEFAULT_MAX_RECOVERY_ATTEMPTS = 5


def is_pre_gp_recovery_enabled() -> bool:
    raw = os.getenv(ENV_PRE_GP_RECOVERY_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_max_recovery_attempts() -> int:
    raw = os.getenv(ENV_PRE_GP_RECOVERY_ATTEMPTS, str(DEFAULT_MAX_RECOVERY_ATTEMPTS)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_MAX_RECOVERY_ATTEMPTS
    return max(1, min(value, 10))


def _structural_family_key(game: Mapping[str, Any]) -> str:
    card = resolve_cartao_final_from_game(dict(game))
    if not card:
        return ""
    prefix = format_dezena_group(compute_prefix(list(card), 3))
    suffix = format_dezena_group(compute_suffix(list(card), 3))
    return f"{prefix}|{suffix}"


def _attempt_metrics_snapshot(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    batch_label: str | None,
    hierarchy_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    metrics = _metric_snapshot(candidate_pool, game_size=game_size, batch_label=batch_label)
    diversity_stage = dict(
        (hierarchy_bundle.get("stage_results") or {}).get(STAGE_DIVERSITY) or {}
    )
    coverage_stage = dict(
        (hierarchy_bundle.get("stage_results") or {}).get(STAGE_COVERAGE) or {}
    )
    conformity_stage = dict(
        (hierarchy_bundle.get("stage_results") or {}).get(STAGE_CONFORMITY) or {}
    )
    return {
        "diversity_score": float(metrics.get("diversity_score", 0.0) or 0.0),
        "similarity_score": float(metrics.get("similarity_score", 0.0) or 0.0),
        "candidate_pool_size": len(candidate_pool),
        "diversity_passed": bool(diversity_stage.get("passed")),
        "coverage_passed": bool(coverage_stage.get("passed")),
        "conformity_passed": bool(conformity_stage.get("passed")),
        "gp_closure_allowed": bool(hierarchy_bundle.get("gp_closure_allowed")),
        "max_overlap": int(
            (diversity_stage.get("metrics") or {}).get("max_overlap", 0) or 0
        ),
    }


def _score_attempt(metrics: Mapping[str, Any]) -> float:
    score = float(metrics.get("diversity_score", 0.0) or 0.0) * 100.0
    if metrics.get("conformity_passed"):
        score += 30.0
    if metrics.get("coverage_passed"):
        score += 20.0
    if metrics.get("diversity_passed"):
        score += 25.0
    if metrics.get("gp_closure_allowed"):
        score += 200.0
    return round(score, 4)


def _penalize_dominant_families(
    pool: list[dict[str, Any]],
    *,
    requested_count: int,
    attempt_index: int,
) -> list[dict[str, Any]]:
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    families: Counter[str] = Counter(_structural_family_key(game) for game in candidate_pool)
    dominant = {family for family, count in families.most_common(5) if family and count >= 3}
    if not dominant:
        return pool
    penalty = 0.45 + (attempt_index * 0.12)
    adjusted: list[dict[str, Any]] = []
    for game in pool:
        row = dict(game)
        if _structural_family_key(row) in dominant:
            row["profile_score"] = round(
                float(row.get("profile_score", 0.0) or 0.0) * (1.0 - penalty),
                4,
            )
            row["dominant_family_penalized"] = True
        adjusted.append(row)
    return adjusted


def _boost_subcovered_dezenas(
    pool: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    batch_label: str | None,
    attempt_index: int,
) -> list[dict[str, Any]]:
    candidate_pool = _pool_candidate_slice(pool, requested_count=requested_count)
    diagnostics = analyze_pool_structural_issues(
        candidate_pool,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=requested_count,
    )
    subcovered: set[int] = set()
    for issue in list(diagnostics.get("issues") or []):
        if str(issue.get("tipo") or "") != "dezena_subcoberta":
            continue
        for number in list(issue.get("dezenas") or issue.get("numbers") or []):
            try:
                subcovered.add(int(number))
            except (TypeError, ValueError):
                continue
    if not subcovered:
        return pool
    boost = 0.25 + (attempt_index * 0.08)
    adjusted: list[dict[str, Any]] = []
    for game in pool:
        row = dict(game)
        card = set(resolve_cartao_final_from_game(row) or [])
        hits = len(card & subcovered)
        if hits:
            row["profile_score"] = round(
                float(row.get("profile_score", 0.0) or 0.0) + (hits * boost),
                4,
            )
            row["subcovered_dezena_boosted"] = True
        adjusted.append(row)
    return adjusted


def _force_material_top_slice_substitution(
    pool: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    batch_label: str | None,
    attempt_index: int,
) -> tuple[list[dict[str, Any]], int]:
    slice_size = max(int(requested_count) * 3, int(requested_count), 20)
    ranked = sorted(
        pool,
        key=lambda row: float(row.get("profile_score", 0.0) or 0.0),
        reverse=True,
    )
    if len(ranked) <= slice_size:
        return pool, 0

    top = [dict(game) for game in ranked[:slice_size]]
    tail = [dict(game) for game in ranked[slice_size:]]
    diagnostics = analyze_pool_structural_issues(
        top,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=requested_count,
    )
    redundancy = dict(diagnostics.get("redundancy") or {})
    dominant_suffixes = {str(row[0]) for row in list(redundancy.get("suffix_top") or [])[:3] if row}
    dominant_prefixes = {str(row[0]) for row in list(redundancy.get("prefix_top") or [])[:3] if row}
    overlap_limit = max(int(game_size) - 1, 13)

    replace_indices: list[int] = []
    seen_cards: list[list[int]] = []
    for index, game in enumerate(top):
        card = resolve_cartao_final_from_game(dict(game))
        if not card:
            continue
        prefix = format_dezena_group(compute_prefix(list(card), 3))
        suffix = format_dezena_group(compute_suffix(list(card), 3))
        is_dominant = prefix in dominant_prefixes or suffix in dominant_suffixes
        is_clone = any(len(set(card) & set(other)) >= overlap_limit for other in seen_cards)
        seen_cards.append(list(card))
        if is_dominant or is_clone:
            replace_indices.append(index)

    min_replace = min(len(replace_indices), 3 + attempt_index * 4)
    if not replace_indices:
        replace_indices = list(range(min(5 + attempt_index, slice_size)))
    replace_indices = replace_indices[: max(min_replace, 1)]

    top_cards = [resolve_cartao_final_from_game(dict(game)) for game in top]
    tail_scored: list[tuple[float, dict[str, Any]]] = []
    for game in tail:
        card = resolve_cartao_final_from_game(dict(game))
        if not card:
            continue
        overlaps = [
            len(set(card) & set(other))
            for other in top_cards
            if other
        ]
        max_overlap = max(overlaps, default=0)
        diversity_bonus = (int(game_size) - max_overlap) / max(int(game_size), 1)
        tail_scored.append(
            (
                diversity_bonus + float(game.get("profile_score", 0.0) or 0.0) * 0.01,
                dict(game),
            )
        )
    tail_scored.sort(key=lambda row: row[0], reverse=True)

    replaced = 0
    used_signatures: set[tuple[int, ...]] = {_game_signature(game) for game in top}
    for index, (score, replacement) in zip(replace_indices, tail_scored):
        signature = _game_signature(replacement)
        if not signature or signature in used_signatures:
            continue
        demoted = dict(top[index])
        demoted["profile_score"] = round(float(demoted.get("profile_score", 0.0) or 0.0) * 0.12, 4)
        demoted["pre_gp_recovery_demoted"] = True
        promoted = dict(replacement)
        promoted["profile_score"] = round(
            float(promoted.get("profile_score", 0.0) or 0.0) * 1.15
            + float(score) * 0.5
            + attempt_index * 0.05,
            4,
        )
        promoted["pre_gp_recovery_promoted"] = True
        top[index] = promoted
        tail.append(demoted)
        used_signatures.add(signature)
        replaced += 1

    demoted_tail = [game for game in tail if not game.get("pre_gp_recovery_demoted")]
    new_pool = top + demoted_tail
    return new_pool, replaced


def _escalate_calibration_plan(
    calibration_plan: Mapping[str, Any] | None,
    *,
    failed_stage: str,
    attempt_index: int,
) -> dict[str, Any]:
    plan = dict(calibration_plan or {})
    plan.setdefault("authorized", True)
    params = dict(plan.get("parametros_sugeridos") or {})
    boost = 1.0 + (attempt_index * 0.18)
    if failed_stage == STAGE_DIVERSITY:
        params["redundancy_penalty_boost"] = max(
            float(params.get("redundancy_penalty_boost", 1.2) or 1.2),
            1.2 * boost,
        )
        params["max_overlap_penalty"] = max(
            float(params.get("max_overlap_penalty", 1.15) or 1.15),
            1.15 * boost,
        )
        params["dominant_family_penalty"] = 1.0 + attempt_index * 0.35
        params["prefix_penalty_boost"] = 1.0 + attempt_index * 0.25
        params["suffix_penalty_boost"] = 1.0 + attempt_index * 0.25
    elif failed_stage == STAGE_COVERAGE:
        params["missing_numbers_boost"] = max(
            float(params.get("missing_numbers_boost", 1.3) or 1.3),
            1.3 * boost,
        )
        params["critical_coverage_boost"] = max(
            float(params.get("critical_coverage_boost", 1.25) or 1.25),
            1.25 * boost,
        )
    elif failed_stage == STAGE_CONFORMITY:
        params["compliance_expansion_boost"] = 1.0 + attempt_index * 0.2
    plan["parametros_sugeridos"] = params
    plan["pre_gp_recovery_attempt"] = attempt_index
    return plan


def apply_deterministic_recovery_action(
    pool: list[dict[str, Any]],
    *,
    failed_stage: str,
    attempt_index: int,
    game_size: int,
    requested_count: int,
    history: Sequence[Any] | None,
    seed: int | None,
    batch_label: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Ações corretivas determinísticas entre tentativas externas de recuperação."""
    actions: list[str] = []
    working = [dict(game) for game in pool]
    size = int(game_size)

    if is_structural_policy_15d_format(size):
        working, _ = build_ml_structural_15d_pool(
            working,
            history=history,
            seed=(abs(int(seed or 0)) + (attempt_index * 131) + 17) % 1_000_003,
        )
        actions.append("expandir_pool_estrutural_15d")

    if failed_stage in {STAGE_DIVERSITY, STAGE_CONFORMITY}:
        working = _filter_near_clone_games(working, game_size=size)
        actions.append("anti_clone_forte")
        working, replaced = _force_material_top_slice_substitution(
            working,
            game_size=size,
            requested_count=requested_count,
            batch_label=batch_label,
            attempt_index=attempt_index,
        )
        if replaced:
            actions.append("substituicao_material_top_slice")
        working = _penalize_dominant_families(
            working,
            requested_count=requested_count,
            attempt_index=attempt_index,
        )
        actions.append("penalizar_familia_estrutural_dominante")

    if failed_stage == STAGE_COVERAGE:
        working = _boost_subcovered_dezenas(
            working,
            game_size=size,
            requested_count=requested_count,
            batch_label=batch_label,
            attempt_index=attempt_index,
        )
        actions.append("reforco_dezenas_subcobertas")

    if failed_stage == STAGE_CONFORMITY and is_structural_policy_15d_format(size):
        actions.append("descartar_nao_conformes_via_expansao")

    return working, list(dict.fromkeys(actions))


def build_pre_gp_recovery_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    attempt_results = []
    for row in list(source.get("attempt_results") or []):
        if not isinstance(row, dict):
            continue
        attempt_results.append(
            {
                "attempt_index": int(row.get("attempt_index", 0) or 0),
                "gp_closure_allowed": bool(row.get("gp_closure_allowed")),
                "failed_stage": str(row.get("failed_stage") or ""),
                "metrics": dict(row.get("metrics") or {}),
                "recovery_actions": list(row.get("recovery_actions") or [])[:12],
                "material_substitutions": int(row.get("material_substitutions", 0) or 0),
            }
        )
    return {
        "mission_id": MISSION_ID,
        "recovery_version": RECOVERY_VERSION,
        "internal_recovery_attempted": bool(source.get("internal_recovery_attempted")),
        "internal_recovery_attempts": int(source.get("internal_recovery_attempts", 0) or 0),
        "internal_recovery_success": bool(source.get("internal_recovery_success")),
        "internal_recovery_failed_reason": str(source.get("internal_recovery_failed_reason") or ""),
        "final_gp_delivered": bool(source.get("final_gp_delivered")),
        "max_recovery_attempts": int(
            source.get("max_recovery_attempts", DEFAULT_MAX_RECOVERY_ATTEMPTS) or 0
        ),
        "best_attempt_selected": source.get("best_attempt_selected"),
        "best_attempt_metrics": dict(source.get("best_attempt_metrics") or {}),
        "attempt_results": attempt_results,
        "successful_attempt_index": source.get("successful_attempt_index"),
        "recovery_exhausted": bool(source.get("recovery_exhausted")),
    }


def merge_recovery_into_hierarchy_bundle(
    hierarchy_bundle: Mapping[str, Any],
    recovery_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(hierarchy_bundle)
    merged["pre_gp_recovery"] = build_pre_gp_recovery_trace(recovery_bundle)
    merged["internal_recovery_attempted"] = bool(recovery_bundle.get("internal_recovery_attempted"))
    merged["internal_recovery_attempts"] = int(recovery_bundle.get("internal_recovery_attempts", 0) or 0)
    merged["internal_recovery_success"] = bool(recovery_bundle.get("internal_recovery_success"))
    merged["final_gp_delivered"] = bool(recovery_bundle.get("final_gp_delivered"))
    return enrich_hierarchy_bundle(merged)


def execute_pre_gp_recovery_cycle(
    games: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    history: Sequence[Any] | None = None,
    seed: int | None = None,
    batch_label: str | None = None,
    calibration_plan: Mapping[str, Any] | None = None,
    event_context: Mapping[str, Any] | None = None,
    compose_gp: Callable[..., list[dict[str, Any]]] | None = None,
    compose_config: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Executa loop M-ML-074 antes de expor bloqueio hierárquico ao usuário."""
    max_attempts = get_max_recovery_attempts()
    pool = [dict(game) for game in games]
    attempt_results: list[dict[str, Any]] = []
    best_attempt_index = 1
    best_score = -1.0
    best_metrics: dict[str, Any] = {}
    best_pool = list(pool)
    best_hierarchy: dict[str, Any] = {}
    best_missions: dict[str, Any] = {}

    successful_pool: list[dict[str, Any]] | None = None
    successful_hierarchy: dict[str, Any] | None = None
    successful_missions: dict[str, Any] | None = None
    successful_attempt_index: int | None = None
    current_plan = dict(calibration_plan or {})

    for attempt_index in range(1, max_attempts + 1):
        pool, hierarchy_bundle, mission_bundles = execute_ml_operational_hierarchy(
            pool,
            game_size=game_size,
            requested_count=requested_count,
            history=history,
            seed=(abs(int(seed or 0)) + attempt_index - 1) if seed is not None else None,
            batch_label=batch_label,
            calibration_plan=current_plan,
            event_context=event_context,
            compose_gp=compose_gp,
            compose_config=compose_config,
        )
        metrics = _attempt_metrics_snapshot(
            pool,
            game_size=game_size,
            requested_count=requested_count,
            batch_label=batch_label,
            hierarchy_bundle=hierarchy_bundle,
        )
        score = _score_attempt(metrics)
        failed_stage = resolve_failed_hierarchy_stage(hierarchy_bundle)
        attempt_row = {
            "attempt_index": attempt_index,
            "gp_closure_allowed": bool(hierarchy_bundle.get("gp_closure_allowed")),
            "failed_stage": failed_stage,
            "metrics": metrics,
            "recovery_actions": [],
            "material_substitutions": 0,
            "attempt_score": score,
        }
        attempt_results.append(attempt_row)

        if score > best_score:
            best_score = score
            best_attempt_index = attempt_index
            best_metrics = dict(metrics)
            best_pool = [dict(game) for game in pool]
            best_hierarchy = dict(hierarchy_bundle)
            best_missions = dict(mission_bundles)

        if hierarchy_bundle.get("gp_closure_allowed"):
            successful_pool = [dict(game) for game in pool]
            successful_hierarchy = dict(hierarchy_bundle)
            successful_missions = dict(mission_bundles)
            successful_attempt_index = attempt_index
            break

        if attempt_index >= max_attempts:
            break

        pool, recovery_actions = apply_deterministic_recovery_action(
            pool,
            failed_stage=failed_stage or STAGE_DIVERSITY,
            attempt_index=attempt_index,
            game_size=game_size,
            requested_count=requested_count,
            history=history,
            seed=seed,
            batch_label=batch_label,
        )
        attempt_row["recovery_actions"] = list(recovery_actions)
        attempt_row["material_substitutions"] = int(
            sum(1 for game in pool if game.get("pre_gp_recovery_promoted"))
        )
        current_plan = _escalate_calibration_plan(
            current_plan,
            failed_stage=failed_stage or STAGE_DIVERSITY,
            attempt_index=attempt_index,
        )

    success = successful_hierarchy is not None
    if success:
        final_pool = list(successful_pool or [])
        final_hierarchy = dict(successful_hierarchy or {})
        final_missions = dict(successful_missions or {})
    else:
        final_pool = list(best_pool)
        final_hierarchy = dict(best_hierarchy)
        final_missions = dict(best_missions)

    failed_reason = ""
    if not success:
        failed_reason = str(
            final_hierarchy.get("blocking_reason")
            or (final_hierarchy.get("stage_failures") or ["etapas 1–3 reprovadas"])[0]
        )

    recovery_bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "recovery_version": RECOVERY_VERSION,
        "internal_recovery_attempted": True,
        "internal_recovery_attempts": len(attempt_results),
        "internal_recovery_success": success,
        "internal_recovery_failed_reason": failed_reason,
        "final_gp_delivered": success,
        "max_recovery_attempts": max_attempts,
        "best_attempt_selected": best_attempt_index,
        "best_attempt_metrics": best_metrics,
        "attempt_results": attempt_results,
        "successful_attempt_index": successful_attempt_index,
        "recovery_exhausted": not success,
    }

    final_hierarchy = merge_recovery_into_hierarchy_bundle(final_hierarchy, recovery_bundle)
    return final_pool, final_hierarchy, final_missions, recovery_bundle
