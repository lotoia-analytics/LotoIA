from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent, ImportedContest
from lotoia.observability import ObservabilityRepository
from lotoia.assistance import build_contextual_recommendations


def test_contextual_recommendations_track_history_and_presence(tmp_path: Path) -> None:
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
                generated_games=[{"numbers": list(range(1, 16))}],
                ml_enabled=0,
                seed=42,
                strategy="test",
                ranking_score=0.91,
                execution_time_ms=1.2,
            )
        )
        session.add(ImportedContest(contest_number=5000, data="{}", dezenas="1,2,3"))
        session.commit()

    execution_id = observability.start_execution(flow_name="generation", stage="runtime", context={"source": "test"})
    observability.record_snapshot(execution_id, snapshot_type="runtime", payload={"state": "ok"}, metadata={"source": "test"})
    observability.finish_execution(execution_id, status="ok", stage="done", duration_ms=12.0)

    recommendation = build_contextual_recommendations(db_path)

    assert recommendation["state"] in {"stable", "attention"}
    assert recommendation["summary"]["presence"] in {"fully_live", "live_monitoring"}
    assert recommendation["summary"]["historical_trend"] != ""
    assert len(recommendation["recommendations"]) >= 4
    assert len(recommendation["explanation"]) >= 3
