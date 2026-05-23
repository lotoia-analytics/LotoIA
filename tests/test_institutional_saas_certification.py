from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.analytics import build_institutional_saas_certification
from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.database.database import WorkflowEvent, create_database, get_session
from lotoia.database.adapter import resolve_institutional_adapter


def test_institutional_saas_certification_reports_full_readiness(tmp_path: Path) -> None:
    db_path = tmp_path / "certification.db"
    create_database(db_path)

    service = AuthenticationService(db_path)
    registration = service.register_user(
        email="premium@lotoia.dev",
        password="SuperSecret123!",
        role="premium",
        metadata_json={"source": "phase_10_validation"},
    )
    login = service.login(
        LoginRequest(email="premium@lotoia.dev", password="SuperSecret123!"),
        runtime_origin="streamlit_cloud",
        ip_hash="hash",
        user_agent="pytest",
        payload={"source": "phase_10_validation"},
    )
    service.configure_feature_policy(
        feature_name="ml",
        enabled=True,
        role_scope="premium",
        max_uses_per_session=2,
        payload={"source": "phase_10_validation"},
    )
    service.authorize_feature_policy(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="ml",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_10_validation"},
    )
    service.authorize_feature(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="expansion",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_10_validation"},
    )
    service.change_role(
        user_id=login.user.id,
        role="admin",
        session_id=login.session_id,
        runtime_origin="streamlit_cloud",
        reason="phase_10_validation",
        payload={"source": "phase_10_validation"},
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
        payload={"source": "phase_10_validation"},
    )
    adapter.save_expansion_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        expansion_type="expanded",
        expansion_size=5,
        runtime_origin="streamlit_cloud",
        strategy_profile="recorrente",
        payload={"source": "phase_10_validation"},
    )
    adapter.save_reconciliation_event(
        lead_id=int(lead["id"]),
        generation_event_id=int(generation["id"]),
        reconciliation_type="operational",
        hits=15,
        matched_numbers=list(range(1, 16)),
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_10_validation"},
    )

    with get_session(db_path) as session:
        session.add(
            WorkflowEvent(
                workflow_id="wf-phase-10",
                workflow_name="phase_10_validation",
                correlation_id="corr-phase-10",
                stage="certification",
                source="manual",
                status="completed",
                duration_ms=34.2,
                payload={"source": "phase_10_validation"},
                error_message="",
            )
        )
        session.commit()

    snapshot = build_institutional_saas_certification(db_path, limit=20)

    assert registration.created is True
    assert snapshot["status"] == "certified"
    assert snapshot["summary"]["shared_persistence_ok"] is True
    assert snapshot["summary"]["runtime_integrity_ok"] is True
    assert snapshot["summary"]["distributed_telemetry_ok"] is True
    assert snapshot["summary"]["identity_ok"] is True
    assert snapshot["summary"]["session_ok"] is True
    assert snapshot["summary"]["role_ok"] is True
    assert snapshot["summary"]["feature_ok"] is True
    assert snapshot["summary"]["lifecycle_ok"] is True
    assert snapshot["summary"]["observability_ok"] is True
    assert snapshot["summary"]["scientific_isolation_ok"] is True
    assert snapshot["audits"]["shared_persistence"] is True
    assert snapshot["audits"]["scientific_isolation"] is True
    assert snapshot["readiness"]["shared_persistence"] == "passed"
    assert snapshot["readiness"]["scientific_isolation"] == "passed"
    assert snapshot["scientific_isolation"]["isolated"] is True
    assert snapshot["scientific_isolation"]["benchmark_runs"] == 0
    assert snapshot["scientific_isolation"]["backtest_runs"] == 0
    assert snapshot["scientific_isolation"]["calibration_runs"] == 0
    assert snapshot["scientific_isolation"]["walk_forward_runs"] == 0

    with get_session(db_path) as session:
        assert session.execute(text("select count(*) from institutional_users")).scalar() == 1
        assert session.execute(text("select count(*) from auth_events")).scalar() == 2
        assert session.execute(text("select count(*) from auth_sessions")).scalar() == 1
        assert session.execute(text("select count(*) from access_events")).scalar() == 1
        assert session.execute(text("select count(*) from feature_flags")).scalar() == 1
        assert session.execute(text("select count(*) from feature_usage_events")).scalar() == 1
        assert session.execute(text("select count(*) from generation_events")).scalar() == 1
        assert session.execute(text("select count(*) from ml_usage_events")).scalar() == 1
        assert session.execute(text("select count(*) from check_events")).scalar() == 1
        assert session.execute(text("select count(*) from report_events")).scalar() == 1
        assert session.execute(text("select count(*) from expansion_events")).scalar() == 1
        assert session.execute(text("select count(*) from reconciliation_events")).scalar() == 1
        assert session.execute(text("select count(*) from workflow_events")).scalar() == 1
