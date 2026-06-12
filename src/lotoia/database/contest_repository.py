from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert

from lotoia.database.adapter import resolve_institutional_adapter
from lotoia.data.loader import load_draws_csv
from lotoia.database.database import ImportedContest, LotofacilOfficialHistory
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
        CREATE TABLE IF NOT EXISTS lotofacil_official_history (
            contest_number INTEGER PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            draw_date TEXT NOT NULL DEFAULT '',
            numbers TEXT NOT NULL DEFAULT '',
            numbers_signature TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'imported_contests',
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            validated_at TEXT,
            is_valid INTEGER NOT NULL DEFAULT 1,
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

        official_columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(lotofacil_official_history)").fetchall()
        }
        for column_sql, column_name in (
            ("ALTER TABLE lotofacil_official_history ADD COLUMN draw_date TEXT NOT NULL DEFAULT ''", "draw_date"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN numbers TEXT NOT NULL DEFAULT ''", "numbers"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN numbers_signature TEXT NOT NULL DEFAULT ''", "numbers_signature"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN source TEXT NOT NULL DEFAULT 'imported_contests'", "source"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP", "imported_at"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN validated_at TEXT", "validated_at"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN is_valid INTEGER NOT NULL DEFAULT 1", "is_valid"),
            ("ALTER TABLE lotofacil_official_history ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'", "metadata_json"),
        ):
            if column_name not in official_columns:
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
            official_stmt = pg_insert(LotofacilOfficialHistory).values(
                contest_number=int(contest["concurso"]),
                created_at=contest.get("created_at") or datetime.now(UTC),
                draw_date=str(contest["data"]),
                numbers=dezenas,
                numbers_signature=" ".join(sorted(f"{int(number):02d}" for number in contest["dezenas"])),
                source="imported_contests",
                imported_at=contest.get("created_at") or datetime.now(UTC),
                validated_at=contest.get("validated_at") or contest.get("created_at") or datetime.now(UTC),
                is_valid=1,
                metadata_json=metadata_json,
            )
            official_stmt = official_stmt.on_conflict_do_update(
                index_elements=[LotofacilOfficialHistory.contest_number],
                set_={
                    "created_at": official_stmt.excluded.created_at,
                    "draw_date": official_stmt.excluded.draw_date,
                    "numbers": official_stmt.excluded.numbers,
                    "numbers_signature": official_stmt.excluded.numbers_signature,
                    "source": official_stmt.excluded.source,
                    "imported_at": official_stmt.excluded.imported_at,
                    "validated_at": official_stmt.excluded.validated_at,
                    "is_valid": official_stmt.excluded.is_valid,
                    "metadata_json": official_stmt.excluded.metadata_json,
                },
            )
            if session is None:
                with get_session(self.db_path) as active_session:
                    try:
                        active_session.execute(stmt)
                        active_session.execute(official_stmt)
                        if commit:
                            active_session.commit()
                    except Exception:
                        active_session.rollback()
                        raise
            else:
                session.execute(stmt)
                session.execute(official_stmt)
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

            cursor.execute(
                """
            INSERT OR REPLACE INTO lotofacil_official_history (
                contest_number,
                created_at,
                draw_date,
                numbers,
                numbers_signature,
                source,
                imported_at,
                validated_at,
                is_valid,
                metadata_json
            )
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, ?)
            """,
                (
                    contest["concurso"],
                    contest["data"],
                    dezenas,
                    " ".join(sorted(f"{int(number):02d}" for number in contest["dezenas"])),
                    "imported_contests",
                    metadata_json,
                ),
            )

            if commit:
                self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _official_history_values(self, contest: dict[str, Any]) -> dict[str, Any]:
        dezenas = ",".join(contest["dezenas"])
        metadata = contest.get("metadata_json", contest.get("metadata", {}))
        if isinstance(metadata, str):
            metadata_json = metadata
        else:
            metadata_json = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        return {
            "contest_number": int(contest["concurso"]),
            "created_at": contest.get("created_at") or datetime.now(UTC),
            "draw_date": str(contest["data"]),
            "numbers": dezenas,
            "numbers_signature": " ".join(sorted(f"{int(number):02d}" for number in contest["dezenas"])),
            "source": str(contest.get("source", "imported_contests") or "imported_contests"),
            "imported_at": contest.get("imported_at") or contest.get("created_at") or datetime.now(UTC),
            "validated_at": contest.get("validated_at") or contest.get("created_at") or datetime.now(UTC),
            "is_valid": int(contest.get("is_valid", 1) or 1),
            "metadata_json": metadata_json,
        }

    def save_official_history_contest(self, contest: dict[str, Any], *, commit: bool = True, session: Any | None = None) -> None:
        values = self._official_history_values(contest)
        if self.backend != "sqlite":
            stmt = pg_insert(LotofacilOfficialHistory).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[LotofacilOfficialHistory.contest_number],
                set_={
                    "created_at": stmt.excluded.created_at,
                    "draw_date": stmt.excluded.draw_date,
                    "numbers": stmt.excluded.numbers,
                    "numbers_signature": stmt.excluded.numbers_signature,
                    "source": stmt.excluded.source,
                    "imported_at": stmt.excluded.imported_at,
                    "validated_at": stmt.excluded.validated_at,
                    "is_valid": stmt.excluded.is_valid,
                    "metadata_json": stmt.excluded.metadata_json,
                },
            )
            if session is None:
                with get_session(self.db_path) as active_session:
                    active_session.execute(stmt)
                    if commit:
                        active_session.commit()
            else:
                session.execute(stmt)
            return
        cursor = self.connection.cursor()
        cursor.execute(
            """
        INSERT OR REPLACE INTO lotofacil_official_history (
            contest_number,
            created_at,
            draw_date,
            numbers,
            numbers_signature,
            source,
            imported_at,
            validated_at,
            is_valid,
            metadata_json
        )
        VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
        """,
            (
                values["contest_number"],
                values["draw_date"],
                values["numbers"],
                values["numbers_signature"],
                values["source"],
                int(values["is_valid"]),
                values["metadata_json"],
            ),
        )
        if commit:
            self.connection.commit()

    def bootstrap_official_history_from_csv(self, *, limit: int | None = None) -> int:
        try:
            draws = load_draws_csv()
        except Exception:
            draws = []
        if limit is not None and int(limit) > 0:
            draws = draws[: int(limit)]
        inserted = 0
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                for draw in draws:
                    contest = {
                        "concurso": int(draw.contest),
                        "data": str(draw.date),
                        "dezenas": [f"{int(number):02d}" for number in draw.numbers],
                        "metadata_json": json.dumps({"source": "historico_lotofacil.csv"}, ensure_ascii=False, sort_keys=True),
                        "source": "historico_lotofacil.csv",
                        "imported_at": datetime.now(UTC),
                        "validated_at": datetime.now(UTC),
                        "is_valid": 1,
                    }
                    self.save_official_history_contest(contest, commit=False, session=session)
                    inserted += 1
                session.commit()
        else:
            for draw in draws:
                contest = {
                    "concurso": int(draw.contest),
                    "data": str(draw.date),
                    "dezenas": [f"{int(number):02d}" for number in draw.numbers],
                    "metadata_json": json.dumps({"source": "historico_lotofacil.csv"}, ensure_ascii=False, sort_keys=True),
                    "source": "historico_lotofacil.csv",
                    "imported_at": datetime.now(UTC),
                    "validated_at": datetime.now(UTC),
                    "is_valid": 1,
                }
                self.save_official_history_contest(contest, commit=False)
                inserted += 1
            if self.connection is not None:
                self.connection.commit()
        return inserted

    def get_official_history_max_contest(self) -> int | None:
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                row = (
                    session.query(LotofacilOfficialHistory.contest_number)
                    .order_by(LotofacilOfficialHistory.contest_number.desc())
                    .first()
                )
                return int(row[0]) if row else None
        cursor = self.connection.cursor()
        cursor.execute(
            """
        SELECT MAX(contest_number)
        FROM lotofacil_official_history
        """
        )
        result = cursor.fetchone()
        return int(result[0]) if result and result[0] is not None else None

    def get_csv_latest_contest(self) -> int | None:
        try:
            draws = load_draws_csv()
        except Exception:
            return None
        if not draws:
            return None
        return max(int(draw.contest) for draw in draws)

    def import_new_contests_from_csv(self) -> list[int]:
        """Import contests present in CSV but newer than the persisted official baseline."""
        self.create_table()
        try:
            draws = load_draws_csv()
        except Exception:
            return []
        if not draws:
            return []
        current_max = max(
            int(self.get_official_history_max_contest() or 0),
            int(self.get_last_contest() or 0),
        )
        new_draws = sorted(
            (draw for draw in draws if int(draw.contest) > current_max),
            key=lambda draw: int(draw.contest),
        )
        if not new_draws:
            return []
        synced: list[int] = []
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                for draw in new_draws:
                    contest = {
                        "concurso": int(draw.contest),
                        "data": str(draw.date),
                        "dezenas": [f"{int(number):02d}" for number in draw.numbers],
                        "metadata_json": json.dumps(
                            {"source": "historico_lotofacil.csv"},
                            ensure_ascii=False,
                            sort_keys=True,
                        ),
                    }
                    self.save_contest(contest, commit=False, session=session)
                    synced.append(int(draw.contest))
                session.commit()
        else:
            for draw in new_draws:
                contest = {
                    "concurso": int(draw.contest),
                    "data": str(draw.date),
                    "dezenas": [f"{int(number):02d}" for number in draw.numbers],
                    "metadata_json": json.dumps(
                        {"source": "historico_lotofacil.csv"},
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                }
                self.save_contest(contest, commit=False)
                synced.append(int(draw.contest))
            if self.connection is not None:
                self.connection.commit()
        return synced

    def sync_official_history_from_imported_contests(self) -> int:
        contests = self.get_all_contests()
        inserted = 0
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                for contest in contests:
                    official_contest = {
                        "concurso": int(contest["concurso"]),
                        "data": str(contest["data"]),
                        "dezenas": list(contest["dezenas"]),
                        "metadata_json": contest.get("metadata_json", "{}"),
                        "source": "imported_contests",
                        "imported_at": datetime.now(UTC),
                        "validated_at": datetime.now(UTC),
                        "is_valid": 1,
                    }
                    self.save_official_history_contest(official_contest, commit=False, session=session)
                    inserted += 1
                session.commit()
        else:
            for contest in contests:
                official_contest = {
                    "concurso": int(contest["concurso"]),
                    "data": str(contest["data"]),
                    "dezenas": list(contest["dezenas"]),
                    "metadata_json": contest.get("metadata_json", "{}"),
                    "source": "imported_contests",
                    "imported_at": datetime.now(UTC),
                    "validated_at": datetime.now(UTC),
                    "is_valid": 1,
                }
                self.save_official_history_contest(official_contest, commit=False)
                inserted += 1
            if self.connection is not None:
                self.connection.commit()
        return inserted

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

    def get_official_history_contest(self, contest_number: int) -> dict[str, Any] | None:
        if self.backend != "sqlite":
            with get_session(self.db_path) as session:
                row = session.get(LotofacilOfficialHistory, int(contest_number))
                if row is None:
                    return None
                return {
                    "concurso": int(row.contest_number),
                    "data": str(row.draw_date or ""),
                    "dezenas": str(row.numbers or "").split(","),
                    "metadata_json": str(row.metadata_json or "{}"),
                    "source": str(row.source or "imported_contests"),
                }
        cursor = self.connection.cursor()
        cursor.execute(
            """
        SELECT contest_number, draw_date, numbers, metadata_json, source
        FROM lotofacil_official_history
        WHERE contest_number = ?
        """,
            (int(contest_number),),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "concurso": int(row[0]),
            "data": str(row[1] or ""),
            "dezenas": str(row[2] or "").split(","),
            "metadata_json": str(row[3] or "{}"),
            "source": str(row[4] or "imported_contests"),
        }

    def confirm_sync_persistence(self, contest_number: int) -> dict[str, Any]:
        """Post-commit verification required by Lei No 001."""
        target = int(contest_number)
        imported_max = int(self.get_last_contest() or 0)
        official_max = int(self.get_official_history_max_contest() or 0)
        imported_row = self.get_contest(target)
        official_row = self.get_official_history_contest(target)
        ok = (
            imported_max >= target
            and official_max >= target
            and imported_row is not None
            and official_row is not None
        )
        return {
            "ok": ok,
            "contest_number": target,
            "imported_contests_max": imported_max or None,
            "lotofacil_official_history_max": official_max or None,
            "imported_contest_found": imported_row is not None,
            "official_history_found": official_row is not None,
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
