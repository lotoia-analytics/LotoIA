from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from typing import Any

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    InstitutionalMemoryLineage,
    InstitutionalMemoryReplay,
    InstitutionalMemorySnapshot,
    InstitutionalMemoryState,
    RuntimeExecution,
    RuntimeLineage,
    RuntimeSnapshot,
    get_session,
)


@dataclass(frozen=True, slots=True)
class MemorySnapshot:
    memory_id: str
    execution_id: str
    snapshot_type: str
    created_at: datetime
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "execution_id": self.execution_id,
            "snapshot_type": self.snapshot_type,
            "created_at": self.created_at.isoformat(),
            "state": self.state,
            "metadata": self.metadata,
            "lineage": self.lineage,
        }


@dataclass(frozen=True, slots=True)
class MemoryState:
    memory_id: str
    execution_id: str
    state_type: str
    created_at: datetime
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "execution_id": self.execution_id,
            "state_type": self.state_type,
            "created_at": self.created_at.isoformat(),
            "state": self.state,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class MemoryComparison:
    left_memory_id: str
    right_memory_id: str
    added_keys: tuple[str, ...]
    removed_keys: tuple[str, ...]
    changed_keys: tuple[str, ...]
    stable_keys: tuple[str, ...]
    drift_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_memory_id": self.left_memory_id,
            "right_memory_id": self.right_memory_id,
            "added_keys": list(self.added_keys),
            "removed_keys": list(self.removed_keys),
            "changed_keys": list(self.changed_keys),
            "stable_keys": list(self.stable_keys),
            "drift_summary": self.drift_summary,
        }


@dataclass(frozen=True, slots=True)
class MemoryReplay:
    replay_id: str
    execution_id: str
    replay_type: str
    created_at: datetime
    memory_ids: tuple[str, ...]
    states: tuple[MemoryState, ...]
    snapshots: tuple[MemorySnapshot, ...]
    comparison: MemoryComparison | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_id": self.replay_id,
            "execution_id": self.execution_id,
            "replay_type": self.replay_type,
            "created_at": self.created_at.isoformat(),
            "memory_ids": list(self.memory_ids),
            "states": [state.to_dict() for state in self.states],
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "comparison": self.comparison.to_dict() if self.comparison else None,
            "metadata": self.metadata,
        }


