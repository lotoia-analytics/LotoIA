from __future__ import annotations

from lotoia.database import create_database
from lotoia.memory import InstitutionalMemoryRegistry, build_memory_timeline
from lotoia.observability import ObservabilityRepository


def test_memory_timeline_uses_execution_id_and_replay(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)

    observability = ObservabilityRepository(db_path)
    execution_id = observability.start_execution(
        flow_name="generation",
        stage="runtime",
        context={"source": "test"},
    )

    registry = InstitutionalMemoryRegistry(db_path)
    registry.register_snapshot(
        execution_id=execution_id,
        snapshot_type="baseline",
        state={"baseline_state": "stable", "drift_state": 0.1, "confidence_state": 0.95},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_loaded", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="adaptive_state",
        state={"adaptive_state": "warm"},
        metadata={"source": "test"},
        lineage={"event_type": "adaptive_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.replay_execution(execution_id)

    timeline = build_memory_timeline(execution_id, db_path=db_path)

    assert timeline["execution_id"] == execution_id
    assert timeline["summary"]["snapshot_count"] == 1
    assert timeline["summary"]["state_count"] == 2
    assert timeline["summary"]["replay_ready"] is True
    assert timeline["summary"]["marker_count"] >= 2
    assert timeline["entries"][0]["execution_id"] == execution_id
    assert timeline["entries"][0]["label"]
