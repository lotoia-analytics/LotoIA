from __future__ import annotations

from pathlib import Path

from lotoia.database.database import DEFAULT_DATABASE_PATH, create_database


def initialize_public_persistence(db_path: Path = DEFAULT_DATABASE_PATH) -> None:
    """Idempotent bootstrap for public persistence tables on institutional SQLite."""
    create_database(db_path)
