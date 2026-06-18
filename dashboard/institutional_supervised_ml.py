"""ML operacional supervisionado CORE_002 — estado institucional (M-ML-045 / M-ML-054 / M-ML-VIS-053)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GeneratedGame,
    GenerationEvent,
    get_session,
)
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
    core_002_batch_label_game_size,
    is_generation_enabled,
    is_sovereign_core_label,
)
from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES
from lotoia.ml.supervised_output_calibration import (
    CALIBRATION_ENGINE_ROLE,
    CALIBRATION_VERSION,
    MISSION_ID as CALIBRATION_MISSION_ID,
    STATUS_ACTIVE as CALIBRATION_STATUS_ACTIVE,
)

MISSION_ID = "M-ML-045"
VIS_MISSION_ID = "M-ML-VIS-053"
OPERATIONAL_PANEL_SOURCE = "postgresql"
OPERATIONAL_PANEL_TABLES = "generation_events / generated_games"
EMPTY_ML_EVENTS_MESSAGE = (
    "Nenhum evento ML operacional supervisionado encontrado no PostgreSQL."
)
ENV_ML_OPERATIONAL_ENABLED = "LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED"

CONSTITUTIONAL_BLOCKS: tuple[str, ...] = (
    "BLK-CORE002-001",
    "BLK-LEI15A-001",
    "BLK-PURGE-001",
    "BLK-PUBLIC-APP-001",
    "BLK-LEGACY-GEN-001",
    "BLK-ML-FREE-001",
    "BLK-ML-NO-TRACE-001",
)

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
    calibration_applied = bool(game.get("calibration_applied"))
    reranked_by: list[str] = []
    if ml_enabled and "score_ml" in game:
        reranked_by.append("score_ml_supervised")
    if calibration_applied:
        reranked_by.append("supervised_output_calibration")
    if ml_enabled and calibration_applied:
        final_reason = "sovereign_core_002_supervised_ml_calibration"
    elif ml_enabled:
        final_reason = "sovereign_core_002_supervised_ml"
    else:
        final_reason = "sovereign_core_002"
    trace = {
        "accepted_by": ["LEI15_CORE_002", "generate_best_games"],
        "promoted_by": ["compose_sovereign_gp"],
        "reranked_by": reranked_by or ["hybrid_final_score"],
        "filtered_by": ["sovereign_pool", "anti_clone_gp"],
        "rejected_by": [],
        "ml_enabled": bool(ml_enabled),
        "score_ml": round(score_ml, 6) if ml_enabled else None,
        "final_selection_reason": final_reason,
        "lei15_core_002_preserved": True,
        "lei15a_applied": False,
        "calibration_applied": calibration_applied,
    }
    if calibration_applied:
        trace.update(
            {
                "calibrated_by": ["apply_supervised_output_calibration"],
                "calibration_version": CALIBRATION_VERSION,
                "calibration_mission": CALIBRATION_MISSION_ID,
                "ml_calibration_status": str(game.get("ml_calibration_status") or ""),
                "ml_calibration_net": float(game.get("ml_calibration_net", 0.0) or 0.0),
                "ml_calibration_penalty": float(game.get("ml_calibration_penalty", 0.0) or 0.0),
                "ml_calibration_boost": float(game.get("ml_calibration_boost", 0.0) or 0.0),
                "ml_calibration_actions": list(game.get("ml_calibration_actions") or []),
            }
        )
    return trace


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
    origin_pipeline = [
        "build_sovereign_pool",
        "rerank_games" if game.get("ml_enabled") else "hybrid_ranking",
    ]
    if game.get("calibration_applied"):
        origin_pipeline.append("apply_supervised_output_calibration")
    origin_pipeline.append("compose_sovereign_gp")
    return {
        "origin_pipeline": origin_pipeline,
        "batch_label": batch_label,
        "generation_path": str(game.get("generation_path") or "LEI15_CORE_002"),
        "profile_type": str(game.get("profile_type") or ""),
        "lei15_core_002_applied": bool(game.get("lei15_core_002_applied", True)),
        "calibration_applied": bool(game.get("calibration_applied")),
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


def resolve_ml_operational_status_label(*, calibration_applied: bool, ml_enabled: bool) -> str:
    if calibration_applied and ml_enabled:
        return CALIBRATION_STATUS_ACTIVE
    if ml_enabled:
        return supervised_ml_status_label()
    return SUPERVISED_ML_STATUS_BLOCKED


def build_calibration_event_summary(calibration_bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    bundle = dict(calibration_bundle or {})
    if not bundle.get("calibration_applied"):
        return {"calibration_applied": False, "calibration_engine_role": "DISABLED"}
    diagnostics = dict(bundle.get("diagnostics") or {})
    issues = list(diagnostics.get("issues") or [])
    return {
        "calibration_applied": True,
        "calibration_version": str(bundle.get("calibration_version") or CALIBRATION_VERSION),
        "calibration_engine_role": str(
            bundle.get("calibration_engine_role") or CALIBRATION_ENGINE_ROLE
        ),
        "calibration_mission": str(bundle.get("mission_id") or CALIBRATION_MISSION_ID),
        "ml_operational_status": str(
            bundle.get("ml_operational_status") or CALIBRATION_STATUS_ACTIVE
        ),
        "action_taken": "supervised_output_calibration",
        "redundancy_penalty": float(bundle.get("redundancy_penalty", 0.0) or 0.0),
        "prefix_penalty": int(bundle.get("prefix_penalty", 0) or 0),
        "suffix_penalty": int(bundle.get("suffix_penalty", 0) or 0),
        "missing_numbers_boost": int(bundle.get("missing_numbers_boost", 0) or 0),
        "critical_coverage_boost": int(bundle.get("critical_coverage_boost", 0) or 0),
        "diversity_score": float(bundle.get("diversity_score", 0.0) or 0.0),
        "final_ml_score_avg": float(bundle.get("final_ml_score_avg", 0.0) or 0.0),
        "calibration_actions_applied": list(bundle.get("actions_applied") or []),
        "calibration_diagnostics": diagnostics,
        "batch_status_counts": dict(bundle.get("batch_status_counts") or {}),
        "issue_count": int(diagnostics.get("issue_count", 0) or 0),
        "issues_detected": [
            str(row.get("descricao") or row.get("tipo") or "")
            for row in issues
            if isinstance(row, dict)
        ][:20],
        "calibration_decision_trace": {
            "why": "Calibração supervisionada automática — problemas estruturais detectados no pool",
            "issues_count": len(issues),
            "actions_count": len(bundle.get("actions_applied") or []),
            "lei15_core_002_preserved": bool(bundle.get("lei15_core_002_preserved", True)),
            "lei15a_applied": bool(bundle.get("lei15a_applied", False)),
        },
        "calibration_feature_attribution": {
            "calibration_version": str(bundle.get("calibration_version") or CALIBRATION_VERSION),
            "redundancy_penalty_total": float(bundle.get("redundancy_penalty", 0.0) or 0.0),
            "prefix_penalty_count": int(bundle.get("prefix_penalty", 0) or 0),
            "suffix_penalty_count": int(bundle.get("suffix_penalty", 0) or 0),
            "missing_numbers_boost_count": int(bundle.get("missing_numbers_boost", 0) or 0),
            "critical_coverage_boost_count": int(bundle.get("critical_coverage_boost", 0) or 0),
        },
        "six_bases_summary": build_calibration_six_bases_summary(diagnostics),
    }


def build_calibration_six_bases_summary(diagnostics: Mapping[str, Any]) -> list[dict[str, str]]:
    issues = list(diagnostics.get("issues") or [])
    issue_types = {
        str(row.get("tipo") or "")
        for row in issues
        if isinstance(row, dict)
    }
    redundancy = dict(diagnostics.get("redundancy") or {})
    before_after = {
        "forca_acerto": ("observado", "observado"),
        "diversidade": (
            "fraca" if "quase_repetidos_alto" in issue_types else "estável",
            "ajustada_por_calibracao",
        ),
        "baixa_redundancia": (
            "alerta" if redundancy.get("sobreposicao_maxima", 0) else "ok",
            "penalizada_por_calibracao",
        ),
        "controle_prefixo_sufixo": (
            "alerta"
            if {"prefixo_excessivo", "sufixo_excessivo"} & issue_types
            else "ok",
            "limitada_por_calibracao",
        ),
        "cobertura_dezenas_criticas": (
            "alerta" if "dezena_subcoberta" in issue_types else "ok",
            "reforcada_por_calibracao",
        ),
        "estabilidade_multi_concurso": ("observado", "observado"),
    }
    return [
        {
            "base": BASE_LABELS_PT[name],
            "status_antes": before_after[name][0],
            "status_depois": before_after[name][1],
            "avaliacao_final": "ML calibrou saída sem alterar CORE_002",
        }
        for name in BASE_NAMES
    ]


def build_supervised_ml_persistence_bundle(
    games: list[dict[str, Any]],
    *,
    batch_label: str,
    ml_enabled: bool,
    calibration_bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    trace = build_supervised_ml_trace_for_games(
        games,
        batch_label=batch_label,
        ml_enabled=ml_enabled,
    )
    calibration_summary = build_calibration_event_summary(calibration_bundle)
    calibration_applied = bool(calibration_summary.get("calibration_applied"))
    if calibration_applied:
        policy_mode = "M-ML-054_SUPERVISED_OUTPUT_CALIBRATION"
        supervised_mission = CALIBRATION_MISSION_ID
    elif ml_enabled:
        policy_mode = "M-ML-045_SUPERVISED_OPERATIONAL"
        supervised_mission = MISSION_ID
    else:
        policy_mode = "M-GER-044_SOVEREIGN_CONTROLLED"
        supervised_mission = MISSION_ID
    six_bases = list(trace.get("ml_six_bases_reading") or [])
    if calibration_applied:
        six_bases = list(calibration_summary.get("six_bases_summary") or six_bases)
    return {
        "ml_enabled": bool(ml_enabled),
        "ml_operational_status": resolve_ml_operational_status_label(
            calibration_applied=calibration_applied,
            ml_enabled=ml_enabled,
        ),
        "policy_mode": policy_mode,
        "supervised_ml_mission": supervised_mission,
        **trace,
        **calibration_summary,
        "ml_six_bases_reading": six_bases,
    }


def _resolve_event_card_format(event: GenerationEvent, context: dict[str, Any]) -> int:
    for key in ("selected_card_format", "card_format", "format_cartao", "formato_cartao", "quantidade_final"):
        raw = context.get(key)
        if raw is not None and str(raw).strip().isdigit():
            return int(raw)
    label_size = core_002_batch_label_game_size(str(getattr(event, "analysis_batch_label", "") or ""))
    if label_size is not None:
        return int(label_size)
    return 15


def _extract_trace_status(context: dict[str, Any]) -> str:
    traces = list(context.get("decision_trace") or [])
    if traces:
        return "persistido"
    return "ausente"


def _extract_attribution_status(context: dict[str, Any]) -> str:
    attributions = list(context.get("feature_attribution") or [])
    if not attributions:
        return "ausente"
    for row in attributions:
        if isinstance(row, dict) and (row.get("attribution") or row.get("score_ml") is not None):
            return "persistido"
    return "ausente"


def _extract_six_bases_status(context: dict[str, Any]) -> str:
    rows = list(context.get("ml_six_bases_reading") or [])
    return "persistido" if rows else "ausente"


def _summarize_decision_trace(traces: list[dict[str, Any]]) -> dict[str, Any]:
    if not traces:
        return {"status": "ausente", "total_jogos": 0, "sample": None}
    sample = dict(traces[0]) if isinstance(traces[0], dict) else {}
    ml_enabled_count = sum(1 for row in traces if isinstance(row, dict) and row.get("ml_enabled"))
    return {
        "status": "persistido",
        "total_jogos": len(traces),
        "ml_enabled_count": ml_enabled_count,
        "sample": {
            "accepted_by": sample.get("accepted_by"),
            "reranked_by": sample.get("reranked_by"),
            "final_selection_reason": sample.get("final_selection_reason"),
            "score_ml": sample.get("score_ml"),
            "lei15_core_002_preserved": sample.get("lei15_core_002_preserved"),
            "lei15a_applied": sample.get("lei15a_applied"),
        },
    }


def _summarize_feature_attribution(attributions: list[dict[str, Any]]) -> dict[str, Any]:
    if not attributions:
        return {"status": "ausente", "total_jogos": 0, "top_factors": [], "sample": None}
    top_factors: list[dict[str, Any]] = []
    sample = None
    for row in attributions:
        if not isinstance(row, dict):
            continue
        if sample is None:
            sample = {
                "score_ml": row.get("score_ml"),
                "model_version": row.get("model_version"),
                "feature_schema_version": row.get("feature_schema_version"),
            }
        for factor in list(row.get("attribution") or [])[:5]:
            if isinstance(factor, dict) and factor not in top_factors:
                top_factors.append(factor)
            if len(top_factors) >= 5:
                break
        if len(top_factors) >= 5:
            break
    return {
        "status": "persistido" if sample else "ausente",
        "total_jogos": len(attributions),
        "top_factors": top_factors,
        "sample": sample,
    }


def load_supervised_ml_operational_events_from_db(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Lista generation_events CORE_002 com ml_enabled=True (fonte soberana PostgreSQL)."""
    events: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        rows = (
            session.query(GenerationEvent)
            .filter(GenerationEvent.ml_enabled == 1)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(max(1, int(limit)) * 5)
            .all()
        )
        for event in rows:
            batch_label = str(getattr(event, "analysis_batch_label", "") or "").strip()
            if not is_sovereign_core_label(batch_label):
                continue
            ge_id = int(event.id or 0)
            if ge_id <= 0:
                continue
            context = dict(getattr(event, "context_json", {}) or {})
            games_count = int(
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == ge_id)
                .count()
            )
            ml_scored_games = int(context.get("ml_scored_games", 0) or 0)
            if ml_scored_games <= 0 and games_count > 0:
                ml_scored_games = games_count
            events.append(
                {
                    "generation_event_id": ge_id,
                    "batch_label": batch_label,
                    "ml_enabled": True,
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "requested_count": int(context.get("selected_quantity", 0) or 0),
                    "persisted_games": games_count,
                    "ml_scored_games": ml_scored_games,
                    "card_format": _resolve_event_card_format(event, context),
                    "decision_trace_status": _extract_trace_status(context),
                    "feature_attribution_status": _extract_attribution_status(context),
                    "ml_six_bases_status": _extract_six_bases_status(context),
                    "supervised_ml_mission": str(context.get("supervised_ml_mission") or MISSION_ID),
                    "calibration_applied": bool(context.get("calibration_applied")),
                }
            )
            if len(events) >= max(1, int(limit)):
                break
    return events


