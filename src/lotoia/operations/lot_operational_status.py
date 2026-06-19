"""Status operacional de lote — M-OPS-062."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

MISSION_ID = "M-OPS-062"
DEFERRED_COVERAGE_MISSION_ID = "M-OPS-062-FIX-06"
POST_CALIBRATION_PROMOTION_MISSION_ID = "M-OPS-064-FIX-01"

QUALITY_TIER_APROVADO = "APROVADO"
QUALITY_TIER_ATENCAO = "ATENÇÃO"
QUALITY_TIER_REPROVADO = "REPROVADO"
QUALITY_TIER_CRITICO = "CRÍTICO"

VERDICT_APROVADO = "APROVADO"
VERDICT_APROVADO_COM_ALERTA = "APROVADO COM ALERTA"
VERDICT_PRECISA_CALIBRAR = "PRECISA CALIBRAR"
VERDICT_REPROVADO = "REPROVADO"
VERDICT_BLOQUEADO = "BLOQUEADO PARA OFICIALIZAÇÃO"

STATUS_PENDING_STRUCTURAL_REVIEW = "pending_structural_review"
STATUS_APPROVED_FOR_OFFICIALIZATION = "approved_for_officialization"
STATUS_OFFICIALIZED = "officialized"
STATUS_APPROVED_WITH_WARNING = "approved_with_warning"
STATUS_NEEDS_CALIBRATION = "needs_calibration"
STATUS_CALIBRATION_AUTHORIZED = "calibration_authorized"
STATUS_CALIBRATION_APPLIED = "calibration_applied"
STATUS_CALIBRATION_SOURCE_ONLY = "calibration_source_only"
STATUS_REJECTED = "rejected"
STATUS_BLOCKED_FOR_OFFICIALIZATION = "blocked_for_officialization"
STATUS_SUPERSEDED_BY_CALIBRATION = "superseded_by_calibration"
STATUS_NOT_OFFICIALIZED = "not_officialized"

PERSIST_TIME_INACTIVE_COVERAGE_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_REJECTED,
        STATUS_BLOCKED_FOR_OFFICIALIZATION,
        STATUS_CALIBRATION_APPLIED,
    }
)

GENERATION_ORIGIN_GENERATOR = "generator"
GENERATION_ORIGIN_SIMULATION = "simulation"

ACTIVE_STRUCTURAL_READING_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PENDING_STRUCTURAL_REVIEW,
        STATUS_NEEDS_CALIBRATION,
        STATUS_CALIBRATION_AUTHORIZED,
        STATUS_APPROVED_FOR_OFFICIALIZATION,
        STATUS_OFFICIALIZED,
        STATUS_APPROVED_WITH_WARNING,
    }
)

OFFICIAL_CONFERENCE_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_APPROVED_FOR_OFFICIALIZATION,
        STATUS_OFFICIALIZED,
        STATUS_APPROVED_WITH_WARNING,
    }
)

ANALYTICAL_HISTORY_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_APPROVED_FOR_OFFICIALIZATION,
        STATUS_OFFICIALIZED,
        STATUS_APPROVED_WITH_WARNING,
    }
)

INACTIVE_AUDIT_ONLY_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_REJECTED,
        STATUS_BLOCKED_FOR_OFFICIALIZATION,
        STATUS_CALIBRATION_SOURCE_ONLY,
        STATUS_SUPERSEDED_BY_CALIBRATION,
        STATUS_NOT_OFFICIALIZED,
        STATUS_CALIBRATION_APPLIED,
    }
)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "sim"}


def resolve_lot_operational_status(
    *,
    ml_verdict: str,
    official_release_allowed: bool,
    generation_origin: str = GENERATION_ORIGIN_GENERATOR,
    calibration_applied: bool = False,
    calibration_authorized: bool = False,
    simulation_mode: bool = False,
) -> str:
    """Resolve status operacional final a partir do veredito ML e origem do lote."""
    verdict = str(ml_verdict or VERDICT_APROVADO).strip().upper()
    origin = str(generation_origin or GENERATION_ORIGIN_GENERATOR).strip().lower()

    if simulation_mode or origin == GENERATION_ORIGIN_SIMULATION:
        if calibration_applied:
            return STATUS_CALIBRATION_SOURCE_ONLY
        if calibration_authorized:
            return STATUS_CALIBRATION_AUTHORIZED
        return STATUS_PENDING_STRUCTURAL_REVIEW

    if calibration_applied and not official_release_allowed:
        return STATUS_CALIBRATION_APPLIED
    if calibration_authorized and not official_release_allowed:
        return STATUS_CALIBRATION_AUTHORIZED

    if verdict == VERDICT_BLOQUEADO:
        return STATUS_BLOCKED_FOR_OFFICIALIZATION
    if verdict == VERDICT_REPROVADO:
        return STATUS_REJECTED
    if verdict == VERDICT_PRECISA_CALIBRAR:
        return STATUS_NEEDS_CALIBRATION
    if verdict == VERDICT_APROVADO_COM_ALERTA and official_release_allowed:
        return STATUS_APPROVED_WITH_WARNING
    if verdict == VERDICT_APROVADO and official_release_allowed:
        return STATUS_OFFICIALIZED
    if official_release_allowed:
        return STATUS_APPROVED_FOR_OFFICIALIZATION
    return STATUS_PENDING_STRUCTURAL_REVIEW


def is_active_structural_reading_status(status: str) -> bool:
    return str(status or "").strip().lower() in ACTIVE_STRUCTURAL_READING_STATUSES


def _legacy_ml_release_allowed(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return True
    if context.get("official_release_allowed") is False:
        return False
    verdict = str(context.get("ml_verdict") or VERDICT_APROVADO).strip().upper()
    return verdict in {VERDICT_APROVADO, VERDICT_APROVADO_COM_ALERTA}


def is_official_conference_eligible(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return True
    status = str(context.get("lot_operational_status") or "").strip().lower()
    if status:
        return status in OFFICIAL_CONFERENCE_STATUSES
    return _legacy_ml_release_allowed(context)


def is_analytical_history_eligible(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return True
    status = str(context.get("lot_operational_status") or "").strip().lower()
    if status:
        return status in ANALYTICAL_HISTORY_STATUSES
    return _legacy_ml_release_allowed(context)


def should_defer_generator_persist_verdict_for_coverage(context: Mapping[str, Any] | None) -> bool:
    """Lotes do Gerador com veredito ML na persistência ainda não revisados na Cobertura."""
    if not isinstance(context, Mapping):
        return False
    origin = str(context.get("generation_origin") or GENERATION_ORIGIN_GENERATOR).strip().lower()
    if origin != GENERATION_ORIGIN_GENERATOR:
        return False
    if context.get("simulation_mode"):
        return False
    if context.get("structural_coverage_review_completed"):
        return False
    if context.get("active_reading_scope") is False and str(
        context.get("excluded_from_active_reading_reason") or ""
    ).strip():
        return False
    lot_status = extract_lot_operational_status(context)
    if lot_status not in PERSIST_TIME_INACTIVE_COVERAGE_STATUSES:
        return False
    return bool(str(context.get("ml_verdict") or "").strip())


def _normalize_quality_tier(value: Any) -> str:
    tier = str(value or "").strip().upper()
    if tier in {"ATENCAO", "ATENÇÃO"}:
        return QUALITY_TIER_ATENCAO
    if tier in {"CRITICO", "CRÍTICO"}:
        return QUALITY_TIER_CRITICO
    return tier


def _post_calibration_promotion_prerequisites_met(
    plan: Mapping[str, Any],
    promo: Mapping[str, Any],
) -> tuple[bool, str]:
    if not bool(plan.get("calibration_plan_loaded_from_db")):
        return False, "calibration_plan_not_loaded_from_db"
    if not bool(plan.get("calibration_plan_applied_to_generation")):
        return False, "calibration_plan_not_applied_to_generation"
    games_count = int(promo.get("generated_games_count", 0) or 0)
    if games_count <= 0:
        return False, "no_generated_games"
    requested_count = int(promo.get("requested_count", 0) or 0)
    if requested_count > 0 and games_count != requested_count:
        return False, "generated_games_count_mismatch"
    if not _safe_bool(promo.get("persistence_supported"), default=True):
        return False, "persistence_not_supported"
    if _safe_bool(promo.get("persistence_blocked")):
        return False, "persistence_blocked"
    generation_event_id = int(promo.get("generation_event_id", 0) or 0)
    if generation_event_id < 0:
        return False, "invalid_generation_event_id"
    if _safe_bool(promo.get("hierarchy_delivery_blocked")):
        return False, "hierarchy_delivery_blocked"
    if _safe_bool(promo.get("runtime_contract_broken")):
        return False, "runtime_contract_broken"
    return True, ""


def _resolve_post_calibration_promoted_status(
    *,
    gp_quality_tier: str,
    ml_verdict: str,
    official_release_allowed: bool,
    current_status: str,
) -> tuple[str, bool, str]:
    tier = _normalize_quality_tier(gp_quality_tier)
    verdict = str(ml_verdict or "").strip().upper()

    if tier in {QUALITY_TIER_REPROVADO, QUALITY_TIER_CRITICO}:
        return current_status, False, f"gp_quality_tier_{tier.lower()}_not_releasable"
    if verdict in {VERDICT_REPROVADO, VERDICT_BLOQUEADO}:
        return current_status, False, f"ml_verdict_{verdict.lower().replace(' ', '_')}_not_releasable"
    if verdict == VERDICT_PRECISA_CALIBRAR and tier not in {QUALITY_TIER_APROVADO, QUALITY_TIER_ATENCAO}:
        return current_status, False, "ml_verdict_precisa_calibrar_not_releasable"

    if current_status in OFFICIAL_CONFERENCE_STATUSES:
        return current_status, True, ""

    if tier == QUALITY_TIER_ATENCAO or verdict == VERDICT_APROVADO_COM_ALERTA:
        return STATUS_APPROVED_WITH_WARNING, True, ""

    if tier == QUALITY_TIER_APROVADO or verdict == VERDICT_APROVADO or official_release_allowed:
        if verdict == VERDICT_APROVADO_COM_ALERTA:
            return STATUS_APPROVED_WITH_WARNING, True, ""
        if verdict == VERDICT_APROVADO:
            return STATUS_OFFICIALIZED, True, ""
        return STATUS_APPROVED_FOR_OFFICIALIZATION, True, ""

    return current_status, False, "quality_tier_or_verdict_insufficient_for_promotion"


def _apply_post_calibration_eligibility_flags(merged: dict[str, Any], *, lot_status: str) -> None:
    conferivel = lot_status in OFFICIAL_CONFERENCE_STATUSES
    merged["lot_operational_status"] = lot_status
    merged["is_active_structural_reading"] = is_active_structural_reading_status(lot_status)
    merged["active_reading_scope"] = merged["is_active_structural_reading"]
    merged["is_official_conference_eligible"] = conferivel
    merged["is_analytical_history_eligible"] = lot_status in ANALYTICAL_HISTORY_STATUSES
    if conferivel:
        merged["official_release_allowed"] = True


def promote_post_calibration_consumer_lot_visibility(
    lot_status_context: Mapping[str, Any],
    *,
    authorized_plan: Mapping[str, Any] | None = None,
    promotion_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Visibilidade Cobertura/Central ML para N+1 — promove a conferível quando elegível (M-OPS-064-FIX-01)."""
    merged = dict(lot_status_context)
    plan = dict(authorized_plan or {})
    promo = dict(promotion_context or {})
    if not bool(plan.get("calibration_plan_loaded_from_db")):
        return merged

    verdict = str(
        promo.get("ml_verdict")
        or merged.get("ml_persist_verdict")
        or merged.get("ml_verdict")
        or (merged.get("lot_status_trace") or {}).get("ml_verdict")
        or ""
    ).strip()
    current_status = extract_lot_operational_status(merged) or str(
        merged.get("lot_operational_status") or STATUS_PENDING_STRUCTURAL_REVIEW
    )
    gp_quality_tier = str(promo.get("gp_quality_tier") or merged.get("gp_quality_tier") or "")
    official_release_allowed = bool(
        promo.get("official_release_allowed", merged.get("official_release_allowed"))
    )

    consumer_base: dict[str, Any] = {
        "post_calibration_consumer_lot": True,
        "calibration_plan_consumer_generation": True,
        "calibration_plan_loaded_from_db": True,
        "calibration_plan_applied_to_generation": bool(plan.get("calibration_plan_applied_to_generation")),
        "calibration_plan_source_generation_event_id": int(
            plan.get("calibration_plan_source_generation_event_id", 0) or 0
        ),
        "calibration_trace_id": str(plan.get("calibration_trace_id") or ""),
        "calibration_plan_visibility_mission_id": "M-ML-075-FIX-01",
        "post_calibration_promotion_mission_id": POST_CALIBRATION_PROMOTION_MISSION_ID,
        "post_calibration_promotion_evaluated": True,
        "excluded_from_active_reading_reason": "",
        "gp_quality_tier": gp_quality_tier or merged.get("gp_quality_tier"),
    }
    if verdict:
        consumer_base["ml_verdict"] = verdict

    prereq_ok, prereq_reason = _post_calibration_promotion_prerequisites_met(plan, promo)
    if not prereq_ok:
        merged.update(consumer_base)
        merged.update(
            {
                "post_calibration_promotion_status": "prerequisites_not_met",
                "promoted_to_analytical_history": False,
                "promoted_to_official_conference": False,
                "promotion_block_reason": prereq_reason,
            }
        )
        merged.setdefault("is_active_structural_reading", is_active_structural_reading_status(current_status))
        merged.setdefault("active_reading_scope", bool(merged.get("is_active_structural_reading")))
        return merged

    promoted_status, promoted, block_reason = _resolve_post_calibration_promoted_status(
        gp_quality_tier=gp_quality_tier,
        ml_verdict=verdict,
        official_release_allowed=official_release_allowed,
        current_status=current_status,
    )

    merged.update(consumer_base)
    if promoted:
        _apply_post_calibration_eligibility_flags(merged, lot_status=promoted_status)
        merged.update(
            {
                "post_calibration_promotion_status": promoted_status,
                "promoted_to_analytical_history": True,
                "promoted_to_official_conference": True,
                "promotion_block_reason": "",
            }
        )
    else:
        if current_status:
            _apply_post_calibration_eligibility_flags(merged, lot_status=current_status)
        merged.update(
            {
                "post_calibration_promotion_status": current_status or "not_promoted",
                "promoted_to_analytical_history": False,
                "promoted_to_official_conference": False,
                "promotion_block_reason": block_reason,
                "post_calibration_consumer_not_released": True,
            }
        )
        merged["is_active_structural_reading"] = True
        merged["active_reading_scope"] = True
        if verdict and current_status in PERSIST_TIME_INACTIVE_COVERAGE_STATUSES:
            merged["ml_persist_verdict_deferred_for_coverage"] = True
            merged["ml_persist_verdict"] = verdict
            merged["structural_coverage_defer_mission_id"] = DEFERRED_COVERAGE_MISSION_ID

    return merged


