from __future__ import annotations

from lotoia.database import create_database
from lotoia.memory import InstitutionalMemoryRegistry, build_adaptive_evolution_tracking


def test_adaptive_evolution_tracking_compares_consecutive_memory_states(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    registry = InstitutionalMemoryRegistry(db_path)

    execution_id = "exec-evolution-1"
    registry.register_snapshot(
        execution_id=execution_id,
        snapshot_type="baseline",
        state={"baseline_state": "stable", "drift_state": 0.1, "confidence_state": 0.95},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_loaded", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_snapshot(
        execution_id=execution_id,
        snapshot_type="adaptive",
        state={"baseline_state": "stable", "drift_state": 0.4, "confidence_state": 0.82, "adaptive_state": "warm"},
        metadata={"source": "test"},
        lineage={"event_type": "adaptive_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="drift_state",
        state={"drift_state": 0.4},
        metadata={"source": "test"},
        lineage={"event_type": "drift_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="confidence_state",
        state={"confidence_state": 0.82},
        metadata={"source": "test"},
        lineage={"event_type": "confidence_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )

    evolution = build_adaptive_evolution_tracking(execution_id, db_path=db_path)

    assert evolution["execution_id"] == execution_id
    assert evolution["summary"]["snapshot_count"] == 2
    assert evolution["summary"]["state_count"] == 4
    assert evolution["summary"]["step_count"] >= 2
    assert evolution["summary"]["change_count"] >= 1
    assert evolution["summary"]["latest_label"]
    assert evolution["steps"][0]["execution_id"] == execution_id
