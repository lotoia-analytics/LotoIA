from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent, ImportedContest
from lotoia.observability import ObservabilityRepository, build_runtime_storytelling


def test_runtime_storytelling_reports_a_live_narrative(tmp_path: Path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    repository = ObservabilityRepository(db_path)

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

    execution_id = repository.start_execution(flow_name="generation", stage="runtime", context={"source": "test"})
    repository.finish_execution(execution_id, status="ok", stage="done", duration_ms=12.0)

    story = build_runtime_storytelling(db_path)

    assert story["summary"]["telemetry_status"] == "live"
    assert story["summary"]["runtime_awareness"] == "connected"
    assert story["summary"]["active_signals"] >= 2
    assert story["headline"] in {"plataforma viva e coordenada", "plataforma em observacao", "plataforma em atencao"}
    assert len(story["narrative"]) >= 3
    assert len(story["timeline"]) == 3
