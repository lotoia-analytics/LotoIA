#!/usr/bin/env python3
"""M-DADOS-066 — validação pós-reset absoluto operacional."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL  # noqa: E402
from lotoia.governance.m_dados_066_absolute_operational_reset import (  # noqa: E402
    MISSION_ID,
    OPERATIONAL_DELETE_ORDER,
    OPERATIONAL_SEQUENCES,
    PRESERVED_COUNT_TABLES,
    validate_post_reset_state,
)


def main() -> int:
    from cloud_env_bootstrap import ensure_database_url, resolve_database_url

    import psycopg

    parser = argparse.ArgumentParser(description=f"{MISSION_ID} post-reset validation")
    parser.add_argument("--json", action="store_true")
    parser.parse_args()

    ensure_database_url(root=ROOT)
    url, _ = resolve_database_url()
    url = url.replace("postgresql+psycopg://", "postgresql://")

    def count_table(cur, table: str) -> int:
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return int(cur.fetchone()[0])

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            operational_counts = {table: count_table(cur, table) for table in OPERATIONAL_DELETE_ORDER}
            preserved_counts = {table: count_table(cur, table) for table in PRESERVED_COUNT_TABLES}

            cur.execute(
                """
                SELECT id, analysis_batch_label, ml_enabled, created_at::text,
                       context_json->>'selected_card_format' AS card_format,
                       context_json->>'selected_quantity' AS quantity,
                       context_json->>'lot_operational_status' AS lot_status
                FROM generation_events
                ORDER BY id ASC
                LIMIT 5
                """
            )
            generations = [
                {
                    "id": row[0],
                    "analysis_batch_label": row[1],
                    "ml_enabled": row[2],
                    "created_at": row[3],
                    "card_format": row[4],
                    "quantity": row[5],
                    "lot_operational_status": row[6],
                }
                for row in cur.fetchall()
            ]
            first_ge_id = int(generations[0]["id"]) if generations else None

            sequence_last: dict[str, int | None] = {}
            for seq in OPERATIONAL_SEQUENCES[:3]:
                try:
                    cur.execute(f"SELECT last_value FROM {seq}")
                    sequence_last[seq] = int(cur.fetchone()[0])
                except Exception:
                    sequence_last[seq] = None

    report = validate_post_reset_state(
        table_counts=operational_counts,
        preserved_counts=preserved_counts,
        sequence_last_values=sequence_last,
        first_generation_event_id=first_ge_id,
    )
    report["generations"] = generations
    report["preserved_counts"] = preserved_counts
    report["operational_counts"] = operational_counts
    if generations:
        latest = generations[0]
        report["checks"]["batch_label_sovereign"] = latest.get("analysis_batch_label") == BATCH_LABEL
        report["checks"]["operational_label_001"] = latest.get("id") == 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("verdict", "").endswith("OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
