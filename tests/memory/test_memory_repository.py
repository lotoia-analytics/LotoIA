from __future__ import annotations

from lotoia.database import create_database
from lotoia.memory import InstitutionalMemoryRegistry, InstitutionalMemoryRepository


def test_memory_repository_summarizes_execution_tables(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    registry = InstitutionalMemoryRegistry(db_path)

    execution_id = "exec-repository-1"
    registry.register_snapshot(
        execution_id=execution_id,
        snapshot_type="baseline",
        state={"baseline_state": "stable"},
        metadata={"source": "test"},
        lineage={"event_type": "baseline_loaded", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.register_state(
        execution_id=execution_id,
        state_type="confidence_state",
        state={"confidence_state": 0.91},
        metadata={"source": "test"},
        lineage={"event_type": "confidence_updated", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    registry.replay_execution(execution_id)

    repository = InstitutionalMemoryRepository(db_path)
    summary = repository.summarize_execution(execution_id)

    assert summary.snapshot_count == 1
    assert summary.state_count >= 2
    assert summary.lineage_count >= 2
    assert summary.replay_count == 1
    assert summary.to_dict()["replay_count"] == 1
