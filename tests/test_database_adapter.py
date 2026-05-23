from __future__ import annotations

from pathlib import Path

from lotoia.database.adapter import (
    InstitutionalDatabaseAdapter,
    PostgresInstitutionalAdapter,
    SQLiteInstitutionalAdapter,
    resolve_institutional_adapter,
)
from lotoia.database.database import bootstrap_institutional_database, database_url


def test_adapter_uses_sqlite_path_when_database_url_is_absent(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    adapter = InstitutionalDatabaseAdapter(tmp_path / "lotoia.db")

    assert adapter.backend == "sqlite"
    assert adapter.database_url.startswith("sqlite:///")
    assert adapter.sqlite_path.name == "lotoia.db"
    assert adapter.is_shared_cloud_ready is False


def test_adapter_prefers_database_url_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/lotoia")
    adapter = InstitutionalDatabaseAdapter(Path("data/lotoia.db"))

    assert adapter.backend == "postgresql"
    assert adapter.database_url == "postgresql+psycopg://user:pass@host:5432/lotoia"
    assert adapter.is_shared_cloud_ready is True


def test_adapter_supports_named_cloud_database_env(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LOTOIA_DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/lotoia")
    adapter = InstitutionalDatabaseAdapter(Path("data/lotoia.db"))

    assert adapter.backend == "postgresql"
    assert adapter.database_url == "postgresql+psycopg://user:pass@host:5432/lotoia"
    assert adapter.database_source == "LOTOIA_DATABASE_URL"
    assert adapter.is_shared_cloud_ready is True


def test_database_url_follows_institutional_adapter(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    resolved = database_url(tmp_path / "lotoia.db")

    assert resolved.startswith("sqlite:///")
    assert "lotoia.db" in resolved


def test_sqlite_adapter_exposes_institutional_contract(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    adapter = SQLiteInstitutionalAdapter(tmp_path / "lotoia.db")

    assert hasattr(adapter, "save_generation_event")
    assert hasattr(adapter, "save_check_event")
    assert hasattr(adapter, "save_ml_usage_event")
    assert hasattr(adapter, "save_report_event")
    assert hasattr(adapter, "save_expansion_event")
    assert hasattr(adapter, "fetch_generation_events")
    assert hasattr(adapter, "fetch_usage_metrics")


def test_resolve_institutional_adapter_switches_by_backend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sqlite_adapter = resolve_institutional_adapter(tmp_path / "lotoia.db")
    assert isinstance(sqlite_adapter, SQLiteInstitutionalAdapter)

    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@host:5432/lotoia")
    postgres_adapter = resolve_institutional_adapter(tmp_path / "lotoia.db")
    assert isinstance(postgres_adapter, PostgresInstitutionalAdapter)
    assert postgres_adapter.is_shared_cloud_ready is True


def test_bootstrap_institutional_database_reports_backend(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    info = bootstrap_institutional_database(tmp_path / "lotoia.db")

    assert info["backend"] == "sqlite"
    assert info["database_url"].startswith("sqlite:///")
