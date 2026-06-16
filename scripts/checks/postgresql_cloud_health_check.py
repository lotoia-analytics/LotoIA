#!/usr/bin/env python3
"""Health-check PostgreSQL cloud (Lei No 001)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", maxsplit=1)
        key = key.strip()
        if key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


DATABASE_ENV_VARS = (
    "LOTOIA_DATABASE_POOLER_URL",
    "STREAMLIT_DATABASE_POOLER_URL",
    "DATABASE_URL",
    "LOTOIA_DATABASE_URL",
    "STREAMLIT_DATABASE_URL",
)

REQUIRED_TABLES = (
    "institutional_users",
    "generation_events",
    "generated_games",
    "reconciliation_runs",
    "reconciliation_games",
    "imported_contests",
    "lotofacil_official_history",
)


def _mask_database_url(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text or "@" not in text:
        return text or "-"
    scheme, remainder = text.split("://", maxsplit=1) if "://" in text else ("", text)
    credentials, host_part = remainder.split("@", maxsplit=1)
    username = credentials.split(":", maxsplit=1)[0] if ":" in credentials else "***"
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}{username}:***@{host_part}"


def _resolve_database_url() -> tuple[str, str]:
    for env_name in DATABASE_ENV_VARS:
        value = os.getenv(env_name, "").strip()
        if value:
            return value, env_name
    return "", ""


def run_health_check() -> dict[str, Any]:
    _load_dotenv()
    errors: list[str] = []
    warnings: list[str] = []
    evidence: dict[str, Any] = {"checked_at": datetime.now(UTC).isoformat()}

    database_url, database_source = _resolve_database_url()
    if not database_url:
        errors.append("DATABASE_URL ausente")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "evidence": evidence,
        }

    evidence["database_source"] = database_source
    evidence["database_url_masked"] = _mask_database_url(database_url)

    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    evidence["database_host"] = host or "-"
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        errors.append("DATABASE_URL aponta para localhost — proibido em cloud")

    scheme = (parsed.scheme or "").lower()
    if not scheme.startswith("postgres"):
        errors.append(f"scheme inválido para PostgreSQL cloud: {scheme or 'unknown'}")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text

    from lotoia.database.adapter import InstitutionalDatabaseAdapter
    from lotoia.database.database import DEFAULT_DATABASE_PATH, get_engine

    adapter = InstitutionalDatabaseAdapter(DEFAULT_DATABASE_PATH)
    evidence["adapter_backend"] = adapter.backend
    if adapter.backend != "postgresql":
        errors.append(f"adapter.backend={adapter.backend} (esperado postgresql)")

    engine = get_engine(DEFAULT_DATABASE_PATH)
    evidence["engine_url_masked"] = _mask_database_url(str(engine.url))

    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar()
            evidence["postgresql_version"] = str(version or "")[:160]
    except Exception as exc:
        errors.append(f"falha ao conectar PostgreSQL: {exc}")
        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "evidence": evidence,
        }

    table_counts: dict[str, int] = {}
    for table in REQUIRED_TABLES:
        try:
            with engine.connect() as connection:
                value = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            table_counts[table] = int(value or 0)
        except Exception as exc:
            errors.append(f"tabela {table} inacessível: {exc}")
    evidence["table_counts"] = table_counts

    if table_counts.get("lotofacil_official_history", 0) <= 0:
        warnings.append("lotofacil_official_history vazia")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL cloud health-check")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    report = run_health_check()
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"postgresql-cloud-health-check: {report['status']}")
        for warning in report.get("warnings", []):
            print(f"  WARN: {warning}")
        for error in report.get("errors", []):
            print(f"  FAIL: {error}")
        evidence = report.get("evidence") or {}
        if evidence.get("database_host"):
            print(f"  host: {evidence['database_host']}")
        counts = evidence.get("table_counts") or {}
        if counts:
            print(f"  lotofacil_official_history rows: {counts.get('lotofacil_official_history', 0)}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