def build_supervised_ml_operational_event_detail(
    db_path: Path | str,
    generation_event_id: int,
) -> dict[str, Any] | None:
    """Detalhe operacional de um generation_event ML (PostgreSQL only)."""
    selected_id = int(generation_event_id or 0)
    if selected_id <= 0:
        return None
    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == selected_id).one_or_none()
        if event is None or int(event.ml_enabled or 0) != 1:
            return None
        batch_label = str(getattr(event, "analysis_batch_label", "") or "").strip()
        if not is_sovereign_core_label(batch_label):
            return None
        context = dict(getattr(event, "context_json", {}) or {})
        game_rows = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == selected_id)
            .order_by(GeneratedGame.game_index.asc())
            .all()
        )
    traces = list(context.get("decision_trace") or [])
    if not traces:
        traces = [
            dict(getattr(row, "context_json", {}) or {}).get("decision_trace")
            for row in game_rows
            if isinstance(getattr(row, "context_json", None), dict)
            and (getattr(row, "context_json", {}) or {}).get("decision_trace")
        ]
        traces = [dict(row) for row in traces if isinstance(row, dict)]
    attributions = list(context.get("feature_attribution") or [])
    if not attributions:
        attributions = [
            dict(getattr(row, "context_json", {}) or {}).get("feature_attribution")
            for row in game_rows
            if isinstance(getattr(row, "context_json", None), dict)
            and (getattr(row, "context_json", {}) or {}).get("feature_attribution")
        ]
        attributions = [dict(row) for row in attributions if isinstance(row, dict)]
    six_bases = list(context.get("ml_six_bases_reading") or [])
    if not six_bases:
        six_bases = build_ml_six_bases_operational_summary()
    calibration_summary = {
        "calibration_applied": bool(context.get("calibration_applied")),
        "calibration_version": str(context.get("calibration_version") or ""),
        "calibration_engine_role": str(context.get("calibration_engine_role") or "DISABLED"),
        "calibration_diagnostics": dict(context.get("calibration_diagnostics") or {}),
        "calibration_actions_applied": list(context.get("calibration_actions_applied") or []),
        "calibration_decision_trace": dict(context.get("calibration_decision_trace") or {}),
        "calibration_feature_attribution": dict(
            context.get("calibration_feature_attribution") or {}
        ),
        "redundancy_penalty": float(context.get("redundancy_penalty", 0.0) or 0.0),
        "prefix_penalty": int(context.get("prefix_penalty", 0) or 0),
        "suffix_penalty": int(context.get("suffix_penalty", 0) or 0),
        "missing_numbers_boost": int(context.get("missing_numbers_boost", 0) or 0),
        "critical_coverage_boost": int(context.get("critical_coverage_boost", 0) or 0),
        "diversity_score": float(context.get("diversity_score", 0.0) or 0.0),
        "final_ml_score_avg": float(context.get("final_ml_score_avg", 0.0) or 0.0),
        "issues_detected": list(context.get("issues_detected") or []),
        "batch_status_counts": dict(context.get("batch_status_counts") or {}),
    }
    return {
        "generation_event_id": selected_id,
        "batch_label": batch_label,
        "ml_enabled": True,
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
        "requested_count": int(context.get("selected_quantity", 0) or 0),
        "persisted_games": len(game_rows),
        "ml_scored_games": int(context.get("ml_scored_games", 0) or 0) or len(game_rows),
        "card_format": _resolve_event_card_format(event, context),
        "ml_operational_status": str(
            context.get("ml_operational_status")
            or (
                CALIBRATION_STATUS_ACTIVE
                if calibration_summary["calibration_applied"]
                else SUPERVISED_ML_STATUS_ACTIVE
            )
        ),
        "supervised_ml_mission": str(
            context.get("supervised_ml_mission")
            or (CALIBRATION_MISSION_ID if calibration_summary["calibration_applied"] else MISSION_ID)
        ),
        "decision_trace": _summarize_decision_trace(traces),
        "feature_attribution": _summarize_feature_attribution(attributions),
        "ml_six_bases_reading": six_bases,
        "constitutional_blocks": list(CONSTITUTIONAL_BLOCKS),
        **calibration_summary,
    }


