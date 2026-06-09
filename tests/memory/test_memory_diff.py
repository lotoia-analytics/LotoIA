from __future__ import annotations

from lotoia.database import create_database
from lotoia.memory import InstitutionalMemoryRegistry, build_institutional_state_diff


def test_institutional_state_diff_tracks_snapshot_and_drift_axes(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    registry = InstitutionalMemoryRegistry(db_path)

    execution_id = "exec-diff-1"
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
        state_type="baseline_state",
        state={"baseline_state": "stable"},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_loaded", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="baseline_state",
        state={"baseline_state": "alert"},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="drift_state",
        state={"drift_state": 0.1},
        metadata={"source": "test"},
        lineage={"event_type": "drift_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="drift_state",
        state={"drift_state": 0.4},
        metadata={"source": "test"},
        lineage={"event_type": "drift_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )

    diff = build_institutional_state_diff(execution_id, db_path=db_path)

    assert diff["execution_id"] == execution_id
    assert diff["summary"]["snapshot_axis_ready"] is True
    assert diff["summary"]["baseline_axis_ready"] is True
    assert diff["summary"]["drift_axis_ready"] is True
    assert diff["summary"]["axis_count"] >= 3
    assert diff["axes"][0]["comparison"]["drift_summary"]["drift_ratio"] >= 0.0
