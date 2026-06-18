#!/usr/bin/env python3
"""M-DADOS-066 — validação pós-reset (psycopg-only, Railway console safe)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-DADOS-066"


def _load_governance_constants():
    module_path = ROOT / "src/lotoia/governance/m_dados_066_absolute_operational_reset.py"
    spec = importlib.util.spec_from_file_location("m_dados_066_gov", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"[{MISSION_ID}] Não foi possível carregar governança.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GOV = _load_governance_constants()
OPERATIONAL_DELETE_ORDER = _GOV.OPERATIONAL_DELETE_ORDER
OPERATIONAL_SEQUENCES = _GOV.OPERATIONAL_SEQUENCES
PRESERVED_COUNT_TABLES = _GOV.PRESERVED_COUNT_TABLES
validate_post_reset_state = _GOV.validate_post_reset_state


def _resolve_url() -> str:
    for key in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "STREAMLIT_DATABASE_URL",
        "DATABASE_PUBLIC_URL",
    ):
        raw = os.environ.get(key, "").strip()
        if not raw or raw == "DATABASE_URL":
            continue
        lowered = raw.lower()
        if "sqlite" in lowered:
            continue
        if "postgres" in lowered or lowered.startswith("postgresql://"):
            return (
                raw.replace("postgresql+psycopg://", "postgresql://")
                .replace("postgresql+psycopg2://", "postgresql://")
            )
    raise RuntimeError(f"[{MISSION_ID}] PostgreSQL não configurado.")


def main() -> int:
    import psycopg

    parser = argparse.ArgumentParser(description=f"{MISSION_ID} post-reset validation")
    parser.add_argument("--json", action="store_true")
    parser.parse_args()

    url = _resolve_url()
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            operational_counts = {}
            for table in OPERATIONAL_DELETE_ORDER:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                operational_counts[table] = int(cur.fetchone()[0])

            preserved_counts = {}
            for table in PRESERVED_COUNT_TABLES:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                preserved_counts[table] = int(cur.fetchone()[0])

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
        report["checks"]["first_generation_event_id_is_one"] = latest.get("id") == 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if str(report.get("verdict", "")).endswith("OK") else 1


if __name__ == "__main__":
    raise SystemExit(main())
