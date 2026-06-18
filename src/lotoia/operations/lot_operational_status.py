"""Status operacional de lote — M-OPS-062."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

MISSION_ID = "M-OPS-062"

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

GENERATION_ORIGIN_GENERATOR = "generator"
GENERATION_ORIGIN_SIMULATION = "simulation"

ACTIVE_STRUCTURAL_READING_STATUSES: frozenset[str] = frozenset(
    {
        STATUS_PENDING_STRUCTURAL_REVIEW,
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
        STATUS_NEEDS_CALIBRATION,
        STATUS_REJECTED,
        STATUS_BLOCKED_FOR_OFFICIALIZATION,
        STATUS_CALIBRATION_SOURCE_ONLY,
        STATUS_SUPERSEDED_BY_CALIBRATION,
        STATUS_NOT_OFFICIALIZED,
        STATUS_CALIBRATION_AUTHORIZED,
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
        if calibration_applied or calibration_authorized:
            return STATUS_CALIBRATION_SOURCE_ONLY
        return STATUS_NOT_OFFICIALIZED

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
