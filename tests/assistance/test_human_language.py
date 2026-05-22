from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent, ImportedContest
from lotoia.observability import ObservabilityRepository
from lotoia.assistance import build_human_analytical_language


def test_human_analytical_language_translates_signals_to_executive_language(tmp_path: Path) -> None:
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

    language = build_human_analytical_language(db_path)

    assert language["state"] in {"linguagem_humana", "linguagem_guiada"}
    assert language["summary"]["guidance_state"] != ""
    assert len(language["phrases"]) >= 4
    assert len(language["highlights"]) >= 4
