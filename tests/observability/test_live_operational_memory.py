from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent
from lotoia.memory import InstitutionalMemoryRegistry
from lotoia.observability import ObservabilityRepository, build_live_operational_memory


def test_live_operational_memory_reads_memory_and_story(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    registry = InstitutionalMemoryRegistry(db_path)

    with get_session(db_path) as session:
        lead = Lead(first_name="Ana", whatsapp="11999999999", source="test", ip_hash="", user_agent="pytest")
        session.add(lead)
        session.commit()
        session.add(
            GenerationEvent(
                lead_id=lead.id,
                generated_games=[{"numbers": list(range(1, 16))}],
                ml_enabled=0,
                seed=42,
                strategy="test",
                ranking_score=0.91,
                execution_time_ms=1.2,
            )
        )
        session.commit()

    observability = ObservabilityRepository(db_path)
    execution_id = observability.start_execution(flow_name="generation", stage="runtime", context={"source": "test"})
    registry.register_state(
        execution_id=execution_id,
        state_type="runtime_health",
        state={"status": "ok"},
        metadata={"source": "test"},
    )
    registry.register_snapshot(
        execution_id=execution_id,
        snapshot_type="runtime",
        state={"status": "ok"},
        metadata={"source": "test"},
        lineage={"event_type": "runtime_snapshot", "entity_type": "runtime_execution", "entity_id": execution_id},
    )
    observability.record_snapshot(execution_id, snapshot_type="runtime", payload={"state": "ok"}, metadata={"source": "test"})
    observability.finish_execution(execution_id, status="ok", stage="done", duration_ms=12.0)

    memory = build_live_operational_memory(db_path)

    assert memory["summary"]["memory_status"] == "live"
    assert memory["summary"]["latest_execution_id"] == execution_id
    assert memory["summary"]["replay_ready"] in {True, False}
    assert "story" in memory
