from __future__ import annotations

import os
from pathlib import Path

import pytest

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.governance.cloud_runtime_policy import (
    cloud_runtime_policy_snapshot,
    enforce_cloud_runtime_policy,
    evaluate_cloud_runtime_policy,
    is_auth_required,
    is_cloud_production_runtime,
)


def test_cloud_runtime_detected_from_railway_env(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("LOTOIA_CLOUD_ONLY", raising=False)
    assert is_cloud_production_runtime() is True


def test_auth_required_by_default_in_cloud(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("LOTOIA_AUTH_REQUIRED", raising=False)
    assert is_auth_required() is True


def test_auth_can_be_disabled_explicitly(monkeypatch) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("LOTOIA_AUTH_REQUIRED", "0")
    assert is_auth_required() is False


def test_cloud_policy_fails_without_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOTOIA_CLOUD_ONLY", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PUBLIC_URL", raising=False)

    result = evaluate_cloud_runtime_policy(tmp_path / "lotoia.db")
    assert result.ok is False
    assert any("DATABASE_URL ausente" in item for item in result.violations)


def test_cloud_policy_passes_with_postgresql_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOTOIA_CLOUD_ONLY", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@postgres.railway.internal:5432/railway")

    result = evaluate_cloud_runtime_policy(tmp_path / "lotoia.db")
    assert result.ok is True
    assert result.backend == "postgresql"


def test_cloud_policy_rejects_localhost_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOTOIA_CLOUD_ONLY", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@127.0.0.1:5432/lotoia")

    with pytest.raises(RuntimeError, match="localhost"):
        enforce_cloud_runtime_policy(tmp_path / "lotoia.db")


def test_cloud_runtime_detected_from_railway_public_domain(monkeypatch) -> None:
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOTOIA_CLOUD_ONLY", raising=False)
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "lotoia-production.up.railway.app")
    assert is_cloud_production_runtime() is True


def test_cloud_policy_snapshot_reports_status(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PUBLIC_URL", raising=False)
    monkeypatch.delenv("LOTOIA_CLOUD_ONLY", raising=False)

    snapshot = cloud_runtime_policy_snapshot(tmp_path / "lotoia.db")
    assert snapshot["backend"] == "sqlite"
    assert snapshot["status"] == "PASS"


def test_cloud_policy_fails_on_operational_path_without_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PUBLIC_URL", raising=False)
    monkeypatch.delenv("LOTOIA_CLOUD_ONLY", raising=False)

    result = evaluate_cloud_runtime_policy(Path("data/lotoia.db"))
    assert result.ok is False
    assert any("DATABASE_URL ausente" in item for item in result.violations)


def test_operational_adapter_requires_database_url(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PUBLIC_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        InstitutionalDatabaseAdapter(Path("data/lotoia.db")).database_url


def test_ephemeral_sqlite_still_allowed_without_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PUBLIC_URL", raising=False)

    adapter = InstitutionalDatabaseAdapter(tmp_path / "lotoia.db")
    assert adapter.backend == "sqlite"
    assert adapter.database_source == "sqlite_ephemeral"
    assert adapter.database_url.startswith("sqlite:///")
