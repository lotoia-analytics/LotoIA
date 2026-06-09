from __future__ import annotations

import sys
import types
import sqlite3
from pathlib import Path

import pandas as pd

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")

    def _subplots(*args, **kwargs):
        class _Ax:
            def axis(self, *args, **kwargs):
                return None

            def text(self, *args, **kwargs):
                return None

            def table(self, *args, **kwargs):
                class _Table:
                    def auto_set_font_size(self, *args, **kwargs):
                        return None

                    def set_fontsize(self, *args, **kwargs):
                        return None

                    def scale(self, *args, **kwargs):
                        return None

                return _Table()

        class _Fig:
            def add_axes(self, *args, **kwargs):
                return _Ax()

            def savefig(self, *args, **kwargs):
                return None

        return _Fig(), _Ax()

    pyplot.subplots = _subplots  # type: ignore[attr-defined]
    pyplot.close = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app


def _temp_sqlite_module(monkeypatch, tmp_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(tmp_path / "lotoia_test.db")
    cursor = conn.cursor()
    for ddl in [
        """
        CREATE TABLE IF NOT EXISTS operational_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms REAL,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            actor TEXT,
            artifact_path TEXT,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]:
        cursor.execute(ddl)
    conn.commit()
    monkeypatch.setattr(admin_app, "conn", conn)
    monkeypatch.setattr(admin_app, "cursor", cursor)
    return conn


def test_generation_and_check_payloads_remain_institutional(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        admin_app,
        "_historical_match_engine",
        lambda numbers: {
            "historical_score": 0.0,
            "rarity": 1.0,
            "occurrences": 0,
            "is_unique": True,
            "last_contest": None,
            "proximity": 0.0,
            "similar_contests": [],
        },
    )
    games = [{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}]
    dataframe, payload = admin_app._build_generation_report_payload(games)
    check_row, check_payload = admin_app._build_check_report_payload({"hits": 12, "correct_numbers": [1, 2, 3]}, 1234, [1, 2, 3])

    assert not dataframe.empty
    assert payload["type"] == "generation"
    assert payload["analytics"]["unique_games"] == 1
    assert check_payload["type"] == "check"
    assert check_payload["contest_id"] == 1234
    assert check_row.loc[0, "hits"] == 12

    snapshot_path = admin_app._write_snapshot("institutional_flow", payload)
    assert snapshot_path.exists()
    assert admin_app._safe_download_bytes(snapshot_path) is not None


def test_sqlite_logs_and_lead_persistence_are_recoverable(monkeypatch, tmp_path: Path) -> None:
    conn = _temp_sqlite_module(monkeypatch, tmp_path)

    admin_app._record_operational_log("generation", "success", 12.5, {"games": 1})
    admin_app._record_audit_trail("snapshot", artifact_path="reports/snapshots/example.json")
    admin_app._persist_lead("Ana", "(11) 99999-0000")

    assert admin_app._sqlite_health_check() is True
    assert pd.read_sql_query("SELECT * FROM operational_logs", conn).shape[0] == 1
    assert pd.read_sql_query("SELECT * FROM audit_trail", conn).shape[0] == 1
    assert pd.read_sql_query("SELECT * FROM leads", conn).shape[0] == 1
