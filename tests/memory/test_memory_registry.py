from __future__ import annotations

from lotoia.database import create_database
from lotoia.memory import InstitutionalMemoryRegistry


def test_memory_registry_registers_snapshots_and_replays(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    registry = InstitutionalMemoryRegistry(db_path)

    first = registry.register_snapshot(
        execution_id="exec-1",
        snapshot_type="baseline",
        state={"baseline_state": "stable", "drift_state": 0.1, "confidence_state": 0.95},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_loaded", "entity_type": "runtime_execution", "entity_id": "exec-1"},
    )
    second = registry.register_snapshot(
        execution_id="exec-1",
        snapshot_type="adaptive",
        state={"baseline_state": "stable", "drift_state": 0.3, "confidence_state": 0.80, "adaptive_state": "warm"},
        metadata={"source": "test"},
        lineage={"event_type": "adaptive_updated", "entity_type": "runtime_execution", "entity_id": "exec-1"},
    )

    fetched = registry.get_snapshot(first.memory_id)
    comparison = registry.compare_snapshots(first.memory_id, second.memory_id)
    memory = registry.get_execution_memory("exec-1")
    replay = registry.replay_execution("exec-1")

    assert fetched is not None
    assert fetched.memory_id == first.memory_id
    assert comparison.changed_keys == ("confidence_state", "drift_state")
    assert comparison.stable_keys == ("baseline_state",)
    assert memory["snapshot_count"] == 2
    assert memory["state_count"] == 2
    assert memory["lineage_count"] == 2
    assert memory["replay_count"] == 0
    assert replay.execution_id == "exec-1"
    assert replay.comparison is not None
    assert replay.comparison.changed_keys == comparison.changed_keys
    assert replay.memory_ids == (second.memory_id, first.memory_id)
