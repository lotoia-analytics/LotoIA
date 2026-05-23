from __future__ import annotations

from pathlib import Path

from lotoia.database.adapter import InstitutionalDatabaseAdapter, SQLiteInstitutionalAdapter
from lotoia.database.database import database_url


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
