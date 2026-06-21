"""Compacta payloads científicos grandes para recuperar espaço no PostgreSQL.

Uso seguro:
    python scripts/maintenance/compact_scientific_memory_payloads.py --dry-run
    python scripts/maintenance/compact_scientific_memory_payloads.py --apply

Objetivo:
- reduzir JSONs enormes em scientific_institutional_memory;
- manter métricas científicas principais;
- remover listas históricas completas e detalhes jogo-a-jogo gigantes;
- evitar DiskFull durante Conferir Resultados.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any

from sqlalchemy import create_engine, text

MAX_RANKING_ROWS = 20
MAX_EVENT_IDS = 50
MAX_CONTESTS = 120

HEAVY_CROSS_VALIDATION_KEYS = {
    "generation_details",
    "best_generation_details",
    "contest_results",
    "game_results",
    "games_with_10_hits",
    "games_with_11_plus",
    "historical_expansion_json",
}

HEAVY_GENERATION_RANGE_KEYS = {
    "generation_details",
    "best_generation_details",
    "games_with_10_hits",
    "games_with_11_plus",
    "contest_results",
    "game_results",
}


def _limited_list(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return value[: max(0, int(limit))]


def _compact_mapping(value: Any, *, heavy_keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if key in heavy_keys:
            if isinstance(item, list):
                compact[f"{key}_count"] = len(item)
            elif isinstance(item, dict):
                compact[f"{key}_keys"] = sorted(str(k) for k in item.keys())[:25]
            continue
        if key == "near_miss_generation_ranking":
            compact[key] = _limited_list(item, MAX_RANKING_ROWS)
        elif key == "generation_event_ids":
            compact[key] = _limited_list(item, MAX_EVENT_IDS)
        elif isinstance(item, dict):
            compact[key] = _compact_mapping(item, heavy_keys=heavy_keys)
        elif isinstance(item, list):
            compact[key] = _limited_list(item, MAX_CONTESTS)
        else:
            compact[key] = item
    compact["payload_compacted"] = True
    compact["payload_compaction_reason"] = "M-OPS-284 DiskFull guardrail"
    return compact


def _json_size(value: Any) -> int:
    try:
        return len(json.dumps(value or {}, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return 0


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica UPDATE no banco.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas reporta impacto.")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL ausente")

    engine = create_engine(database_url)
    updated = 0
    inspected = 0
    bytes_before = 0
    bytes_after = 0

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, generation_range, validation_contests, cross_validation_summary
                FROM scientific_institutional_memory
                ORDER BY id DESC
                LIMIT :limit
                """
            ),
            {"limit": int(args.limit)},
        ).mappings().all()

        for row in rows:
            inspected += 1
            generation_range = dict(row["generation_range"] or {})
            validation_contests = list(row["validation_contests"] or [])
            cross_validation_summary = dict(row["cross_validation_summary"] or {})

            before = _json_size(generation_range) + _json_size(validation_contests) + _json_size(cross_validation_summary)
            compact_generation_range = _compact_mapping(generation_range, heavy_keys=HEAVY_GENERATION_RANGE_KEYS)
            compact_validation_contests = _limited_list(validation_contests, MAX_CONTESTS)
            compact_cross_validation = _compact_mapping(cross_validation_summary, heavy_keys=HEAVY_CROSS_VALIDATION_KEYS)
            after = _json_size(compact_generation_range) + _json_size(compact_validation_contests) + _json_size(compact_cross_validation)

            bytes_before += before
            bytes_after += after
            if after >= before:
                continue
            updated += 1
            if args.apply:
                conn.execute(
                    text(
                        """
                        UPDATE scientific_institutional_memory
                           SET generation_range = CAST(:generation_range AS jsonb),
                               validation_contests = CAST(:validation_contests AS jsonb),
                               cross_validation_summary = CAST(:cross_validation_summary AS jsonb)
                         WHERE id = :id
                        """
                    ),
                    {
                        "id": int(row["id"]),
                        "generation_range": json.dumps(compact_generation_range, ensure_ascii=False, default=str),
                        "validation_contests": json.dumps(compact_validation_contests, ensure_ascii=False, default=str),
                        "cross_validation_summary": json.dumps(compact_cross_validation, ensure_ascii=False, default=str),
                    },
                )

    print(
        json.dumps(
            {
                "status": "applied" if args.apply else "dry_run",
                "inspected": inspected,
                "rows_to_update": updated,
                "bytes_before": bytes_before,
                "bytes_after": bytes_after,
                "bytes_saved_estimate": max(0, bytes_before - bytes_after),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
