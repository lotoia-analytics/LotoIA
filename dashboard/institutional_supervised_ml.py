"""ML operacional supervisionado CORE_002 — estado institucional (M-ML-045)."""

from __future__ import annotations

from typing import Any

from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
    is_generation_enabled,
    is_sovereign_core_label,
)
from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES

MISSION_ID = "M-ML-045"
ENV_ML_OPERATIONAL_ENABLED = "LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED"

SUPERVISED_ML_STATUS_ACTIVE = "ML OPERACIONAL SUPERVISIONADO — ATIVO SOBRE CORE_002"
SUPERVISED_ML_STATUS_BLOCKED = "BLOQUEADO"

SUPERVISED_ML_DISCLAIMER = (
    "ML operacional supervisionado ativo exclusivamente sobre geração soberana CORE_002. "
    "Pontua, reranqueia, diagnostica e prioriza dentro do path generate_best_games — "
    "sem alterar LEI15_CORE_002, Lei 15A ou caminhos legados."
)

SUPERVISED_ML_GOVERNANCE_ALERT = (
    "Path autorizado: generate_best_games("
    f"batch_label={BATCH_LABEL}, ml_enabled=True). "
    "Geração por ML fora do CORE_002 permanece proibida."
)

ML_OPERATIONAL_PROHIBITIONS: tuple[str, ...] = (
    "Alterar LEI15_CORE_002 ou papéis/pesos soberanos",
    "Reativar Lei 15A ou mecânica 15+1/15+2",
    "Gerar via public_app ou batch_label=None",
    "Usar _generate_direct_15_games ou geração legada",
    "Executar purge ou alterar schema sem missão",
    "Decidir com hit isolado ou promover política automaticamente",
    "Operar ML sem decision trace, attribution ou persistência PostgreSQL",
)


