"""Validate institutional PostgreSQL connectivity (cloud). Never prints credentials."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from lotoia.database.adapter import InstitutionalDatabaseAdapter  # noqa: E402
from lotoia.database.database import get_engine  # noqa: E402


def _load_url_from_env() -> str:
    for name in ("LOTOIA_DATABASE_POOLER_URL", "DATABASE_URL", "LOTOIA_DATABASE_URL", "STREAMLIT_DATABASE_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _load_url_from_test_fixture() -> str:
    test_file = ROOT / "tests" / "test_database_adapter.py"
    if not test_file.exists():
        return ""
    content = test_file.read_text(encoding="utf-8")
    match = re.search(
        r'monkeypatch\.setenv\(\s*\n\s*"LOTOIA_DATABASE_URL",\s*\n\s*"([^"]+)"',
        content,
    )
    return match.group(1).strip() if match else ""


def main() -> int:
    url = _load_url_from_env()
    source = "environment"
    if not url:
        url = _load_url_from_test_fixture()
        source = "test_fixture"
    if not url:
        print("CLOUD_CONNECTION: NOT_CONFIGURED")
        print("Defina DATABASE_URL ou LOTOIA_DATABASE_URL (ou .env) e rode de novo.")
        return 2

    os.environ["LOTOIA_DATABASE_URL"] = url
    os.environ.pop("DATABASE_URL", None)

    adapter = InstitutionalDatabaseAdapter()
    print("=== Cloud Database Health Check ===")
    print(f"config_source: {source}")
    print(f"backend: {adapter.backend}")
    print(f"env_name: {adapter.database_source}")
    print(f"host: {adapter.database_host}")
    print(f"pooler: {adapter.uses_pooler}")
    from urllib.parse import urlparse

    parsed = urlparse(adapter.database_url)
    print(f"db_user: {parsed.username}")
    print(f"has_password: {bool(parsed.password)}")

    if adapter.backend != "postgresql":
        print("CLOUD_CONNECTION: FAIL — backend nao e PostgreSQL")
        return 1

    try:
        engine = get_engine()
        with engine.connect() as conn:
            ping = conn.execute(text("SELECT 1")).scalar()
            version = conn.execute(text("SELECT version()")).scalar() or ""
            tables = sorted(inspect(engine).get_table_names())
        print(f"SELECT 1 => {ping}")
        print(f"tables: {len(tables)}")
        print(f"postgres: {version.split(',')[0]}")
        print("CLOUD_CONNECTION: OK")
        return 0
    except Exception as exc:
        print("CLOUD_CONNECTION: FAIL")
        print(f"error: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
