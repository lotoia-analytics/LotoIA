from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent, ImportedContest
from lotoia.observability import ObservabilityRepository
from lotoia.assistance import build_adaptive_assistance_memory


def test_adaptive_assistance_memory_persists_context_and_replay(tmp_path: Path) -> None:
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

    memory = build_adaptive_assistance_memory(db_path)

    assert memory["state"] in {"memoria_adaptativa", "memoria_observacao"}
    assert memory["summary"]["execution_id"] != ""
    assert memory["summary"]["snapshot_count"] >= 0
    assert len(memory["memory_items"]) >= 4
    assert "replay_available" in memory["memory"]
