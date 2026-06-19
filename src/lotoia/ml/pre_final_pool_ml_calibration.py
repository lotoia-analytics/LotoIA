"""Calibração ML do pool pré-final format-aware 15D–23D — M-ML-071."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from lotoia.ml.structural_auto_calibration import (
    MISSION_ID as STRUCTURAL_AUTO_MISSION_ID,
    is_structural_auto_calibration_format,
)
from lotoia.ml.structural_policy_15d import (
    MISSION_ID as STRUCTURAL_POLICY_15D_MISSION_ID,
    POLICY_VERSION as STRUCTURAL_POLICY_15D_VERSION,
    is_structural_policy_15d_format,
)
from lotoia.ml.supervised_output_calibration import (
    analyze_pool_structural_issues,
    apply_supervised_output_calibration,
    is_output_calibration_enabled,
    resolve_pool_game_size,
)
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-ML-071"
CALIBRATION_VERSION = "M-ML-071-v1"
ENV_PRE_FINAL_POOL_ML_ENABLED = "LOTOIA_ML_PRE_FINAL_POOL_ENABLED"


def is_pre_final_pool_ml_enabled() -> bool:
    raw = os.getenv(ENV_PRE_FINAL_POOL_ML_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _game_signature(game: Mapping[str, Any]) -> tuple[int, ...]:
    numbers = resolve_cartao_final_from_game(dict(game))
    return tuple(sorted(int(value) for value in numbers))


def _dedupe_pool(games: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[int, ...]] = set()
    for game in games:
        signature = _game_signature(game)
        if not signature or signature in seen:
            continue
        seen.add(signature)
        deduped.append(dict(game))
    return deduped


def _top_gp_signatures(games: Sequence[Mapping[str, Any]], requested_count: int) -> list[tuple[int, ...]]:
    count = max(0, int(requested_count))
    return [_game_signature(game) for game in list(games)[:count]]


def _resolve_pre_final_policy(game_size: int) -> str:
    if is_structural_policy_15d_format(int(game_size)):
        return STRUCTURAL_POLICY_15D_VERSION
    if is_structural_auto_calibration_format(int(game_size)):
        return STRUCTURAL_AUTO_MISSION_ID
    return "NONE"


def _pool_exposure_payload(
    *,
    raw_pool: Sequence[Mapping[str, Any]],
    deduped_pool: Sequence[Mapping[str, Any]],
    requested_count: int,
    game_size: int,
) -> dict[str, Any]:
    return {
        "pre_final_pool_size": len(raw_pool),
        "pre_final_pool_deduped_size": len(deduped_pool),
        "requested_count": int(requested_count),
        "game_size": int(game_size),
        "games_exposed_to_gp": min(len(deduped_pool), max(int(requested_count), 1)),
        "exposure_ratio": round(
            min(len(deduped_pool), max(int(requested_count), 1)) / max(len(deduped_pool), 1),
            4,
        ),
    }


def _metric_snapshot(games: Sequence[Mapping[str, Any]], *, game_size: int, batch_label: str | None) -> dict[str, Any]:
    diagnostics = analyze_pool_structural_issues(
        games,
        game_size=int(game_size),
        batch_label=batch_label,
    )
    redundancy = dict(diagnostics.get("redundancy") or {})
    return {
        "diversity_score": round(
            1.0 - float(redundancy.get("similaridade_media_entre_jogos", 0) or 0),
            4,
        ),
        "similarity_score": float(redundancy.get("similaridade_media_entre_jogos", 0) or 0),
        "issue_count": int(diagnostics.get("issue_count", 0) or 0),
        "redundancy": redundancy,
    }


def apply_pre_final_pool_ml_calibration(
    games: list[dict[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    ml_enabled: bool,
    batch_label: str | None = None,
    calibration_plan: Mapping[str, Any] | None = None,
    event_context: Mapping[str, Any] | None = None,
    baseline_pool: Sequence[Mapping[str, Any]] | None = None,
    compose_gp: Callable[..., list[dict[str, Any]]] | None = None,
    compose_config: Any = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Calibra pool pré-final antes do fechamento do GP soberano."""
    empty_bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "pre_final_pool_ml_enabled": is_pre_final_pool_ml_enabled(),
        "pre_final_calibration_applied": False,
        "pre_final_pool_ml_applied": False,
    }
    if not games:
        return games, empty_bundle

    context_payload = dict(event_context or {})
    resolved_size, size_contract = resolve_pool_game_size(
        games,
        batch_label=batch_label,
        game_size=game_size,
        requested_count=requested_count,
    )
    size = int(resolved_size)
    raw_pool = [dict(game) for game in games]
    baseline = [dict(game) for game in (baseline_pool or raw_pool)]
    deduped_pool = _dedupe_pool(raw_pool)
    policy_label = _resolve_pre_final_policy(size)
    metrics_before = _metric_snapshot(baseline, game_size=size, batch_label=batch_label)

    if not ml_enabled or not is_pre_final_pool_ml_enabled() or not is_output_calibration_enabled():
        return games, {
            **empty_bundle,
            "pre_final_pool_size": len(raw_pool),
            "pre_final_pool_deduped_size": len(deduped_pool),
            "pre_final_calibration_format": f"{size}D",
            "pre_final_calibration_policy": policy_label,
            "metrics_before": metrics_before,
            "metrics_after": metrics_before,
            "pool_exposure": _pool_exposure_payload(
                raw_pool=raw_pool,
                deduped_pool=deduped_pool,
                requested_count=requested_count,
                game_size=size,
            ),
            "game_size_contract": size_contract,
        }

    before_top = _top_gp_signatures(baseline, requested_count)
    calibrated_pool, supervised_bundle = apply_supervised_output_calibration(
        [dict(game) for game in games],
        game_size=size,
        ml_enabled=True,
        calibration_plan=calibration_plan,
        event_context={
            **context_payload,
            "batch_label": batch_label,
            "requested_count": requested_count,
            "game_size_contract": size_contract,
            "pre_final_pool_ml_mission_id": MISSION_ID,
        },
    )
    after_top = _top_gp_signatures(calibrated_pool, requested_count)
    metrics_after = _metric_snapshot(calibrated_pool, game_size=size, batch_label=batch_label)

    baseline_gp_signatures: list[tuple[int, ...]] = []
    calibrated_gp_signatures: list[tuple[int, ...]] = []
    if compose_gp is not None and compose_config is not None:
        try:
            baseline_gp = compose_gp(
                [dict(game) for game in baseline],
                int(requested_count),
                compose_config,
                game_size=size,
            )
            calibrated_gp = compose_gp(
                [dict(game) for game in calibrated_pool],
                int(requested_count),
                compose_config,
                game_size=size,
            )
            baseline_gp_signatures = [_game_signature(game) for game in baseline_gp]
            calibrated_gp_signatures = [_game_signature(game) for game in calibrated_gp]
        except Exception:  # noqa: BLE001 — comparação opcional não deve bloquear geração
            baseline_gp_signatures = []
            calibrated_gp_signatures = []

    candidates_reordered = sum(
        1 for left, right in zip(before_top, after_top, strict=False) if left != right
    )
    gp_changed = (
        baseline_gp_signatures != calibrated_gp_signatures
        if baseline_gp_signatures and calibrated_gp_signatures
        else before_top != after_top
    )
    candidates_replaced = (
        sum(
            1
            for left, right in zip(baseline_gp_signatures, calibrated_gp_signatures, strict=False)
            if left != right
        )
        if baseline_gp_signatures and calibrated_gp_signatures
        else candidates_reordered
    )

    bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "calibration_version": CALIBRATION_VERSION,
        "pre_final_pool_ml_enabled": True,
        "pre_final_pool_ml_applied": True,
        "pre_final_calibration_applied": bool(supervised_bundle.get("calibration_applied")),
        "pre_final_pool_size": len(raw_pool),
        "pre_final_pool_deduped_size": len(deduped_pool),
        "pre_final_calibration_format": f"{size}D",
        "pre_final_calibration_policy": policy_label,
        "requested_count": int(requested_count),
        "game_size": size,
        "game_size_contract": size_contract,
        "pool_exposure": _pool_exposure_payload(
            raw_pool=raw_pool,
            deduped_pool=deduped_pool,
            requested_count=requested_count,
            game_size=size,
        ),
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
        "candidates_reordered": int(candidates_reordered),
        "candidates_replaced": int(candidates_replaced),
        "final_gp_changed_by_ml": bool(gp_changed),
        "actions_applied": list(supervised_bundle.get("actions_applied") or []),
        "final_diversity_score": float(metrics_after.get("diversity_score", 0.0) or 0.0),
        "final_similarity_score": float(metrics_after.get("similarity_score", 0.0) or 0.0),
        "diversity_delta": round(
            float(metrics_after.get("diversity_score", 0.0) or 0.0)
            - float(metrics_before.get("diversity_score", 0.0) or 0.0),
            4,
        ),
        "similarity_delta": round(
            float(metrics_after.get("similarity_score", 0.0) or 0.0)
            - float(metrics_before.get("similarity_score", 0.0) or 0.0),
            4,
        ),
        "supervised_calibration_bundle": dict(supervised_bundle),
        "structural_auto_calibration_mission_id": supervised_bundle.get("structural_auto_calibration_mission_id"),
        "structural_policy_15d_mission_id": supervised_bundle.get("structural_policy_15d_mission_id"),
        "structural_calibration_memory": dict(supervised_bundle.get("structural_calibration_memory") or {}),
    }
    if is_structural_policy_15d_format(size):
        bundle["policy_mission_id"] = STRUCTURAL_POLICY_15D_MISSION_ID
    elif is_structural_auto_calibration_format(size):
        bundle["policy_mission_id"] = STRUCTURAL_AUTO_MISSION_ID

    merged_calibration = {
        **dict(supervised_bundle),
        **bundle,
        "calibration_applied": bool(supervised_bundle.get("calibration_applied")),
        "pre_final_pool_ml_mission_id": MISSION_ID,
    }
    return calibrated_pool, merged_calibration


