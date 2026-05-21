from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .memory_registry import InstitutionalMemoryRegistry


@dataclass(frozen=True, slots=True)
class MemoryTimelineEntry:
    execution_id: str
    timestamp: datetime
    event_type: str
    label: str
    memory_id: str
    state_type: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "label": self.label,
            "memory_id": self.memory_id,
            "state_type": self.state_type,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class MemoryTimeline:
    execution_id: str
    created_at: datetime
    entries: tuple[MemoryTimelineEntry, ...]
    markers: tuple[dict[str, Any], ...]
    summary: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at.isoformat(),
            "entries": [entry.to_dict() for entry in self.entries],
            "markers": list(self.markers),
            "summary": self.summary,
            "metadata": self.metadata,
        }


def build_memory_timeline(
    execution_id: str,
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    registry = InstitutionalMemoryRegistry(db_path)
    snapshots = registry.list_snapshots(execution_id=execution_id, limit=limit)
    states = registry.list_states(execution_id=execution_id, limit=limit)
    replay = registry.get_execution_replay(execution_id)

    entries = _timeline_entries(execution_id, snapshots, states, replay)
    markers = [
        {
            "timestamp": entry.timestamp.isoformat(),
            "label": entry.label,
            "event_type": entry.event_type,
            "state_type": entry.state_type,
        }
        for entry in entries
    ]
    timeline = MemoryTimeline(
        execution_id=execution_id,
        created_at=datetime.now(UTC),
        entries=tuple(entries),
        markers=tuple(markers),
        summary={
            "snapshot_count": len(snapshots),
            "state_count": len(states),
            "marker_count": len(markers),
            "latest_event": entries[0].event_type if entries else "-",
            "replay_ready": replay is not None,
        },
        metadata={
            "layer": "executive_memory_timeline",
            "lineage_available": bool(registry.get_execution_memory(execution_id).get("lineage")),
            "replay_available": replay is not None,
        },
    )
    return timeline.to_dict()


def _timeline_entries(
    execution_id: str,
    snapshots: list[Any],
    states: list[Any],
    replay: Any | None,
) -> list[MemoryTimelineEntry]:
    entries: list[MemoryTimelineEntry] = []

    for snapshot in snapshots:
        entries.append(
            MemoryTimelineEntry(
                execution_id=execution_id,
                timestamp=snapshot.created_at,
                event_type=f"snapshot::{snapshot.snapshot_type}",
                label=_label_for_snapshot(snapshot.snapshot_type),
                memory_id=snapshot.memory_id,
                state_type=snapshot.snapshot_type,
                details={
                    "metadata": snapshot.metadata,
                    "lineage": snapshot.lineage,
                    "state_keys": sorted(snapshot.state.keys()),
                },
            )
        )

    for state in states:
        entries.append(
            MemoryTimelineEntry(
                execution_id=execution_id,
                timestamp=state.created_at,
                event_type=f"state::{state.state_type}",
                label=_label_for_state(state.state_type),
                memory_id=state.memory_id,
                state_type=state.state_type,
                details={
                    "metadata": state.metadata,
                    "state_keys": sorted(state.state.keys()),
                },
            )
        )

    if replay is not None:
        entries.append(
            MemoryTimelineEntry(
                execution_id=execution_id,
                timestamp=replay.created_at,
                event_type=f"replay::{replay.replay_type}",
                label="Replay cronologico",
                memory_id=replay.replay_id,
                state_type="replay",
                details={
                    "memory_ids": list(replay.memory_ids),
                    "comparison": replay.comparison.to_dict() if replay.comparison else None,
                },
            )
        )

    entries.sort(key=lambda entry: (entry.timestamp, entry.memory_id), reverse=True)
    return entries[:100]


def _label_for_snapshot(snapshot_type: str) -> str:
    mapping = {
        "baseline": "Snapshot baseline",
        "adaptive": "Snapshot adaptativo",
        "runtime": "Snapshot runtime",
        "drift": "Snapshot drift",
        "confidence": "Snapshot confianca",
        "health": "Snapshot saude",
    }
    return mapping.get(snapshot_type, f"Snapshot {snapshot_type}")


def _label_for_state(state_type: str) -> str:
    mapping = {
        "baseline_state": "Estado baseline",
        "drift_state": "Estado drift",
        "confidence_state": "Estado confianca",
        "adaptive_state": "Estado adaptativo",
        "runtime_health": "Estado de saude",
    }
    return mapping.get(state_type, f"Estado {state_type}")
