#!/usr/bin/env python3
"""M-GER-DADOS-051 — remoção controlada GE 114 e GE 1115 (dry-run padrão).

Uso:
  python scripts/ops/m_ger_dados_051_controlled_ge_removal.py
  python scripts/ops/m_ger_dados_051_controlled_ge_removal.py --json-out reports/m_ger_dados_051_dry_run.json

  LOTOIA_M_GER_DADOS_051_RESET_CONFIRM=M_GER_DADOS_051_CONTROLLED_GE_REMOVAL \\
    LOTOIA_M_GER_DADOS_051_BACKUP_CONFIRMED=1 \\
    python scripts/ops/m_ger_dados_051_controlled_ge_removal.py --execute \\
      --json-out reports/m_ger_dados_051_executed.json
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

from lotoia.governance.m_ger_dados_051_controlled_ge_removal import (  # noqa: E402
    CANCEL_CONFIRMATION_TOKEN,
    CONFIRMATION_TOKEN,
    MISSION_ID,
    REQUESTED_TARGET_IDS,
    GenerationEventAuditRow,
    assert_m_ger_dados_051_confirmation,
    authorize_controlled_ge_removal,
    build_dry_run_report,
    build_post_removal_report,
    delete_operational_rows_for_generation_events,
    resolve_authorized_target_ids,
    resolve_explicit_target_ids,
)

PRESERVED_COUNT_TABLES = (
    "imported_contests",
    "lotofacil_official_history",
    "scientific_institutional_memory",
    "scientific_calibration_decisions",
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


def _inventory(cur, tables: tuple[str, ...]) -> dict[str, int | str]:
    return {table: _count_table(cur, table) for table in tables}


def _child_count(cur, table: str, ge_id: int) -> int:
    try:
        if table == "reconciliation_games":
            cur.execute(
                """
                SELECT COUNT(*) FROM reconciliation_games
                WHERE reconciliation_run_id IN (
                    SELECT id FROM reconciliation_runs WHERE generation_event_id = %s
                )
                """,
                (ge_id,),
            )
        else:
            cur.execute(f'SELECT COUNT(*) FROM "{table}" WHERE generation_event_id = %s', (ge_id,))
        return int(cur.fetchone()[0])
    except Exception:
        return 0


def _fetch_target_audit(cur, ge_id: int) -> GenerationEventAuditRow | None:
    cur.execute(
        """
        SELECT id, analysis_batch_label, analysis_batch_type, created_at::text, ml_enabled
        FROM generation_events
        WHERE id = %s
        """,
        (ge_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return GenerationEventAuditRow(
        id=int(row[0]),
        analysis_batch_label=row[1],
        analysis_batch_type=row[2],
        created_at=row[3],
        ml_enabled=bool(row[4]) if row[4] is not None else None,
        generated_games_count=_child_count(cur, "generated_games", ge_id),
        reconciliation_runs_count=_child_count(cur, "reconciliation_runs", ge_id),
        reconciliation_games_count=_child_count(cur, "reconciliation_games", ge_id),
        output_signatures_count=_child_count(cur, "institutional_output_signatures", ge_id),
        ml_usage_events_count=_child_count(cur, "ml_usage_events", ge_id),
        report_events_count=_child_count(cur, "report_events", ge_id),
    )


def _record_reset_event(cur, *, dry_run: dict[str, Any], deleted_counts: dict[str, int]) -> int | None:
    try:
        payload = {
            "mission_id": MISSION_ID,
            "deleted_counts": deleted_counts,
            "authorized_generation_event_ids": dry_run.get("authorized_generation_event_ids"),
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
                "m_ger_dados_051_controlled_ge_removal",
                json.dumps(list(deleted_counts.keys())),
                json.dumps(payload),
                "EXECUTED",
                "Remoção controlada GE 114/1115 — M-GER-DADOS-051",
            ),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None


def run(
    *,
    execute: bool,
    json_out: Path,
    skip_backup: bool,
    ge_ids: list[int] | None = None,
    confirmation_token: str = CONFIRMATION_TOKEN,
) -> dict[str, Any]:
    import psycopg

    assert_m_ger_dados_051_confirmation(
        confirmation=os.getenv("LOTOIA_M_GER_DADOS_051_RESET_CONFIRM"),
        execute=execute,
        token=confirmation_token,
    )

    target_ids = sorted({int(value) for value in (ge_ids or sorted(REQUESTED_TARGET_IDS)) if int(value) > 0})
    url = _resolve_url()
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            from lotoia.governance.m_dados_049_controlled_reset import OPERATIONAL_DELETE_ORDER

            table_counts_before = _inventory(cur, OPERATIONAL_DELETE_ORDER)
            preserved_counts = _inventory(cur, PRESERVED_COUNT_TABLES)

            audits: list[GenerationEventAuditRow] = []
            existing_ids: list[int] = []
            for ge_id in target_ids:
                audit = _fetch_target_audit(cur, ge_id)
                if audit is not None:
                    audits.append(audit)
                    existing_ids.append(ge_id)

            if ge_ids is not None:
                authorized_ids, interpretation = resolve_explicit_target_ids(target_ids, existing_ids)
            else:
                cur.execute("SELECT id FROM generation_events WHERE id = %s", (115,))
                ge115_exists = cur.fetchone() is not None
                authorized_ids, interpretation = resolve_authorized_target_ids(
                    existing_ids,
                    ge_115_exists=ge115_exists,
                )
                interpretation["ge_115_exists_confirmed"] = ge115_exists
            dry_run = build_dry_run_report(
                target_audits=audits,
                table_counts_before=table_counts_before,
                preserved_table_counts=preserved_counts,
                authorized_ids=authorized_ids,
                interpretation=interpretation,
                requested_ids=target_ids,
                confirmation_token=confirmation_token,
            )

        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(dry_run, indent=2, ensure_ascii=False), encoding="utf-8")

        if not execute:
            return dry_run

        authorize_controlled_ge_removal(
            backup_confirmed=skip_backup or os.getenv("LOTOIA_M_GER_DADOS_051_BACKUP_CONFIRMED", "") == "1",
            dry_run_approved=True,
            authorized_ids=authorized_ids,
        )

        with conn.transaction():
            with conn.cursor() as cur:
                deleted_counts = delete_operational_rows_for_generation_events(cur, authorized_ids)
                reset_event_id = _record_reset_event(cur, dry_run=dry_run, deleted_counts=deleted_counts)
                table_counts_after = _inventory(cur, OPERATIONAL_DELETE_ORDER)
                preserved_after = _inventory(cur, PRESERVED_COUNT_TABLES)

        post = build_post_removal_report(
            dry_run={**dry_run, "preserved_table_counts": preserved_after},
            table_counts_after=table_counts_after,
            deleted_counts=deleted_counts,
            reset_event_id=reset_event_id,
        )
        json_out.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
        return post


def main() -> int:
    parser = argparse.ArgumentParser(description=MISSION_ID)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--skip-backup-confirm", action="store_true")
    parser.add_argument(
        "--ge-ids",
        type=str,
        default="",
        help="IDs explícitos separados por vírgula (ex.: 115,120)",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=ROOT / "reports" / "m_ger_dados_051_dry_run.json",
    )
    args = parser.parse_args()
    ge_ids = [int(value.strip()) for value in args.ge_ids.split(",") if value.strip().isdigit()] or None
    confirmation_token = CANCEL_CONFIRMATION_TOKEN if ge_ids is not None else CONFIRMATION_TOKEN
    result = run(
        execute=args.execute,
        json_out=args.json_out,
        skip_backup=args.skip_backup_confirm,
        ge_ids=ge_ids,
        confirmation_token=confirmation_token,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
