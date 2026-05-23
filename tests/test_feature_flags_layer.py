from __future__ import annotations

from pathlib import Path

from sqlalchemy import text

from lotoia.authentication import AuthenticationService, LoginRequest
from lotoia.database.database import create_database, get_session


def test_feature_flag_governance_records_feature_usage_and_limits(tmp_path: Path) -> None:
    db_path = tmp_path / "feature_flags.db"
    create_database(db_path)
    service = AuthenticationService(db_path)

    registration = service.register_user(
        email="premium@lotoia.dev",
        password="SuperSecret123!",
        role="premium",
        metadata_json={"source": "phase_8_validation"},
    )
    login = service.login(
        LoginRequest(email="premium@lotoia.dev", password="SuperSecret123!"),
        runtime_origin="streamlit_cloud",
        ip_hash="hash",
        user_agent="pytest",
        payload={"source": "phase_8_validation"},
    )
    flag = service.configure_feature_policy(
        feature_name="ml",
        enabled=True,
        role_scope="premium",
        max_uses_per_session=1,
        payload={"source": "phase_8_validation"},
    )
    first_decision = service.authorize_feature_policy(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="ml",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_8_validation"},
    )
    second_decision = service.authorize_feature_policy(
        user_id=login.user.id,
        session_id=login.session_id,
        feature_name="ml",
        runtime_origin="streamlit_cloud",
        payload={"source": "phase_8_validation"},
    )

    assert registration.created is True
    assert flag["feature_name"] == "ml"
    assert flag["enabled"] == 1
    assert first_decision.allowed is True
    assert first_decision.usage_count == 0
    assert second_decision.allowed is False
    assert second_decision.usage_count == 1
    assert second_decision.limit == 1
    assert second_decision.snapshot["feature_flags"] == 1
    assert second_decision.snapshot["feature_usage_events"] == 2

    with get_session(db_path) as session:
        assert session.execute(text("select count(*) from institutional_users")).scalar() == 1
        assert session.execute(text("select count(*) from auth_events")).scalar() == 1
        assert session.execute(text("select count(*) from auth_sessions")).scalar() == 1
        assert session.execute(text("select count(*) from feature_flags")).scalar() == 1
        assert session.execute(text("select count(*) from feature_usage_events")).scalar() == 2
