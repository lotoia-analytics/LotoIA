"""Persistência institucional do plano de calibração autorizado — M-ML-075-FIX-01."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ScientificInstitutionalMemory,
    create_database,
    get_session,
)
from lotoia.governance.institutional_agent_routing_matrix import (
    AGENT_DADOS,
    AGENT_ESTATISTICO,
    AGENT_GERACAO,
    AGENT_ML,
    AGENT_PLATAFORMA,
    AGENT_QUALIDADE,
)

MISSION_ID = "M-ML-075-FIX-01"
MEMORY_KIND = "authorized_ml_calibration_plan"
POLICY_VERSION = "M-ML-075-FIX-01-v1"
TARGET_FORMAT_15D = "15D"

STATUS_ACTIVE = "active"
STATUS_CONSUMED = "consumed"
STATUS_APPLIED_ONCE = "applied_once"
STATUS_REJECTED = "rejected"
STATUS_EXPIRED = "expired"

EFFECT_IMPROVED = "improved"
EFFECT_NEUTRAL = "neutral"
EFFECT_WORSENED = "worsened"
EFFECT_INSUFFICIENT_DATA = "insufficient_data"

VALIDATION_IMPROVED = "melhorou"
VALIDATION_WORSENED = "piorou"
VALIDATION_NEUTRAL = "neutro"
VALIDATION_INCONCLUSIVE = "inconclusivo"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _memory_row_to_plan(row: ScientificInstitutionalMemory) -> dict[str, Any]:
    payload = dict(getattr(row, "policy_applied", {}) or {})
    payload.setdefault("memory_row_id", int(getattr(row, "id", 0) or 0))
    payload.setdefault("status", str(getattr(row, "structural_status", STATUS_ACTIVE) or STATUS_ACTIVE))
    payload.setdefault("created_at", getattr(row, "created_at", datetime.now(UTC)).isoformat())
    return payload


def build_calibration_trace_id(*, source_generation_event_id: int = 0) -> str:
    suffix = f"GE{int(source_generation_event_id)}" if int(source_generation_event_id) > 0 else "NA"
    return f"{MISSION_ID}-{suffix}-{uuid.uuid4().hex[:12]}"


def persist_authorized_ml_calibration_plan(
    *,
    source_generation_event_id: int,
    parametros_sugeridos: Mapping[str, Any],
    plan_items: Sequence[str],
    db_path: Any = DEFAULT_DATABASE_PATH,
    target_format: str = TARGET_FORMAT_15D,
    apply_to_next_generation: bool = True,
    authorized_by_operator: bool = True,
    operator: str = "cockpit_operador_adm",
    calibration_plan: Mapping[str, Any] | None = None,
    evidencias: Sequence[str] | None = None,
    problemas_detectados: Sequence[str] | None = None,
    responsible_agent: str = AGENT_ML,
    supporting_agents: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Persiste plano autorizado para consumo na próxima geração 15D."""
    now = datetime.now(UTC).isoformat()
    trace_id = build_calibration_trace_id(source_generation_event_id=int(source_generation_event_id))
    supporting = list(
        supporting_agents
        or [AGENT_DADOS, AGENT_ESTATISTICO, AGENT_GERACAO, AGENT_QUALIDADE, AGENT_PLATAFORMA]
    )
    payload: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "memory_kind": MEMORY_KIND,
        "policy_version": POLICY_VERSION,
        "source_generation_event_id": int(source_generation_event_id),
        "target_format": str(target_format or TARGET_FORMAT_15D),
        "status": STATUS_ACTIVE,
        "authorized_at": now,
        "authorized_by_operator": bool(authorized_by_operator),
        "apply_to_next_generation": bool(apply_to_next_generation),
        "parametros_sugeridos": dict(parametros_sugeridos or {}),
        "plan_items": [str(item) for item in plan_items if str(item).strip()],
        "calibration_plan": dict(calibration_plan or {}),
        "responsible_agent": str(responsible_agent or AGENT_ML),
        "supporting_agents": supporting,
        "calibration_trace_id": trace_id,
        "operator": str(operator or "cockpit_operador_adm"),
        "evidencias": list(evidencias or []),
        "problemas_detectados": list(problemas_detectados or []),
        "target_generation_event_id": None,
        "calibration_effect": None,
        "metrics_before": {},
        "metrics_after": {},
        "validation_outcome": None,
    }
    create_database(db_path)
    with get_session(db_path) as session:
        _expire_other_active_plans(session, target_format=str(target_format or TARGET_FORMAT_15D))
        row = ScientificInstitutionalMemory(
            memory_kind=MEMORY_KIND,
            strategy_name="Calibração autorizada 15D",
            game_size=15,
            batch_id=trace_id,
            generation_range={
                "mission_id": MISSION_ID,
                "source_generation_event_id": int(source_generation_event_id),
                "target_format": str(target_format or TARGET_FORMAT_15D),
            },
            total_games=0,
            unique_games=0,
            duplicate_games=0,
            structural_status=STATUS_ACTIVE,
            scientific_status=STATUS_ACTIVE,
            scientific_classification="AUTHORIZED_ML_CALIBRATION_PLAN",
            main_reason="Plano de calibração autorizado para próxima geração 15D",
            recommended_action="apply_on_next_15d_generation",
            policy_applied=payload,
            policy_before={},
            policy_after=dict(payload),
            decision_mode="INSTITUCIONAL",
            approved_for_use=1,
            notes="M-ML-075-FIX-01 — calibração cross-geração via PostgreSQL",
            source=MISSION_ID,
        )
        session.add(row)
        session.flush()
        payload["memory_row_id"] = int(row.id or 0)
        session.commit()
    return payload


