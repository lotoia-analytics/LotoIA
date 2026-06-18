from __future__ import annotations

import os

from lotoia.database.env_resolution import (
    COMPAT_DATABASE_PUBLIC_URL_ENV,
    is_invalid_database_url_literal,
    is_placeholder_database_url,
    promote_resolved_database_url_to_env,
    resolve_institutional_database_url_from_env,
)
from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy


def test_rejects_literal_database_url_name(monkeypatch) -> None:
    assert is_invalid_database_url_literal("DATABASE_URL") is True
    monkeypatch.setenv("DATABASE_URL", "DATABASE_URL")
    monkeypatch.delenv(COMPAT_DATABASE_PUBLIC_URL_ENV, raising=False)
    assert resolve_institutional_database_url_from_env() == ("", "")


def test_database_url_is_sovereign_over_public_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")
    monkeypatch.setenv(
        COMPAT_DATABASE_PUBLIC_URL_ENV,
        "postgresql://user:pass@shortline.proxy.rlwy.net:32647/railway",
    )
    url, source = resolve_institutional_database_url_from_env()
    assert source == "DATABASE_URL"
    assert "railway.internal" in url


def test_public_url_fallback_when_database_url_literal(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "DATABASE_URL")
    monkeypatch.setenv(
        COMPAT_DATABASE_PUBLIC_URL_ENV,
        "postgresql://user:pass@shortline.proxy.rlwy.net:32647/railway",
    )
    url, source = resolve_institutional_database_url_from_env()
    assert source == COMPAT_DATABASE_PUBLIC_URL_ENV
    assert "shortline.proxy.rlwy.net" in url


def test_promote_public_fallback_into_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "DATABASE_URL")
    monkeypatch.setenv(
        COMPAT_DATABASE_PUBLIC_URL_ENV,
        "postgresql://user:pass@shortline.proxy.rlwy.net:32647/railway",
    )
    promote_resolved_database_url_to_env()
    assert os.environ["DATABASE_URL"].startswith("postgresql://")
    assert "shortline.proxy.rlwy.net" in os.environ["DATABASE_URL"]


def test_cloud_policy_allows_public_fallback_on_railway(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "DATABASE_URL")
    monkeypatch.setenv(
        COMPAT_DATABASE_PUBLIC_URL_ENV,
        "postgresql://user:pass@shortline.proxy.rlwy.net:32647/railway",
    )
    result = evaluate_cloud_runtime_policy(tmp_path / "lotoia.db")
    assert result.ok is True
    assert result.backend == "postgresql"
    assert result.database_source == "DATABASE_URL"


def test_cloud_policy_fails_literal_without_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOTOIA_CLOUD_ONLY", "1")
    monkeypatch.setenv("DATABASE_URL", "DATABASE_URL")
    monkeypatch.delenv(COMPAT_DATABASE_PUBLIC_URL_ENV, raising=False)
    result = evaluate_cloud_runtime_policy(tmp_path / "lotoia.db")
    assert result.ok is False
    assert any("literal" in item.lower() or "ausente" in item.lower() for item in result.violations)


def test_placeholder_host_user_pass_rejected() -> None:
    assert is_placeholder_database_url("postgresql://user:pass@host:5432/lotoia") is True
    assert (
        is_placeholder_database_url("postgresql://user:pass@postgres.railway.internal:5432/railway")
        is False
    )


def test_cursor_placeholder_host_rejected() -> None:
    assert is_placeholder_database_url("https://cursor.com") is True
    assert is_placeholder_database_url("postgresql://user:pass@cursor.com:5432/railway") is True
