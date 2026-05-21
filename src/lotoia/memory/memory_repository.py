from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    InstitutionalMemoryLineage,
    InstitutionalMemoryReplay,
    InstitutionalMemorySnapshot,
    InstitutionalMemoryState,
    get_session,
)


@dataclass(frozen=True, slots=True)
class MemoryRepositorySummary:
    snapshot_count: int
    state_count: int
    lineage_count: int
    replay_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_count": self.snapshot_count,
            "state_count": self.state_count,
            "lineage_count": self.lineage_count,
            "replay_count": self.replay_count,
        }


class InstitutionalMemoryRepository:
    """Persistence access layer for institutional memory tables."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def list_snapshots(self, *, execution_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemorySnapshot).order_by(
                InstitutionalMemorySnapshot.created_at.desc(),
                InstitutionalMemorySnapshot.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemorySnapshot.execution_id == execution_id)
            rows = query.limit(limit).all()
        return [self._snapshot_row(row) for row in rows]

    def list_states(self, *, execution_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemoryState).order_by(
                InstitutionalMemoryState.created_at.desc(),
                InstitutionalMemoryState.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemoryState.execution_id == execution_id)
            rows = query.limit(limit).all()
        return [self._state_row(row) for row in rows]

    def list_lineage(self, *, execution_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemoryLineage).order_by(
                InstitutionalMemoryLineage.created_at.desc(),
                InstitutionalMemoryLineage.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemoryLineage.execution_id == execution_id)
            rows = query.limit(limit).all()
        return [self._lineage_row(row) for row in rows]

    def list_replays(self, *, execution_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemoryReplay).order_by(
                InstitutionalMemoryReplay.created_at.desc(),
                InstitutionalMemoryReplay.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemoryReplay.execution_id == execution_id)
            rows = query.limit(limit).all()
        return [self._replay_row(row) for row in rows]

    def summarize_execution(self, execution_id: str) -> MemoryRepositorySummary:
        return MemoryRepositorySummary(
            snapshot_count=len(self.list_snapshots(execution_id=execution_id)),
            state_count=len(self.list_states(execution_id=execution_id)),
            lineage_count=len(self.list_lineage(execution_id=execution_id)),
            replay_count=len(self.list_replays(execution_id=execution_id)),
        )

    def _snapshot_row(self, row: InstitutionalMemorySnapshot) -> dict[str, Any]:
        return {
            "memory_id": row.memory_id,
            "execution_id": row.execution_id,
            "snapshot_type": row.snapshot_type,
            "created_at": row.created_at,
            "state_json": dict(row.state_json or {}),
            "metadata_json": dict(row.metadata_json or {}),
            "lineage_json": dict(row.lineage_json or {}),
        }

    def _state_row(self, row: InstitutionalMemoryState) -> dict[str, Any]:
        return {
            "memory_id": row.memory_id,
            "execution_id": row.execution_id,
            "state_type": row.state_type,
            "created_at": row.created_at,
            "state_json": dict(row.state_json or {}),
            "metadata_json": dict(row.metadata_json or {}),
        }

    def _lineage_row(self, row: InstitutionalMemoryLineage) -> dict[str, Any]:
        return {
            "id": row.id,
            "execution_id": row.execution_id,
            "memory_id": row.memory_id,
            "event_type": row.event_type,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "created_at": row.created_at,
            "payload_json": dict(row.payload_json or {}),
        }

    def _replay_row(self, row: InstitutionalMemoryReplay) -> dict[str, Any]:
        return {
            "replay_id": row.replay_id,
            "execution_id": row.execution_id,
            "replay_type": row.replay_type,
            "created_at": row.created_at,
            "request_json": dict(row.request_json or {}),
            "result_json": dict(row.result_json or {}),
        }