def _expire_other_active_plans(session: Any, *, target_format: str) -> None:
    rows = (
        session.query(ScientificInstitutionalMemory)
        .filter(
            ScientificInstitutionalMemory.memory_kind == MEMORY_KIND,
            ScientificInstitutionalMemory.structural_status == STATUS_ACTIVE,
            ScientificInstitutionalMemory.approved_for_use == 1,
        )
        .all()
    )
    for row in rows:
        stored = dict(getattr(row, "policy_applied", {}) or {})
        if str(stored.get("target_format") or TARGET_FORMAT_15D) != str(target_format):
            continue
        stored["status"] = STATUS_EXPIRED
        stored["expired_at"] = datetime.now(UTC).isoformat()
        row.structural_status = STATUS_EXPIRED
        row.scientific_status = STATUS_EXPIRED
        row.policy_applied = stored
        row.policy_after = stored


def load_active_authorized_ml_calibration_plan(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    target_format: str = TARGET_FORMAT_15D,
) -> dict[str, Any] | None:
    """Carrega último plano ativo para o formato alvo."""
    create_database(db_path)
    with get_session(db_path) as session:
        row = (
            session.query(ScientificInstitutionalMemory)
            .filter(
                ScientificInstitutionalMemory.memory_kind == MEMORY_KIND,
                ScientificInstitutionalMemory.approved_for_use == 1,
                ScientificInstitutionalMemory.structural_status == STATUS_ACTIVE,
            )
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .first()
        )
    if row is None:
        return None
    plan = _memory_row_to_plan(row)
    if str(plan.get("target_format") or TARGET_FORMAT_15D) != str(target_format):
        return None
    if not bool(plan.get("apply_to_next_generation")):
        return None
    if not list(plan.get("plan_items") or []):
        return None
    return plan


def build_runtime_calibration_plan_from_memory(memory: Mapping[str, Any]) -> dict[str, Any]:
    """Converte memória persistida em calibration_plan operacional para o gerador."""
    params = dict(memory.get("parametros_sugeridos") or {})
    stored_plan = dict(memory.get("calibration_plan") or {})
    return {
        "mission_id": MISSION_ID,
        "plan_items": list(memory.get("plan_items") or stored_plan.get("plan_items") or []),
        "impact_items": list(stored_plan.get("impact_items") or []),
        "parametros_sugeridos": params,
        "evidencias": list(memory.get("evidencias") or []),
        "problemas_detectados": list(memory.get("problemas_detectados") or []),
        "trace": {
            "mission_id": MISSION_ID,
            "calibration_trace_id": str(memory.get("calibration_trace_id") or ""),
            "source_generation_event_id": int(memory.get("source_generation_event_id", 0) or 0),
            "loaded_from_db": True,
            "responsible_agent": str(memory.get("responsible_agent") or AGENT_ML),
            "supporting_agents": list(memory.get("supporting_agents") or []),
        },
        "operador": str(memory.get("operator") or "postgresql_loader"),
        "timestamp": str(memory.get("authorized_at") or ""),
        "authorized": True,
        "calibration_plan_loaded_from_db": True,
        "calibration_plan_source_generation_event_id": int(
            memory.get("source_generation_event_id", 0) or 0
        ),
        "calibration_plan_applied_to_generation": True,
        "calibration_trace_id": str(memory.get("calibration_trace_id") or ""),
        "memory_row_id": int(memory.get("memory_row_id", 0) or 0),
    }


