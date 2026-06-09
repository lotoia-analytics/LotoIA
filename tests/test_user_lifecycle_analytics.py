from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.analytics import build_user_lifecycle_analytics
from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.database.database import WorkflowEvent, create_database, get_session
from lotoia.database.adapter import resolve_institutional_adapter


def test_user_lifecycle_analytics_aggregates_institutional_journey(tmp_path: Path) -> None:
    db_path = tmp_path / "lifecycle.db"
    create_database(db_path)

    service = AuthenticationService(db_path)
    registration = service.register_user(
        email="premium@lotoia.dev",
        password="SuperSecret123!",
        role="premium",
        metadata_json={"source": "phase_9_validation"},
    )
    login = service.login(
        LoginRequest(email="premium@lotoia.dev", password="SuperSecret123!"),
        runtime_origin="streamlit_cloud",
        ip_hash="hash",
        user_agent="pytest",
        payload={"source": "phase_9_validation"},
    )
    service.configure_feature_policy(
        feature_name="ml",
        enabled=True,
        role_scope="premium",
        max_uses_per_session=2,
        payload={"source": "phase_9_validation"},
    )
    policy = service.authorize_feature_policy(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="ml",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_9_validation"},
    )

    adapter = resolve_institutional_adapter(db_path)
    lead = adapter.save_lead(
        first_name="Maria Divina",
        whatsapp="65998895555",
        source="user",
        ip_hash="hash",
        user_agent="pytest",
    )
    generation = adapter.save_generation_event(
        lead_id=int(lead["id"]),
        first_name="Maria Divina",
        whatsapp="65998895555",
        generated_games=[{"numbers": list(range(1, 16)), "profile_type": "recorrente"}],
        ml_enabled=True,
        seed=7,
        strategy="hybrid",
        ranking_score=0.97,
        execution_time_ms=12.5,
    )
    adapter.save_check_event(
        lead_id=int(lead["id"]),
        contest_id=3692,
        selected_numbers=list(range(1, 16)),
        hits=15,
        result_payload={"contest_id": 3692, "matched_numbers": list(range(1, 16))},
    )
    adapter.save_report_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        report_type="user_report",
        generation_origin="user",
        runtime_origin="streamlit_cloud",
        strategy_profile="recorrente",
        payload={"source": "phase_9_validation"},
    )
    adapter.save_expansion_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        expansion_type="expanded",
        expansion_size=5,
        runtime_origin="streamlit_cloud",
        strategy_profile="recorrente",
        payload={"source": "phase_9_validation"},
    )
    adapter.save_reconciliation_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        reconciliation_type="operational",
        hits=15,
        matched_numbers=list(range(1, 16)),
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_9_validation"},
    )

    with get_session(db_path) as session:
        session.add(
            WorkflowEvent(
                workflow_id="wf-phase-9",
                workflow_name="phase_9_validation",
                correlation_id="corr-phase-9",
                stage="telemetry",
                source="manual",
                status="completed",
                duration_ms=34.2,
                payload={"source": "phase_9_validation"},
                error_message="",
            )
        )
        session.commit()

    snapshot = build_user_lifecycle_analytics(db_path, limit=20)

    assert registration.created is True
    assert policy.allowed is True
    assert snapshot["summary"]["status"] == "active"
    assert snapshot["summary"]["active_users"] == 1
    assert snapshot["summary"]["active_sessions"] == 1
    assert snapshot["lifecycle"]["institutional_users"] == 1
    assert snapshot["lifecycle"]["auth_events"] == 1
    assert snapshot["lifecycle"]["auth_sessions"] == 1
    assert snapshot["lifecycle"]["feature_usage_events"] == 1
    assert snapshot["lifecycle"]["generation_events"] == 1
    assert snapshot["lifecycle"]["ml_usage_events"] == 1
    assert snapshot["lifecycle"]["check_events"] == 1
    assert snapshot["lifecycle"]["report_events"] == 1
    assert snapshot["lifecycle"]["expansion_events"] == 1
    assert snapshot["lifecycle"]["reconciliation_events"] == 1
    assert snapshot["lifecycle"]["workflow_events"] == 1
    assert snapshot["lifecycle"]["role_distribution"]["premium"] == 1
    assert snapshot["lifecycle"]["feature_usage"]["ml"]["allowed"] == 1
    assert snapshot["analytics"]["session_activity_rate"] == 1.0
    assert snapshot["analytics"]["feature_governance_density"] == 1.0
    assert snapshot["analytics"]["event_coverage"] == 6.0
    event_types = {row["event_type"] for row in snapshot["timeline"]}
    assert {"login", "feature_usage", "generation", "check", "report", "expansion", "reconciliation", "workflow"} <= event_types

    with get_session(db_path) as session:
        assert session.execute(text("select count(*) from auth_events")).scalar() == 1
        assert session.execute(text("select count(*) from feature_usage_events")).scalar() == 1
        assert session.execute(text("select count(*) from generation_events")).scalar() == 1
        assert session.execute(text("select count(*) from check_events")).scalar() == 1
        assert session.execute(text("select count(*) from report_events")).scalar() == 1
        assert session.execute(text("select count(*) from expansion_events")).scalar() == 1
        assert session.execute(text("select count(*) from reconciliation_events")).scalar() == 1
        assert session.execute(text("select count(*) from workflow_events")).scalar() == 1
