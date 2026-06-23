#!/usr/bin/env python3
"""M-GER-002 — Deduplicação cross-event de jogos gerados.

Problema identificado: 203 grupos de duplicatas (536 instâncias) onde o mesmo
jogo aparece em múltiplos generation_events. O anti_clone_gp atual só funciona
dentro do mesmo batch, não entre eventos diferentes.

Solução:
1. Identifica todos os jogos duplicados no banco
2. Mantém apenas a primeira ocorrência (menor generation_event_id)
3. Remove duplicatas ou marca como inválidas
4. Adiciona constraint UNIQUE para prevenir futuras duplicatas

Uso:
  python scripts/ops/m_ger_002_cross_event_dedup.py --dry-run --json
  python scripts/ops/m_ger_002_cross_event_dedup.py --fix --json
  python scripts/ops/m_ger_002_cross_event_dedup.py --add-constraint --json
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
MISSION_ID = "M-GER-002"


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


def find_duplicate_games() -> list[dict[str, Any]]:
    """Encontra todos os jogos duplicados no banco."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Encontra grupos de duplicatas
        rows = (
            session.execute(
                text(
                    """
                SELECT 
                    numbers::text as numbers_key,
                    COUNT(*) as total_occurrences,
                    COUNT(DISTINCT generation_event_id) as distinct_events,
                    MIN(id) as first_id,
                    MIN(generation_event_id) as first_event_id,
                    ARRAY_AGG(id ORDER BY id) as all_ids,
                    ARRAY_AGG(generation_event_id ORDER BY generation_event_id) as all_event_ids
                FROM generated_games
                GROUP BY numbers::text
                HAVING COUNT(*) > 1
                ORDER BY total_occurrences DESC
                """
                )
            )
            .mappings()
            .all()
        )

        duplicates = []
        for row in rows:
            duplicates.append(
                {
                    "numbers_key": row["numbers_key"],
                    "total_occurrences": int(row["total_occurrences"]),
                    "distinct_events": int(row["distinct_events"]),
                    "first_id": int(row["first_id"]),
                    "first_event_id": int(row["first_event_id"]),
                    "all_ids": list(row["all_ids"]),
                    "all_event_ids": list(row["all_event_ids"]),
                }
            )

        return duplicates


def remove_duplicate_games(duplicates: list[dict[str, Any]]) -> dict[str, Any]:
    """Remove duplicatas, mantendo apenas a primeira ocorrência."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    removed_count = 0
    removed_ids = []

    with get_session(DB_PATH) as session:
        for dup in duplicates:
            # Mantém o primeiro (menor ID), remove os outros
            ids_to_remove = [id for id in dup["all_ids"] if id != dup["first_id"]]
            if ids_to_remove:
                session.execute(
                    text(
                        """
                    DELETE FROM generated_games
                    WHERE id = ANY(:ids)
                    """
                    ),
                    {"ids": ids_to_remove},
                )
                removed_count += len(ids_to_remove)
                removed_ids.extend(ids_to_remove)

        session.commit()

    return {
        "status": "success",
        "duplicates_processed": len(duplicates),
        "games_removed": removed_count,
        "removed_ids": removed_ids,
    }


def add_unique_constraint() -> dict[str, Any]:
    """Adiciona constraint UNIQUE para prevenir futuras duplicatas."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Verifica se índice já existe
        exists = session.execute(
            text(
                """
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'uq_generated_games_numbers_hash'
                """
            )
        ).scalar()

        if exists:
            return {"status": "skipped", "reason": "index_already_exists"}

        # Adiciona unique index via hash (json não suporta UNIQUE direto com btree)
        session.execute(
            text(
                """
                CREATE UNIQUE INDEX uq_generated_games_numbers_hash
                ON generated_games (md5(numbers::text))
                """
            )
        )
        session.commit()

    return {
        "status": "success",
        "constraint_added": "uq_generated_games_numbers_hash (md5 expression index)",
    }


def run_dedup_analysis() -> dict[str, Any]:
    """Executa análise completa de duplicatas."""
    started = datetime.now(UTC)

    duplicates = find_duplicate_games()

    total_duplicate_groups = len(duplicates)
    total_duplicate_instances = sum(d["total_occurrences"] for d in duplicates)
    total_removable = sum(d["total_occurrences"] - 1 for d in duplicates)
    cross_event_duplicates = sum(1 for d in duplicates if d["distinct_events"] > 1)

    # Top 10 piores
    top_worst = duplicates[:10]

    execution_time_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "summary": {
            "total_duplicate_groups": total_duplicate_groups,
            "total_duplicate_instances": total_duplicate_instances,
            "total_removable_games": total_removable,
            "cross_event_duplicates": cross_event_duplicates,
        },
        "top_worst_duplicates": [
            {
                "numbers": d["numbers_key"][:80] + "...",
                "occurrences": d["total_occurrences"],
                "distinct_events": d["distinct_events"],
                "first_event_id": d["first_event_id"],
            }
            for d in top_worst
        ],
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": started.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Deduplicação cross-event de jogos gerados"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas analisa, não remove nada",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Remove duplicatas (mantém primeira ocorrência)",
    )
    parser.add_argument(
        "--add-constraint",
        action="store_true",
        help="Adiciona constraint UNIQUE para prevenir futuras duplicatas",
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        if args.dry_run:
            result = run_dedup_analysis()
        elif args.fix:
            # Primeiro analisa
            analysis = run_dedup_analysis()
            duplicates = find_duplicate_games()
            # Depois remove
            removal = remove_duplicate_games(duplicates)
            result = {
                **analysis,
                "removal": removal,
            }
        elif args.add_constraint:
            result = add_unique_constraint()
        else:
            print(
                "Erro: especifique --dry-run, --fix ou --add-constraint",
                file=sys.stderr,
            )
            return 1

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if args.dry_run:
                summary = result.get("summary", {})
                print(f"[{MISSION_ID}] Análise de Duplicatas:")
                print(f"  Grupos duplicados: {summary.get('total_duplicate_groups')}")
                print(
                    f"  Instâncias duplicadas: {summary.get('total_duplicate_instances')}"
                )
                print(f"  Jogos removíveis: {summary.get('total_removable_games')}")
                print(
                    f"  Duplicatas cross-event: {summary.get('cross_event_duplicates')}"
                )
                print()
                print("  TOP 10 PIORES:")
                for d in result.get("top_worst_duplicates", []):
                    print(
                        f"    {d['numbers']} | {d['occurrences']}x em {d['distinct_events']} events"
                    )
            elif args.fix:
                removal = result.get("removal", {})
                print(f"[{MISSION_ID}] Remoção de Duplicatas:")
                print(f"  Grupos processados: {removal.get('duplicates_processed')}")
                print(f"  Jogos removidos: {removal.get('games_removed')}")
            elif args.add_constraint:
                print(f"[{MISSION_ID}] Constraint:")
                print(f"  Status: {result.get('status')}")
                if result.get("constraint_added"):
                    print(f"  Constraint adicionada: {result.get('constraint_added')}")

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
