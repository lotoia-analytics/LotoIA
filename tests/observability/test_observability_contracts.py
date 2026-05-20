from __future__ import annotations

import sys
import types
import sqlite3

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


def test_runtime_health_and_metrics_table_are_safe(monkeypatch, tmp_path) -> None:
    conn = sqlite3.connect(tmp_path / "observability.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE operational_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            status TEXT NOT NULL,
            duration_ms REAL,
            context_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.executemany(
        "INSERT INTO operational_logs (event_type, status, duration_ms, context_json) VALUES (?, ?, ?, ?)",
        [
            ("generation", "success", 10.0, "{}"),
            ("check", "failed", 20.0, "{}"),
        ],
    )
    conn.commit()
    monkeypatch.setattr(admin_app, "conn", conn)
    monkeypatch.setattr(admin_app, "cursor", cursor)
    monkeypatch.setattr(admin_app, "_observability_tables", lambda: {"logs": pd.read_sql_query("SELECT * FROM operational_logs", conn), "audit": pd.DataFrame()})

    health = admin_app._runtime_health()
    metrics = admin_app._observability_metrics_table()

    assert health["total_runs"] == 2
    assert health["failures"] == 1
    assert not metrics.empty
    assert set(metrics["event_type"]) == {"generation", "check"}