def is_ml_operational_enabled() -> bool:
    import os

    raw = os.getenv(ENV_ML_OPERATIONAL_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def is_adm_supervised_ml_active() -> bool:
    return is_generation_enabled() and is_ml_operational_enabled()


def supervised_ml_status_label() -> str:
    if is_adm_supervised_ml_active():
        return SUPERVISED_ML_STATUS_ACTIVE
    return SUPERVISED_ML_STATUS_BLOCKED


def resolve_adm_ml_enabled(
    *,
    ml_enabled: bool | None = None,
    batch_label: str | None = None,
) -> bool:
    """Resolve ml_enabled para geração ADM — default operacional quando flag ativa."""
    if ml_enabled is False:
        return False
    if not is_ml_operational_enabled():
        if ml_enabled is True:
            raise RuntimeError(
                "[M-ML-045] ml_enabled=True rejeitado — ML operacional supervisionado desativado "
                f"({ENV_ML_OPERATIONAL_ENABLED}=0)."
            )
        return False
    if not is_generation_enabled():
        if ml_enabled is True:
            raise RuntimeError(
                "[M-ML-045] ml_enabled=True rejeitado — geração soberana CORE_002 inativa."
            )
        return False
    if ml_enabled is True or ml_enabled is None:
        enforce_ml_enabled_for_batch(batch_label=batch_label, ml_enabled=True)
        return True
    return False


def enforce_ml_enabled_for_batch(*, batch_label: str | None, ml_enabled: bool) -> None:
    if not ml_enabled:
        return
    if batch_label is None or not str(batch_label).strip():
        raise RuntimeError(
            "[M-ML-045] ml_enabled=True rejeitado — batch_label=None proibido no contexto ADM."
        )
    normalized = str(batch_label).strip().upper()
    if not is_sovereign_core_label(normalized):
        raise RuntimeError(
            f"[M-ML-045] ml_enabled=True rejeitado — label não soberano: {normalized!r}. "
            f"Obrigatório: {BATCH_LABEL}."
        )


def _final_score_value(game: dict[str, Any]) -> float:
    final_score = game.get("final_score")
    if isinstance(final_score, dict):
        return float(final_score.get("final_score", 0.0) or 0.0)
    return float(final_score or 0.0)


def build_game_decision_trace(game: dict[str, Any], *, ml_enabled: bool) -> dict[str, Any]:
    score_ml = float(game.get("score_ml", 0.0) or 0.0)
    reranked_by = ["score_ml_supervised"] if ml_enabled and "score_ml" in game else []
    return {
        "accepted_by": ["LEI15_CORE_002", "generate_best_games"],
        "promoted_by": ["compose_sovereign_gp"],
        "reranked_by": reranked_by or ["hybrid_final_score"],
        "filtered_by": ["sovereign_pool", "anti_clone_gp"],
        "rejected_by": [],
        "ml_enabled": bool(ml_enabled),
        "score_ml": round(score_ml, 6) if ml_enabled else None,
        "final_selection_reason": "sovereign_core_002_supervised_ml" if ml_enabled else "sovereign_core_002",
        "lei15_core_002_preserved": True,
        "lei15a_applied": False,
    }


def build_game_feature_attribution(game: dict[str, Any]) -> dict[str, Any]:
    details = game.get("score_ml_details")
    if isinstance(details, dict) and details.get("attribution"):
        return {
            "score_ml": round(float(details.get("score_ml", 0.0) or 0.0), 6),
            "model_version": str(details.get("model_version", "")),
            "feature_schema_version": str(details.get("feature_schema_version", "")),
            "attribution": list(details.get("attribution") or []),
            "features": dict(details.get("features") or {}),
            "calibration": dict(details.get("calibration") or {}),
        }
    return {
        "score_ml": None,
        "final_score": round(_final_score_value(game), 4),
        "quadra_found": int(
            (game.get("quadra_score") or {}).get("found_quadras", 0)
            if isinstance(game.get("quadra_score"), dict)
            else 0
        ),
        "attribution": [],
        "features": {},
    }


def build_game_generation_lineage(game: dict[str, Any], *, batch_label: str) -> dict[str, Any]:
    return {
        "origin_pipeline": [
            "build_sovereign_pool",
            "rerank_games" if game.get("ml_enabled") else "hybrid_ranking",
            "compose_sovereign_gp",
        ],
        "batch_label": batch_label,
        "generation_path": str(game.get("generation_path") or "LEI15_CORE_002"),
        "profile_type": str(game.get("profile_type") or ""),
        "lei15_core_002_applied": bool(game.get("lei15_core_002_applied", True)),
        "legacy_path_blocked": True,
        "public_app_blocked": True,
    }


def build_supervised_ml_trace_for_games(
    games: list[dict[str, Any]],
    *,
    batch_label: str,
    ml_enabled: bool,
) -> dict[str, Any]:
    traces = [build_game_decision_trace(game, ml_enabled=ml_enabled) for game in games]
    attributions = [build_game_feature_attribution(game) for game in games]
    lineages = [build_game_generation_lineage(game, batch_label=batch_label) for game in games]
    scored = sum(1 for game in games if game.get("score_ml") is not None)
    return {
        "decision_trace": traces,
        "feature_attribution": attributions,
        "generation_lineage": lineages,
        "ml_scored_games": scored,
        "ml_total_games": len(games),
        "ml_six_bases_reading": build_ml_six_bases_operational_summary(),
    }


def build_ml_six_bases_operational_summary() -> list[dict[str, str]]:
    roles = {
        "forca_acerto": "Pontua e reranqueia — hit isolado ≠ veredicto",
        "diversidade": "Classifica risco de colapso estrutural no lote",
        "baixa_redundancia": "Diagnostica overlap e clones",
        "controle_prefixo_sufixo": "Alerta vícios nas faixas 01–03 e 22–25",
        "cobertura_dezenas_criticas": "Observa blind spots — cobertura ≠ contagem cega",
        "estabilidade_multi_concurso": "Apoia leitura walk-forward supervisionada",
    }
    return [
        {
            "base": BASE_LABELS_PT[name],
            "papel_ml_operacional": roles[name],
            "decisao": "ML informa dentro do CORE_002 — Núcleo avaliado pelas 6 bases",
        }
        for name in BASE_NAMES
    ]


def build_supervised_ml_activation_snapshot() -> dict[str, object]:
    active = is_adm_supervised_ml_active()
    return {
        "mission_id": MISSION_ID,
        "core_id": "LEI15_CORE_002",
        "batch_label": BATCH_LABEL,
        "ml_operational_active": active,
        "ml_operational_status": supervised_ml_status_label(),
        "env_var": ENV_ML_OPERATIONAL_ENABLED,
        "env_value_expected": "1" if active else "0",
        "generation_env_var": ENV_GENERATION_ENABLED,
        "ml_enabled_default": active,
        "sovereign_path": "generate_best_games",
        "ml_layer": "score_ml + rerank_games (subordinado ao híbrido estrutural)",
        "persistence": "PostgreSQL — generation_events / generated_games + trace ML",
        "prohibitions": list(ML_OPERATIONAL_PROHIBITIONS),
    }


def build_supervised_ml_persistence_bundle(
    games: list[dict[str, Any]],
    *,
    batch_label: str,
    ml_enabled: bool,
) -> dict[str, Any]:
    trace = build_supervised_ml_trace_for_games(
        games,
        batch_label=batch_label,
        ml_enabled=ml_enabled,
    )
    return {
        "ml_enabled": bool(ml_enabled),
        "ml_operational_status": supervised_ml_status_label() if ml_enabled else SUPERVISED_ML_STATUS_BLOCKED,
        "policy_mode": "M-ML-045_SUPERVISED_OPERATIONAL" if ml_enabled else "M-GER-044_SOVEREIGN_CONTROLLED",
        "supervised_ml_mission": MISSION_ID,
        **trace,
    }
