#!/usr/bin/env python3
"""M-DADOS-066 — reset absoluto operacional da LotoIA (nova fase 001).

Etapas:
  1. inventário (padrão / --json)
  2. backup lógico JSON (--execute)
  3. --execute — apaga camada operacional + reinicia sequences

Uso:
  python scripts/ops/m_dados_066_absolute_operational_reset.py --json
  python scripts/ops/m_dados_066_absolute_operational_reset.py --json-out reports/m_dados_066_dry_run.json

  LOTOIA_M_DADOS_066_RESET_CONFIRM=M_DADOS_066_ABSOLUTE_OPERATIONAL_RESET \\
    python scripts/ops/m_dados_066_absolute_operational_reset.py --execute --json
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

from lotoia.governance.m_dados_066_absolute_operational_reset import (  # noqa: E402
    CONFIRMATION_TOKEN,
    INVENTORY_TABLES,
    MISSION_ID,
    OPERATIONAL_DELETE_ORDER,
    OPERATIONAL_SEQUENCES,
    PRESERVED_COUNT_TABLES,
    assert_m_dados_066_confirmation,
    assert_preserved_table_not_in_scope,
    build_dry_run_report,
    build_inventory_report,
    build_post_reset_report,
)

BACKUP_DIR = ROOT / "data" / "backups"


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


def _fetch_generation_event_ids(cur) -> list[int]:
    try:
        cur.execute("SELECT id FROM generation_events ORDER BY id")
        return [int(row[0]) for row in cur.fetchall()]
    except Exception:
        return []


def _distinct_batch_labels(cur) -> list[str]:
    try:
        cur.execute(
            """
            SELECT DISTINCT analysis_batch_label
            FROM generation_events
            WHERE analysis_batch_label IS NOT NULL AND analysis_batch_label <> ''
            ORDER BY 1
            """
        )
        return [str(row[0]) for row in cur.fetchall()]
    except Exception:
        return []


def _create_logical_backup(url: str) -> Path:
    import psycopg

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"m_dados_066_pre_reset_{ts}.json"
    backup: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "created_at": ts,
        "tables": {},
    }
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for table in OPERATIONAL_DELETE_ORDER:
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    row_count = int(cur.fetchone()[0])
                    backup["tables"][table] = {"row_count": row_count}
                except Exception as exc:
                    backup["tables"][table] = {"error": str(exc)}
                    conn.rollback()
    backup_path.write_text(json.dumps(backup, indent=2, ensure_ascii=False), encoding="utf-8")
    return backup_path


def _delete_all_operational(cur) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for table in OPERATIONAL_DELETE_ORDER:
        assert_preserved_table_not_in_scope(table)
        try:
            cur.execute(f'DELETE FROM "{table}"')
            deleted[table] = int(cur.rowcount)
        except Exception as exc:
            deleted[table] = -1
            raise RuntimeError(f"[{MISSION_ID}] Falha ao apagar {table}: {exc}") from exc
    return deleted


def _reset_sequences(cur) -> dict[str, str | int]:
    status: dict[str, str | int] = {}
    for seq in OPERATIONAL_SEQUENCES:
        try:
            cur.execute(f"ALTER SEQUENCE IF EXISTS {seq} RESTART WITH 1")
            cur.execute(f"SELECT last_value FROM {seq}")
            row = cur.fetchone()
            status[seq] = int(row[0]) if row else "restarted"
        except Exception as exc:
            status[seq] = f"skip: {exc}"
    return status


def _record_reset_event(cur, *, inventory: dict[str, Any], deleted_counts: dict[str, int]) -> int | None:
    try:
        payload = {
            "mission_id": MISSION_ID,
            "deleted_counts": deleted_counts,
            "inventory_before": inventory,
            "executed_at": datetime.now(UTC).isoformat(),
            "absolute_reset": True,
            "sequence_reset": True,
        }
        cur.execute(
            """
            INSERT INTO reset_events (reset_type, triggered_by, affected_tables, payload, status, notes, created_at)
            VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, NOW())
            RETURNING id
            """,
            (
                MISSION_ID,
                "m_dados_066_absolute_operational_reset",
                json.dumps(list(deleted_counts.keys())),
                json.dumps(payload),
                "EXECUTED",
                "Reset absoluto operacional — nova fase FASE_OPERACIONAL_001",
            ),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    except Exception:
        return None


def run(*, execute: bool, json_out: Path, skip_backup: bool) -> dict[str, Any]:
    import psycopg

    assert_m_dados_066_confirmation(
        confirmation=os.getenv("LOTOIA_M_DADOS_066_RESET_CONFIRM"),
        execute=execute,
    )

    url = _resolve_url()
    masked_url = url.split("@")[-1] if "@" in url else "postgresql://***"

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            table_counts = _inventory(cur, INVENTORY_TABLES)
            ge_ids = _fetch_generation_event_ids(cur)
            batch_labels = _distinct_batch_labels(cur)

        inventory = build_inventory_report(
            table_counts=table_counts,
            generation_event_ids=ge_ids,
            batch_labels=batch_labels,
        )
        inventory["database_host"] = masked_url

        if not execute:
            report = build_dry_run_report(inventory=inventory)
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            return report

        backup_path: Path | None = None
        if not skip_backup:
            backup_path = _create_logical_backup(url)

        with conn.transaction():
            with conn.cursor() as cur:
                deleted_counts = _delete_all_operational(cur)
                sequence_status = _reset_sequences(cur)
                table_counts_after = _inventory(cur, OPERATIONAL_DELETE_ORDER)
                preserved_after = _inventory(cur, PRESERVED_COUNT_TABLES)

        reset_event_id: int | None = None
        with conn.cursor() as cur:
            reset_event_id = _record_reset_event(
                cur, inventory=inventory, deleted_counts=deleted_counts
            )
            conn.commit()

        post = build_post_reset_report(
            inventory_before=inventory,
            table_counts_after=table_counts_after,
            preserved_counts_after=preserved_after,
            deleted_counts=deleted_counts,
            sequence_status=sequence_status,
            reset_event_id=reset_event_id,
        )
        post["backup_path"] = str(backup_path) if backup_path else None
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
        return post


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=f"{MISSION_ID} absolute operational reset")
    parser.add_argument("--execute", action="store_true", help="Executa reset absoluto (exige confirmação)")
    parser.add_argument("--json", action="store_true", help="Alias para saída JSON no stdout")
    parser.add_argument(
        "--json-out",
        default=str(ROOT / "reports" / "m_dados_066_absolute_reset_report.json"),
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Pula backup lógico local (somente se snapshot Railway confirmado)",
    )
    args = parser.parse_args()
    report = run(
        execute=bool(args.execute),
        json_out=Path(args.json_out),
        skip_backup=bool(args.skip_backup),
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nVeredicto: {report.get('verdict')}")
    print(f"Arquivo: {args.json_out}")
    if not args.execute:
        print(
            f"\nPara executar: LOTOIA_M_DADOS_066_RESET_CONFIRM={CONFIRMATION_TOKEN!r} "
            f"python scripts/ops/m_dados_066_absolute_operational_reset.py --execute --json"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
