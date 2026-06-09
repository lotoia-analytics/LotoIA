from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent
from lotoia.database import DEFAULT_DATABASE_PATH
from lotoia.observability import ObservabilityRepository, build_live_telemetry_snapshot


def test_live_telemetry_snapshot_reads_runtime_activity(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    observability = ObservabilityRepository(db_path)

    with get_session(db_path) as session:
        lead = Lead(first_name="Ana", whatsapp="11999999999", source="test", ip_hash="", user_agent="pytest")
        session.add(lead)
        session.commit()
        session.add(
            GenerationEvent(
                lead_id=lead.id,
                generated_games=[{"numbers": list(range(1, 16)), "profile_type": "recorrente"}],
                ml_enabled=0,
                seed=42,
                strategy="test",
                ranking_score=0.91,
                execution_time_ms=1.2,
            )
        )
        session.commit()
    execution_id = observability.start_execution(flow_name="generation", stage="runtime", context={"source": "test"})
    observability.record_snapshot(execution_id, snapshot_type="runtime", payload={"state": "ok"}, metadata={"source": "test"})
    observability.finish_execution(execution_id, status="ok", stage="done", duration_ms=12.0)

    snapshot = build_live_telemetry_snapshot(db_path)

    assert snapshot["summary"]["telemetry_status"] == "live"
    assert snapshot["activity"]["generation_events"] == 1
    assert snapshot["runtime_status"]["execution_count"] == 1
    assert snapshot["summary"]["latest_execution_id"] == execution_id
    assert len(snapshot["alerts"]) == 2
