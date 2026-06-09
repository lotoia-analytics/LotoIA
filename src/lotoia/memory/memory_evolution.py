from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .memory_registry import InstitutionalMemoryRegistry


@dataclass(frozen=True, slots=True)
class MemoryEvolutionStep:
    execution_id: str
    timestamp: datetime
    label: str
    event_type: str
    memory_id: str
    change_count: int
    stable_count: int
    drift_ratio: float
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "timestamp": self.timestamp.isoformat(),
            "label": self.label,
            "event_type": self.event_type,
            "memory_id": self.memory_id,
            "change_count": self.change_count,
            "stable_count": self.stable_count,
            "drift_ratio": self.drift_ratio,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class MemoryEvolution:
    execution_id: str
    created_at: datetime
    steps: tuple[MemoryEvolutionStep, ...]
    summary: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "created_at": self.created_at.isoformat(),
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary,
            "metadata": self.metadata,
        }


def build_adaptive_evolution_tracking(
    execution_id: str,
    db_path: Path = DEFAULT_DATABASE_PATH,
    *,
    limit: int = 100,
) -> dict[str, Any]:
    registry = InstitutionalMemoryRegistry(db_path)
    snapshots = registry.list_snapshots(execution_id=execution_id, limit=limit)
    states = registry.list_states(execution_id=execution_id, limit=limit)

    steps = _evolution_steps(execution_id, snapshots, states)
    evolution = MemoryEvolution(
        execution_id=execution_id,
        created_at=datetime.now(UTC),
        steps=tuple(steps),
        summary={
            "snapshot_count": len(snapshots),
            "state_count": len(states),
            "step_count": len(steps),
            "change_count": sum(step.change_count for step in steps),
            "stable_count": sum(step.stable_count for step in steps),
            "latest_label": steps[0].label if steps else "-",
        },
        metadata={
            "layer": "adaptive_evolution_tracking",
            "execution_id": execution_id,
            "timeline_ready": bool(steps),
        },
    )
    return evolution.to_dict()


def _evolution_steps(
    execution_id: str,
    snapshots: list[Any],
    states: list[Any],
) -> list[MemoryEvolutionStep]:
    steps: list[MemoryEvolutionStep] = []
    snapshot_pairs = list(zip(snapshots[1:], snapshots[:-1]))
    state_pairs = list(zip(states[1:], states[:-1]))

    for current, previous in snapshot_pairs:
        comparison = _compare_payloads(previous.state, current.state)
        steps.append(
            MemoryEvolutionStep(
                execution_id=execution_id,
                timestamp=current.created_at,
                label=_label_for_snapshot(current.snapshot_type),
                event_type=f"snapshot::{current.snapshot_type}",
                memory_id=current.memory_id,
                change_count=len(comparison["changed_keys"]),
                stable_count=len(comparison["stable_keys"]),
                drift_ratio=comparison["drift_ratio"],
                details={
                    "changed_keys": comparison["changed_keys"],
                    "stable_keys": comparison["stable_keys"],
                    "added_keys": comparison["added_keys"],
                    "removed_keys": comparison["removed_keys"],
                },
            )
        )

    for current, previous in state_pairs:
        comparison = _compare_payloads(previous.state, current.state)
        steps.append(
            MemoryEvolutionStep(
                execution_id=execution_id,
                timestamp=current.created_at,
                label=_label_for_state(current.state_type),
                event_type=f"state::{current.state_type}",
                memory_id=current.memory_id,
                change_count=len(comparison["changed_keys"]),
                stable_count=len(comparison["stable_keys"]),
                drift_ratio=comparison["drift_ratio"],
                details={
                    "changed_keys": comparison["changed_keys"],
                    "stable_keys": comparison["stable_keys"],
                    "added_keys": comparison["added_keys"],
                    "removed_keys": comparison["removed_keys"],
                },
            )
        )

    steps.sort(key=lambda step: (step.timestamp, step.memory_id), reverse=True)
    return steps[:100]


def _compare_payloads(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_keys = set(left)
    right_keys = set(right)
    added = sorted(right_keys - left_keys)
    removed = sorted(left_keys - right_keys)
    shared = sorted(left_keys & right_keys)
    changed = sorted(key for key in shared if left.get(key) != right.get(key))
    stable = sorted(key for key in shared if left.get(key) == right.get(key))
    return {
        "added_keys": added,
        "removed_keys": removed,
        "changed_keys": changed,
        "stable_keys": stable,
        "drift_ratio": round(len(changed) / max(len(shared), 1), 4),
    }


def _label_for_snapshot(snapshot_type: str) -> str:
    mapping = {
        "baseline": "Evolucao baseline",
        "adaptive": "Evolucao adaptativa",
        "runtime": "Evolucao runtime",
        "drift": "Evolucao drift",
        "confidence": "Evolucao confianca",
        "health": "Evolucao saude",
    }
    return mapping.get(snapshot_type, f"Evolucao {snapshot_type}")


def _label_for_state(state_type: str) -> str:
    mapping = {
        "baseline_state": "Evolucao baseline",
        "drift_state": "Evolucao drift",
        "confidence_state": "Evolucao confianca",
        "adaptive_state": "Evolucao adaptativa",
        "runtime_health": "Evolucao saude",
    }
    return mapping.get(state_type, f"Evolucao {state_type}")
