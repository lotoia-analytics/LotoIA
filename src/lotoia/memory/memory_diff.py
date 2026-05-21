from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .memory_registry import InstitutionalMemoryRegistry, MemoryComparison


@dataclass(frozen=True, slots=True)
class MemoryDiffAxis:
    axis: str
    left_memory_id: str
    right_memory_id: str
    comparison: MemoryComparison

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis,
            "left_memory_id": self.left_memory_id,
            "right_memory_id": self.right_memory_id,
            "comparison": self.comparison.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class InstitutionalStateDiff:
    execution_id: str
    created_at: datetime
    axes: tuple[MemoryDiffAxis, ...]
    summary: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at.isoformat(),
            "axes": [axis.to_dict() for axis in self.axes],
            "summary": self.summary,
            "metadata": self.metadata,
        }


def build_institutional_state_diff(
    execution_id: str,
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    left_memory_id: str | None = None,
    right_memory_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    registry = InstitutionalMemoryRegistry(db_path)
    snapshots = registry.list_snapshots(execution_id=execution_id, limit=limit)
    states = registry.list_states(execution_id=execution_id, limit=limit)

    axes: list[MemoryDiffAxis] = []
    if len(snapshots) >= 2:
        left_snapshot = registry.get_snapshot(left_memory_id or snapshots[-1].memory_id)
        right_snapshot = registry.get_snapshot(right_memory_id or snapshots[0].memory_id)
        if left_snapshot is not None and right_snapshot is not None:
            axes.append(
                MemoryDiffAxis(
                    axis="snapshot_vs_snapshot",
                    left_memory_id=left_snapshot.memory_id,
                    right_memory_id=right_snapshot.memory_id,
                    comparison=registry.compare_snapshots(left_snapshot.memory_id, right_snapshot.memory_id),
                )
            )

    baseline_states = [state for state in states if state.state_type == "baseline_state"]
    if len(baseline_states) >= 2:
        left_state = baseline_states[-1]
        right_state = baseline_states[0]
        axes.append(
                MemoryDiffAxis(
                    axis="baseline_vs_baseline",
                    left_memory_id=left_state.memory_id,
                    right_memory_id=right_state.memory_id,
                    comparison=_compare_state_payloads(left_state.state, right_state.state),
                )
            )

    drift_states = [state for state in states if state.state_type == "drift_state"]
    if len(drift_states) >= 2:
        left_state = drift_states[-1]
        right_state = drift_states[0]
        axes.append(
                MemoryDiffAxis(
                    axis="drift_evolution",
                    left_memory_id=left_state.memory_id,
                    right_memory_id=right_state.memory_id,
                    comparison=_compare_state_payloads(left_state.state, right_state.state),
                )
            )

    diff = InstitutionalStateDiff(
        execution_id=execution_id,
        created_at=datetime.now(UTC),
        axes=tuple(axes),
        summary={
            "axis_count": len(axes),
            "snapshot_count": len(snapshots),
            "state_count": len(states),
            "baseline_axis_ready": any(axis.axis == "baseline_vs_baseline" for axis in axes),
            "drift_axis_ready": any(axis.axis == "drift_evolution" for axis in axes),
            "snapshot_axis_ready": any(axis.axis == "snapshot_vs_snapshot" for axis in axes),
        },
        metadata={
            "layer": "institutional_state_diff_engine",
            "execution_id": execution_id,
            "drift_aware": True,
        },
    )
    return diff.to_dict()


def _compare_state_payloads(left: dict[str, Any], right: dict[str, Any]) -> MemoryComparison:
    left_keys = set(left)
    right_keys = set(right)
    added = tuple(sorted(right_keys - left_keys))
    removed = tuple(sorted(left_keys - right_keys))
    shared = sorted(left_keys & right_keys)
    changed = tuple(sorted(key for key in shared if left.get(key) != right.get(key)))
    stable = tuple(sorted(key for key in shared if left.get(key) == right.get(key)))
    drift_summary = {
        "changed_count": len(changed),
        "stable_count": len(stable),
        "added_count": len(added),
        "removed_count": len(removed),
        "drift_ratio": round(len(changed) / max(len(shared), 1), 4),
    }
    return MemoryComparison(
        left_memory_id="left_state",
        right_memory_id="right_state",
        added_keys=added,
        removed_keys=removed,
        changed_keys=changed,
        stable_keys=stable,
        drift_summary=drift_summary,
    )
