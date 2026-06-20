"""Limpeza operacional ao sair da Cobertura Estrutural (M-OPS-080)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from sqlalchemy import text

from lotoia.database.database import (
    ExpansionEvent,
    GeneratedGame,
    GenerationEvent,
    InstitutionalOutputSignature,
    InstitutionalValidatedExpansion,
    LotoiaClientGeneration,
    MlUsageEvent,
    ReconciliationEvent,
    ReconciliationRun,
    ReportEvent,
    get_session,
)
from lotoia.governance.batch_operational_scope import (
    is_analytical_official_scope,
    is_generation_event_active_reading,
)
from lotoia.governance.history_preservation_policy import (
    is_protected_generation_event_id,
)
from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
from lotoia.governance.m_dados_049_controlled_reset import OPERATIONAL_DELETE_ORDER
from lotoia.governance.m_ger_dados_051_controlled_ge_removal import (
    delete_operational_rows_for_generation_events,
)

MISSION_ID = "M-OPS-080"
REVIEW_FLAG = "structural_coverage_review_completed"
REVIEW_AT_KEY = "structural_coverage_reviewed_at"
REVIEW_MISSION_KEY = "structural_coverage_review_mission_id"
REVIEW_SCOPE_KEY = "structural_coverage_review_scope"


def build_structural_coverage_review_context(
    *,
    reviewed_at: str | None = None,
    scope: str = "aggregate_all_active",
) -> dict[str, Any]:
    return {
        REVIEW_FLAG: True,
        REVIEW_AT_KEY: str(reviewed_at or datetime.now(UTC).isoformat()),
        REVIEW_MISSION_KEY: MISSION_ID,
        REVIEW_SCOPE_KEY: str(scope or "aggregate_all_active"),
    }


def is_structural_coverage_review_completed(context: Mapping[str, Any] | None) -> bool:
    if not isinstance(context, Mapping):
        return False
    return bool(context.get(REVIEW_FLAG))


def _has_persisted_reconciliation(session: Any, generation_event_id: int) -> bool:
    ge_id = int(generation_event_id or 0)
    if ge_id <= 0:
        return False
    count = (
        session.query(ReconciliationRun)
        .filter(ReconciliationRun.generation_event_id == ge_id)
        .count()
    )
    return int(count or 0) > 0


def is_generation_eligible_for_post_coverage_deletion(
    event: GenerationEvent,
    *,
    reconciliation_exists: bool = False,
) -> tuple[bool, str]:
    ge_id = int(getattr(event, "id", 0) or 0)
    batch_label = str(getattr(event, "analysis_batch_label", "") or "")
    context = dict(getattr(event, "context_json", {}) or {})

    if ge_id <= 0:
        return False, "invalid_generation_event_id"
    if is_protected_generation_event_id(ge_id):
        return False, "protected_generation_event_id"
    if not is_sovereign_core_label(batch_label):
        return False, "not_sovereign_core_002"
    if not is_structural_coverage_review_completed(context):
        return False, "structural_coverage_review_pending"
    if reconciliation_exists or str(context.get("conference_status") or "").strip().lower() == "checked":
        return False, "lot_already_conferred"
    if is_analytical_official_scope(context):
        return False, "official_analytical_scope_preserved"
    if not is_generation_event_active_reading(event):
        return False, "not_active_reading"
    return True, ""


def persist_structural_coverage_review_completed(
    db_path: Any,
    generation_event_ids: Sequence[int],
    *,
    scope: str = "aggregate_all_active",
) -> dict[str, Any]:
    """Marca gerações como auditadas/conferidas na Cobertura Estrutural."""
    target_ids = sorted({int(value) for value in generation_event_ids if int(value or 0) > 0})
    if not target_ids:
        return {
            "mission_id": MISSION_ID,
            "updated_generation_event_ids": [],
            "skipped_generation_event_ids": [],
        }

    review_patch = build_structural_coverage_review_context(scope=scope)
    updated: list[int] = []
    skipped: list[int] = []
    with get_session(db_path) as session:
        events = session.query(GenerationEvent).filter(GenerationEvent.id.in_(target_ids)).all()
        found_ids = {int(event.id or 0) for event in events}
        skipped.extend(sorted(set(target_ids) - found_ids))
        for event in events:
            ge_id = int(event.id or 0)
            if ge_id <= 0:
                continue
            context = dict(getattr(event, "context_json", {}) or {})
            if is_structural_coverage_review_completed(context):
                skipped.append(ge_id)
                continue
            context.update(review_patch)
            event.context_json = context
            updated.append(ge_id)
        if updated:
            session.commit()
    return {
        "mission_id": MISSION_ID,
        "updated_generation_event_ids": sorted(set(updated)),
        "skipped_generation_event_ids": sorted(set(skipped)),
        "review_scope": scope,
    }


def list_active_core_002_generation_event_ids(
    db_path: Any,
    *,
    limit: int | None = None,
) -> list[int]:
    from lotoia.governance.batch_operational_scope import is_generation_event_active_reading

    resolved_limit = int(limit) if limit is not None and int(limit) > 0 else None
    scan_buffer = max(resolved_limit * 3, resolved_limit or 0, 20) if resolved_limit else None
    active_ids: list[int] = []
    with get_session(db_path) as session:
        events_query = session.query(GenerationEvent).order_by(
            GenerationEvent.created_at.desc(),
            GenerationEvent.id.desc(),
        )
        if scan_buffer is not None:
            events_query = events_query.limit(scan_buffer)
        for event in events_query.all():
            batch_label = str(getattr(event, "analysis_batch_label", "") or "")
            if not is_sovereign_core_label(batch_label):
                continue
            if not is_generation_event_active_reading(event):
                continue
            ge_id = int(event.id or 0)
            if ge_id <= 0:
                continue
            game_count = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == ge_id)
                .count()
            )
            if int(game_count or 0) <= 0:
                continue
            active_ids.append(ge_id)
            if resolved_limit is not None and len(active_ids) >= resolved_limit:
                break
    active_ids.sort()
    return active_ids


def all_active_generations_review_completed(
    db_path: Any,
    generation_event_ids: Sequence[int],
) -> bool:
    target_ids = [int(value) for value in generation_event_ids if int(value or 0) > 0]
    if not target_ids:
        return False
    with get_session(db_path) as session:
        events = session.query(GenerationEvent).filter(GenerationEvent.id.in_(target_ids)).all()
        if len(events) != len(target_ids):
            return False
        return all(
            is_structural_coverage_review_completed(dict(getattr(event, "context_json", {}) or {}))
            for event in events
        )


def resolve_post_coverage_deletion_targets(
    db_path: Any,
    generation_event_ids: Sequence[int],
) -> dict[str, Any]:
    """Dry-run dos generation_events elegíveis para purge pós-Cobertura."""
    target_ids = sorted({int(value) for value in generation_event_ids if int(value or 0) > 0})
    eligible: list[int] = []
    ineligible: list[dict[str, Any]] = []
    with get_session(db_path) as session:
        if not target_ids:
            return {
                "mission_id": MISSION_ID,
                "dry_run": True,
                "eligible_generation_event_ids": [],
                "ineligible_generation_event_ids": [],
                "ineligible_details": [],
            }
        events = session.query(GenerationEvent).filter(GenerationEvent.id.in_(target_ids)).all()
        for event in events:
            ge_id = int(event.id or 0)
            reconciliation_exists = _has_persisted_reconciliation(session, ge_id)
            allowed, reason = is_generation_eligible_for_post_coverage_deletion(
                event,
                reconciliation_exists=reconciliation_exists,
            )
            if allowed:
                eligible.append(ge_id)
            else:
                ineligible.append(
                    {
                        "generation_event_id": ge_id,
                        "reason": reason,
                        "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                    }
                )
        missing = sorted(set(target_ids) - {int(event.id or 0) for event in events})
        for ge_id in missing:
            ineligible.append(
                {
                    "generation_event_id": ge_id,
                    "reason": "generation_event_not_found",
                    "analysis_batch_label": "",
                }
            )
    return {
        "mission_id": MISSION_ID,
        "dry_run": True,
        "eligible_generation_event_ids": sorted(eligible),
        "ineligible_generation_event_ids": [
            int(row["generation_event_id"]) for row in ineligible
        ],
        "ineligible_details": ineligible,
    }


def _delete_with_sqlalchemy_session(session: Any, target_ids: list[int]) -> dict[str, int]:
    if not target_ids:
        return {table: 0 for table in OPERATIONAL_DELETE_ORDER}

    id_list = ",".join(str(int(value)) for value in sorted(set(target_ids)))
    deleted: dict[str, int] = {}

    session.execute(
        text(
            f"""
            DELETE FROM reconciliation_games
            WHERE reconciliation_run_id IN (
                SELECT id FROM reconciliation_runs
                WHERE generation_event_id IN ({id_list})
            )
            """
        )
    )
    deleted["reconciliation_games"] = 0

    child_models = (
        (ExpansionEvent, "expansion_events"),
        (InstitutionalValidatedExpansion, "institutional_validated_expansions"),
        (LotoiaClientGeneration, "lotoia_client_generations"),
        (MlUsageEvent, "ml_usage_events"),
        (ReconciliationEvent, "reconciliation_events"),
        (ReportEvent, "report_events"),
        (ReconciliationRun, "reconciliation_runs"),
        (GeneratedGame, "generated_games"),
        (InstitutionalOutputSignature, "institutional_output_signatures"),
    )
    for model, table_name in child_models:
        count = (
            session.query(model)
            .filter(model.generation_event_id.in_(target_ids))
            .delete(synchronize_session=False)
        )
        deleted[table_name] = int(count or 0)

    deleted["generation_events"] = (
        session.query(GenerationEvent)
        .filter(GenerationEvent.id.in_(target_ids))
        .delete(synchronize_session=False)
    )
    return deleted


def delete_reviewed_operational_generations(
    db_path: Any,
    generation_event_ids: Sequence[int],
) -> dict[str, Any]:
    """Remove gerações CORE_002 auditadas na Cobertura e elegíveis para purge."""
    dry_run = resolve_post_coverage_deletion_targets(db_path, generation_event_ids)
    eligible_ids = list(dry_run.get("eligible_generation_event_ids") or [])
    if not eligible_ids:
        return {
            **dry_run,
            "dry_run": False,
            "deleted_generation_event_ids": [],
            "deleted_counts": {table: 0 for table in OPERATIONAL_DELETE_ORDER},
            "verdict": "NENHUMA GERAÇÃO ELEGÍVEL PARA REMOÇÃO",
        }

    deleted_counts: dict[str, int] = {table: 0 for table in OPERATIONAL_DELETE_ORDER}
    with get_session(db_path) as session:
        connection = session.connection()
        raw_connection = getattr(connection, "connection", None)
        dbapi_connection = getattr(raw_connection, "dbapi_connection", raw_connection)
        if dbapi_connection is not None and hasattr(dbapi_connection, "cursor"):
            cursor = dbapi_connection.cursor()
            deleted_counts = delete_operational_rows_for_generation_events(cursor, eligible_ids)
            session.commit()
        else:
            deleted_counts = _delete_with_sqlalchemy_session(session, eligible_ids)
            session.commit()

    return {
        **dry_run,
        "dry_run": False,
        "deleted_generation_event_ids": eligible_ids,
        "deleted_counts": deleted_counts,
        "verdict": "M-OPS-080 LIMPEZA PÓS-COBERTURA EXECUTADA",
    }


def execute_structural_coverage_exit_cleanup(
    db_path: Any,
    *,
    active_generation_event_ids: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Apaga gerações ativas CORE_002 já auditadas ao sair da Cobertura Estrutural."""
    target_ids = list(active_generation_event_ids or [])
    if not target_ids:
        target_ids = list_active_core_002_generation_event_ids(db_path)
    if not target_ids:
        return {
            "mission_id": MISSION_ID,
            "executed": False,
            "reason": "no_active_generations",
            "deleted_generation_event_ids": [],
        }
    if not all_active_generations_review_completed(db_path, target_ids):
        return {
            "mission_id": MISSION_ID,
            "executed": False,
            "reason": "pending_structural_coverage_review",
            "active_generation_event_ids": target_ids,
            "deleted_generation_event_ids": [],
        }
    result = delete_reviewed_operational_generations(db_path, target_ids)
    return {
        "mission_id": MISSION_ID,
        "executed": bool(result.get("deleted_generation_event_ids")),
        "active_generation_event_ids": target_ids,
        **result,
    }
