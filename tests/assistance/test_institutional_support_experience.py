from __future__ import annotations

from pathlib import Path

from lotoia.database.database import create_database, get_session, Lead, GenerationEvent, ImportedContest
from lotoia.observability import ObservabilityRepository
from lotoia.assistance import build_institutional_support_experience, build_assistance_governance


def test_institutional_support_experience_and_governance_align(tmp_path: Path) -> None:
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

    experience = build_institutional_support_experience(db_path)
    governance = build_assistance_governance(db_path)

    assert experience["state"] in {"experiencia_assistida", "experiencia_em_observacao"}
    assert governance["state"] in {"governada", "revisar"}
    assert experience["summary"]["presence"] in {"fully_live", "live_monitoring"}
    assert len(experience["experience"]) >= 6
    assert len(governance["rules"]) >= 4
