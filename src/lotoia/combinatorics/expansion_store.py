from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_EXPANSION_DB_PATH = Path("data/user_panel_expansion.db")


def _connect(db_path: Path = DEFAULT_EXPANSION_DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def create_expansion_store(db_path: Path = DEFAULT_EXPANSION_DB_PATH) -> None:
    with _connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS user_expansion_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                selected_numbers TEXT NOT NULL,
                preview_combinations TEXT NOT NULL,
                total_combinations INTEGER NOT NULL,
                generated_count INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                runtime_ms REAL NOT NULL,
                complete INTEGER NOT NULL,
                stopped_reason TEXT NOT NULL,
                metrics TEXT NOT NULL
            )
            """
        )
        connection.commit()


def save_expansion_event(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_EXPANSION_DB_PATH,
) -> int:
    create_expansion_store(db_path)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO user_expansion_events (
                created_at,
                selected_numbers,
                preview_combinations,
                total_combinations,
                generated_count,
                estimated_cost,
                runtime_ms,
                complete,
                stopped_reason,
                metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(UTC).replace(microsecond=0).isoformat(),
                json.dumps(payload["selected_numbers"]),
                json.dumps(payload.get("combinations", [])),
                int(payload["total_combinations"]),
                int(payload["generated_count"]),
                float(payload["estimated_cost"]),
                float(payload["runtime_ms"]),
                1 if payload["complete"] else 0,
                str(payload.get("stopped_reason") or ""),
                json.dumps(payload.get("metrics", {}), ensure_ascii=False),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_expansion_events(
    *,
    limit: int = 20,
    db_path: Path = DEFAULT_EXPANSION_DB_PATH,
) -> list[dict[str, Any]]:
    create_expansion_store(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                selected_numbers,
                total_combinations,
                generated_count,
                estimated_cost,
                runtime_ms,
                complete,
                stopped_reason
            FROM user_expansion_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "id": row[0],
            "created_at": row[1],
            "selected_numbers": json.loads(row[2]),
            "total_combinations": row[3],
            "generated_count": row[4],
            "estimated_cost": row[5],
            "runtime_ms": row[6],
            "complete": bool(row[7]),
            "stopped_reason": row[8],
        }
        for row in rows
    ]
