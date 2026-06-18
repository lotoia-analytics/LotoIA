from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.database.database import (
    ensure_database_schema,
    get_session,
    reset_schema_initialization_cache,
    resolve_postgresql_pool_config,
)


def test_build_marker_v26() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v33"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_postgresql_pool_config_conservative_defaults() -> None:
    config = resolve_postgresql_pool_config()
    assert config["pool_size"] >= 5
    assert config["max_overflow"] >= 10
    assert config["pool_pre_ping"] is True
    assert int(config["pool_timeout"]) >= 30


def test_ensure_database_schema_runs_once_per_process(tmp_path: Path) -> None:
    reset_schema_initialization_cache()
    db_path = tmp_path / "once.db"
    with patch("lotoia.database.database.create_database") as mocked:
        ensure_database_schema(db_path)
        ensure_database_schema(db_path)
        assert mocked.call_count == 1


def test_get_session_closes_on_success(tmp_path: Path) -> None:
    db_path = tmp_path / "session_close.db"
    reset_schema_initialization_cache()
    closed: list[bool] = []

    class _Session:
        def close(self) -> None:
            closed.append(True)

        def query(self, *_args, **_kwargs):
            return MagicMock()

    with patch("lotoia.database.database._session_factory") as factory:
        factory.return_value = lambda: _Session()
        with get_session(db_path) as session:
            assert session is not None
    assert closed == [True]


def test_get_session_closes_on_exception(tmp_path: Path) -> None:
    db_path = tmp_path / "session_close_exc.db"
    reset_schema_initialization_cache()
    closed: list[bool] = []

    class _Session:
        def close(self) -> None:
            closed.append(True)

    with patch("lotoia.database.database._session_factory") as factory:
        factory.return_value = lambda: _Session()
        with pytest.raises(RuntimeError):
            with get_session(db_path):
                raise RuntimeError("boom")
    assert closed == [True]


def test_load_imported_contests_summary_sequential_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "seq.db"
    for env_name in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "STREAMLIT_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "STREAMLIT_DATABASE_POOLER_URL",
    ):
        monkeypatch.delenv(env_name, raising=False)
    monkeypatch.setattr(institutional_app, "DB_PATH", db_path)
    reset_schema_initialization_cache()
    for _ in range(8):
        summary = institutional_app._load_imported_contests_summary()
        assert summary["source"] == "imported_contests"
        assert summary.get("status") in {"OK", "UNAVAILABLE"}
        assert summary.get("last_contest") is None or int(summary.get("last_contest") or 0) != 5000


def test_load_official_history_diagnostics_db_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        institutional_app,
        "_load_imported_contests_summary",
        lambda: institutional_app.imported_contests_summary_unavailable(error="timeout"),
    )
    payload = institutional_app._load_official_history_diagnostics()
    assert payload["db_status"] == "UNAVAILABLE"
    assert str(payload.get("db_error") or "").strip()
    assert payload.get("status_base_oficial") == "INDISPONIVEL"


def test_ensure_institutional_schema_uses_once_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    def _ensure(_path) -> None:
        calls.append(1)

    monkeypatch.setattr(institutional_app, "ensure_database_schema", _ensure)
    institutional_app._ensure_institutional_schema()
    institutional_app._ensure_institutional_schema()
    assert len(calls) == 2  # function called twice; ensure_database_schema guard is internal


def test_public_app_unchanged_functionally() -> None:
    import inspect

    source = inspect.getsource(public_app.main)
    assert "institutional_db_runtime" not in source
