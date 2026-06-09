from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.database.database import create_database, get_session


def test_role_governance_records_access_events_and_role_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "roles.db"
    create_database(db_path)
    service = AuthenticationService(db_path)

    registration = service.register_user(
        email="operator@lotoia.dev",
        password="SuperSecret123!",
        role="operator",
        metadata_json={"source": "phase_7_validation"},
    )
    login = service.login(
        LoginRequest(email="operator@lotoia.dev", password="SuperSecret123!"),
        runtime_origin="streamlit_cloud",
        ip_hash="hash",
        user_agent="pytest",
        payload={"source": "phase_7_validation"},
    )
    decision = service.authorize_feature(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="expansion",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_7_validation"},
    )
    role_change = service.change_role(
        user_id=login.user.id,
        role="admin",
        session_id=login.session_id,
        runtime_origin="streamlit_cloud",
        reason="phase_7_validation",
        payload={"source": "phase_7_validation"},
    )
    second_decision = service.authorize_feature(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="expansion",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_7_validation"},
    )

    assert registration.created is True
    assert decision.allowed is False
    assert decision.role == "operator"
    assert second_decision.allowed is True
    assert second_decision.role == "admin"
    assert role_change["event_type"] == "role_change"

    with get_session(db_path) as session:
        assert session.execute(text("select count(*) from institutional_users")).scalar() == 1
        assert session.execute(text("select count(*) from auth_events")).scalar() == 2
        assert session.execute(text("select count(*) from auth_sessions")).scalar() == 1
        assert session.execute(text("select count(*) from access_events")).scalar() == 2
