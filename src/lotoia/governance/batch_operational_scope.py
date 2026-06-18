"""Escopo operacional de lotes — leitura ativa vs auditoria técnica (M-DADOS-ML-061)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import GeneratedGame, GenerationEvent, get_session

OPERATIONAL_STATUS_PENDING = "pending_structural_review"
OPERATIONAL_STATUS_NEEDS_CALIBRATION = "needs_calibration"
OPERATIONAL_STATUS_CALIBRATION_AUTHORIZED = "calibration_authorized"
OPERATIONAL_STATUS_CALIBRATION_APPLIED = "calibration_applied"
OPERATIONAL_STATUS_REJECTED = "rejected"
OPERATIONAL_STATUS_DISCARDED = "discarded"
OPERATIONAL_STATUS_SUPERSEDED = "superseded_by_calibration"
OPERATIONAL_STATUS_CALIBRATION_SOURCE = "calibration_source_only"
OPERATIONAL_STATUS_FAILED_STRUCTURAL = "failed_structural_validation"
OPERATIONAL_STATUS_NOT_OFFICIALIZED = "not_officialized"
OPERATIONAL_STATUS_APPROVED = "approved_for_officialization"
OPERATIONAL_STATUS_OFFICIALIZED = "officialized"

ACTIVE_READING_OPERATIONAL_STATUSES: frozenset[str] = frozenset(
    {
        OPERATIONAL_STATUS_PENDING,
        OPERATIONAL_STATUS_NEEDS_CALIBRATION,
        OPERATIONAL_STATUS_CALIBRATION_AUTHORIZED,
        OPERATIONAL_STATUS_APPROVED,
        OPERATIONAL_STATUS_OFFICIALIZED,
    }
)

INACTIVE_READING_OPERATIONAL_STATUSES: frozenset[str] = frozenset(
    {
        OPERATIONAL_STATUS_REJECTED,
        OPERATIONAL_STATUS_DISCARDED,
        OPERATIONAL_STATUS_SUPERSEDED,
        OPERATIONAL_STATUS_CALIBRATION_SOURCE,
        OPERATIONAL_STATUS_FAILED_STRUCTURAL,
        OPERATIONAL_STATUS_NOT_OFFICIALIZED,
        OPERATIONAL_STATUS_CALIBRATION_APPLIED,
    }
)

CONFERENCE_ELIGIBLE_OPERATIONAL_STATUSES: frozenset[str] = frozenset(
    {
        OPERATIONAL_STATUS_APPROVED,
        OPERATIONAL_STATUS_OFFICIALIZED,
    }
)

ANALYTICAL_OFFICIAL_OPERATIONAL_STATUSES: frozenset[str] = CONFERENCE_ELIGIBLE_OPERATIONAL_STATUSES

MISSION_ID = "M-DADOS-ML-061"


def _safe_str(value: object, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def normalize_operational_status(value: object | None) -> str:
    normalized = _safe_str(value).lower()
    aliases = {
        "superseded": OPERATIONAL_STATUS_SUPERSEDED,
        "calibration_source": OPERATIONAL_STATUS_CALIBRATION_SOURCE,
        "failed_structural_validation": OPERATIONAL_STATUS_FAILED_STRUCTURAL,
        "not_officialized": OPERATIONAL_STATUS_NOT_OFFICIALIZED,
        "approved": OPERATIONAL_STATUS_APPROVED,
        "officialized": OPERATIONAL_STATUS_OFFICIALIZED,
        "pending": OPERATIONAL_STATUS_PENDING,
    }
    if normalized in aliases:
        return aliases[normalized]
    allowed = ACTIVE_READING_OPERATIONAL_STATUSES | INACTIVE_READING_OPERATIONAL_STATUSES
    if normalized in allowed:
        return normalized
    return OPERATIONAL_STATUS_PENDING


def resolve_batch_operational_fields(context_json: Mapping[str, Any] | None) -> dict[str, str]:
    payload = dict(context_json or {})
    commander_status = _safe_str(payload.get("status_comandante_saida"), "APROVADO").upper()
    total_duplicates = int(payload.get("total_jogos_duplicados", 0) or 0)
    operational_status = normalize_operational_status(payload.get("operational_status"))
    if operational_status == OPERATIONAL_STATUS_PENDING and commander_status != "APROVADO":
        operational_status = OPERATIONAL_STATUS_FAILED_STRUCTURAL
    if operational_status == OPERATIONAL_STATUS_PENDING and total_duplicates > 0:
        operational_status = OPERATIONAL_STATUS_REJECTED
    ml_validation_status = _safe_str(
        payload.get("ml_validation_status"),
        operational_status if operational_status in INACTIVE_READING_OPERATIONAL_STATUSES else OPERATIONAL_STATUS_PENDING,
    )
    officialization_status = _safe_str(
        payload.get("officialization_status"),
        operational_status
        if operational_status in {OPERATIONAL_STATUS_OFFICIALIZED, OPERATIONAL_STATUS_NOT_OFFICIALIZED, OPERATIONAL_STATUS_APPROVED}
        else OPERATIONAL_STATUS_NOT_OFFICIALIZED,
    )
    calibration_state = _safe_str(payload.get("calibration_state"), "none")
    return {
        "operational_status": operational_status,
        "ml_validation_status": ml_validation_status,
        "officialization_status": officialization_status,
        "calibration_state": calibration_state,
    }


def is_active_reading_scope(context_json: Mapping[str, Any] | None) -> bool:
    status = resolve_batch_operational_fields(context_json)["operational_status"]
    return status in ACTIVE_READING_OPERATIONAL_STATUSES


def is_conference_eligible_scope(context_json: Mapping[str, Any] | None) -> bool:
    fields = resolve_batch_operational_fields(context_json)
    return fields["operational_status"] in CONFERENCE_ELIGIBLE_OPERATIONAL_STATUSES


def is_analytical_official_scope(context_json: Mapping[str, Any] | None) -> bool:
    fields = resolve_batch_operational_fields(context_json)
    return fields["operational_status"] in ANALYTICAL_OFFICIAL_OPERATIONAL_STATUSES


def generation_event_context(event: GenerationEvent | None) -> dict[str, Any]:
    if event is None:
        return {}
    return dict(getattr(event, "context_json", {}) or {})


def is_generation_event_active_reading(event: GenerationEvent | None) -> bool:
    return is_active_reading_scope(generation_event_context(event))


def is_generation_event_conference_eligible(event: GenerationEvent | None) -> bool:
    return is_conference_eligible_scope(generation_event_context(event))


def build_operational_status_trace(
    *,
    batch_id: str,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
    authorized_plan: Mapping[str, Any] | None = None,
    operator: str = "",
    operational_status: str = OPERATIONAL_STATUS_SUPERSEDED,
    calibration_state: str = OPERATIONAL_STATUS_CALIBRATION_APPLIED,
    source: str = "scientific_calibration_engine",
) -> dict[str, Any]:
    timestamp = datetime.now(UTC).isoformat()
    return {
        "mission_id": MISSION_ID,
        "batch_id": batch_id,
        "operational_status": operational_status,
        "ml_validation_status": operational_status,
        "officialization_status": OPERATIONAL_STATUS_NOT_OFFICIALIZED,
        "calibration_state": calibration_state,
        "reason": _safe_str(reason),
        "evidence": dict(evidence or {}),
        "authorized_plan": dict(authorized_plan or {}),
        "operator": _safe_str(operator),
        "timestamp": timestamp,
        "source": source,
        "purge": False,
    }


def _merge_operational_status(context_json: Mapping[str, Any], trace: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(context_json or {})
    merged["operational_status"] = trace["operational_status"]
    merged["ml_validation_status"] = trace["ml_validation_status"]
    merged["officialization_status"] = trace["officialization_status"]
    merged["calibration_state"] = trace["calibration_state"]
    existing_trace = list(merged.get("batch_operational_trace") or [])
    existing_trace.append(dict(trace))
    merged["batch_operational_trace"] = existing_trace
    merged["active_reading_scope"] = False
    merged["excluded_from_active_reading_at"] = trace["timestamp"]
    merged["excluded_from_active_reading_reason"] = trace["reason"]
    return merged


def _generation_events_for_batch_id(session, batch_id: str) -> list[GenerationEvent]:
    resolved_batch_id = _safe_str(batch_id)
    if not resolved_batch_id:
        return []
    events = session.query(GenerationEvent).order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc()).all()
    matched: list[GenerationEvent] = []
    for event in events:
        event_context = generation_event_context(event)
        event_batch_id = _safe_str(event_context.get("batch_id"))
        if event_batch_id == resolved_batch_id:
            matched.append(event)
            continue
        game_rows = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == event.id)
            .limit(1)
            .all()
        )
        if game_rows:
            game_context = dict(game_rows[0].context_json or {})
            if _safe_str(game_context.get("batch_id")) == resolved_batch_id:
                matched.append(event)
    return matched


def mark_batch_removed_from_active_reading(
    batch_id: str,
    *,
    db_path: Any,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
    authorized_plan: Mapping[str, Any] | None = None,
    operator: str = "",
    operational_status: str = OPERATIONAL_STATUS_SUPERSEDED,
    calibration_state: str = OPERATIONAL_STATUS_CALIBRATION_APPLIED,
    source: str = "scientific_calibration_engine",
) -> dict[str, Any]:
    """Persiste status inativo no PostgreSQL (context_json) sem purge."""
    resolved_batch_id = _safe_str(batch_id)
    if not resolved_batch_id:
        raise ValueError("batch_id é obrigatório para marcar lote fora do escopo ativo.")
    trace = build_operational_status_trace(
        batch_id=resolved_batch_id,
        reason=reason,
        evidence=evidence,
        authorized_plan=authorized_plan,
        operator=operator,
        operational_status=operational_status,
        calibration_state=calibration_state,
        source=source,
    )
    updated_event_ids: list[int] = []
    updated_game_rows = 0
    with get_session(db_path) as session:
        events = _generation_events_for_batch_id(session, resolved_batch_id)
        for event in events:
            event_context = generation_event_context(event)
            merged_event_context = _merge_operational_status(event_context, trace)
            event.context_json = merged_event_context
            game_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .all()
            )
            for row in game_rows:
                row.context_json = _merge_operational_status(dict(row.context_json or {}), trace)
                updated_game_rows += 1
            updated_event_ids.append(int(event.id or 0))
        session.commit()
    return {
        "batch_id": resolved_batch_id,
        "updated_generation_event_ids": updated_event_ids,
        "updated_game_rows": updated_game_rows,
        "trace": trace,
        "active_reading_scope": False,
    }


def mark_batch_superseded_by_calibration(
    batch_id: str,
    *,
    db_path: Any,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
    authorized_plan: Mapping[str, Any] | None = None,
    operator: str = "",
    calibration_source_only: bool = False,
) -> dict[str, Any]:
    status = OPERATIONAL_STATUS_CALIBRATION_SOURCE if calibration_source_only else OPERATIONAL_STATUS_SUPERSEDED
    return mark_batch_removed_from_active_reading(
        batch_id,
        db_path=db_path,
        reason=reason,
        evidence=evidence,
        authorized_plan=authorized_plan,
        operator=operator,
        operational_status=status,
        calibration_state=OPERATIONAL_STATUS_CALIBRATION_APPLIED,
    )


def list_excluded_batches_audit(
    db_path: Any,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(max(1, int(limit)))
            .all()
        )
        seen_batches: set[str] = set()
        for event in events:
            context = generation_event_context(event)
            if is_active_reading_scope(context):
                continue
            batch_id = _safe_str(context.get("batch_id"))
            if not batch_id or batch_id in seen_batches:
                continue
            seen_batches.add(batch_id)
            fields = resolve_batch_operational_fields(context)
            trace_rows = list(context.get("batch_operational_trace") or [])
            latest_trace = dict(trace_rows[-1]) if trace_rows else {}
            rows.append(
                {
                    "batch_id": batch_id,
                    "generation_event_id": int(event.id or 0),
                    "analysis_batch_label": _safe_str(getattr(event, "analysis_batch_label", "")),
                    "operational_status": fields["operational_status"],
                    "officialization_status": fields["officialization_status"],
                    "calibration_state": fields["calibration_state"],
                    "reason": _safe_str(latest_trace.get("reason") or context.get("excluded_from_active_reading_reason")),
                    "timestamp": _safe_str(latest_trace.get("timestamp") or context.get("excluded_from_active_reading_at")),
                    "operator": _safe_str(latest_trace.get("operator")),
                    "trace": latest_trace,
                }
            )
    return rows


def summarize_active_reading_exclusions(db_path: Any) -> dict[str, Any]:
    excluded = list_excluded_batches_audit(db_path)
    return {
        "excluded_batches_count": len(excluded),
        "excluded_batches": excluded,
        "message": (
            f"{len(excluded)} lote(s) removido(s) da leitura ativa por calibração/reprovação."
            if excluded
            else "Nenhum lote excluído da leitura ativa."
        ),
    }


def filter_generation_events_active_reading(events: Sequence[GenerationEvent]) -> list[GenerationEvent]:
    return [event for event in events if is_generation_event_active_reading(event)]


def filter_generation_event_ids_active_reading(
    generation_event_ids: Sequence[int],
    *,
    db_path: Any,
) -> list[int]:
    normalized = [int(value) for value in generation_event_ids if int(value or 0) > 0]
    if not normalized:
        return []
    with get_session(db_path) as session:
        rows = session.query(GenerationEvent).filter(GenerationEvent.id.in_(normalized)).all()
        active_ids = {int(event.id) for event in rows if is_generation_event_active_reading(event)}
    return [value for value in normalized if value in active_ids]