def finalize_pre_final_gp_outcome(
    bundle: Mapping[str, Any] | None,
    *,
    baseline_gp: Sequence[Mapping[str, Any]] | None,
    final_gp: Sequence[Mapping[str, Any]],
    structural_policy_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Enriquece bundle com efeito real no GP final (pós-compose / pós-política)."""
    payload = dict(bundle or {})
    baseline_signatures = [_game_signature(game) for game in list(baseline_gp or [])]
    final_signatures = [_game_signature(game) for game in list(final_gp or [])]
    if baseline_signatures and final_signatures:
        payload["final_gp_changed_by_ml"] = baseline_signatures != final_signatures
        payload["candidates_replaced"] = sum(
            1
            for left, right in zip(baseline_signatures, final_signatures, strict=False)
            if left != right
        )
    policy_bundle = dict(structural_policy_bundle or {})
    if policy_bundle:
        payload["final_compliance_rate"] = float(policy_bundle.get("compliance_rate", 0.0) or 0.0)
        payload["policy_compliance_status"] = str(policy_bundle.get("policy_compliance_status") or "")
        payload["games_compliant"] = int(policy_bundle.get("games_compliant", 0) or 0)
        payload["games_non_compliant"] = int(policy_bundle.get("games_non_compliant", 0) or 0)
    payload["final_gp_size"] = len(final_gp or [])
    return payload


def build_pre_final_pool_trace(
    bundle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Resumo seguro para persistência/dashboard — sem payload bruto do pool."""
    source = dict(bundle or {})
    metrics_before = dict(source.get("metrics_before") or {})
    metrics_after = dict(source.get("metrics_after") or {})
    return {
        "mission_id": str(source.get("mission_id") or MISSION_ID),
        "pre_final_pool_ml_enabled": bool(source.get("pre_final_pool_ml_enabled")),
        "pre_final_calibration_applied": bool(source.get("pre_final_calibration_applied")),
        "pre_final_pool_size": int(source.get("pre_final_pool_size", 0) or 0),
        "pre_final_pool_deduped_size": int(source.get("pre_final_pool_deduped_size", 0) or 0),
        "pre_final_calibration_format": str(source.get("pre_final_calibration_format") or ""),
        "pre_final_calibration_policy": str(source.get("pre_final_calibration_policy") or ""),
        "requested_count": int(source.get("requested_count", 0) or 0),
        "game_size": int(source.get("game_size", 0) or 0),
        "candidates_reordered": int(source.get("candidates_reordered", 0) or 0),
        "candidates_replaced": int(source.get("candidates_replaced", 0) or 0),
        "final_gp_changed_by_ml": bool(source.get("final_gp_changed_by_ml")),
        "final_compliance_rate": float(source.get("final_compliance_rate", 0.0) or 0.0),
        "final_diversity_score": float(source.get("final_diversity_score", 0.0) or 0.0),
        "final_similarity_score": float(source.get("final_similarity_score", 0.0) or 0.0),
        "diversity_delta": float(source.get("diversity_delta", 0.0) or 0.0),
        "similarity_delta": float(source.get("similarity_delta", 0.0) or 0.0),
        "actions_applied": list(source.get("actions_applied") or [])[:40],
        "pool_exposure": dict(source.get("pool_exposure") or {}),
        "metrics_before": {
            "diversity_score": metrics_before.get("diversity_score"),
            "similarity_score": metrics_before.get("similarity_score"),
            "issue_count": metrics_before.get("issue_count"),
        },
        "metrics_after": {
            "diversity_score": metrics_after.get("diversity_score"),
            "similarity_score": metrics_after.get("similarity_score"),
            "issue_count": metrics_after.get("issue_count"),
        },
        "structural_calibration_memory": dict(source.get("structural_calibration_memory") or {}),
        "policy_compliance_status": str(source.get("policy_compliance_status") or ""),
    }
