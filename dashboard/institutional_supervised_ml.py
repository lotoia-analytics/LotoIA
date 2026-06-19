"""ML operacional supervisionado CORE_002 — estado institucional (M-ML-045 / M-ML-054 / M-ML-VIS-053)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GeneratedGame,
    GenerationEvent,
    get_session,
)
from lotoia.governance.institutional_agent_routing_matrix import (
    MISSION_ID as AGENT_ROUTING_MISSION_ID,
)
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL,
    ENV_GENERATION_ENABLED,
    core_002_batch_label_game_size,
    is_generation_enabled,
    is_sovereign_core_label,
)
from lotoia.governance.batch_operational_scope import is_generation_event_active_reading, summarize_active_reading_exclusions
from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES
from lotoia.ml.pre_final_pool_ml_calibration import (
    MISSION_ID as PRE_FINAL_POOL_MISSION_ID,
    build_pre_final_pool_trace,
)
from lotoia.ml.structural_pool_15d_generator import (
    MISSION_ID as STRUCTURAL_15D_POOL_MISSION_ID,
    build_structural_15d_pool_trace,
)
from lotoia.ml.ml_operational_hierarchy import (
    MISSION_ID as ML_OPERATIONAL_HIERARCHY_MISSION_ID,
    build_ml_operational_hierarchy_trace,
)
from lotoia.ml.supervised_output_calibration import (
    CALIBRATION_ENGINE_ROLE,
    CALIBRATION_VERSION,
    MISSION_ID as CALIBRATION_MISSION_ID,
    STATUS_ACTIVE as CALIBRATION_STATUS_ACTIVE,
    is_output_calibration_enabled,
)
from lotoia.ml.authorized_ml_calibration_plan import classify_calibration_display_flags
from lotoia.observability.card_structure_diagnostics import (
    SCOPE_ALL_OPERATIONAL_CORE_002,
    SCOPE_LABEL_ALL_OPERATIONAL,
    compare_structural_coverage_scopes,
)
from lotoia.observability.coverage_evidence_interpreter import (
    SOVEREIGN_MISSION_ID,
    build_calibration_plan,
    get_structural_coverage_evidence,
    interpret_coverage_evidence,
)

MISSION_ID = "M-ML-045"
VIS_MISSION_ID = "M-ML-VIS-053"
VIS_COCKPIT_MISSION_ID = "M-ML-VIS-056"
VIS_COCKPIT_FIX02_MISSION_ID = "M-ML-VIS-056-FIX-02"
CARD_FORMAT_FILTER_MISSION_ID = "M-ML-071-FIX-01"
OPERATIONAL_GENERATION_FILTER_MISSION_ID = CARD_FORMAT_FILTER_MISSION_ID
VIS_COVERAGE_EVIDENCE_MISSION_ID = "M-ML-VIS-058"
VIS_COVERAGE_FIX01_MISSION_ID = "M-ML-VIS-058-FIX-01"
VIS_COVERAGE_SOVEREIGN_MISSION_ID = SOVEREIGN_MISSION_ID
OVERLAP_FORMAT_MISSION_ID = "M-ML-060"
OVERLAP_FORMAT_MISSION_ID_067 = "M-ML-067"
STRUCTURAL_AUTO_CALIBRATION_MISSION_ID = "M-ML-069"
STRUCTURAL_POLICY_15D_MISSION_ID = "M-ML-070"
PRE_FINAL_POOL_ML_DASHBOARD_MISSION_ID = PRE_FINAL_POOL_MISSION_ID
STRUCTURAL_15D_POOL_DASHBOARD_MISSION_ID = STRUCTURAL_15D_POOL_MISSION_ID
ML_OPERATIONAL_HIERARCHY_DASHBOARD_MISSION_ID = ML_OPERATIONAL_HIERARCHY_MISSION_ID
AGENT_ROUTING_DASHBOARD_MISSION_ID = AGENT_ROUTING_MISSION_ID
ML_VERDICT_MISSION_ID = "M-ML-060-FIX-01"
SOVEREIGN_COVERAGE_SCOPE_LABEL = (
    "Escopo soberano: Cobertura Estrutural — todas as gerações operacionais CORE_002 (PostgreSQL)"
)
AGGREGATE_SCOPE_LABEL = "Escopo analisado: visão geral das gerações oficiais recentes"
AGGREGATE_DIAGNOSIS_HEADLINE = "Diagnóstico geral da saída CORE_002 + ML"
DEFAULT_AGGREGATE_EVENTS_LIMIT = 10
CALIBRATION_SUPERVISED_LABEL = "CALIBRAÇÃO ML SUPERVISIONADA: ATIVA"
RECALIBRATION_OUTPUT_ACTIVE_LABEL = "RECALIBRAÇÃO DE SAÍDA: ATIVA COM SUPERVISÃO"
ML_FREE_RECALIBRATION_BLOCKED = "BLOQUEADA — ML livre fora do CORE_002"
COCKPIT_WORKFLOW_PENDING = "pendente"
COCKPIT_WORKFLOW_AUTHORIZED = "autorizada"
COCKPIT_WORKFLOW_APPLIED = "aplicada"
COCKPIT_WORKFLOW_REJECTED = "rejeitada"
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
        "pre_final_pool_ml_calibration": build_pre_final_pool_trace(bundle),
        "ml_structural_15d_pool": build_structural_15d_pool_trace(
            dict(bundle.get("ml_structural_15d_pool") or {})
        ),
        "ml_operational_hierarchy": build_ml_operational_hierarchy_trace(
            dict(bundle.get("ml_operational_hierarchy") or {})
        ),
        "pre_final_calibration_applied": bool(bundle.get("pre_final_calibration_applied")),
        "pre_final_pool_ml_enabled": bool(bundle.get("pre_final_pool_ml_enabled")),
        "final_gp_changed_by_ml": bool(bundle.get("final_gp_changed_by_ml")),
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
            if not is_generation_event_active_reading(event):
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
                    **classify_calibration_display_flags(context),
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
        "pre_final_pool_ml_calibration": build_pre_final_pool_trace(
            dict(context.get("pre_final_pool_ml_calibration") or {})
        ),
        "ml_structural_15d_pool": build_structural_15d_pool_trace(
            dict(context.get("ml_structural_15d_pool") or {})
        ),
        "ml_operational_hierarchy": build_ml_operational_hierarchy_trace(
            dict(context.get("ml_operational_hierarchy") or {})
        ),
        "pre_final_calibration_applied": bool(context.get("pre_final_calibration_applied")),
        "final_gp_changed_by_ml": bool(context.get("final_gp_changed_by_ml")),
        **classify_calibration_display_flags(context),
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


def is_supervised_output_calibration_active() -> bool:
    return is_adm_supervised_ml_active() and is_output_calibration_enabled()


def resolve_recalibration_display_status() -> dict[str, Any]:
    """Separa ML livre (bloqueada) de calibração supervisionada da saída (ativa)."""
    supervised = is_supervised_output_calibration_active()
    if supervised:
        return {
            "pill_label": "Calibração ML",
            "pill_status": "ATIVA COM SUPERVISÃO",
            "pill_tone": "success",
            "headline": CALIBRATION_SUPERVISED_LABEL,
            "detail": RECALIBRATION_OUTPUT_ACTIVE_LABEL,
            "ml_free_status": ML_FREE_RECALIBRATION_BLOCKED,
            "supervised_calibration_active": True,
            "recalibration_cmd": False,
            "recalibration_free_blocked": True,
        }
    return {
        "pill_label": "Recalibração",
        "pill_status": "BLOQUEADA",
        "pill_tone": "danger",
        "headline": "RECALIBRAÇÃO: BLOQUEADA",
        "detail": "Recalibração livre ou automática fora do CORE_002 permanece bloqueada.",
        "ml_free_status": ML_FREE_RECALIBRATION_BLOCKED,
        "supervised_calibration_active": False,
        "recalibration_cmd": False,
        "recalibration_free_blocked": True,
    }


def resolve_institutional_ml_status_line() -> str:
    if is_supervised_output_calibration_active():
        return "SUPERVISIONADO — calibração de saída ativa (M-ML-054)"
    if is_adm_supervised_ml_active():
        return "SUPERVISIONADO — operacional sobre CORE_002"
    return "ASSISTIVO — diagnóstico — sem efeito operacional automático"


def _issue_types_from_event(event: Mapping[str, Any] | None) -> set[str]:
    if not isinstance(event, Mapping):
        return set()
    diagnostics = dict(event.get("calibration_diagnostics") or {})
    return {
        str(row.get("tipo") or "")
        for row in list(diagnostics.get("issues") or [])
        if isinstance(row, dict)
    }


def build_ml_calibration_recommendations(
    source: Mapping[str, Any] | None,
    *,
    coverage_evidence: Mapping[str, Any] | None = None,
) -> list[str]:
    if isinstance(coverage_evidence, Mapping) and coverage_evidence.get("available"):
        policy_plan = dict(coverage_evidence.get("structural_policy_15d_calibration_plan") or {})
        policy_items = list(policy_plan.get("plan_items") or [])
        policy_violations = list(coverage_evidence.get("policy_violations") or [])
        if policy_items and policy_violations:
            return policy_items[:12]
        plan_items = list(coverage_evidence.get("plan_items") or [])
        if plan_items:
            return plan_items[:12]
        calibration_plan = dict(coverage_evidence.get("calibration_plan") or {})
        plan_items = list(calibration_plan.get("plan_items") or [])
        if plan_items:
            return plan_items[:12]
        recs = list(coverage_evidence.get("acoes_recomendadas") or [])
        if recs:
            return recs[:12]
        interpretation = dict(coverage_evidence.get("interpretation") or {})
        plan_items = list(interpretation.get("plan_items") or [])
        if plan_items:
            return plan_items[:12]
        recs = list(interpretation.get("acoes_recomendadas") or [])
        if recs:
            return recs[:12]

    if not isinstance(source, Mapping):
        return ["Gerar lote CORE_002 com ML ativo para obter diagnóstico estrutural."]

    metrics = dict(source.get("metrics") or {})
    raw_diversity = metrics.get("diversity_score", source.get("diversity_score"))
    diversity_score = float(raw_diversity) if raw_diversity is not None else None
    diversidade = str(metrics.get("diversidade") or metrics.get("diversidade_global") or "")
    has_negative = (
        diversidade == "baixa"
        or (diversity_score is not None and diversity_score < 0.55)
        or str(metrics.get("redundancia") or metrics.get("redundancia_geral") or "") == "alta"
        or int(metrics.get("quase_repetidos", 0) or 0) >= 20
        or int(metrics.get("dezenas_subcobertas", 0) or 0) > 0
        or str(metrics.get("prefixos_sufixos") or "") == "viciados"
        or bool(source.get("issues_preview"))
        or bool(source.get("issue_types"))
        or bool(_issue_types_from_event(source))
    )
    if (
        has_negative
        and not source.get("calibration_applied")
        and (metrics or source.get("aggregate_available"))
    ):
        interpreted = interpret_coverage_evidence(
            metrics if metrics else {"diversity_score": diversity_score or 0.0},
            calibration_applied=bool(source.get("calibration_applied")),
            trace_persistido=False,
        )
        recs = list(interpreted.get("acoes_recomendadas") or [])
        if recs:
            return recs[:6]
        return [
            "Calibração pendente — revisar evidências da Cobertura Estrutural e autorizar ajuste supervisionado."
        ]

    issue_types = set(source.get("issue_types") or []) or _issue_types_from_event(source)
    if not issue_types and source.get("aggregate_available"):
        issue_types = set(source.get("aggregate_issue_types") or [])
    recommendations: list[str] = []
    mapping = {
        "quase_repetidos_alto": "Reduzir quase repetidos — penalizar overlap no pool",
        "similaridade_media_gp_elevada": "Melhorar diversidade por lote — separar cartões similares",
        "sobreposicao_maxima_elevada": "Penalizar sobreposição excessiva entre jogos",
        "prefixo_excessivo": "Penalizar prefixos repetidos (faixa 01–03)",
        "sufixo_excessivo": "Penalizar sufixos repetidos (faixa 22–25)",
        "dezena_subcoberta": "Reforçar dezenas ausentes e subcobertas (7/15/23 críticas)",
        "padrao_ausencia_recorrente": "Equilibrar padrões de ausência recorrentes",
        "diversidade_baixa": "Aumentar diversidade mínima e redistribuir padrões no rerank",
    }
    for issue_type, text in mapping.items():
        if issue_type in issue_types:
            recommendations.append(text)
    if not recommendations and source.get("calibration_applied"):
        recommendations.append("Lote calibrado — validar diversidade e cobertura na próxima geração.")
    elif not recommendations and source.get("aggregate_calibrated_events", 0):
        recommendations.append(
            "Calibração aplicada em gerações recentes — validar diversidade global na próxima geração."
        )
    elif not recommendations and not has_negative:
        recommendations.append("Estrutura estável — manter calibração supervisionada ativa na geração.")
    return recommendations[:6]


def load_ml_calibration_event_details(
    db_path: Path | str,
    *,
    limit: int = DEFAULT_AGGREGATE_EVENTS_LIMIT,
) -> list[dict[str, Any]]:
    events = load_supervised_ml_operational_events_from_db(db_path, limit=limit)
    details: list[dict[str, Any]] = []
    for row in events:
        ge_id = int(row.get("generation_event_id", 0) or 0)
        if ge_id <= 0:
            continue
        detail = build_supervised_ml_operational_event_detail(db_path, ge_id)
        if isinstance(detail, dict):
            details.append(detail)
    return details


def build_ml_calibration_aggregate_context(
    event_details: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if not event_details:
        return {
            "available": False,
            "scope_label": AGGREGATE_SCOPE_LABEL,
            "headline": "Sem gerações ML oficiais recentes no PostgreSQL",
            "metrics": {},
            "issues_preview": [],
            "lot_rows": [],
            "format_breakdown": [],
        }
    all_issue_types: set[str] = set()
    issues_preview: list[str] = []
    near_dup_total = 0
    overlap_values: list[float] = []
    diversity_scores: list[float] = []
    subcovered_total = 0
    total_games = 0
    calibrated_events = 0
    intra_generation_calibrated_events = 0
    format_counter: Counter[int] = Counter()
    lot_rows: list[dict[str, Any]] = []

    for event in event_details:
        card_format = int(event.get("card_format", 15) or 15)
        format_counter[card_format] += 1
        persisted = int(event.get("persisted_games", 0) or 0)
        total_games += persisted
        if event.get("authorized_cross_generation_calibration"):
            calibrated_events += 1
        if event.get("intra_generation_score_calibration"):
            intra_generation_calibrated_events += 1
        diagnostics = dict(event.get("calibration_diagnostics") or {})
        redundancy = dict(diagnostics.get("redundancy") or {})
        near_dup_total += int(redundancy.get("cartoes_quase_repetidos", 0) or 0)
        overlap_values.append(float(redundancy.get("sobreposicao_media", 0) or 0))
        diversity_scores.append(float(event.get("diversity_score", 0.0) or 0.0))
        for issue in list(diagnostics.get("issues") or []):
            if not isinstance(issue, dict):
                continue
            issue_type = str(issue.get("tipo") or "")
            if issue_type:
                all_issue_types.add(issue_type)
            desc = str(issue.get("descricao") or issue_type or "")
            if desc and desc not in issues_preview:
                issues_preview.append(desc)
        for desc in list(event.get("issues_detected") or []):
            text = str(desc or "")
            if text and text not in issues_preview:
                issues_preview.append(text)
        subcovered_total += sum(
            1
            for row in list(diagnostics.get("issues") or [])
            if isinstance(row, dict) and row.get("tipo") == "dezena_subcoberta"
        )
        lot_rows.append(
            {
                "generation_event_id": int(event.get("generation_event_id", 0) or 0),
                "batch_label": str(event.get("batch_label") or "-"),
                "formato": f"{card_format}D",
                "jogos": persisted,
                "calibracao": bool(event.get("authorized_cross_generation_calibration")),
                "calibracao_intrageracional": bool(event.get("intra_generation_score_calibration")),
                "problemas": len(list(event.get("issues_detected") or [])),
                "diversidade": round(float(event.get("diversity_score", 0.0) or 0.0), 3),
                "created_at": str(event.get("created_at") or ""),
            }
        )

    avg_overlap = sum(overlap_values) / len(overlap_values) if overlap_values else 0.0
    avg_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.0
    prefix_suffix_vicio = bool({"prefixo_excessivo", "sufixo_excessivo"} & all_issue_types)
    return {
        "available": True,
        "scope_label": AGGREGATE_SCOPE_LABEL,
        "headline": AGGREGATE_DIAGNOSIS_HEADLINE,
        "total_events": len(event_details),
        "total_games": total_games,
        "calibrated_events": calibrated_events,
        "intra_generation_calibrated_events": intra_generation_calibrated_events,
        "issue_types": sorted(all_issue_types),
        "aggregate_issue_types": sorted(all_issue_types),
        "aggregate_available": True,
        "metrics": {
            "redundancia": "alta" if near_dup_total >= 20 or avg_overlap >= 10 else "normal",
            "quase_repetidos": near_dup_total,
            "similaridade_media": round(avg_overlap, 2),
            "prefixos_sufixos": "viciados" if prefix_suffix_vicio else "ok",
            "dezenas_subcobertas": subcovered_total,
            "diversidade": "baixa" if avg_diversity < 0.55 else "adequada",
            "diversity_score": round(avg_diversity, 3),
            "six_bases_risco": "alerta" if issues_preview else "estável",
            "geracoes_analisadas": len(event_details),
        },
        "issues_preview": issues_preview[:8],
        "format_breakdown": [
            {"formato": f"{fmt}D", "geracoes": count}
            for fmt, count in sorted(format_counter.items())
        ],
        "lot_rows": lot_rows,
        "calibration_applied": calibrated_events > 0,
        "intra_generation_calibration_applied": intra_generation_calibrated_events > 0,
        "aggregate_calibrated_events": calibrated_events,
    }


def build_sovereign_coverage_diagnosis_card(
    coverage_evidence: Mapping[str, Any],
    *,
    aggregate: Mapping[str, Any] | None = None,
    scope_comparison: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Diagnóstico Central ML — métricas 100% herdadas da Cobertura Estrutural (M-ML-VIS-059)."""
    if not coverage_evidence.get("available"):
        return {
            "available": False,
            "headline": str(coverage_evidence.get("headline") or "Sem evidências estruturais"),
            "scope_label": SOVEREIGN_COVERAGE_SCOPE_LABEL,
            "metrics": {},
            "issues_preview": [],
        }
    metrics = dict(coverage_evidence.get("metrics") or {})
    reading = dict(coverage_evidence.get("reading") or {})
    agg = dict(aggregate or {})
    comparison = dict(scope_comparison or {})
    issues_preview = list(coverage_evidence.get("problemas_detectados") or [])
    return {
        "available": True,
        "scope_label": str(coverage_evidence.get("scope_label") or SOVEREIGN_COVERAGE_SCOPE_LABEL),
        "headline": "Diagnóstico soberano — leitura idêntica à Cobertura Estrutural",
        "coverage_source": "cobertura_estrutural",
        "sovereign_mission_id": VIS_COVERAGE_SOVEREIGN_MISSION_ID,
        "metrics": metrics,
        "issues_preview": issues_preview[:8],
        "total_events": int(metrics.get("total_geracoes", 0) or 0),
        "total_games": int(metrics.get("total_jogos", 0) or 0),
        "calibrated_events": int(metrics.get("calibrated_events", agg.get("calibrated_events", 0)) or 0),
        "intra_generation_calibrated_events": int(
            metrics.get("intra_generation_calibrated_events", agg.get("intra_generation_calibrated_events", 0))
            or 0
        ),
        "format_breakdown": list(metrics.get("format_breakdown") or reading.get("format_breakdown") or []),
        "reading": reading,
        "coverage_snapshot_checksum": str(
            coverage_evidence.get("coverage_snapshot_checksum")
            or reading.get("coverage_snapshot_checksum")
            or ""
        ),
        "read_at": str(coverage_evidence.get("read_at") or reading.get("read_at") or ""),
        "generation_event_ids": list(metrics.get("generation_event_ids") or []),
        "filters": dict(coverage_evidence.get("filters") or reading.get("filters") or {}),
        "scope_comparison": comparison,
        "scope_mismatch": False,
        "scope_mismatch_reason": "",
        "ml_detail_scope_label": str(comparison.get("ml_detail_scope_label") or ""),
        "ml_events_window": int(agg.get("total_events", 0) or 0),
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
        "overlap_format_mission_id_067": OVERLAP_FORMAT_MISSION_ID_067,
        "overlap_format_memory": dict(coverage_evidence.get("overlap_format_memory") or {}),
        "ml_format_aware_memory": dict(
            coverage_evidence.get("ml_format_aware_memory")
            or coverage_evidence.get("overlap_format_memory")
            or {}
        ),
        "structural_concentration_mission_id": coverage_evidence.get("structural_concentration_mission_id"),
        "structural_concentration_audit": dict(coverage_evidence.get("structural_concentration_audit") or {}),
        "structural_auto_calibration_mission_id": coverage_evidence.get(
            "structural_auto_calibration_mission_id", STRUCTURAL_AUTO_CALIBRATION_MISSION_ID
        ),
        "structural_auto_calibration_plan": dict(coverage_evidence.get("structural_auto_calibration_plan") or {}),
        "structural_calibration_memory": dict(coverage_evidence.get("structural_calibration_memory") or {}),
        "structural_policy_15d_mission_id": coverage_evidence.get(
            "structural_policy_15d_mission_id", STRUCTURAL_POLICY_15D_MISSION_ID
        ),
        "structural_policy_15d_memory": dict(coverage_evidence.get("structural_policy_15d_memory") or {}),
        "structural_policy_15d_application": dict(
            coverage_evidence.get("structural_policy_15d_application") or {}
        ),
        "structural_policy_memory_loaded": bool(coverage_evidence.get("structural_policy_memory_loaded")),
        "structural_policy_version": str(coverage_evidence.get("structural_policy_version") or ""),
        "structural_policy_applied": bool(coverage_evidence.get("structural_policy_applied")),
        "policy_compliance_status": str(coverage_evidence.get("policy_compliance_status") or ""),
        "policy_violations": list(coverage_evidence.get("policy_violations") or []),
        "structural_policy_15d_analysis": dict(coverage_evidence.get("structural_policy_15d_analysis") or {}),
        "structural_policy_15d_calibration_plan": dict(
            coverage_evidence.get("structural_policy_15d_calibration_plan") or {}
        ),
        "pre_final_pool_ml_mission_id": PRE_FINAL_POOL_ML_DASHBOARD_MISSION_ID,
        "pre_final_pool_ml_calibration": dict(coverage_evidence.get("pre_final_pool_ml_calibration") or {}),
        "structural_15d_pool_mission_id": STRUCTURAL_15D_POOL_DASHBOARD_MISSION_ID,
        "ml_structural_15d_pool": dict(coverage_evidence.get("ml_structural_15d_pool") or {}),
        "ml_operational_hierarchy_mission_id": ML_OPERATIONAL_HIERARCHY_DASHBOARD_MISSION_ID,
        "ml_operational_hierarchy": dict(coverage_evidence.get("ml_operational_hierarchy") or {}),
        "pre_gp_recovery_mission_id": coverage_evidence.get("pre_gp_recovery_mission_id", "M-ML-074"),
        "pre_gp_recovery": dict(coverage_evidence.get("pre_gp_recovery") or {}),
        "ml_hierarchy_version": str(coverage_evidence.get("ml_hierarchy_version") or ""),
        "hierarchy_compliance": bool(coverage_evidence.get("hierarchy_compliance")),
        "agent_routing_mission_id": coverage_evidence.get(
            "agent_routing_mission_id", AGENT_ROUTING_DASHBOARD_MISSION_ID
        ),
        "agent_routing_matrix_version": str(coverage_evidence.get("agent_routing_matrix_version") or ""),
        "primary_responsible_agent": str(coverage_evidence.get("primary_responsible_agent") or ""),
        "responsible_agents": list(coverage_evidence.get("responsible_agents") or []),
        "agent_routing": dict(coverage_evidence.get("agent_routing") or {}),
        "pool_origin": str(coverage_evidence.get("pool_origin") or ""),
        "pre_final_calibration_applied": bool(coverage_evidence.get("pre_final_calibration_applied")),
        "final_gp_changed_by_ml": bool(coverage_evidence.get("final_gp_changed_by_ml")),
        "format_analyses": list(coverage_evidence.get("format_analyses") or []),
        "primary_format_analysis": dict(coverage_evidence.get("primary_format_analysis") or {}),
    }


