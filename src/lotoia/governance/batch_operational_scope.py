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

OPERATIONAL_STATUS_APPROVED_WITH_WARNING = "approved_with_warning"

ACTIVE_READING_OPERATIONAL_STATUSES: frozenset[str] = frozenset(
    {
        OPERATIONAL_STATUS_PENDING,
        OPERATIONAL_STATUS_NEEDS_CALIBRATION,
        OPERATIONAL_STATUS_CALIBRATION_AUTHORIZED,
        OPERATIONAL_STATUS_APPROVED,
        OPERATIONAL_STATUS_OFFICIALIZED,
        OPERATIONAL_STATUS_APPROVED_WITH_WARNING,
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
        OPERATIONAL_STATUS_PENDING,  # M-SENSOR-001: conferência observacional
        OPERATIONAL_STATUS_APPROVED,
        OPERATIONAL_STATUS_OFFICIALIZED,
        OPERATIONAL_STATUS_APPROVED_WITH_WARNING,
    }
)

ANALYTICAL_OFFICIAL_OPERATIONAL_STATUSES: frozenset[str] = (
    CONFERENCE_ELIGIBLE_OPERATIONAL_STATUSES
)

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
    allowed = (
        ACTIVE_READING_OPERATIONAL_STATUSES | INACTIVE_READING_OPERATIONAL_STATUSES
    )
    if normalized in allowed:
        return normalized
    return OPERATIONAL_STATUS_PENDING


LOT_OPERATIONAL_STATUS_ALIASES: dict[str, str] = {
    "superseded_by_calibration": OPERATIONAL_STATUS_SUPERSEDED,
    "calibration_source_only": OPERATIONAL_STATUS_CALIBRATION_SOURCE,
    "not_officialized": OPERATIONAL_STATUS_NOT_OFFICIALIZED,
    "rejected": OPERATIONAL_STATUS_REJECTED,
    "blocked_for_officialization": OPERATIONAL_STATUS_REJECTED,
    "needs_calibration": OPERATIONAL_STATUS_NEEDS_CALIBRATION,
    "calibration_authorized": OPERATIONAL_STATUS_CALIBRATION_AUTHORIZED,
    "calibration_applied": OPERATIONAL_STATUS_CALIBRATION_APPLIED,
    "pending_structural_review": OPERATIONAL_STATUS_PENDING,
    "approved_for_officialization": OPERATIONAL_STATUS_APPROVED,
    "officialized": OPERATIONAL_STATUS_OFFICIALIZED,
    "approved_with_warning": OPERATIONAL_STATUS_APPROVED_WITH_WARNING,
    "failed_structural_validation": OPERATIONAL_STATUS_FAILED_STRUCTURAL,
    "discarded": OPERATIONAL_STATUS_DISCARDED,
}


def resolve_operational_status_from_context(payload: Mapping[str, Any]) -> str:
    """Resolve operational_status — lê lot_operational_status (M-OPS-062) quando necessário."""
    explicit = normalize_operational_status(payload.get("operational_status"))
    lot_status = _safe_str(payload.get("lot_operational_status")).lower()
    if lot_status:
        mapped = LOT_OPERATIONAL_STATUS_ALIASES.get(lot_status, lot_status)
        if (
            mapped
            in ACTIVE_READING_OPERATIONAL_STATUSES
            | INACTIVE_READING_OPERATIONAL_STATUSES
        ):
            return mapped
    if payload.get("active_reading_scope") is False:
        excluded_reason = _safe_str(payload.get("excluded_from_active_reading_reason"))
        if "calibra" in excluded_reason.lower():
            return OPERATIONAL_STATUS_SUPERSEDED
        if "legacy" in excluded_reason.lower():
            return OPERATIONAL_STATUS_NOT_OFFICIALIZED
        return OPERATIONAL_STATUS_NOT_OFFICIALIZED
    if explicit != OPERATIONAL_STATUS_PENDING or not lot_status:
        return explicit
    if payload.get("legacy_excluded_from_active_coverage"):
        return OPERATIONAL_STATUS_NOT_OFFICIALIZED
    if (
        payload.get("simulation_mode")
        or _safe_str(payload.get("generation_origin")).lower() == "simulation"
    ):
        lot_trace = payload.get("lot_status_trace") or {}
        if isinstance(lot_trace, dict) and lot_trace.get("lot_operational_status"):
            mapped = LOT_OPERATIONAL_STATUS_ALIASES.get(
                _safe_str(lot_trace.get("lot_operational_status")).lower(),
                _safe_str(lot_trace.get("lot_operational_status")).lower(),
            )
            if mapped in ACTIVE_READING_OPERATIONAL_STATUSES:
                return mapped
        return OPERATIONAL_STATUS_PENDING
    return explicit


