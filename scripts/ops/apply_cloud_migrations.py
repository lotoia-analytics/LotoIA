#!/usr/bin/env python3
"""Apply versioned PostgreSQL migrations from database/migrations/."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "database" / "migrations"


def _resolve_database_url() -> str:
    for env_name in (
        "LOTOIA_DATABASE_POOLER_URL",
        "STREAMLIT_DATABASE_POOLER_URL",
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "STREAMLIT_DATABASE_URL",
    ):
        value = os.getenv(env_name, "").strip()
        if value:
            return value
    return ""


def _ensure_migration_table(connection) -> None:
    from sqlalchemy import text

    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL DEFAULT '',
                status VARCHAR(32) NOT NULL DEFAULT 'applied'
            )
            """
        )
    )


def _applied_migrations(connection) -> set[str]:
    from sqlalchemy import text

    rows = connection.execute(text("SELECT migration_name FROM schema_migrations")).fetchall()
    return {str(row[0]) for row in rows}


def apply_migrations(*, dry_run: bool = False) -> dict:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text

    from lotoia.database.database import DEFAULT_DATABASE_PATH, get_engine
    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy

    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError("Migrations cloud exigem backend PostgreSQL")

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    report = {
        "applied_at": datetime.now(UTC).isoformat(),
        "dry_run": dry_run,
        "migrations_dir": str(MIGRATIONS_DIR),
        "applied": [],
        "skipped": [],
        "errors": [],
    }

    engine = get_engine(DEFAULT_DATABASE_PATH)
    with engine.begin() as connection:
        _ensure_migration_table(connection)
        already_applied = _applied_migrations(connection)
        for migration_file in migration_files:
            name = migration_file.name
            if name in already_applied:
                report["skipped"].append(name)
                continue
            sql = migration_file.read_text(encoding="utf-8")
            if dry_run:
                report["applied"].append({"name": name, "dry_run": True})
                continue
            try:
                connection.execute(text(sql))
                connection.execute(
                    text(
                        "INSERT INTO schema_migrations (migration_name, checksum, status) "
                        "VALUES (:name, :checksum, 'applied')"
                    ),
                    {"name": name, "checksum": str(len(sql))},
                )
                report["applied"].append(name)
            except Exception as exc:
                report["errors"].append({"name": name, "error": str(exc)})
                break

    report["status"] = "PASS" if not report["errors"] else "FAIL"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply cloud PostgreSQL migrations")
    parser.add_argument("--dry-run", action="store_true", help="List pending migrations only")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    report = apply_migrations(dry_run=args.dry_run)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"apply-cloud-migrations: {report['status']}")
        for name in report.get("applied", []):
            print(f"  APPLIED: {name}")
        for name in report.get("skipped", []):
            print(f"  SKIPPED: {name}")
        for item in report.get("errors", []):
            print(f"  FAIL: {item}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
