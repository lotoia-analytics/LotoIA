from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.database.database import create_database, get_session


def test_authentication_service_registers_and_logs_user_session(tmp_path: Path) -> None:
    db_path = tmp_path / "auth.db"
    create_database(db_path)
    service = AuthenticationService(db_path)

    registration = service.register_user(
        email="operator@lotoia.dev",
        password="SuperSecret123!",
        role="operator",
        metadata_json={"source": "phase_6_validation"},
    )
    login = service.login(
        LoginRequest(email="operator@lotoia.dev", password="SuperSecret123!"),
        runtime_origin="streamlit_cloud",
        ip_hash="hash",
        user_agent="pytest",
        payload={"source": "phase_6_validation"},
    )
    logout = service.logout(
        user_id=login.user.id,
        session_id=login.session_id,
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_6_validation"},
    )

    assert registration.created is True
    assert registration.user.email == "operator@lotoia.dev"
    assert login.created is False
    assert login.session_id
    assert login.backend_snapshot["institutional_users"] == 1
    assert login.backend_snapshot["auth_events"] == 1
    assert login.backend_snapshot["auth_sessions"] == 1
    assert logout["event_type"] == "logout"

    with get_session(db_path) as session:
        assert session.execute(text("select count(*) from institutional_users")).scalar() == 1
        assert session.execute(text("select count(*) from auth_events")).scalar() == 2
        assert session.execute(text("select count(*) from auth_sessions")).scalar() == 1
