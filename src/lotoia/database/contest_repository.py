from __future__ import annotations

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

        self.connection.commit()

    def get_last_contest(self) -> int | None:
        cursor = self.connection.cursor()

        cursor.execute("""
        SELECT MAX(concurso)
        FROM contests
        """)

        result = cursor.fetchone()

        return result[0]

    def get_all_contests(self) -> list[dict[str, Any]]:
        cursor = self.connection.cursor()

        cursor.execute("""
        SELECT concurso, data, dezenas
        FROM contests
        ORDER BY concurso
        """)

        rows = cursor.fetchall()

        contests = []

        for row in rows:
            contest = {
                "concurso": row[0],
                "data": row[1],
                "dezenas": row[2].split(","),
            }

            contests.append(contest)

        return contests

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
