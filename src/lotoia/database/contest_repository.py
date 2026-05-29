from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from lotoia.database.adapter import resolve_institutional_adapter
from lotoia.database.database import ImportedContest
from lotoia.database.database import create_database
from lotoia.database.database import get_session


class ContestRepository:
    """Legacy contest persistence API owned by the official database namespace."""

    def __init__(self, db_path: str | Path = "data/lotoia.db") -> None:
        self.db_path = Path(db_path)
        self.adapter = resolve_institutional_adapter(self.db_path)
        self.backend = self.adapter.backend
        self.database_url = self.adapter.database_url
        self.connection = sqlite3.connect(self.db_path) if self.backend == "sqlite" else None

    def create_table(self) -> None:
        if self.backend != "sqlite":
            create_database(self.db_path)
            return
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

    @contextmanager
    def transaction(self):
        if self.backend == "sqlite":
            if self.connection is None:
                raise RuntimeError("SQLite connection not available.")
            try:
                yield self.connection
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise
            return
        with get_session(self.db_path) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def save_contest(self, contest: dict[str, Any], *, commit: bool = True, session: Any | None = None) -> None:
        dezenas = ",".join(contest["dezenas"])
        metadata = contest.get("metadata_json", contest.get("metadata", {}))
        if isinstance(metadata, str):
            metadata_json = metadata
        else:
            metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        if self.backend != "sqlite":
            values = {
                "contest_number": int(contest["concurso"]),
                "created_at": contest.get("created_at") or datetime.now(UTC),
                "data": str(contest["data"]),
                "dezenas": dezenas,
                "metadata_json": metadata_json,
            }
            stmt = pg_insert(ImportedContest).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[ImportedContest.contest_number],
                set_={
                    "created_at": stmt.excluded.created_at,
                    "data": stmt.excluded.data,
                    "dezenas": stmt.excluded.dezenas,
                    "metadata_json": stmt.excluded.metadata_json,
                },
            )
            if session is None:
                with get_session(self.db_path) as active_session:
                    try:
                        active_session.execute(stmt)
                        if commit:
                            active_session.commit()
                    except Exception:
                        active_session.rollback()
                        raise
            else:
                session.execute(stmt)
            return

        cursor = self.connection.cursor()
        try:
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

            if commit:
                self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

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
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                row = (
                    session.query(ImportedContest.contest_number)
                    .order_by(ImportedContest.contest_number.desc())
                    .first()
                )
                return int(row[0]) if row else None
        cursor = self.connection.cursor()

        cursor.execute("""
        SELECT MAX(contest_number)
        FROM imported_contests
        """)

        result = cursor.fetchone()

        return result[0]

    def get_all_contests(self) -> list[dict[str, Any]]:
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                rows = (
                    session.query(ImportedContest)
                    .order_by(ImportedContest.contest_number)
                    .all()
                )
                return [
                    {
                        "concurso": row.contest_number,
                        "data": row.data,
                        "dezenas": row.dezenas.split(","),
                        "metadata_json": row.metadata_json,
                    }
                    for row in rows
                ]
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
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                row = session.get(ImportedContest, int(contest_number))
                if row is None:
                    return None
                return {
                    "concurso": row.contest_number,
                    "data": row.data,
                    "dezenas": row.dezenas.split(","),
                    "metadata_json": row.metadata_json,
                }
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
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                row = (
                    session.query(ImportedContest)
                    .order_by(ImportedContest.contest_number.desc())
                    .first()
                )
                if row is None:
                    return None
                return {
                    "concurso": row.contest_number,
                    "data": row.data,
                    "dezenas": row.dezenas.split(","),
                    "metadata_json": row.metadata_json,
                }
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
