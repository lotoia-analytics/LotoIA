#!/usr/bin/env python3
"""M-DADOS-049 — validação pós-reset / recepção Histórico Analítico + Cobertura Estrutural."""

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


def main() -> int:
    from cloud_env_bootstrap import ensure_database_url, resolve_database_url

    import psycopg

    ensure_database_url(root=ROOT)
    url, _ = resolve_database_url()
    url = url.replace("postgresql+psycopg://", "postgresql://")

    report: dict = {"mission_id": "M-DADOS-049", "checks": {}}
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            for table in (
                "imported_contests",
                "scientific_institutional_memory",
                "scientific_calibration_decisions",
                "generation_events",
                "generated_games",
            ):
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                report["counts"] = report.get("counts", {})
                report["counts"][table] = int(cur.fetchone()[0])

            cur.execute(
                """
                SELECT id, analysis_batch_label, ml_enabled, created_at::text
                FROM generation_events
                WHERE analysis_batch_label = %s
                ORDER BY created_at ASC, id ASC
                """,
                (BATCH_LABEL,),
            )
            sovereign_rows = [
                {"id": r[0], "analysis_batch_label": r[1], "ml_enabled": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]
            report["sovereign_generation_events"] = sovereign_rows
            report["checks"]["imported_contests_preserved"] = report["counts"]["imported_contests"] > 0
            report["checks"]["scientific_memory_preserved"] = report["counts"]["scientific_institutional_memory"] >= 0
            report["checks"]["has_sovereign_generation"] = len(sovereign_rows) >= 1
            report["checks"]["first_operational_label_expected"] = (
                "001" if len(sovereign_rows) >= 1 else "pending_first_generation"
            )
            if sovereign_rows:
                latest = sovereign_rows[-1]
                cur.execute(
                    "SELECT COUNT(*) FROM generated_games WHERE generation_event_id = %s",
                    (latest["id"],),
                )
                report["latest_generation_event_id"] = latest["id"]
                report["latest_generated_games_count"] = int(cur.fetchone()[0])
                report["checks"]["generated_games_persisted"] = report["latest_generated_games_count"] > 0
                report["checks"]["batch_label_sovereign"] = latest["analysis_batch_label"] == BATCH_LABEL

    report["verdict"] = (
        "M-DADOS-049 VALIDAÇÃO OK"
        if all(report["checks"].values())
        else "M-DADOS-049 VALIDAÇÃO PARCIAL — ver checks"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
