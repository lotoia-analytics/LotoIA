#!/usr/bin/env python3
"""PostgreSQL cloud backup helper (pg_dump wrapper for Railway cron)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def default_backup_dir() -> Path:
    return Path(
        os.getenv("LOTOIA_BACKUP_OUTPUT_DIR", "").strip()
        or str(ROOT / "backups" / "postgresql")
    )


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


def _mask_database_url(database_url: str) -> str:
    if "@" not in database_url:
        return database_url
    scheme, remainder = database_url.split("://", maxsplit=1)
    credentials, host_part = remainder.split("@", maxsplit=1)
    username = credentials.split(":", maxsplit=1)[0] if ":" in credentials else "***"
    return f"{scheme}://{username}:***@{host_part}"


def _resolve_pg_dump_binary() -> str:
    override = os.getenv("LOTOIA_PG_DUMP_BIN", "").strip()
    if override:
        return override
    major = os.getenv("LOTOIA_POSTGRESQL_CLIENT_MAJOR", "").strip()
    if major.isdigit():
        candidate = f"/usr/lib/postgresql/{major}/bin/pg_dump"
        if Path(candidate).is_file():
            return candidate
    default = shutil.which("pg_dump")
    if default:
        return default
    raise RuntimeError("pg_dump não encontrado no PATH — instale postgresql-client compatível")


def _server_major_version(database_url: str) -> int | None:
    try:
        import psycopg
    except ImportError:
        try:
            import psycopg2 as psycopg  # type: ignore[no-redef]
        except ImportError:
            return None
    try:
        with psycopg.connect(database_url, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SHOW server_version")
                row = cursor.fetchone()
        if not row or not row[0]:
            return None
        version_text = str(row[0])
        major_text = version_text.split(".", maxsplit=1)[0]
        return int(major_text) if major_text.isdigit() else None
    except Exception:
        return None


def run_backup(*, output_dir: Path, compress: bool = True) -> dict:
    database_url = _resolve_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL ausente — backup cloud requer PostgreSQL")

    parsed = urlparse(database_url)
    if not (parsed.scheme or "").lower().startswith("postgres"):
        raise RuntimeError("DATABASE_URL deve ser PostgreSQL para backup cloud")

    pg_dump_bin = _resolve_pg_dump_binary()
    server_major = _server_major_version(database_url)
    client_major = None
    match = None
    for token in Path(pg_dump_bin).parts:
        if token.isdigit():
            client_major = int(token)
            break
    if client_major is None:
        import re

        version_match = re.search(r"postgresql-client-(\d+)", pg_dump_bin)
        if version_match:
            client_major = int(version_match.group(1))
    if server_major is not None and client_major is not None and server_major != client_major:
        raise RuntimeError(
            f"pg_dump incompatível: client={client_major}, server={server_major}. "
            f"Defina LOTOIA_POSTGRESQL_CLIENT_MAJOR={server_major} ou atualize o Postgres."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    host = parsed.hostname or "postgres"
    dump_path = output_dir / f"lotoia_{host}_{timestamp}.sql"
    if compress:
        dump_path = dump_path.with_suffix(".sql.gz")

    command = [pg_dump_bin, database_url, "--no-owner", "--no-privileges"]
    if compress:
        import gzip

        with gzip.open(dump_path, "wb") as handle:
            completed = subprocess.run(
                command,
                check=False,
                stdout=handle,
                stderr=subprocess.PIPE,
            )
    else:
        with dump_path.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(command, check=False, stdout=handle, stderr=subprocess.PIPE, text=True)

    if completed.returncode != 0:
        stderr = (completed.stderr or b"").decode("utf-8", errors="replace") if isinstance(completed.stderr, bytes) else str(completed.stderr or "")
        raise RuntimeError(f"pg_dump falhou: {stderr.strip()}")

    retention_days = int(os.getenv("LOTOIA_BACKUP_RETENTION_DAYS", "14") or "14")
    removed: list[str] = []
    cutoff = datetime.now(UTC).timestamp() - (retention_days * 86400)
    for existing in sorted(output_dir.glob("lotoia_*.sql*")):
        if existing.stat().st_mtime < cutoff:
            existing.unlink(missing_ok=True)
            removed.append(existing.name)

    return {
        "status": "PASS",
        "backup_file": str(dump_path),
        "database_url_masked": _mask_database_url(database_url),
        "pg_dump_bin": pg_dump_bin,
        "server_major_version": server_major,
        "retention_days": retention_days,
        "removed_old_backups": removed,
        "created_at": datetime.now(UTC).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PostgreSQL cloud backup")
    parser.add_argument(
        "--output-dir",
        default=str(default_backup_dir()),
        help="Diretório de saída dos dumps",
    )
    parser.add_argument("--no-compress", action="store_true", help="Não comprimir com gzip")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    try:
        report = run_backup(output_dir=Path(args.output_dir), compress=not args.no_compress)
    except Exception as exc:
        report = {"status": "FAIL", "error": str(exc)}
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"postgresql-cloud-backup: FAIL")
            print(f"  FAIL: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("postgresql-cloud-backup: PASS")
        print(f"  file: {report['backup_file']}")
        if report.get("removed_old_backups"):
            print(f"  removed: {', '.join(report['removed_old_backups'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
