"""DB-first read helpers for Histórico, Analítico and Institucional layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar

from sqlalchemy.orm import Session

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    AccessEvent,
    AuthEvent,
    GeneratedGame,
    GenerationEvent,
    InstitutionalMemorySnapshot,
    LotofacilOfficialHistory,
    ReconciliationGame,
    ReconciliationRun,
    RuntimeSnapshot,
    get_session,
)

T = TypeVar("T")


def _model_to_dict(model) -> dict[str, Any]:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def get_latest_official_contest(db: Session) -> LotofacilOfficialHistory | None:
    return (
        db.query(LotofacilOfficialHistory)
        .order_by(LotofacilOfficialHistory.contest_number.desc())
        .first()
    )


def get_generation_event_with_games(
    db: Session,
    generation_event_id: int,
) -> tuple[GenerationEvent | None, list[GeneratedGame]]:
    event = db.get(GenerationEvent, int(generation_event_id))
    if event is None:
        return None, []
    games = (
        db.query(GeneratedGame)
        .filter(GeneratedGame.generation_event_id == int(generation_event_id))
        .order_by(GeneratedGame.game_index.asc())
        .all()
    )
    return event, games


def get_latest_generation_event_with_games(db: Session) -> tuple[GenerationEvent | None, list[GeneratedGame]]:
    event = (
        db.query(GenerationEvent)
        .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
        .first()
    )
    if event is None:
        return None, []
    return get_generation_event_with_games(db, int(event.id))


def get_reconciliation_run_with_items(
    db: Session,
    run_id: int,
) -> tuple[ReconciliationRun | None, list[ReconciliationGame]]:
    run = db.get(ReconciliationRun, int(run_id))
    if run is None:
        return None, []
    items = (
        db.query(ReconciliationGame)
        .filter(ReconciliationGame.reconciliation_run_id == run.id)
        .order_by(ReconciliationGame.game_index.asc())
        .all()
    )
    return run, items


def get_latest_reconciliation_for_generation(
    db: Session,
    generation_event_id: int,
) -> tuple[ReconciliationRun | None, list[ReconciliationGame]]:
    run = (
        db.query(ReconciliationRun)
        .filter(ReconciliationRun.generation_event_id == int(generation_event_id))
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    if run is None:
        return None, []
    return get_reconciliation_run_with_items(db, int(run.id))


def count_generated_games_for_event(db: Session, generation_event_id: int) -> int:
    return int(
        db.query(GeneratedGame)
        .filter(GeneratedGame.generation_event_id == int(generation_event_id))
        .count()
    )


def get_analytical_snapshot(
    db: Session,
    snapshot_id_or_latest: int | str | None = None,
) -> dict[str, Any] | None:
    query = db.query(RuntimeSnapshot).filter(
        RuntimeSnapshot.snapshot_type.in_(
            ["analytical", "institutional_analytics", "analytical_snapshot"]
        )
    )
    if snapshot_id_or_latest is not None:
        if isinstance(snapshot_id_or_latest, int) or str(snapshot_id_or_latest).isdigit():
            row = db.get(RuntimeSnapshot, int(snapshot_id_or_latest))
        else:
            row = query.filter(RuntimeSnapshot.snapshot_id == str(snapshot_id_or_latest)).first()
    else:
        row = query.order_by(RuntimeSnapshot.created_at.desc(), RuntimeSnapshot.id.desc()).first()
    if row is not None:
        return {
            "source": "runtime_snapshots",
            "snapshot_id": row.snapshot_id,
            "id": int(row.id),
            "payload_json": dict(row.payload_json or {}),
            "metadata_json": dict(row.metadata_json or {}),
            "db_table": "runtime_snapshots",
        }

    latest_run = (
        db.query(ReconciliationRun)
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    if latest_run is None:
        return None
    _, items = get_reconciliation_run_with_items(db, int(latest_run.id))
    return {
        "source": "reconciliation_runs",
        "reconciliation_run_id": int(latest_run.id),
        "generation_event_id": int(getattr(latest_run, "generation_event_id", 0) or 0),
        "items_count": len(items),
        "payload_json": {},
        "metadata_json": {"derived": True, "db_table": "reconciliation_games"},
        "db_table": "reconciliation_runs",
    }


def get_institutional_snapshot(
    db: Session,
    snapshot_id_or_latest: int | str | None = None,
) -> dict[str, Any] | None:
    query = db.query(InstitutionalMemorySnapshot)
    if snapshot_id_or_latest is not None:
        if isinstance(snapshot_id_or_latest, int) or str(snapshot_id_or_latest).isdigit():
            row = db.get(InstitutionalMemorySnapshot, int(snapshot_id_or_latest))
        else:
            row = query.filter(InstitutionalMemorySnapshot.memory_id == str(snapshot_id_or_latest)).first()
    else:
        row = query.order_by(
            InstitutionalMemorySnapshot.created_at.desc(),
            InstitutionalMemorySnapshot.id.desc(),
        ).first()
    if row is not None:
        return {
            "source": "institutional_memory_snapshots",
            "memory_id": row.memory_id,
            "id": int(row.id),
            "state_json": dict(row.state_json or {}),
            "metadata_json": dict(row.metadata_json or {}),
            "db_table": "institutional_memory_snapshots",
        }

    audit = db.query(AuthEvent).order_by(AuthEvent.created_at.desc(), AuthEvent.id.desc()).first()
    if audit is None:
        audit = db.query(AccessEvent).order_by(AccessEvent.created_at.desc(), AccessEvent.id.desc()).first()
    if audit is None:
        return None
    return {
        "source": "audit_logs",
        "audit_event_id": int(audit.id),
        "event_type": str(getattr(audit, "event_type", type(audit).__name__) or ""),
        "db_table": audit.__tablename__,
        "metadata_json": _model_to_dict(audit),
    }


class InstitutionalReadRepository:
    """Facade for DB-first reads with optional external session injection."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def _with_session(self, fn: Callable[[Session], T], session: Session | None = None) -> T:
        if session is not None:
            return fn(session)
        with get_session(self.db_path) as db:
            return fn(db)

    def get_latest_official_contest(self, session: Session | None = None) -> LotofacilOfficialHistory | None:
        return self._with_session(get_latest_official_contest, session)

    def get_generation_event_with_games(
        self,
        generation_event_id: int,
        session: Session | None = None,
    ) -> tuple[GenerationEvent | None, list[GeneratedGame]]:
        return self._with_session(lambda db: get_generation_event_with_games(db, generation_event_id), session)

    def get_latest_generation_event_with_games(
        self,
        session: Session | None = None,
    ) -> tuple[GenerationEvent | None, list[GeneratedGame]]:
        return self._with_session(get_latest_generation_event_with_games, session)

    def get_reconciliation_run_with_items(
        self,
        run_id: int,
        session: Session | None = None,
    ) -> tuple[ReconciliationRun | None, list[ReconciliationGame]]:
        return self._with_session(lambda db: get_reconciliation_run_with_items(db, run_id), session)

    def get_latest_reconciliation_for_generation(
        self,
        generation_event_id: int,
        session: Session | None = None,
    ) -> tuple[ReconciliationRun | None, list[ReconciliationGame]]:
        return self._with_session(
            lambda db: get_latest_reconciliation_for_generation(db, generation_event_id),
            session,
        )

    def get_analytical_snapshot(
        self,
        snapshot_id_or_latest: int | str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any] | None:
        return self._with_session(
            lambda db: get_analytical_snapshot(db, snapshot_id_or_latest),
            session,
        )

    def get_institutional_snapshot(
        self,
        snapshot_id_or_latest: int | str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any] | None:
        return self._with_session(
            lambda db: get_institutional_snapshot(db, snapshot_id_or_latest),
            session,
        )