def build_ml_calibration_aggregate_diagnosis_card(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    if not aggregate.get("available"):
        return {
            "available": False,
            "headline": str(aggregate.get("headline") or "Sem gerações ML recentes"),
            "scope_label": AGGREGATE_SCOPE_LABEL,
            "metrics": {},
            "issues_preview": [],
        }
    return {
        "available": True,
        "scope_label": str(aggregate.get("scope_label") or AGGREGATE_SCOPE_LABEL),
        "headline": str(aggregate.get("headline") or AGGREGATE_DIAGNOSIS_HEADLINE),
        "metrics": dict(aggregate.get("metrics") or {}),
        "issues_preview": list(aggregate.get("issues_preview") or []),
        "total_events": int(aggregate.get("total_events", 0) or 0),
        "total_games": int(aggregate.get("total_games", 0) or 0),
        "calibrated_events": int(aggregate.get("calibrated_events", 0) or 0),
        "intra_generation_calibrated_events": int(
            aggregate.get("intra_generation_calibrated_events", 0) or 0
        ),
        "format_breakdown": list(aggregate.get("format_breakdown") or []),
    }


def build_ml_calibration_aggregate_result_card(
    aggregate: Mapping[str, Any],
    *,
    workflow_status: str,
    decision_at: str,
    apply_next_generation: bool,
) -> dict[str, Any]:
    calibrated = bool(aggregate.get("calibration_applied"))
    intra_calibrated = bool(aggregate.get("intra_generation_calibration_applied"))
    issues_count = len(list(aggregate.get("issues_preview") or []))
    if workflow_status == COCKPIT_WORKFLOW_REJECTED:
        operational_status = "rejeitada"
    elif calibrated:
        operational_status = "aplicada"
    elif workflow_status == COCKPIT_WORKFLOW_AUTHORIZED:
        operational_status = "autorizada"
    elif workflow_status == COCKPIT_WORKFLOW_PENDING and issues_count > 0:
        operational_status = "pendente"
    else:
        operational_status = workflow_status or "pendente"
    metrics = dict(aggregate.get("metrics") or {})
    return {
        "operational_status": operational_status,
        "calibration_applied": calibrated,
        "intra_generation_calibration_applied": intra_calibrated,
        "trace_persistido": calibrated,
        "proxima_geracao_afetada": bool(apply_next_generation),
        "decision_at": decision_at,
        "diversity_score": float(metrics.get("diversity_score", 0.0) or 0.0),
        "issues_count": issues_count,
        "actions_count": int(aggregate.get("calibrated_events", 0) or 0),
        "before_after_available": calibrated,
        "geracoes_analisadas": int(aggregate.get("total_events", 0) or 0),
    }


def build_ml_calibration_diagnosis_card(event: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        return {
            "available": False,
            "headline": "Sem lote ML persistido",
            "metrics": {},
            "issues_preview": [],
        }
    diagnostics = dict(event.get("calibration_diagnostics") or {})
    redundancy = dict(diagnostics.get("redundancy") or {})
    issues = list(event.get("issues_detected") or [])
    near_dup = int(redundancy.get("cartoes_quase_repetidos", 0) or 0)
    avg_overlap = float(redundancy.get("sobreposicao_media", 0) or 0)
    diversity_score = float(event.get("diversity_score", 0.0) or 0.0)
    issue_types = _issue_types_from_event(event)
    prefix_suffix_vicio = bool({"prefixo_excessivo", "sufixo_excessivo"} & issue_types)
    subcovered = sum(1 for row in list(diagnostics.get("issues") or []) if row.get("tipo") == "dezena_subcoberta")
    return {
        "available": True,
        "headline": f"Lote {int(event.get('generation_event_id', 0) or 0)} — {event.get('batch_label', '-')}",
        "metrics": {
            "redundancia": "alta" if near_dup >= 20 or avg_overlap >= 10 else "normal",
            "quase_repetidos": near_dup,
            "similaridade_media": round(avg_overlap, 2),
            "prefixos_sufixos": "viciados" if prefix_suffix_vicio else "ok",
            "dezenas_subcobertas": subcovered,
            "diversidade": "baixa" if diversity_score < 0.55 else "adequada",
            "diversity_score": round(diversity_score, 3),
            "six_bases_risco": "alerta" if issues else "estável",
        },
        "issues_preview": issues[:5],
        "formato": f"{int(event.get('card_format', 15) or 15)}D",
        "jogos": int(event.get("persisted_games", 0) or 0),
        "created_at": str(event.get("created_at") or ""),
    }


def build_ml_calibration_result_card(
    event: Mapping[str, Any] | None,
    *,
    workflow_status: str,
    decision_at: str,
    apply_next_generation: bool,
) -> dict[str, Any]:
    calibration_applied = bool(event.get("calibration_applied")) if isinstance(event, Mapping) else False
    trace_persisted = bool(
        isinstance(event, Mapping)
        and (event.get("calibration_decision_trace") or event.get("decision_trace"))
    )
    if workflow_status == COCKPIT_WORKFLOW_REJECTED:
        operational_status = "rejeitada"
    elif calibration_applied:
        operational_status = "aplicada"
    elif workflow_status == COCKPIT_WORKFLOW_AUTHORIZED:
        operational_status = "autorizada"
    elif workflow_status == COCKPIT_WORKFLOW_PENDING and isinstance(event, Mapping) and event.get("issues_detected"):
        operational_status = "pendente"
    else:
        operational_status = workflow_status or "pendente"
    return {
        "operational_status": operational_status,
        "calibration_applied": calibration_applied,
        "trace_persistido": trace_persisted,
        "proxima_geracao_afetada": bool(apply_next_generation),
        "decision_at": decision_at,
        "diversity_score": float(event.get("diversity_score", 0.0) or 0.0) if isinstance(event, Mapping) else 0.0,
        "issues_count": len(list(event.get("issues_detected") or [])) if isinstance(event, Mapping) else 0,
        "actions_count": len(list(event.get("calibration_actions_applied") or [])) if isinstance(event, Mapping) else 0,
        "before_after_available": calibration_applied,
    }


def build_ml_calibration_cockpit_snapshot(
    db_path: Path | str,
    *,
    operational_selection: Mapping[str, Any] | None = None,
    workflow_status: str = COCKPIT_WORKFLOW_PENDING,
    decision_at: str = "",
    apply_next_generation: bool = False,
    events_limit: int = DEFAULT_AGGREGATE_EVENTS_LIMIT,
) -> dict[str, Any]:
    from dashboard.institutional_operational_structural_coverage import (
        OPERATIONAL_GENERATION_ALL_LABEL,
        build_operational_generation_scope_caption,
        load_operational_core_002_generations,
        resolve_operational_generation_selection,
    )

    operational_generations = load_operational_core_002_generations(db_path)
    if operational_selection is not None:
        selection = dict(operational_selection)
    else:
        selection = resolve_operational_generation_selection(
            OPERATIONAL_GENERATION_ALL_LABEL,
            operational_generations,
        )
    is_aggregate = bool(selection.get("is_aggregate"))
    selected_ge_id = int(selection.get("generation_event_id", 0) or 0)
    scoped_generation_event_ids = [
        int(value)
        for value in list(selection.get("generation_event_ids") or [])
        if int(value) > 0
    ]
    selected_card_format = selection.get("card_format")
    game_size = int(selected_card_format) if selected_card_format is not None and int(selected_card_format) > 0 else None
    scope_caption = build_operational_generation_scope_caption(selection)
    format_scope_label = (
        scope_caption
        if not is_aggregate
        else SCOPE_LABEL_ALL_OPERATIONAL
    )

    panel = build_supervised_ml_operational_panel_snapshot(db_path, events_limit=events_limit)
    event_details = load_ml_calibration_event_details(db_path, limit=events_limit)
    if is_aggregate and scoped_generation_event_ids:
        allowed_ids = set(scoped_generation_event_ids)
        event_details = [
            dict(row)
            for row in event_details
            if int(row.get("generation_event_id", 0) or 0) in allowed_ids
        ]
    elif not is_aggregate and selected_ge_id > 0:
        event_details = [
            dict(row)
            for row in event_details
            if int(row.get("generation_event_id", 0) or 0) == selected_ge_id
        ]
    aggregate = build_ml_calibration_aggregate_context(event_details)
    if not is_aggregate:
        aggregate = {
            **aggregate,
            "scope_label": scope_caption,
            "selected_generation_event_id": selected_ge_id,
            "analyzed_card_format": game_size,
            "analyzed_card_format_label": f"{game_size}D" if game_size else "—",
        }
    if workflow_status in {COCKPIT_WORKFLOW_AUTHORIZED, COCKPIT_WORKFLOW_APPLIED}:
        aggregate = {**aggregate, "calibration_authorized": True}
    ml_event_ids = [
        int(row.get("generation_event_id", 0) or 0)
        for row in event_details
        if int(row.get("generation_event_id", 0) or 0) > 0
    ]
    coverage_evidence = get_structural_coverage_evidence(
        db_path,
        scope=SCOPE_ALL_OPERATIONAL_CORE_002,
        scope_label=format_scope_label,
        events_limit=events_limit,
        generation_event_id=selected_ge_id if selected_ge_id > 0 and not is_aggregate else None,
        generation_event_ids=scoped_generation_event_ids if is_aggregate and scoped_generation_event_ids else None,
        game_size=game_size if not is_aggregate else None,
        ml_aggregate=aggregate if aggregate.get("available") else None,
    )
    sovereign_ids = list(coverage_evidence.get("generation_event_ids") or [])
    exclusions_summary = summarize_active_reading_exclusions(db_path)
    scope_comparison = compare_structural_coverage_scopes(sovereign_ids, ml_event_ids)
    scope_comparison["metrics_scope_label"] = format_scope_label
    scope_comparison["ml_detail_scope_label"] = (
        f"Últimas {len(ml_event_ids)} gerações ML — detalhe operacional (não altera métricas)"
    )
    scope_comparison["scope_mismatch"] = False
    recalibration = resolve_recalibration_display_status()
    diagnosis = build_sovereign_coverage_diagnosis_card(
        coverage_evidence,
        aggregate=aggregate if aggregate.get("available") else None,
        scope_comparison=scope_comparison,
    )
    recommendations = build_ml_calibration_recommendations(
        aggregate if aggregate.get("available") else None,
        coverage_evidence=coverage_evidence if coverage_evidence.get("available") else None,
    )
    result = build_ml_calibration_aggregate_result_card(
        aggregate,
        workflow_status=workflow_status,
        decision_at=decision_at,
        apply_next_generation=apply_next_generation,
    )
    latest_event = dict(event_details[0]) if event_details else {}
    primary_decision = dict(coverage_evidence.get("primary_decision") or {})
    decision_blocks = list(coverage_evidence.get("decision_blocks") or [])
    calibration_plan = dict(coverage_evidence.get("calibration_plan") or {})
    if not calibration_plan.get("plan_items") and coverage_evidence.get("available"):
        calibration_plan = build_calibration_plan(
            dict(coverage_evidence.get("metrics") or {}),
            format_analyses=list(coverage_evidence.get("format_analyses") or []),
        )
    return {
        "mission_id": VIS_COCKPIT_MISSION_ID,
        "fix_mission_id": VIS_COCKPIT_FIX02_MISSION_ID,
        "coverage_evidence_mission": VIS_COVERAGE_EVIDENCE_MISSION_ID,
        "coverage_fix_mission_id": VIS_COVERAGE_FIX01_MISSION_ID,
        "coverage_sovereign_mission_id": VIS_COVERAGE_SOVEREIGN_MISSION_ID,
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
        "ml_verdict_mission_id": ML_VERDICT_MISSION_ID,
        "ml_verdict": str(coverage_evidence.get("ml_verdict") or ""),
        "ml_verdict_reason": str(coverage_evidence.get("ml_verdict_reason") or ""),
        "motivo_principal": str(coverage_evidence.get("motivo_principal") or ""),
        "official_release_allowed": bool(coverage_evidence.get("official_release_allowed", True)),
        "official_release_label": str(coverage_evidence.get("official_release_label") or ""),
        "officialization_status": str(coverage_evidence.get("officialization_status") or ""),
        "next_action": str(coverage_evidence.get("next_action") or ""),
        "proxima_acao": str(coverage_evidence.get("proxima_acao") or ""),
        "ml_verdict_trace": dict(coverage_evidence.get("ml_verdict_trace") or {}),
        "ml_verdict_payload": dict(coverage_evidence.get("ml_verdict_payload") or {}),
        "overlap_format_mission_id_067": OVERLAP_FORMAT_MISSION_ID_067,
        "overlap_format_memory": dict(coverage_evidence.get("overlap_format_memory") or {}),
        "ml_format_aware_memory": dict(
            coverage_evidence.get("ml_format_aware_memory")
            or coverage_evidence.get("overlap_format_memory")
            or {}
        ),
        "structural_concentration_mission_id": coverage_evidence.get("structural_concentration_mission_id"),
        "structural_concentration_audit": dict(coverage_evidence.get("structural_concentration_audit") or {}),
        "structural_auto_calibration_mission_id": coverage_evidence.get(
            "structural_auto_calibration_mission_id", STRUCTURAL_AUTO_CALIBRATION_MISSION_ID
        ),
        "structural_auto_calibration_plan": dict(coverage_evidence.get("structural_auto_calibration_plan") or {}),
        "structural_calibration_memory": dict(coverage_evidence.get("structural_calibration_memory") or {}),
        "structural_policy_15d_mission_id": coverage_evidence.get(
            "structural_policy_15d_mission_id", STRUCTURAL_POLICY_15D_MISSION_ID
        ),
        "structural_policy_15d_memory": dict(coverage_evidence.get("structural_policy_15d_memory") or {}),
        "structural_policy_15d_application": dict(
            coverage_evidence.get("structural_policy_15d_application") or {}
        ),
        "structural_policy_memory_loaded": bool(coverage_evidence.get("structural_policy_memory_loaded")),
        "structural_policy_version": str(coverage_evidence.get("structural_policy_version") or ""),
        "structural_policy_applied": bool(coverage_evidence.get("structural_policy_applied")),
        "policy_compliance_status": str(coverage_evidence.get("policy_compliance_status") or ""),
        "policy_violations": list(coverage_evidence.get("policy_violations") or []),
        "structural_policy_15d_analysis": dict(coverage_evidence.get("structural_policy_15d_analysis") or {}),
        "structural_policy_15d_calibration_plan": dict(
            coverage_evidence.get("structural_policy_15d_calibration_plan") or {}
        ),
        "pre_final_pool_ml_mission_id": PRE_FINAL_POOL_ML_DASHBOARD_MISSION_ID,
        "pre_final_pool_ml_calibration": dict(coverage_evidence.get("pre_final_pool_ml_calibration") or {}),
        "structural_15d_pool_mission_id": STRUCTURAL_15D_POOL_DASHBOARD_MISSION_ID,
        "ml_structural_15d_pool": dict(coverage_evidence.get("ml_structural_15d_pool") or {}),
        "ml_operational_hierarchy_mission_id": ML_OPERATIONAL_HIERARCHY_DASHBOARD_MISSION_ID,
        "ml_operational_hierarchy": dict(coverage_evidence.get("ml_operational_hierarchy") or {}),
        "pre_gp_recovery_mission_id": coverage_evidence.get("pre_gp_recovery_mission_id", "M-ML-074"),
        "pre_gp_recovery": dict(coverage_evidence.get("pre_gp_recovery") or {}),
        "ml_hierarchy_version": str(coverage_evidence.get("ml_hierarchy_version") or ""),
        "hierarchy_compliance": bool(coverage_evidence.get("hierarchy_compliance")),
        "agent_routing_mission_id": coverage_evidence.get(
            "agent_routing_mission_id", AGENT_ROUTING_DASHBOARD_MISSION_ID
        ),
        "agent_routing_matrix_version": str(coverage_evidence.get("agent_routing_matrix_version") or ""),
        "primary_responsible_agent": str(coverage_evidence.get("primary_responsible_agent") or ""),
        "responsible_agents": list(coverage_evidence.get("responsible_agents") or []),
        "agent_routing": dict(coverage_evidence.get("agent_routing") or {}),
        "pool_origin": str(coverage_evidence.get("pool_origin") or ""),
        "pre_final_calibration_applied": bool(coverage_evidence.get("pre_final_calibration_applied")),
        "final_gp_changed_by_ml": bool(coverage_evidence.get("final_gp_changed_by_ml")),
        "format_analyses": list(coverage_evidence.get("format_analyses") or []),
        "primary_format_analysis": dict(coverage_evidence.get("primary_format_analysis") or {}),
        "calibration_engine_mission": CALIBRATION_MISSION_ID,
        "supervised_calibration_active": recalibration["supervised_calibration_active"],
        "recalibration_display": recalibration,
        "scope_label": (
            AGGREGATE_SCOPE_LABEL
            if is_aggregate
            else str(diagnosis.get("scope_label") or scope_caption)
        ),
        "scope_comparison": dict(scope_comparison or {}),
        "aggregate_mode": is_aggregate,
        "operational_generation_selection": selection,
        "operational_generation_filter_mission_id": OPERATIONAL_GENERATION_FILTER_MISSION_ID,
        "selected_generation_event_id": selected_ge_id if not is_aggregate else 0,
        "selected_card_format": game_size,
        "analyzed_card_format_caption": scope_caption if not is_aggregate else "",
        "scoped_generation_event_ids": list(scoped_generation_event_ids),
        "constitutional_summary": {
            "core_002": "ATIVO" if panel.get("ml_operational_active") else "BLOQUEADO",
            "lei_15": "ATIVA",
            "lei_15a": "INOPERANTE",
            "ml_livre": "BLOQUEADA",
            "geracao_ml_fora_path": "BLOQUEADA",
            "calibracao_supervisionada": (
                "ATIVA" if recalibration["supervised_calibration_active"] else "INATIVA"
            ),
            "purge": "PROTEGIDO",
            "public_app_ml": "SEM ML OPERACIONAL",
        },
        "diagnosis": diagnosis,
        "recommendations": recommendations,
        "result": result,
        "coverage_evidence": coverage_evidence,
        "primary_decision": primary_decision,
        "decision_blocks": decision_blocks,
        "calibration_plan": calibration_plan,
        "plan_items": list(calibration_plan.get("plan_items") or recommendations),
        "impacto_detalhado": list(
            calibration_plan.get("impact_items")
            or coverage_evidence.get("impacto_detalhado")
            or []
        ),
        "parametros_sugeridos": dict(
            calibration_plan.get("parametros_sugeridos")
            or coverage_evidence.get("parametros_sugeridos")
            or {}
        ),
        "aggregate": aggregate,
        "lot_details": list(aggregate.get("lot_rows") or []),
        "panel": panel,
        "latest_event": latest_event,
        "events": list(panel.get("events") or []),
        "generation_event_ids": sovereign_ids,
        "excluded_batches_count": int(exclusions_summary.get("excluded_batches_count", 0) or 0),
        "excluded_batches_message": str(exclusions_summary.get("message") or ""),
        "excluded_batches_audit": list(exclusions_summary.get("excluded_batches") or []),
        "pre_gp_hierarchy_block": _load_pre_gp_hierarchy_block_snapshot(),
    }


def _load_pre_gp_hierarchy_block_snapshot() -> dict[str, Any]:
    try:
        import streamlit as st

        from dashboard.institutional_ml_hierarchy_block import SESSION_HIERARCHY_BLOCK_KEY

        return dict(st.session_state.get(SESSION_HIERARCHY_BLOCK_KEY) or {})
    except Exception:  # noqa: BLE001 — snapshot fora de contexto Streamlit
        return {}


def build_cockpit_persist_bundle(
    *,
    workflow_status: str,
    decision_at: str,
    apply_next_generation: bool,
    recommendations: list[str],
    scope: str = "aggregate",
    coverage_evidence: Mapping[str, Any] | None = None,
    primary_decision: Mapping[str, Any] | None = None,
    operator_decision: str = "",
    calibration_plan: Mapping[str, Any] | None = None,
    impacto_detalhado: list[str] | None = None,
    parametros_sugeridos: Mapping[str, Any] | None = None,
    operador: str = "operador_adm",
) -> dict[str, Any]:
    evidence = dict(coverage_evidence or {})
    decision = dict(primary_decision or evidence.get("primary_decision") or {})
    plan = dict(calibration_plan or evidence.get("calibration_plan") or {})
    plan_items = list(plan.get("plan_items") or recommendations)
    impact_items = list(
        impacto_detalhado
        or plan.get("impact_items")
        or evidence.get("impacto_detalhado")
        or []
    )
    suggested_params = dict(
        parametros_sugeridos
        or plan.get("parametros_sugeridos")
        or evidence.get("parametros_sugeridos")
        or {}
    )
    calibration_authorized = workflow_status == COCKPIT_WORKFLOW_AUTHORIZED
    trace = {
        "mission_id": VIS_COVERAGE_EVIDENCE_MISSION_ID,
        "fix_mission_id": VIS_COVERAGE_FIX01_MISSION_ID,
        "cockpit_mission_id": VIS_COCKPIT_MISSION_ID,
        "ml_verdict_mission_id": ML_VERDICT_MISSION_ID,
        "workflow_status": workflow_status,
        "operator_decision": operator_decision or workflow_status,
        "operador": operador,
        "decision_at": decision_at,
        "calibration_authorized": calibration_authorized,
        "apply_next_generation": bool(apply_next_generation),
        "plan_items_count": len(plan_items),
        "evidencias_count": len(evidence.get("evidencias") or []),
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
    }
    if decision.get("trace"):
        trace.update(dict(decision.get("trace") or {}))
    ml_verdict_payload = dict(evidence.get("ml_verdict_payload") or {})
    return {
        "mission_id": VIS_COCKPIT_MISSION_ID,
        "fix_mission_id": VIS_COCKPIT_FIX02_MISSION_ID,
        "coverage_evidence_mission": VIS_COVERAGE_EVIDENCE_MISSION_ID,
        "coverage_fix_mission_id": VIS_COVERAGE_FIX01_MISSION_ID,
        "overlap_format_mission_id": OVERLAP_FORMAT_MISSION_ID,
        "ml_verdict_mission_id": ML_VERDICT_MISSION_ID,
        "ml_verdict": str(evidence.get("ml_verdict") or ml_verdict_payload.get("ml_verdict") or ""),
        "ml_verdict_reason": str(
            evidence.get("ml_verdict_reason") or ml_verdict_payload.get("ml_verdict_reason") or ""
        ),
        "motivo_principal": str(
            evidence.get("motivo_principal") or ml_verdict_payload.get("motivo_principal") or ""
        ),
        "official_release_allowed": bool(
            evidence.get("official_release_allowed", ml_verdict_payload.get("official_release_allowed", True))
        ),
        "official_release_label": str(
            evidence.get("official_release_label") or ml_verdict_payload.get("official_release_label") or ""
        ),
        "officialization_status": str(
            evidence.get("officialization_status") or ml_verdict_payload.get("officialization_status") or ""
        ),
        "next_action": str(evidence.get("next_action") or ml_verdict_payload.get("next_action") or ""),
        "proxima_acao": str(evidence.get("proxima_acao") or ml_verdict_payload.get("proxima_acao") or ""),
        "ml_verdict_trace": dict(evidence.get("ml_verdict_trace") or ml_verdict_payload.get("trace") or {}),
        "ml_verdict_payload": ml_verdict_payload,
        "overlap_format_mission_id_067": OVERLAP_FORMAT_MISSION_ID_067,
        "overlap_format_memory": dict(evidence.get("overlap_format_memory") or {}),
        "ml_format_aware_memory": dict(
            evidence.get("ml_format_aware_memory") or evidence.get("overlap_format_memory") or {}
        ),
        "format_analyses": list(evidence.get("format_analyses") or plan.get("format_analyses") or []),
        "primary_format_analysis": dict(
            evidence.get("primary_format_analysis") or plan.get("primary_format_analysis") or {}
        ),
        "cockpit_scope": scope,
        "cockpit_workflow_status": workflow_status,
        "cockpit_decision_at": decision_at,
        "cockpit_apply_next_generation": bool(apply_next_generation),
        "cockpit_recommendations": list(plan_items or recommendations),
        "calibration_plan": plan,
        "plan_items": list(plan_items),
        "impacto_detalhado": impact_items,
        "parametros_sugeridos": suggested_params,
        "operador": operador,
        "supervised_calibration_active": is_supervised_output_calibration_active(),
        "coverage_evidence_snapshot": dict(evidence.get("coverage_evidence_snapshot") or {}),
        "problemas_detectados": list(evidence.get("problemas_detectados") or []),
        "evidencias": list(evidence.get("evidencias") or []),
        "acoes_recomendadas": list(plan_items or recommendations),
        "impacto_esperado": "; ".join(impact_items) if impact_items else str(
            decision.get("impacto_esperado") or evidence.get("impacto_esperado") or ""
        ),
        "decisao_operador": operator_decision or workflow_status,
        "calibration_authorized": calibration_authorized,
        "calibration_applied": workflow_status == COCKPIT_WORKFLOW_APPLIED,
        "trace": trace,
        "timestamp": decision_at,
    }


def resolve_authorized_calibration_plan(
    cockpit_bundle: Mapping[str, Any] | None,
    *,
    db_path: Any = None,
    prefer_database: bool = True,
) -> dict[str, Any] | None:
    """Retorna plano autorizado — PostgreSQL é fonte primária (M-ML-075-FIX-01)."""
    if prefer_database and db_path is not None:
        from lotoia.ml.authorized_ml_calibration_plan import (
            resolve_authorized_calibration_plan_from_db,
        )

        db_plan = resolve_authorized_calibration_plan_from_db(db_path)
        if db_plan:
            return db_plan

    if not isinstance(cockpit_bundle, Mapping):
        return None
    if not bool(cockpit_bundle.get("cockpit_apply_next_generation")):
        return None
    if not bool(cockpit_bundle.get("calibration_authorized")):
        return None
    plan = dict(cockpit_bundle.get("calibration_plan") or {})
    plan_items = list(cockpit_bundle.get("plan_items") or plan.get("plan_items") or [])
    if not plan_items:
        return None
    return {
        "mission_id": VIS_COVERAGE_FIX01_MISSION_ID,
        "plan_items": plan_items,
        "impact_items": list(cockpit_bundle.get("impacto_detalhado") or plan.get("impact_items") or []),
        "parametros_sugeridos": dict(
            cockpit_bundle.get("parametros_sugeridos") or plan.get("parametros_sugeridos") or {}
        ),
        "evidencias": list(cockpit_bundle.get("evidencias") or []),
        "problemas_detectados": list(cockpit_bundle.get("problemas_detectados") or []),
        "trace": {
            **dict(cockpit_bundle.get("trace") or {}),
            "loaded_from_db": False,
            "session_fallback": True,
        },
        "operador": str(cockpit_bundle.get("operador") or "operador_adm"),
        "timestamp": str(cockpit_bundle.get("timestamp") or cockpit_bundle.get("cockpit_decision_at") or ""),
        "authorized": True,
        "calibration_plan_loaded_from_db": False,
    }