def resolve_authorized_calibration_plan_from_db(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    target_format: str = TARGET_FORMAT_15D,
) -> dict[str, Any] | None:
    memory = load_active_authorized_ml_calibration_plan(db_path, target_format=target_format)
    if not memory:
        return None
    return build_runtime_calibration_plan_from_memory(memory)


def extract_module_operational_params(
    calibration_plan: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Mapeia parametros_sugeridos para efeitos concretos por módulo."""
    plan = dict(calibration_plan or {})
    if not plan.get("authorized") and not plan.get("calibration_plan_loaded_from_db"):
        return {"applied": False, "trace": [], "modules": {}}
    params = dict(plan.get("parametros_sugeridos") or {})
    redundancy_boost = max(1.0, _safe_float(params.get("redundancy_penalty_boost"), 1.0))
    overlap_boost = max(1.0, _safe_float(params.get("max_overlap_penalty"), 1.0))
    near_dup_boost = max(1.0, _safe_float(params.get("near_duplicate_penalty"), 1.0))
    prefix_boost = max(1.0, _safe_float(params.get("prefix_penalty"), 1.0))
    suffix_boost = max(1.0, _safe_float(params.get("suffix_penalty"), 1.0))
    missing_boost = max(1.0, _safe_float(params.get("missing_numbers_boost"), 1.0))
    diversity_boost = max(1.0, _safe_float(params.get("diversity_floor_boost"), 1.0))
    discourage_boost = max(1.0, _safe_float(params.get("discourage_penalty_boost"), 1.0))
    subcovered = [
        str(value).strip()
        for value in list(params.get("dezenas_subcobertas") or [])
        if str(value).strip()
    ]
    prefix_target = str(params.get("prefixo_alvo") or "")
    suffix_target = str(params.get("sufixo_alvo") or "")

    max_overlap_adj = max(8, int(12 - (overlap_boost - 1.0) * 4))
    prefix_cap_adj = max(2, int(6 - (prefix_boost - 1.0) * 3))
    suffix_cap_adj = max(2, int(6 - (suffix_boost - 1.0) * 3))
    min_diversity_gain = max(0.10, 0.20 * diversity_boost)

    trace = [
        f"redundancy_penalty_boost={redundancy_boost:.2f}",
        f"max_overlap_penalty={overlap_boost:.2f}",
        f"near_duplicate_penalty={near_dup_boost:.2f}",
        f"prefix_penalty={prefix_boost:.2f}",
        f"suffix_penalty={suffix_boost:.2f}",
        f"missing_numbers_boost={missing_boost:.2f}",
        f"diversity_floor_boost={diversity_boost:.2f}",
    ]
    if subcovered:
        trace.append(f"dezenas_subcobertas={','.join(subcovered[:12])}")
    if prefix_target:
        trace.append(f"prefixo_alvo={prefix_target}")
    if suffix_target:
        trace.append(f"sufixo_alvo={suffix_target}")

    return {
        "applied": True,
        "trace": trace,
        "calibration_trace_id": str(plan.get("calibration_trace_id") or ""),
        "modules": {
            "M-ML-072": {
                "missing_numbers_boost": missing_boost,
                "dezenas_subcobertas": subcovered,
                "discourage_penalty_boost": discourage_boost,
                "redundancy_penalty_boost": redundancy_boost,
            },
            "M-STAT-002": {
                "max_overlap": max_overlap_adj,
                "prefix_cap": prefix_cap_adj,
                "suffix_cap": suffix_cap_adj,
                "diversity_floor_boost": diversity_boost,
                "min_material_diversity_gain": min_diversity_gain,
                "prefixo_alvo": prefix_target,
                "sufixo_alvo": suffix_target,
            },
            "M-ML-074": {
                "redundancy_penalty_boost": max(redundancy_boost, 1.15),
                "max_overlap_penalty": max(overlap_boost, 1.15),
                "missing_numbers_boost": max(missing_boost, 1.1),
            },
            "M-ML-073b": {
                "calibration_plan_applied": True,
                "calibration_trace_id": str(plan.get("calibration_trace_id") or ""),
                "plan_items_count": len(list(plan.get("plan_items") or [])),
            },
            "M-ML-071": {
                "parametros_sugeridos": params,
                "authorized": True,
            },
        },
    }


def is_authorized_cross_generation_calibration(context: Mapping[str, Any] | None) -> bool:
    """Calibração autorizada cockpit N→N+1 (M-ML-075-FIX-01) — distinta de score intrageracional."""
    payload = dict(context or {})
    if bool(payload.get("calibration_plan_consumer_generation")):
        return True
    if bool(payload.get("calibration_plan_applied_to_generation")) and bool(
        payload.get("calibration_plan_loaded_from_db")
    ):
        return True
    authorized_plan = dict(payload.get("authorized_calibration_plan") or {})
    return bool(
        authorized_plan.get("calibration_plan_loaded_from_db")
        and authorized_plan.get("calibration_plan_applied_to_generation")
    )


def is_intra_generation_score_calibration(context: Mapping[str, Any] | None) -> bool:
    """Calibração score-only na mesma geração (M-ML-071) — não conta como autorização cockpit."""
    payload = dict(context or {})
    if is_authorized_cross_generation_calibration(payload):
        return False
    return bool(
        payload.get("pre_final_calibration_applied")
        or payload.get("calibration_applied")
    )


def classify_calibration_display_flags(context: Mapping[str, Any] | None) -> dict[str, bool]:
    authorized = is_authorized_cross_generation_calibration(context)
    intra = is_intra_generation_score_calibration(context)
    return {
        "authorized_cross_generation_calibration": authorized,
        "intra_generation_score_calibration": intra,
        "calibration_applied_any": authorized or intra,
    }


def classify_calibration_effect(
    metrics_before: Mapping[str, Any] | None,
    metrics_after: Mapping[str, Any] | None,
) -> str:
    before = dict(metrics_before or {})
    after = dict(metrics_after or {})
    if not before or not after:
        return EFFECT_INSUFFICIENT_DATA
    diversity_delta = _safe_float(after.get("diversity_score")) - _safe_float(before.get("diversity_score"))
    similarity_delta = _safe_float(after.get("similarity_score")) - _safe_float(
        before.get("similarity_score")
    )
    overlap_delta = _safe_float(after.get("sobreposicao_maxima")) - _safe_float(
        before.get("sobreposicao_maxima")
    )
    if diversity_delta > 0.01 and similarity_delta < -0.01:
        return EFFECT_IMPROVED
    if diversity_delta < -0.01 or similarity_delta > 0.01 or overlap_delta > 0:
        return EFFECT_WORSENED
    return EFFECT_NEUTRAL


def classify_validation_outcome(effect: str) -> str:
    if effect == EFFECT_IMPROVED:
        return VALIDATION_IMPROVED
    if effect == EFFECT_WORSENED:
        return VALIDATION_WORSENED
    if effect == EFFECT_INSUFFICIENT_DATA:
        return VALIDATION_INCONCLUSIVE
    return VALIDATION_NEUTRAL


def extract_generation_metrics(context_json: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(context_json or {})
    pre_final = dict(payload.get("pre_final_pool_ml_calibration") or payload.get("calibration_bundle") or {})
    hierarchy = dict(payload.get("ml_hierarchy_bundle") or payload.get("hierarchy_bundle") or {})
    return {
        "diversity_score": _safe_float(
            pre_final.get("final_diversity_score") or payload.get("diversity_score")
        ),
        "similarity_score": _safe_float(
            pre_final.get("final_similarity_score")
            or (pre_final.get("metrics_after") or {}).get("similarity_score")
        ),
        "sobreposicao_maxima": int(
            ((pre_final.get("metrics_after") or {}).get("redundancy") or {}).get("sobreposicao_maxima", 0)
            or 0
        ),
        "quality_tier": str(hierarchy.get("gp_quality_tier") or ""),
        "ml_verdict": str(payload.get("ml_verdict") or ""),
        "hits_13": int(payload.get("desempenho_13_hits", 0) or 0),
        "hits_14": int(payload.get("desempenho_14_hits", 0) or 0),
        "hits_15": int(payload.get("desempenho_15_hits", 0) or 0),
    }


def compare_generations_n_vs_n1(
    source_context: Mapping[str, Any] | None,
    target_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    before = extract_generation_metrics(source_context)
    after = extract_generation_metrics(target_context)
    effect = classify_calibration_effect(before, after)
    return {
        "metrics_before": before,
        "metrics_after": after,
        "deltas": {
            "diversity_score": round(after["diversity_score"] - before["diversity_score"], 4),
            "similarity_score": round(after["similarity_score"] - before["similarity_score"], 4),
            "sobreposicao_maxima": after["sobreposicao_maxima"] - before["sobreposicao_maxima"],
        },
        "calibration_effect": effect,
        "validation_outcome": classify_validation_outcome(effect),
    }


def mark_calibration_plan_consumed(
    memory_row_id: int,
    *,
    target_generation_event_id: int,
    metrics_before: Mapping[str, Any] | None = None,
    metrics_after: Mapping[str, Any] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    effect = classify_calibration_effect(metrics_before, metrics_after)
    validation = classify_validation_outcome(effect)
    create_database(db_path)
    with get_session(db_path) as session:
        row = session.get(ScientificInstitutionalMemory, int(memory_row_id))
        if row is None:
            return {"updated": False, "reason": "memory_row_not_found"}
        stored = dict(getattr(row, "policy_applied", {}) or {})
        stored["status"] = STATUS_APPLIED_ONCE
        stored["consumed_at"] = datetime.now(UTC).isoformat()
        stored["target_generation_event_id"] = int(target_generation_event_id)
        stored["metrics_before"] = dict(metrics_before or {})
        stored["metrics_after"] = dict(metrics_after or {})
        stored["calibration_effect"] = effect
        stored["validation_outcome"] = validation
        row.structural_status = STATUS_APPLIED_ONCE
        row.scientific_status = STATUS_APPLIED_ONCE
        row.policy_applied = stored
        row.policy_after = stored
        session.commit()
    return {
        "updated": True,
        "status": STATUS_APPLIED_ONCE,
        "calibration_effect": effect,
        "validation_outcome": validation,
        "target_generation_event_id": int(target_generation_event_id),
    }


def load_generation_event_context(
    generation_event_id: int,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    create_database(db_path)
    with get_session(db_path) as session:
        from lotoia.database.database import GenerationEvent

        row = session.get(GenerationEvent, int(generation_event_id))
        if row is None:
            return {}
        return dict(getattr(row, "context_json", {}) or {})


def load_latest_consumed_calibration_plan(
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any] | None:
    create_database(db_path)
    with get_session(db_path) as session:
        row = (
            session.query(ScientificInstitutionalMemory)
            .filter(
                ScientificInstitutionalMemory.memory_kind == MEMORY_KIND,
                ScientificInstitutionalMemory.structural_status == STATUS_APPLIED_ONCE,
            )
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .first()
        )
    if row is None:
        return None
    return _memory_row_to_plan(row)


def build_validation_report_from_consumed_plan(
    plan: Mapping[str, Any],
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    source_id = int(plan.get("source_generation_event_id", 0) or 0)
    target_id = int(plan.get("target_generation_event_id", 0) or 0)
    source_ctx = load_generation_event_context(source_id, db_path) if source_id > 0 else {}
    target_ctx = load_generation_event_context(target_id, db_path) if target_id > 0 else {}
    comparison = compare_generations_n_vs_n1(source_ctx, target_ctx)
    return {
        "calibration_trace_id": str(plan.get("calibration_trace_id") or ""),
        "source_generation_event_id": source_id,
        "target_generation_event_id": target_id,
        **comparison,
        "status": str(plan.get("status") or ""),
    }


def reject_active_calibration_plan(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    target_format: str = TARGET_FORMAT_15D,
    operator: str = "cockpit_operador_adm",
) -> dict[str, Any]:
    memory = load_active_authorized_ml_calibration_plan(db_path, target_format=target_format)
    if not memory:
        return {"updated": False, "reason": "no_active_plan"}
    row_id = int(memory.get("memory_row_id", 0) or 0)
    create_database(db_path)
    with get_session(db_path) as session:
        row = session.get(ScientificInstitutionalMemory, row_id)
        if row is None:
            return {"updated": False, "reason": "memory_row_not_found"}
        stored = dict(getattr(row, "policy_applied", {}) or {})
        stored["status"] = STATUS_REJECTED
        stored["rejected_at"] = datetime.now(UTC).isoformat()
        stored["operator"] = operator
        row.structural_status = STATUS_REJECTED
        row.scientific_status = STATUS_REJECTED
        row.policy_applied = stored
        row.policy_after = stored
        session.commit()
    return {"updated": True, "status": STATUS_REJECTED, "memory_row_id": row_id}
