from __future__ import annotations

from pathlib import Path

import pytest

from lotoia.authentication import AuthenticationService
from lotoia.database.database import create_database
from lotoia.governance.cloud_runtime_policy import is_auth_required


def test_is_auth_required_respects_explicit_disable(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("LOTOIA_AUTH_REQUIRED", "0")
    assert is_auth_required() is False


def test_authentication_service_bootstrap_admin_pattern(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOTOIA_ADMIN_EMAIL", "admin@lotoia.chat")
    monkeypatch.setenv("LOTOIA_ADMIN_PASSWORD", "SecurePass123!")
    db_path = tmp_path / "auth.db"
    create_database(db_path)
    service = AuthenticationService(db_path)

    email = "admin@lotoia.chat"
    password = "SecurePass123!"
    snapshot = service.adapter.fetch_latest_auth_snapshot()
    if int(snapshot.get("institutional_users", 0) or 0) == 0:
        service.register_user(email=email, password=password, role="admin")

    from lotoia.authentication import LoginRequest

    login = service.login(LoginRequest(email=email, password=password))
    assert login.user.email == email
    assert login.user.role == "admin"
    assert login.session_id
