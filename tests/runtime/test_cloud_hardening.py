from __future__ import annotations

import sqlite3
import sys
import types
from pathlib import Path

import pandas as pd

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app


def test_safe_input_helpers_apply_limits() -> None:
    assert admin_app._safe_int("9", 0, minimum=1, maximum=10) == 9
    assert admin_app._safe_int("invalid", 3) == 3
    assert admin_app._safe_float("4.5", 0.0, minimum=1.0, maximum=5.0) == 4.5
    assert admin_app._safe_text("  hello world  ", max_length=5) == "hello"


def test_safe_dataframe_and_download_helpers_handle_missing_data(tmp_path: Path) -> None:
    frame = admin_app._safe_dataframe(None, columns=["a", "b"])
    assert list(frame.columns) == ["a", "b"]

    missing = tmp_path / "missing.txt"
    assert admin_app._safe_download_bytes(missing) is None

    existing = tmp_path / "existing.csv"
    pd.DataFrame([{"a": 1}]).to_csv(existing, index=False)
    assert admin_app._safe_download_bytes(existing) is not None


def test_sqlite_bootstrap_creates_institutional_tables(tmp_path: Path, monkeypatch) -> None:
    conn = sqlite3.connect(tmp_path / "bootstrap.db")
    cursor = conn.cursor()
    monkeypatch.setattr(admin_app, "conn", conn)
    monkeypatch.setattr(admin_app, "cursor", cursor)

    admin_app._sqlite_ensure_admin_schema()
    conn.commit()

    tables = {
        row[0]
        for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert {"generation_events", "check_events", "operational_logs", "audit_trail", "snapshots", "generated_games", "imported_contests"} <= tables

    generation_columns = {row[1] for row in cursor.execute("PRAGMA table_info(generation_events)").fetchall()}
    check_columns = {row[1] for row in cursor.execute("PRAGMA table_info(check_events)").fetchall()}
    snapshot_columns = {row[1] for row in cursor.execute("PRAGMA table_info(snapshots)").fetchall()}

    assert {"first_name", "whatsapp", "ml_enabled"} <= generation_columns
    assert {"first_name", "whatsapp", "contest_id", "hits"} <= check_columns
    assert {"snapshot_type", "artifact_path", "metadata_json"} <= snapshot_columns


def test_generation_events_are_persisted_with_generated_games() -> None:
    connection = sqlite3.connect(":memory:")
    try:
        admin_app._sqlite_bind_connection(connection)
        admin_app._sqlite_ensure_admin_schema()

        games = [
            {
                "numbers": list(range(1, 16)),
                "profile_type": "recorrente",
                "final_score": {"final_score": 98.5},
                "quadra_score": {"found_quadras": 3},
            },
            {
                "numbers": list(range(2, 17)),
                "profile_type": "hibrido",
                "final_score": {"final_score": 95.25},
                "quadra_score": {"found_quadras": 2},
            },
        ]

        event_id = admin_app._persist_generation_events(
            first_name="Ana",
            whatsapp="11999999999",
            games=games,
            duration_ms=12.5,
            strategy="Ranking hibrido",
            lead_id=7,
        )

        assert event_id is not None
        assert admin_app._safe_count("generation_events") == 1
        assert admin_app._safe_count("generated_games") == 2
    finally:
        connection.close()


def test_sqlite_engine_enables_wal_and_autocheckpoint(tmp_path: Path) -> None:
    from lotoia.database.database import get_engine

    engine = get_engine(tmp_path / "wal.db")
    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
        synchronous = connection.exec_driver_sql("PRAGMA synchronous").scalar()
        wal_autocheckpoint = connection.exec_driver_sql("PRAGMA wal_autocheckpoint").scalar()

    assert str(journal_mode).lower() == "wal"
    assert int(synchronous) in {1, 2}
    assert int(wal_autocheckpoint) == 100


def test_sqlite_bootstrap_error_classification() -> None:
    diagnostic = admin_app._sqlite_classify_error(
        "SELECT * FROM missing_table",
        sqlite3.OperationalError("no such table: missing_table"),
        "missing_table",
    )

    assert diagnostic["issue"] == "table ausente"
    assert diagnostic["table"] == "missing_table"


def test_sidebar_logo_falls_back_when_image_is_missing(monkeypatch) -> None:
    captured = {}

    class _Sidebar:
        def image(self, path, use_container_width=False):
            captured["image"] = path

        def markdown(self, html, unsafe_allow_html=False):
            captured["markdown"] = html

    monkeypatch.setattr(admin_app.st, "sidebar", _Sidebar())
    monkeypatch.setattr(admin_app, "LOGO_DIRECTORY", Path("does-not-exist"))
    monkeypatch.setattr(admin_app, "LOGO_PATH", Path("also-missing.png"))

    admin_app._render_sidebar_logo()

    assert "markdown" in captured
    assert "image" not in captured


def test_sqlite_recovery_moves_corrupted_database(tmp_path: Path, monkeypatch) -> None:
    admin_app.SQLITE_RECOVERY_STATE["attempted"] = False
    admin_app.SQLITE_RECOVERY_STATE["active"] = False
    corrupted_db = tmp_path / "lotoia.db"
    corrupted_db.write_bytes(b"not a sqlite database")

    monkeypatch.setattr(admin_app, "DB_PATH", corrupted_db)
    monkeypatch.setattr(admin_app, "conn", type("DummyConn", (), {"close": lambda self: None})())
    monkeypatch.setattr(admin_app, "cursor", None)
    monkeypatch.setattr(admin_app, "_sqlite_ensure_admin_schema", lambda: None)
    monkeypatch.setattr(admin_app, "_record_operational_log", lambda *args, **kwargs: None)

    fresh_db = tmp_path / "fresh.db"
    fresh_conn = sqlite3.connect(fresh_db)
    monkeypatch.setattr(admin_app, "_sqlite_open_connection", lambda path=admin_app.DB_PATH: fresh_conn)

    recovered = admin_app._sqlite_maybe_recover_connection(sqlite3.DatabaseError("database disk image is malformed"))

    assert recovered is True
    assert not corrupted_db.exists()
    backup_dir = tmp_path / "data" / "corrupted"
    assert backup_dir.exists()
    assert admin_app.SQLITE_RECOVERY_STATE["active"] is True
