#!/usr/bin/env python3
"""M-PERF-001 — auditoria read-only de carga das telas operacionais críticas."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-PERF-001"


def _bench(label: str, fn) -> dict[str, Any]:
    started = time.perf_counter()
    result = fn()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    rows = 0
    if isinstance(result, list):
        rows = len(result)
    elif isinstance(result, dict):
        rows = len(result.get("rows", []) or result.get("games", []) or [])
    return {
        "screen": label,
        "elapsed_ms": round(elapsed_ms, 2),
        "rows_loaded": rows,
        "query_count_estimate": "see notes",
    }


def run_audit(db_path: Any, *, card_format: int = 15) -> dict[str, Any]:
    from dashboard.institutional_light_mode import ANALYTICAL_PAGE_SIZE, CONFERENCE_EVENTS_LIMIT, OPERATIONAL_EVENTS_LIMIT
    from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations
    import dashboard.institutional_app as app

    app.DB_PATH = db_path
    benchmarks: list[dict[str, Any]] = []

    benchmarks.append(
        _bench(
            "Cobertura Estrutural (20 lotes)",
            lambda: load_operational_core_002_generations(db_path, limit=OPERATIONAL_EVENTS_LIMIT),
        )
    )
    benchmarks.append(
        _bench(
            "Conferir Resultados (resumo)",
            lambda: app._load_official_conference_generation_groups(page_load=True),
        )
    )
    benchmarks.append(
        _bench(
            "Histórico Analítico (20 gerações)",
            lambda: app._load_generation_history_light(limit=ANALYTICAL_PAGE_SIZE),
        )
    )
    benchmarks.append(
        _bench(
            "Histórico Analítico (linhas)",
            lambda: app._load_accumulated_analytical_rows_light(limit=ANALYTICAL_PAGE_SIZE),
        )
    )
    benchmarks.append(
        _bench(
            "Persisted groups (conferível, limit)",
            lambda: app._load_persisted_generation_event_groups(
                conference_eligible_only=True,
                limit=CONFERENCE_EVENTS_LIMIT,
                summary_only=True,
                use_cache=False,
            ),
        )
    )

    return {
        "mission_id": MISSION_ID,
        "status": "OK",
        "card_format": card_format,
        "benchmarks": benchmarks,
        "notes": [
            "Comparar com baseline pré-M-PERF-001: full scan generation_events sem limit.",
            "Modo leve: lazy gates evitam execução até clique do operador.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=MISSION_ID)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    from lotoia.database.env_resolution import is_postgresql_database_url, resolve_institutional_database_url_from_env

    url, _source = resolve_institutional_database_url_from_env()
    if not url or not is_postgresql_database_url(url):
        payload = {"mission_id": MISSION_ID, "status": "SKIP", "reason": "PostgreSQL não configurado"}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    payload = run_audit(url)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