def build_supervised_ml_operational_panel_snapshot(
    db_path: Path | str = DEFAULT_DATABASE_PATH,
    *,
    generation_event_id: int | None = None,
    events_limit: int = 10,
) -> dict[str, Any]:
    """Snapshot operacional da Central ML — PostgreSQL como fonte soberana."""
    events = load_supervised_ml_operational_events_from_db(db_path, limit=events_limit)
    selected_id = int(generation_event_id or 0)
    if selected_id <= 0 and events:
        selected_id = int(events[0].get("generation_event_id", 0) or 0)
    selected_event = (
        build_supervised_ml_operational_event_detail(db_path, selected_id)
        if selected_id > 0
        else None
    )
    return {
        "mission_id": VIS_MISSION_ID,
        "source": OPERATIONAL_PANEL_SOURCE,
        "tables": OPERATIONAL_PANEL_TABLES,
        "available": bool(events),
        "ml_operational_active": is_adm_supervised_ml_active(),
        "ml_operational_status": supervised_ml_status_label(),
        "core_id": "LEI15_CORE_002",
        "sovereign_batch_label": BATCH_LABEL,
        "public_app_ml": False,
        "lei15a_operational": False,
        "generation_cmd": False,
        "recalibration_cmd": False,
        "constitutional_blocks": list(CONSTITUTIONAL_BLOCKS),
        "events": events,
        "selected_generation_event_id": selected_id if selected_id > 0 else None,
        "selected_event": selected_event,
        "empty_message": EMPTY_ML_EVENTS_MESSAGE,
    }