def resolve_batch_operational_fields(
    context_json: Mapping[str, Any] | None,
) -> dict[str, str]:
    payload = dict(context_json or {})
    commander_status = _safe_str(
        payload.get("status_comandante_saida"), "APROVADO"
    ).upper()
    total_duplicates = int(payload.get("total_jogos_duplicados", 0) or 0)
    operational_status = resolve_operational_status_from_context(payload)
    if (
        operational_status == OPERATIONAL_STATUS_PENDING
        and commander_status != "APROVADO"
    ):
        operational_status = OPERATIONAL_STATUS_FAILED_STRUCTURAL
    if operational_status == OPERATIONAL_STATUS_PENDING and total_duplicates > 0:
        operational_status = OPERATIONAL_STATUS_REJECTED
    ml_validation_status = _safe_str(
        payload.get("ml_validation_status"),
        operational_status
        if operational_status in INACTIVE_READING_OPERATIONAL_STATUSES
        else OPERATIONAL_STATUS_PENDING,
    )
    officialization_status = _safe_str(
        payload.get("officialization_status"),
        operational_status
        if operational_status
        in {
            OPERATIONAL_STATUS_OFFICIALIZED,
            OPERATIONAL_STATUS_NOT_OFFICIALIZED,
            OPERATIONAL_STATUS_APPROVED,
        }
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
    context = generation_event_context(event)
    if bool(context.get("calibration_plan_consumer_generation")):
        return True
    if is_active_reading_scope(context):
        return True
    from lotoia.operations.lot_operational_status import (
        should_defer_generator_persist_verdict_for_coverage,
    )

    return should_defer_generator_persist_verdict_for_coverage(context)


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


def _merge_operational_status(
    context_json: Mapping[str, Any], trace: Mapping[str, Any]
) -> dict[str, Any]:
    merged = dict(context_json or {})
    operational_status = trace["operational_status"]
    merged["operational_status"] = operational_status
    merged["ml_validation_status"] = trace["ml_validation_status"]
    merged["officialization_status"] = trace["officialization_status"]
    merged["calibration_state"] = trace["calibration_state"]
    lot_status_map = {
        OPERATIONAL_STATUS_SUPERSEDED: "superseded_by_calibration",
        OPERATIONAL_STATUS_CALIBRATION_SOURCE: "calibration_source_only",
        OPERATIONAL_STATUS_NOT_OFFICIALIZED: "not_officialized",
        OPERATIONAL_STATUS_REJECTED: "rejected",
    }
    if operational_status in lot_status_map:
        merged["lot_operational_status"] = lot_status_map[operational_status]
    existing_trace = list(merged.get("batch_operational_trace") or [])
    existing_trace.append(dict(trace))
    merged["batch_operational_trace"] = existing_trace
    merged["active_reading_scope"] = False
    merged["excluded_from_active_reading_at"] = trace["timestamp"]
    merged["excluded_from_active_reading_reason"] = trace["reason"]
    merged["is_active_structural_reading"] = False
    # ML é apenas observacional — conferência sempre liberada (M-SENSOR-001)
    merged["is_official_conference_eligible"] = True
    merged["is_analytical_history_eligible"] = True
    merged["official_release_allowed"] = True
    return merged


def _generation_events_for_batch_id(session, batch_id: str) -> list[GenerationEvent]:
    resolved_batch_id = _safe_str(batch_id)
    if not resolved_batch_id:
        return []
    events = (
        session.query(GenerationEvent)
        .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
        .all()
    )
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
        raise ValueError(
            "batch_id é obrigatório para marcar lote fora do escopo ativo."
        )
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
                row.context_json = _merge_operational_status(
                    dict(row.context_json or {}), trace
                )
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


def merge_supersede_operational_fields(
    context_json: Mapping[str, Any],
    *,
    superseded_by_event_id: int,
    reason: str = "",
    calibration_source_only: bool = False,
) -> dict[str, Any]:
    """Sincroniza lot_operational_status (M-OPS-062) com operational_status (M-DADOS-ML-061).

    ML é apenas observacional — conferência sempre liberada (M-SENSOR-001).
    """
    status = (
        OPERATIONAL_STATUS_CALIBRATION_SOURCE
        if calibration_source_only
        else OPERATIONAL_STATUS_SUPERSEDED
    )
    lot_status = (
        "calibration_source_only"
        if calibration_source_only
        else "superseded_by_calibration"
    )
    trace = build_operational_status_trace(
        batch_id=_safe_str(context_json.get("batch_id")),
        reason=reason or "superseded_by_calibration",
        operational_status=status,
        calibration_state=OPERATIONAL_STATUS_CALIBRATION_APPLIED,
        source="supersede_prior_lots_for_calibration",
    )
    merged = _merge_operational_status(context_json, trace)
    merged["lot_operational_status"] = lot_status
    # ML é apenas observacional — conferência sempre liberada (M-SENSOR-001)
    merged["official_release_allowed"] = True
    merged["is_active_structural_reading"] = False
    merged["is_official_conference_eligible"] = True
    merged["is_analytical_history_eligible"] = True
    merged["superseded_by_generation_event_id"] = int(superseded_by_event_id)
    merged["superseded_reason"] = reason or "calibration_new_lot_generated"
    return merged


def mark_generation_events_superseded_by_calibration(
    generation_event_ids: Sequence[int],
    *,
    db_path: Any,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
    authorized_plan: Mapping[str, Any] | None = None,
    operator: str = "",
    calibration_source_only: bool = False,
    superseded_by_event_id: int = 0,
) -> dict[str, Any]:
    """Marca generation_events específicos como fora do escopo ativo (PostgreSQL)."""
    normalized_ids = sorted(
        {int(value) for value in generation_event_ids if int(value or 0) > 0}
    )
    if not normalized_ids:
        return {
            "updated_generation_event_ids": [],
            "updated_game_rows": 0,
            "active_reading_scope": True,
        }
    updated_event_ids: list[int] = []
    updated_game_rows = 0
    with get_session(db_path) as session:
        events = (
            session.query(GenerationEvent)
            .filter(GenerationEvent.id.in_(normalized_ids))
            .all()
        )
        for event in events:
            event_context = generation_event_context(event)
            merged = merge_supersede_operational_fields(
                event_context,
                superseded_by_event_id=superseded_by_event_id,
                reason=reason,
                calibration_source_only=calibration_source_only,
            )
            if evidence:
                merged.setdefault("batch_operational_trace", [])[-1]["evidence"] = dict(
                    evidence
                )
            if authorized_plan:
                merged.setdefault("batch_operational_trace", [])[-1][
                    "authorized_plan"
                ] = dict(authorized_plan)
            if operator:
                merged.setdefault("batch_operational_trace", [])[-1]["operator"] = (
                    operator
                )
            event.context_json = merged
            game_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .all()
            )
            for row in game_rows:
                row.context_json = merge_supersede_operational_fields(
                    dict(row.context_json or {}),
                    superseded_by_event_id=superseded_by_event_id,
                    reason=reason,
                    calibration_source_only=calibration_source_only,
                )
                updated_game_rows += 1
            updated_event_ids.append(int(event.id or 0))
        session.commit()
    return {
        "updated_generation_event_ids": updated_event_ids,
        "updated_game_rows": updated_game_rows,
        "active_reading_scope": False,
        "reason": reason,
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
    status = (
        OPERATIONAL_STATUS_CALIBRATION_SOURCE
        if calibration_source_only
        else OPERATIONAL_STATUS_SUPERSEDED
    )
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
                    "analysis_batch_label": _safe_str(
                        getattr(event, "analysis_batch_label", "")
                    ),
                    "operational_status": fields["operational_status"],
                    "officialization_status": fields["officialization_status"],
                    "calibration_state": fields["calibration_state"],
                    "reason": _safe_str(
                        latest_trace.get("reason")
                        or context.get("excluded_from_active_reading_reason")
                    ),
                    "timestamp": _safe_str(
                        latest_trace.get("timestamp")
                        or context.get("excluded_from_active_reading_at")
                    ),
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


def filter_generation_events_active_reading(
    events: Sequence[GenerationEvent],
) -> list[GenerationEvent]:
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
        rows = (
            session.query(GenerationEvent)
            .filter(GenerationEvent.id.in_(normalized))
            .all()
        )
        active_ids = {
            int(event.id) for event in rows if is_generation_event_active_reading(event)
        }
    return [value for value in normalized if value in active_ids]


def _is_legacy_generation_without_operational_status(
    context: Mapping[str, Any],
) -> bool:
    if _safe_str(context.get("lot_operational_status")):
        return False
    if _safe_str(context.get("lot_operational_status_mission_id")):
        return False
    lot_trace = context.get("lot_status_trace")
    if isinstance(lot_trace, Mapping) and lot_trace.get("mission_id"):
        return False
    explicit = _safe_str(context.get("operational_status")).lower()
    if explicit and explicit != OPERATIONAL_STATUS_PENDING:
        return False
    return True


def evaluate_active_coverage_exclusion(context: Mapping[str, Any]) -> str | None:
    """Retorna motivo de exclusão da leitura ativa ou None se elegível."""
    if context.get("legacy_excluded_from_active_coverage"):
        return "legacy_excluded_from_active_coverage"
    if context.get("active_reading_scope") is False:
        return _safe_str(
            context.get("excluded_from_active_reading_reason")
            or "active_reading_scope_false"
        )
    status = resolve_operational_status_from_context(context)
    if status in INACTIVE_READING_OPERATIONAL_STATUSES:
        return f"inactive_status:{status}"
    if _is_legacy_generation_without_operational_status(context):
        return "legacy_without_operational_status"
    if not is_active_reading_scope(context):
        return f"not_active_reading:{status}"
    return None


def dry_run_active_coverage_cleanup(
    db_path: Any,
    *,
    limit: int = 500,
) -> dict[str, Any]:
    """Lista lotes que seriam removidos da leitura ativa (sem purge)."""
    from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label

    candidates: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(max(1, int(limit)))
            .all()
        )
        for event in events:
            batch_label = _safe_str(getattr(event, "analysis_batch_label", ""))
            if not is_sovereign_core_label(batch_label):
                continue
            context = generation_event_context(event)
            if context.get("active_reading_scope") is False and context.get(
                "legacy_excluded_from_active_coverage"
            ):
                continue
            reason = evaluate_active_coverage_exclusion(context)
            if not reason:
                continue
            if (
                reason.startswith("inactive_status:")
                or reason == "legacy_without_operational_status"
            ):
                game_count = (
                    session.query(GeneratedGame)
                    .filter(GeneratedGame.generation_event_id == event.id)
                    .count()
                )
                fields = resolve_batch_operational_fields(context)
                candidates.append(
                    {
                        "generation_event_id": int(event.id or 0),
                        "analysis_batch_label": batch_label,
                        "operational_status": fields["operational_status"],
                        "lot_operational_status": _safe_str(
                            context.get("lot_operational_status")
                        ),
                        "games_count": int(game_count),
                        "exclusion_reason": reason,
                        "created_at": event.created_at.isoformat()
                        if getattr(event, "created_at", None)
                        else "",
                    }
                )
    return {
        "mission_id": "M-OPS-062-FIX-04",
        "dry_run": True,
        "purge": False,
        "candidates_count": len(candidates),
        "candidates": candidates,
    }


