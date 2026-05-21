from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ContestRepository:
    """Legacy contest persistence API owned by the official database namespace."""

    def __init__(self, db_path: str | Path = "data/lotoia.db") -> None:
        self.connection = sqlite3.connect(db_path)

    def create_table(self) -> None:
        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contests (
            concurso INTEGER PRIMARY KEY,
            data TEXT,
            dezenas TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS imported_contests (
            contest_number INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            dezenas TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generation_event_id INTEGER,
            lead_id INTEGER,
            target_contest INTEGER,
            origin TEXT NOT NULL DEFAULT 'dashboard',
            generation_mode TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            game_index INTEGER,
            numbers TEXT,
            profile_type TEXT,
            final_score TEXT,
            quadra_score TEXT,
            context_json TEXT NOT NULL DEFAULT '{}'
        )
        """)

        existing_columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(imported_contests)").fetchall()
        }
        if "metadata_json" not in existing_columns:
            cursor.execute(
                """
            ALTER TABLE imported_contests
            ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'
            """
            )

        generated_columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(generated_games)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE generated_games ADD COLUMN target_contest INTEGER", "target_contest"),
            ("ALTER TABLE generated_games ADD COLUMN origin TEXT NOT NULL DEFAULT 'dashboard'", "origin"),
            ("ALTER TABLE generated_games ADD COLUMN generation_mode TEXT NOT NULL DEFAULT ''", "generation_mode"),
            ("ALTER TABLE generated_games ADD COLUMN context_json TEXT NOT NULL DEFAULT '{}'", "context_json"),
        ):
            if column_name not in generated_columns:
                cursor.execute(column_sql)

        self.connection.commit()

    def create_feature_table(self) -> None:
        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS frequency_snapshots (
            concurso INTEGER,
            dezena TEXT,
            frequencia INTEGER
        )
        """)

        self.connection.commit()

    def save_contest(self, contest: dict[str, Any]) -> None:
        cursor = self.connection.cursor()

        dezenas = ",".join(contest["dezenas"])
        metadata = contest.get("metadata_json", contest.get("metadata", {}))
        if isinstance(metadata, str):
            metadata_json = metadata
        else:
            metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)

        cursor.execute(
            """
        INSERT OR IGNORE INTO contests (
            concurso,
            data,
            dezenas
        )
        VALUES (?, ?, ?)
        """,
            (
                contest["concurso"],
                contest["data"],
                dezenas,
            ),
        )

        cursor.execute(
            """
        INSERT OR REPLACE INTO imported_contests (
            contest_number,
            created_at,
            data,
            dezenas,
            metadata_json
        )
        VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)
        """,
            (
                contest["concurso"],
                contest["data"],
                dezenas,
                metadata_json,
            ),
        )

        self.connection.commit()

    def save_generated_games(
        self,
        *,
        generation_event_id: int | None,
        lead_id: int | None,
        target_contest: int | None,
        origin: str,
        generation_mode: str,
        games: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> int:
        cursor = self.connection.cursor()
        context_json = json.dumps(context or {}, ensure_ascii=False, sort_keys=True)
        inserted = 0
        for index, game in enumerate(games, start=1):
            cursor.execute(
                """
            INSERT INTO generated_games (
                generation_event_id,
                lead_id,
                target_contest,
                origin,
                generation_mode,
                game_index,
                numbers,
                profile_type,
                final_score,
                quadra_score,
                context_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    generation_event_id,
                    lead_id,
                    target_contest,
                    origin,
                    generation_mode,
                    index,
                    ",".join(str(number) for number in game.get("numbers", [])),
                    str(game.get("profile_type", "")),
                    json.dumps(game.get("final_score", {}), ensure_ascii=False, sort_keys=True),
                    json.dumps(game.get("quadra_score", {}), ensure_ascii=False, sort_keys=True),
                    context_json,
                ),
            )
            inserted += 1
        self.connection.commit()
        return inserted

    def get_last_contest(self) -> int | None:
        cursor = self.connection.cursor()

        cursor.execute("""
        SELECT MAX(contest_number)
        FROM imported_contests
        """)

        result = cursor.fetchone()

        return result[0]

    def get_all_contests(self) -> list[dict[str, Any]]:
        cursor = self.connection.cursor()

        cursor.execute("""
        SELECT contest_number, data, dezenas, metadata_json
        FROM imported_contests
        ORDER BY contest_number
        """)

        rows = cursor.fetchall()

        contests = []

        for row in rows:
            contest = {
                "concurso": row[0],
                "data": row[1],
                "dezenas": row[2].split(","),
                "metadata_json": row[3],
            }

            contests.append(contest)

        return contests

    def get_contest(self, contest_number: int) -> dict[str, Any] | None:
        cursor = self.connection.cursor()

        cursor.execute(
            """
        SELECT contest_number, data, dezenas, metadata_json
        FROM imported_contests
        WHERE contest_number = ?
        """,
            (contest_number,),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "concurso": row[0],
            "data": row[1],
            "dezenas": row[2].split(","),
            "metadata_json": row[3],
        }

    def get_latest_contest_record(self) -> dict[str, Any] | None:
        cursor = self.connection.cursor()

        cursor.execute(
            """
        SELECT contest_number, data, dezenas, metadata_json
        FROM imported_contests
        ORDER BY contest_number DESC
        LIMIT 1
        """
        )

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "concurso": row[0],
            "data": row[1],
            "dezenas": row[2].split(","),
            "metadata_json": row[3],
        }

    def save_frequency_snapshot(
        self,
        concurso: int,
        frequencies: dict[str, int],
    ) -> None:
        cursor = self.connection.cursor()

        for dezena, frequencia in frequencies.items():
            cursor.execute(
                """
            INSERT INTO frequency_snapshots (
                concurso,
                dezena,
                frequencia
            )
            VALUES (?, ?, ?)
            """,
                (
                    concurso,
                    dezena,
                    frequencia,
                ),
            )

        self.connection.commit()
