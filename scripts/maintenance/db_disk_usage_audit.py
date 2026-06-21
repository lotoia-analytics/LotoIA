"""Auditoria sanitizada de uso de disco do PostgreSQL.

Uso:
    python scripts/maintenance/db_disk_usage_audit.py

Não imprime DATABASE_URL nem credenciais.
"""

from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text


def _main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL ausente")

    engine = create_engine(database_url)
    report: dict[str, object] = {}
    with engine.connect() as conn:
        report["database_size"] = conn.execute(
            text("SELECT pg_size_pretty(pg_database_size(current_database()))")
        ).scalar()
        report["top_tables"] = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT
                      schemaname,
                      relname AS table_name,
                      pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
                      pg_total_relation_size(relid) AS total_bytes,
                      n_live_tup,
                      n_dead_tup
                    FROM pg_stat_user_tables
                    ORDER BY pg_total_relation_size(relid) DESC
                    LIMIT 20
                    """
                )
            ).mappings().all()
        ]
        report["scientific_memory_payload_estimate"] = [
            dict(row)
            for row in conn.execute(
                text(
                    """
                    SELECT
                      id,
                      memory_kind,
                      game_size,
                      total_games,
                      octet_length(coalesce(generation_range::text,'')) AS generation_range_bytes,
                      octet_length(coalesce(validation_contests::text,'')) AS validation_contests_bytes,
                      octet_length(coalesce(cross_validation_summary::text,'')) AS cross_validation_summary_bytes,
                      created_at
                    FROM scientific_institutional_memory
                    ORDER BY
                      octet_length(coalesce(generation_range::text,''))
                      + octet_length(coalesce(validation_contests::text,''))
                      + octet_length(coalesce(cross_validation_summary::text,'')) DESC
                    LIMIT 20
                    """
                )
            ).mappings().all()
        ]
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
