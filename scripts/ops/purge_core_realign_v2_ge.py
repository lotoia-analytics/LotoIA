#!/usr/bin/env python3
"""Remove invalid V2 test generation event (non-official batch evidence)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

from lotoia.governance.history_preservation_policy import assert_generation_event_deletion_allowed

GE_ID = 51
BATCH_LABEL = "STRUCT_CORE_REALIGN_V2_15D_001"


def main() -> int:
    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT analysis_batch_label FROM generation_events WHERE id = %s",
                (GE_ID,),
            )
            row = cur.fetchone()
            if not row:
                print(f"GE {GE_ID} não existe — nada a remover.")
                return 0
            if row[0] != BATCH_LABEL:
                raise RuntimeError(f"GE {GE_ID} label={row[0]!r} — abortado por segurança.")
            assert_generation_event_deletion_allowed(
                generation_event_id=GE_ID,
                batch_label=row[0],
                source="scripts.ops.purge_core_realign_v2_ge",
            )

            for table, col in (
                ("reconciliation_games", "reconciliation_run_id IN (SELECT id FROM reconciliation_runs WHERE generation_event_id = %s)"),
                ("reconciliation_runs", "generation_event_id = %s"),
                ("institutional_output_signatures", "generation_event_id = %s"),
                ("generated_games", "generation_event_id = %s"),
            ):
                if "reconciliation_games" in table:
                    cur.execute(
                        f"DELETE FROM {table} WHERE {col}",
                        (GE_ID,),
                    )
                else:
                    cur.execute(f"DELETE FROM {table} WHERE {col}", (GE_ID,))
                print(f"  deleted {table}: {cur.rowcount}")

            cur.execute("DELETE FROM generation_events WHERE id = %s", (GE_ID,))
            print(f"  deleted generation_events: {cur.rowcount}")
        conn.commit()
    print(f"GE {GE_ID} removido (lote não oficial).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