def apply_active_coverage_logical_cleanup(
    db_path: Any,
    *,
    dry_run: bool = True,
    limit: int = 500,
    operator: str = "",
) -> dict[str, Any]:
    """Marca lotes legados/inativos como fora da leitura ativa (sem apagar linhas)."""
    report = dry_run_active_coverage_cleanup(db_path, limit=limit)
    if dry_run:
        return report

    updated_event_ids: list[int] = []
    for row in report.get("candidates") or []:
        ge_id = int(row.get("generation_event_id", 0) or 0)
        if ge_id <= 0:
            continue
        reason = str(row.get("exclusion_reason") or "active_coverage_cleanup")
        if reason == "legacy_without_operational_status":
            result = mark_generation_events_superseded_by_calibration(
                [ge_id],
                db_path=db_path,
                reason="legacy_excluded_from_active_coverage",
                operator=operator,
                calibration_source_only=False,
            )
            with get_session(db_path) as session:
                event = (
                    session.query(GenerationEvent)
                    .filter(GenerationEvent.id == ge_id)
                    .first()
                )
                if event is not None:
                    merged = dict(event.context_json or {})
                    merged["legacy_excluded_from_active_coverage"] = True
                    merged["excluded_from_active_reading_reason"] = (
                        "legacy_without_operational_status"
                    )
                    event.context_json = merged
                    session.commit()
        else:
            status = OPERATIONAL_STATUS_SUPERSEDED
            if reason.startswith("inactive_status:"):
                status = reason.split(":", maxsplit=1)[1]
            result = mark_generation_events_superseded_by_calibration(
                [ge_id],
                db_path=db_path,
                reason=reason,
                operator=operator,
                calibration_source_only=status == OPERATIONAL_STATUS_CALIBRATION_SOURCE,
            )
        updated_event_ids.extend(list(result.get("updated_generation_event_ids") or []))
    return {
        **report,
        "dry_run": False,
        "updated_generation_event_ids": sorted(set(updated_event_ids)),
    }
