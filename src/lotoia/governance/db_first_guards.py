"""Persistence guards for DB-first Histórico, Analítico and Institucional layers."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from lotoia.database.database import GenerationEvent
from lotoia.database.institutional_read_repository import (
    get_analytical_snapshot,
    get_generation_event_with_games,
    get_institutional_snapshot,
    get_latest_reconciliation_for_generation,
    get_reconciliation_run_with_items,
)


class DbFirstGuardStatus(str, Enum):
    OK = "OK"
    BLOCKED = "BLOCKED"
    CONFLITANTE = "CONFLITANTE"


def evaluate_history_guard(db: Session, generation_event_id: int | None) -> dict[str, Any]:
    if generation_event_id is None or int(generation_event_id) <= 0:
        return {
            "status": DbFirstGuardStatus.BLOCKED.value,
            "classification": DbFirstGuardStatus.BLOCKED.value,
            "reason": "historico_sem_generation_event_id",
            "allowed": False,
        }
    event, games = get_generation_event_with_games(db, int(generation_event_id))
    if event is None:
        return {
            "status": DbFirstGuardStatus.BLOCKED.value,
            "classification": DbFirstGuardStatus.BLOCKED.value,
            "reason": "historico_sem_generation_event_id",
            "allowed": False,
        }
    return {
        "status": DbFirstGuardStatus.OK.value,
        "classification": DbFirstGuardStatus.OK.value,
        "allowed": True,
        "generation_event_id": int(event.id),
        "games_count": len(games),
    }


def evaluate_analytical_guard(
    db: Session,
    *,
    reconciliation_run_id: int | None = None,
    generation_event_id: int | None = None,
) -> dict[str, Any]:
    if reconciliation_run_id is not None and int(reconciliation_run_id) > 0:
        run, items = get_reconciliation_run_with_items(db, int(reconciliation_run_id))
        if run is None:
            return {
                "status": DbFirstGuardStatus.BLOCKED.value,
                "classification": DbFirstGuardStatus.BLOCKED.value,
                "reason": "analitico_sem_reconciliation_run_id",
                "allowed": False,
            }
        return {
            "status": DbFirstGuardStatus.OK.value,
            "classification": DbFirstGuardStatus.OK.value,
            "allowed": True,
            "reconciliation_run_id": int(run.id),
            "items_count": len(items),
            "db_table": "reconciliation_games",
        }

    if generation_event_id is not None and int(generation_event_id) > 0:
        run, items = get_latest_reconciliation_for_generation(db, int(generation_event_id))
        if run is not None:
            return {
                "status": DbFirstGuardStatus.OK.value,
                "classification": DbFirstGuardStatus.OK.value,
                "allowed": True,
                "reconciliation_run_id": int(run.id),
                "items_count": len(items),
                "db_table": "reconciliation_games",
            }

    snapshot = get_analytical_snapshot(db, None)
    if snapshot is not None:
        return {
            "status": DbFirstGuardStatus.OK.value,
            "classification": DbFirstGuardStatus.OK.value,
            "allowed": True,
            "source": snapshot.get("source"),
            "snapshot": snapshot,
        }

    has_generations = int(db.query(GenerationEvent).limit(1).count() or 0) > 0
    if has_generations:
        return {
            "status": DbFirstGuardStatus.OK.value,
            "classification": DbFirstGuardStatus.OK.value,
            "allowed": True,
            "reason": "sem_conferencia_persistida",
        }

    return {
        "status": DbFirstGuardStatus.OK.value,
        "classification": DbFirstGuardStatus.OK.value,
        "allowed": True,
        "reason": "sem_dados_analiticos",
    }


def evaluate_institutional_guard(db: Session) -> dict[str, Any]:
    snapshot = get_institutional_snapshot(db, None)
    if snapshot is not None:
        return {
            "status": DbFirstGuardStatus.OK.value,
            "classification": DbFirstGuardStatus.OK.value,
            "allowed": True,
            "snapshot": snapshot,
        }

    has_generations = int(db.query(GenerationEvent).limit(1).count() or 0) > 0
    if has_generations:
        return {
            "status": DbFirstGuardStatus.OK.value,
            "classification": DbFirstGuardStatus.OK.value,
            "allowed": True,
            "reason": "generation_events_disponivel",
        }

    return {
        "status": DbFirstGuardStatus.BLOCKED.value,
        "classification": DbFirstGuardStatus.BLOCKED.value,
        "reason": "institucional_sem_snapshot_ou_audit_log",
        "allowed": False,
    }


def detect_session_truth(
    session_payload: dict[str, Any] | None,
    db_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not session_payload:
        return {"conflict": False}
    if db_payload:
        return {"conflict": False}
    if session_payload.get("warning"):
        return {"conflict": False}
    if str(session_payload.get("status", "") or "") == "checked":
        return {
            "conflict": True,
            "reason": "session_truth_detectado",
            "classification": DbFirstGuardStatus.CONFLITANTE.value,
        }
    return {"conflict": False}


def detect_csv_operational_usage(source_label: str | None) -> dict[str, Any]:
    normalized = str(source_label or "").strip().lower()
    if normalized in {"historico_lotofacil.csv", "csv", "load_draws_csv"}:
        return {
            "conflict": True,
            "reason": "csv_operacional_detectado",
            "classification": DbFirstGuardStatus.CONFLITANTE.value,
        }
    return {"conflict": False}


def build_db_export_metadata(
    *,
    db_table: str,
    event_id: int | None = None,
    run_id: int | None = None,
    snapshot_id: str | None = None,
    commit_hash: str | None = None,
) -> dict[str, str]:
    metadata = {
        "db_table": db_table,
        "export_origin": "postgresql",
    }
    if event_id is not None and int(event_id) > 0:
        metadata["generation_event_id"] = str(int(event_id))
    if run_id is not None and int(run_id) > 0:
        metadata["reconciliation_run_id"] = str(int(run_id))
    if snapshot_id:
        metadata["snapshot_id"] = str(snapshot_id)
    if commit_hash:
        metadata["commit_hash"] = str(commit_hash)
    return metadata
