#!/usr/bin/env python3
"""M-CONF-003 — Limpeza de conferências com target_contest mismatch.

Remove reconciliation_runs e reconciliation_games onde o generation_event
tem target_contest diferente do contest_id da conferência.

Uso:
  python scripts/ops/m_conf_003_cleanup_wrong_conference.py --dry-run
  python scripts/ops/m_conf_003_cleanup_wrong_conference.py --fix
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-CONF-003"


def _resolve_database_url() -> str:
    """Resolve PostgreSQL URL (Lei No 001)."""
    for key in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        value = str(os.getenv(key, "") or "").strip()
        if (
            value
            and not value.startswith("[")
            and "user:pass@host" not in value
            and len(value) >= 20
        ):
            return value.replace("postgresql+psycopg://", "postgresql://").replace(
                "postgresql+psycopg2://", "postgresql://"
            )
    raise RuntimeError(
        f"[{MISSION_ID}] PostgreSQL não configurado. Defina DATABASE_URL."
    )


def find_mismatched_conferences() -> list[dict[str, Any]]:
    """Encontra conferências onde target_contest != contest_id."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Encontra reconciliation_runs com mismatch
        rows = (
            session.execute(
                text(
                    """
                SELECT 
                    rr.id as run_id,
                    rr.generation_event_id,
                    rr.contest_id,
                    ge.context_json->>'target_contest' as target_contest,
                    COUNT(rg.id) as games_count
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                LEFT JOIN reconciliation_games rg ON rg.reconciliation_run_id = rr.id
                WHERE ge.context_json->>'target_contest' != rr.contest_id::text
                   OR ge.context_json->>'target_contest' IS NULL
                GROUP BY rr.id, rr.generation_event_id, rr.contest_id, ge.context_json->>'target_contest'
                ORDER BY rr.id
                """
                )
            )
            .mappings()
            .all()
        )

        mismatches = []
        for row in rows:
            mismatches.append(
                {
                    "run_id": int(row["run_id"]),
                    "generation_event_id": int(row["generation_event_id"]),
                    "contest_id": int(row["contest_id"]),
                    "target_contest": row["target_contest"],
                    "games_count": int(row["games_count"]),
                }
            )

        return mismatches


def cleanup_mismatched_conferences() -> dict[str, Any]:
    """Remove conferências com mismatch."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    mismatches = find_mismatched_conferences()

    if not mismatches:
        return {
            "status": "success",
            "message": "Nenhuma conferência com mismatch encontrada",
            "cleaned_runs": 0,
            "cleaned_games": 0,
        }

    run_ids = [m["run_id"] for m in mismatches]
    total_games = sum(m["games_count"] for m in mismatches)

    with get_session(DB_PATH) as session:
        # Remove reconciliation_games
        session.execute(
            text(
                """
            DELETE FROM reconciliation_games
            WHERE reconciliation_run_id = ANY(:run_ids)
            """
            ),
            {"run_ids": run_ids},
        )

        # Remove reconciliation_runs
        session.execute(
            text(
                """
            DELETE FROM reconciliation_runs
            WHERE id = ANY(:run_ids)
            """
            ),
            {"run_ids": run_ids},
        )

        # Reset conference_status nos generation_events
        ge_ids = [m["generation_event_id"] for m in mismatches]
        session.execute(
            text(
                """
            UPDATE generation_events
            SET context_json = jsonb_set(
                COALESCE(context_json, '{}')::jsonb,
                '{conference_status}',
                '"unchecked"'
            )
            WHERE id = ANY(:ge_ids)
            """
            ),
            {"ge_ids": ge_ids},
        )

        session.commit()

    return {
        "status": "success",
        "message": f"Limpeza concluída: {len(run_ids)} runs, {total_games} games",
        "cleaned_runs": len(run_ids),
        "cleaned_games": total_games,
        "run_ids": run_ids,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Limpeza de conferências com target_contest mismatch"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas mostra o que seria feito, sem executar",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Executa a limpeza",
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")

    args = parser.parse_args()

    if not args.dry_run and not args.fix:
        parser.error("Especifique --dry-run ou --fix")

    try:
        if args.dry_run:
            mismatches = find_mismatched_conferences()
            result = {
                "status": "success",
                "mode": "dry-run",
                "mismatches_found": len(mismatches),
                "total_games": sum(m["games_count"] for m in mismatches),
                "mismatches": mismatches,
            }
        else:
            result = cleanup_mismatched_conferences()

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            print(f"\n[{MISSION_ID}] {result['message']}")
            if "mismatches" in result:
                print(f"\nMismatches encontrados: {result['mismatches_found']}")
                for m in result["mismatches"]:
                    print(
                        f"  Run#{m['run_id']} | GE#{m['generation_event_id']} | "
                        f"target={m['target_contest']} | contest={m['contest_id']} | "
                        f"games={m['games_count']}"
                    )

        return 0

    except Exception as exc:
        error_result = {
            "status": "error",
            "mission_id": MISSION_ID,
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if args.json:
            print(json.dumps(error_result, indent=2, default=str))
        else:
            print(f"[{MISSION_ID}] Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