class InstitutionalMemoryRegistry:
    """Declarative registry for institutional memory snapshots and replay."""

    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path

    def register_snapshot(
        self,
        *,
        execution_id: str,
        snapshot_type: str,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        lineage: dict[str, Any] | None = None,
    ) -> MemorySnapshot:
        memory_id = f"memory-{uuid4().hex}"
        payload_metadata = dict(metadata or {})
        lineage_payload = dict(lineage or {})
        state_payload = dict(state)
        with get_session(self.db_path) as session:
            session.add(
                InstitutionalMemorySnapshot(
                    memory_id=memory_id,
                    execution_id=execution_id,
                    snapshot_type=snapshot_type,
                    state_json=state_payload,
                    metadata_json=payload_metadata,
                    lineage_json=lineage_payload,
                )
            )
            session.add(
                InstitutionalMemoryState(
                    memory_id=memory_id,
                    execution_id=execution_id,
                    state_type=snapshot_type,
                    state_json=state_payload,
                    metadata_json=payload_metadata,
                )
            )
            session.add(
                InstitutionalMemoryLineage(
                    execution_id=execution_id,
                    memory_id=memory_id,
                    event_type=str(lineage_payload.get("event_type") or f"{snapshot_type}_snapshot"),
                    entity_type=str(lineage_payload.get("entity_type") or "runtime_execution"),
                    entity_id=str(lineage_payload.get("entity_id") or execution_id),
                    payload_json=lineage_payload,
                )
            )
            session.add(
                RuntimeSnapshot(
                    execution_id=execution_id,
                    snapshot_id=memory_id,
                    snapshot_type=snapshot_type,
                    payload_json=state_payload,
                    metadata_json=payload_metadata,
                )
            )
            session.commit()
        return MemorySnapshot(
            memory_id=memory_id,
            execution_id=execution_id,
            snapshot_type=snapshot_type,
            created_at=datetime.now(UTC),
            state=state_payload,
            metadata=payload_metadata,
            lineage=lineage_payload,
        )

    def register_state(
        self,
        *,
        execution_id: str,
        state_type: str,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        lineage: dict[str, Any] | None = None,
    ) -> MemoryState:
        memory_id = f"memory-state-{uuid4().hex}"
        payload_metadata = dict(metadata or {})
        lineage_payload = dict(lineage or {})
        state_payload = dict(state)
        with get_session(self.db_path) as session:
            session.add(
                InstitutionalMemoryState(
                    memory_id=memory_id,
                    execution_id=execution_id,
                    state_type=state_type,
                    state_json=state_payload,
                    metadata_json=payload_metadata,
                )
            )
            session.add(
                InstitutionalMemoryLineage(
                    execution_id=execution_id,
                    memory_id=memory_id,
                    event_type=str(lineage_payload.get("event_type") or f"{state_type}_state"),
                    entity_type=str(lineage_payload.get("entity_type") or "runtime_execution"),
                    entity_id=str(lineage_payload.get("entity_id") or execution_id),
                    payload_json={**lineage_payload, "state_type": state_type},
                )
            )
            session.commit()
        return MemoryState(
            memory_id=memory_id,
            execution_id=execution_id,
            state_type=state_type,
            created_at=datetime.now(UTC),
            state=state_payload,
            metadata=payload_metadata,
        )

    def get_snapshot(self, memory_id: str) -> MemorySnapshot | None:
        with get_session(self.db_path) as session:
            row = (
                session.query(InstitutionalMemorySnapshot)
                .filter(InstitutionalMemorySnapshot.memory_id == memory_id)
                .first()
            )
            if row is None:
                return None
            return MemorySnapshot(
                memory_id=row.memory_id,
                execution_id=row.execution_id,
                snapshot_type=row.snapshot_type,
                created_at=row.created_at,
                state=dict(row.state_json or {}),
                metadata=dict(row.metadata_json or {}),
                lineage=dict(row.lineage_json or {}),
            )

    def list_snapshots(self, *, execution_id: str | None = None, limit: int = 100) -> list[MemorySnapshot]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemorySnapshot).order_by(
                InstitutionalMemorySnapshot.created_at.desc(),
                InstitutionalMemorySnapshot.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemorySnapshot.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                MemorySnapshot(
                    memory_id=row.memory_id,
                    execution_id=row.execution_id,
                    snapshot_type=row.snapshot_type,
                    created_at=row.created_at,
                    state=dict(row.state_json or {}),
                    metadata=dict(row.metadata_json or {}),
                    lineage=dict(row.lineage_json or {}),
                )
                for row in rows
            ]

    def list_states(self, *, execution_id: str | None = None, limit: int = 100) -> list[MemoryState]:
        with get_session(self.db_path) as session:
            query = session.query(InstitutionalMemoryState).order_by(
                InstitutionalMemoryState.created_at.desc(),
                InstitutionalMemoryState.id.desc(),
            )
            if execution_id is not None:
                query = query.filter(InstitutionalMemoryState.execution_id == execution_id)
            rows = query.limit(limit).all()
            return [
                MemoryState(
                    memory_id=row.memory_id,
                    execution_id=row.execution_id,
                    state_type=row.state_type,
                    created_at=row.created_at,
                    state=dict(row.state_json or {}),
                    metadata=dict(row.metadata_json or {}),
                )
                for row in rows
            ]

    def get_state(self, memory_id: str) -> MemoryState | None:
        with get_session(self.db_path) as session:
            row = (
                session.query(InstitutionalMemoryState)
                .filter(InstitutionalMemoryState.memory_id == memory_id)
                .first()
            )
            if row is None:
                return None
            return MemoryState(
                memory_id=row.memory_id,
                execution_id=row.execution_id,
                state_type=row.state_type,
                created_at=row.created_at,
                state=dict(row.state_json or {}),
                metadata=dict(row.metadata_json or {}),
            )

    def compare_snapshots(self, left_memory_id: str, right_memory_id: str) -> MemoryComparison:
        left = self.get_snapshot(left_memory_id)
        right = self.get_snapshot(right_memory_id)
        if left is None or right is None:
            raise ValueError("both snapshots must exist for comparison")

        left_keys = set(left.state)
        right_keys = set(right.state)
        added = tuple(sorted(right_keys - left_keys))
        removed = tuple(sorted(left_keys - right_keys))
        shared = sorted(left_keys & right_keys)
        changed = tuple(sorted(key for key in shared if left.state.get(key) != right.state.get(key)))
        stable = tuple(sorted(key for key in shared if left.state.get(key) == right.state.get(key)))
        drift_summary = {
            "changed_count": len(changed),
            "stable_count": len(stable),
            "added_count": len(added),
            "removed_count": len(removed),
            "drift_ratio": round(len(changed) / max(len(shared), 1), 4),
        }
        return MemoryComparison(
            left_memory_id=left_memory_id,
            right_memory_id=right_memory_id,
            added_keys=added,
            removed_keys=removed,
            changed_keys=changed,
            stable_keys=stable,
            drift_summary=drift_summary,
        )

    def get_execution_memory(self, execution_id: str) -> dict[str, Any]:
        snapshots = self.list_snapshots(execution_id=execution_id)
        states = self.list_states(execution_id=execution_id)
        lineage = self._list_lineage(execution_id)
        replay = self._list_replays(execution_id)
        return {
            "execution_id": execution_id,
            "snapshot_count": len(snapshots),
            "state_count": len(states),
            "lineage_count": len(lineage),
            "replay_count": len(replay),
            "latest_snapshot": snapshots[0].to_dict() if snapshots else None,
            "latest_state": states[0].to_dict() if states else None,
            "state_map": {
                state.state_type: state.to_dict()
                for state in states
            },
            "snapshots": [snapshot.to_dict() for snapshot in snapshots],
            "states": [state.to_dict() for state in states],
            "lineage": lineage,
            "replays": replay,
        }

    def replay_execution(self, execution_id: str) -> MemoryReplay:
        snapshots = self.list_snapshots(execution_id=execution_id)
        states = self.list_states(execution_id=execution_id)
        comparison = self.compare_snapshots(snapshots[-2].memory_id, snapshots[-1].memory_id) if len(snapshots) >= 2 else None
        replay_id = f"memory-replay-{uuid4().hex}"
        replay_type = "chronological"
        payload = {
            "memory_ids": [snapshot.memory_id for snapshot in snapshots],
            "state_count": len(states),
            "snapshot_count": len(snapshots),
            "comparison": comparison.to_dict() if comparison else None,
        }
        with get_session(self.db_path) as session:
            session.add(
                InstitutionalMemoryReplay(
                    replay_id=replay_id,
                    execution_id=execution_id,
                    replay_type=replay_type,
                    request_json={"execution_id": execution_id},
                    result_json=payload,
                )
            )
            session.commit()
        return MemoryReplay(
            replay_id=replay_id,
            execution_id=execution_id,
            replay_type=replay_type,
            created_at=datetime.now(UTC),
            memory_ids=tuple(snapshot.memory_id for snapshot in snapshots),
            states=tuple(states),
            snapshots=tuple(snapshots),
            comparison=comparison,
            metadata={"replay_strategy": replay_type},
        )

    def _list_lineage(self, execution_id: str) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(InstitutionalMemoryLineage)
                .filter(InstitutionalMemoryLineage.execution_id == execution_id)
                .order_by(InstitutionalMemoryLineage.created_at.desc(), InstitutionalMemoryLineage.id.desc())
                .all()
            )
            return [
                {
                    "id": row.id,
                    "execution_id": row.execution_id,
                    "memory_id": row.memory_id,
                    "event_type": row.event_type,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "payload_json": row.payload_json,
                    "created_at": row.created_at,
                }
                for row in rows
            ]

    def _list_replays(self, execution_id: str) -> list[dict[str, Any]]:
        with get_session(self.db_path) as session:
            rows = (
                session.query(InstitutionalMemoryReplay)
                .filter(InstitutionalMemoryReplay.execution_id == execution_id)
                .order_by(InstitutionalMemoryReplay.created_at.desc(), InstitutionalMemoryReplay.id.desc())
                .all()
            )
            return [
                {
                    "id": row.id,
                    "replay_id": row.replay_id,
                    "execution_id": row.execution_id,
                    "replay_type": row.replay_type,
                    "request_json": row.request_json,
                    "result_json": row.result_json,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
