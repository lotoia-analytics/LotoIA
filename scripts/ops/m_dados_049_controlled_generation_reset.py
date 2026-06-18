#!/usr/bin/env python3
"""M-DADOS-049 — reset controlado de gerações operacionais antigas.

Etapas:
  1. dry-run (padrão) — contagens, batch_labels, preservação
  2. --execute — limpeza controlada com confirmação explícita

Uso:
  python scripts/ops/m_dados_049_controlled_generation_reset.py
  python scripts/ops/m_dados_049_controlled_generation_reset.py --json-out reports/m_dados_049_dry_run.json

  LOTOIA_M_DADOS_049_RESET_CONFIRM=M_DADOS_049_CONTROLLED_RESET \\
    python scripts/ops/m_dados_049_controlled_generation_reset.py --execute \\
      --json-out reports/m_dados_049_reset_executed.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from lotoia.governance.m_dados_049_controlled_reset import (  # noqa: E402
    CONFIRMATION_TOKEN,
    MISSION_ID,
    OPERATIONAL_DELETE_ORDER,
    PRESERVED_TABLES,
    GenerationEventRow,
    assert_m_dados_049_confirmation,
    assert_preserved_table_not_in_scope,
    authorize_controlled_reset,
    build_dry_run_report,
    build_post_reset_report,
    partition_generation_events,
)

PRESERVED_COUNT_TABLES = (
    "imported_contests",
    "lotofacil_official_history",
    "scientific_institutional_memory",
    "scientific_calibration_decisions",
    "institutional_memory_snapshots",
    "institutional_memory_states",
)


def _resolve_url() -> str:
    from cloud_env_bootstrap import ensure_database_url, resolve_database_url

    ensure_database_url(root=ROOT)
    url, _ = resolve_database_url()
    if "sqlite" in url.lower():
        raise RuntimeError(f"[{MISSION_ID}] SQLite proibido — use PostgreSQL Railway.")
    return url.replace("postgresql+psycopg://", "postgresql://")


def _count_table(cur, table: str) -> int | str:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return int(cur.fetchone()[0])
    except Exception as exc:
        return f"error: {exc}"


def _fetch_generation_events(cur) -> list[GenerationEventRow]:
    cur.execute(
        """
        SELECT id, analysis_batch_label, analysis_batch_type, created_at::text, ml_enabled
        FROM generation_events
        ORDER BY id
        """
    )
    return [
        GenerationEventRow(
            id=int(row[0]),
            analysis_batch_label=row[1],
            analysis_batch_type=row[2],
            created_at=row[3],
            ml_enabled=bool(row[4]) if row[4] is not None else None,
        )
        for row in cur.fetchall()
    ]


def _inventory(cur, tables: tuple[str, ...]) -> dict[str, int | str]:
    return {table: _count_table(cur, table) for table in tables}


def _distinct_batch_labels(cur) -> list[str]:
    cur.execute(
        """
        SELECT DISTINCT analysis_batch_label
        FROM generation_events
        WHERE analysis_batch_label IS NOT NULL AND analysis_batch_label <> ''
        ORDER BY 1
        """
    )
    return [str(row[0]) for row in cur.fetchall()]


def _delete_operational_rows(cur, deletable_ids: list[int]) -> dict[str, int]:
    if not deletable_ids:
        return {table: 0 for table in OPERATIONAL_DELETE_ORDER}

    id_list = ",".join(str(int(value)) for value in sorted(set(deletable_ids)))
    deleted: dict[str, int] = {}

    cur.execute(
        f"""
        DELETE FROM reconciliation_games
        WHERE reconciliation_run_id IN (
            SELECT id FROM reconciliation_runs
            WHERE generation_event_id IN ({id_list})
        )
        """
    )
    deleted["reconciliation_games"] = int(cur.rowcount)

    child_tables_with_ge = (
        "expansion_events",
        "institutional_validated_expansions",
        "lotoia_client_generations",
        "ml_usage_events",
        "reconciliation_events",
        "report_events",
        "reconciliation_runs",
        "generated_games",
        "institutional_output_signatures",
    )
    for table in child_tables_with_ge:
        assert_preserved_table_not_in_scope(table)
        cur.execute(f'DELETE FROM "{table}" WHERE generation_event_id IN ({id_list})')
        deleted[table] = int(cur.rowcount)

    assert_preserved_table_not_in_scope("generation_events")
    cur.execute(f'DELETE FROM generation_events WHERE id IN ({id_list})')
    deleted["generation_events"] = int(cur.rowcount)
    return deleted


def _record_reset_event(cur, *, dry_run: dict[str, Any], deleted_counts: dict[str, int]) -> int | None:
    try:
        payload = {
            "mission_id": MISSION_ID,
            "deleted_counts": deleted_counts,
            "deletable_generation_event_ids": dry_run.get("deletable_generation_event_ids"),
            "executed_at": datetime.now(UTC).isoformat(),
        }
        cur.execute(
            """
            INSERT INTO reset_events (reset_type, triggered_by, affected_tables, payload, status, notes, created_at)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, NOW())
            RETURNING id
            """,
            (
                MISSION_ID,
                "m_dados_049_controlled_generation_reset",
                json.dumps(list(deleted_counts.keys())),
                json.dumps(payload),
                "EXECUTED",
                "Reset controlado gerações operacionais antigas",
            ),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None


def run(*, execute: bool, json_out: Path, skip_backup: bool) -> dict[str, Any]:
    import psycopg

    assert_m_dados_049_confirmation(
        confirmation=os.getenv("LOTOIA_M_DADOS_049_RESET_CONFIRM"),
        execute=execute,
    )

    url = _resolve_url()
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            table_counts_before = _inventory(cur, OPERATIONAL_DELETE_ORDER)
            preserved_counts = _inventory(cur, PRESERVED_COUNT_TABLES)
            events = _fetch_generation_events(cur)
            batch_labels = _distinct_batch_labels(cur)

        dry_run = build_dry_run_report(
            table_counts_before=table_counts_before,
            generation_events=events,
            batch_labels=batch_labels,
            preserved_table_counts=preserved_counts,
        )
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(dry_run, indent=2, ensure_ascii=False), encoding="utf-8")

        if not execute:
            return dry_run

        authorize_controlled_reset(
            backup_confirmed=skip_backup or bool(os.getenv("LOTOIA_M_DADOS_049_BACKUP_CONFIRMED")),
            dry_run_approved=True,
            agent_dados_authorized=True,
            agent_governanca_authorized=True,
            preservation_report_path=str(json_out),
        )

        partitioned = partition_generation_events(events)
        deletable_ids = [int(row["id"]) for row in partitioned["deletable"]]

        with conn.transaction():
            with conn.cursor() as cur:
                deleted_counts = _delete_operational_rows(cur, deletable_ids)
                table_counts_after = _inventory(cur, OPERATIONAL_DELETE_ORDER)
                preserved_after = _inventory(cur, PRESERVED_COUNT_TABLES)

        reset_event_id: int | None = None
        with conn.cursor() as cur:
            reset_event_id = _record_reset_event(cur, dry_run=dry_run, deleted_counts=deleted_counts)
            conn.commit()

        post = build_post_reset_report(
            dry_run=dry_run,
            table_counts_after=table_counts_after,
            deleted_counts=deleted_counts,
            reset_event_id=reset_event_id,
        )
        post["preserved_table_counts_after"] = preserved_after
        json_out.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
        return post


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=f"{MISSION_ID} controlled generation reset")
    parser.add_argument("--execute", action="store_true", help="Executa limpeza real (exige confirmação)")
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "reports" / "m_dados_049_controlled_reset_report.json"),
    )
    parser.add_argument(
        "--skip-backup-confirm",
        action="store_true",
        help="Pula LOTOIA_M_DADOS_049_BACKUP_CONFIRMED (somente ambientes autorizados)",
    )
    args = parser.parse_args()
    report = run(
        execute=bool(args.execute),
        json_out=Path(args.json_out),
        skip_backup=bool(args.skip_backup_confirm),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nVeredicto: {report.get('verdict')}")
    print(f"Arquivo: {args.json_out}")
    if not args.execute:
        print(
            f"\nPara executar: LOTOIA_M_DADOS_049_RESET_CONFIRM={CONFIRMATION_TOKEN!r} "
            f"python scripts/ops/m_dados_049_controlled_generation_reset.py --execute"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