def defer_lot_status_for_structural_coverage(
    lot_status_context: Mapping[str, Any],
    *,
    generation_origin: str,
    simulation_mode: bool,
    ml_verdict_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Garante visibilidade na Cobertura antes da revisão Central ML (M-OPS-062)."""
    merged = dict(lot_status_context)
    if simulation_mode or str(generation_origin or "").strip().lower() == GENERATION_ORIGIN_SIMULATION:
        return merged
    lot_status = extract_lot_operational_status(merged)
    if is_active_structural_reading_status(lot_status):
        return merged
    if lot_status not in PERSIST_TIME_INACTIVE_COVERAGE_STATUSES:
        return merged
    verdict = str(ml_verdict_payload.get("ml_verdict") or "")
    merged.update(
        {
            "lot_operational_status": STATUS_PENDING_STRUCTURAL_REVIEW,
            "is_active_structural_reading": True,
            "is_official_conference_eligible": False,
            "is_analytical_history_eligible": False,
            "official_release_allowed": False,
            "ml_persist_verdict": verdict,
            "ml_persist_verdict_reason": str(ml_verdict_payload.get("ml_verdict_reason") or ""),
            "ml_persist_verdict_deferred_for_coverage": True,
            "structural_coverage_defer_mission_id": DEFERRED_COVERAGE_MISSION_ID,
        }
    )
    return merged


def build_lot_status_context(
    *,
    ml_verdict_payload: Mapping[str, Any],
    generation_origin: str = GENERATION_ORIGIN_GENERATOR,
    calibration_applied: bool = False,
    calibration_authorized: bool = False,
    simulation_mode: bool = False,
) -> dict[str, Any]:
    """Monta campos de status operacional para context_json."""
    verdict = str(ml_verdict_payload.get("ml_verdict") or "")
    official_release_allowed = bool(ml_verdict_payload.get("official_release_allowed"))
    lot_status = resolve_lot_operational_status(
        ml_verdict=verdict,
        official_release_allowed=official_release_allowed,
        generation_origin=generation_origin,
        calibration_applied=calibration_applied,
        calibration_authorized=calibration_authorized,
        simulation_mode=simulation_mode,
    )
    status_trace = {
        "mission_id": MISSION_ID,
        "lot_operational_status": lot_status,
        "ml_verdict": verdict,
        "generation_origin": generation_origin,
        "official_release_allowed": official_release_allowed,
        "calibration_applied": bool(calibration_applied),
        "calibration_authorized": bool(calibration_authorized),
        "simulation_mode": bool(simulation_mode),
        "resolved_at": datetime.now(UTC).isoformat(),
    }
    return {
        "lot_operational_status": lot_status,
        "lot_operational_status_mission_id": MISSION_ID,
        "generation_origin": generation_origin,
        "lot_status_trace": status_trace,
        "is_active_structural_reading": is_active_structural_reading_status(lot_status),
        "is_official_conference_eligible": lot_status in OFFICIAL_CONFERENCE_STATUSES,
        "is_analytical_history_eligible": lot_status in ANALYTICAL_HISTORY_STATUSES,
        "official_release_allowed": official_release_allowed and lot_status in OFFICIAL_CONFERENCE_STATUSES,
    }


def extract_lot_operational_status(context: Mapping[str, Any] | None) -> str:
    if not isinstance(context, Mapping):
        return ""
    return str(context.get("lot_operational_status") or "").strip().lower()


def supersede_status_update(*, superseded_by_event_id: int, reason: str = "") -> dict[str, Any]:
    """Payload para marcar lote anterior como substituído por calibração."""
    return {
        "lot_operational_status": STATUS_SUPERSEDED_BY_CALIBRATION,
        "official_release_allowed": False,
        "is_active_structural_reading": False,
        "is_official_conference_eligible": False,
        "is_analytical_history_eligible": False,
        "is_evaluated_non_official": True,
        "superseded_by_generation_event_id": int(superseded_by_event_id),
        "superseded_reason": reason or "calibration_new_lot_generated",
        "superseded_at": datetime.now(UTC).isoformat(),
    }


def filter_event_ids_for_active_structural_reading(
    event_contexts: Sequence[tuple[int, Mapping[str, Any]]],
) -> list[int]:
    """Filtra generation_event_ids elegíveis para leitura ativa da Cobertura Estrutural."""
    active_ids: list[int] = []
    for event_id, context in event_contexts:
        if int(event_id) <= 0:
            continue
        status = extract_lot_operational_status(context)
        if not status:
            if _legacy_ml_release_allowed(context):
                active_ids.append(int(event_id))
            continue
        if is_active_structural_reading_status(status):
            active_ids.append(int(event_id))
    return active_ids
