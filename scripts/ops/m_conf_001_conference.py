#!/usr/bin/env python3
"""M-CONF-001 — Script de conferência institucional.

Executa a conferência de jogos gerados contra resultados oficiais:
1. Carrega resultado oficial do concurso
2. Seleciona generation_events não conferidos
3. Compara jogos contra resultado oficial
4. Persiste em reconciliation_runs e reconciliation_games
5. Marca events como conferidos

Uso:
  python scripts/ops/m_conf_001_conference.py --contest 3717 --json
  python scripts/ops/m_conf_001_conference.py --latest --persist --json
  python scripts/ops/m_conf_001_conference.py --generation-event 188 --contest 3717 --persist
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
MISSION_ID = "M-CONF-001"


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


def load_official_contest(contest_number: int) -> dict[str, Any] | None:
    """Carrega resultado oficial de um concurso."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT contest_number, numbers, draw_date
                FROM lotofacil_official_history
                WHERE contest_number = :contest_number
                """
                ),
                {"contest_number": contest_number},
            )
            .mappings()
            .first()
        )

        if not row:
            # Tenta imported_contests
            row = (
                session.execute(
                    text(
                        """
                    SELECT contest_number, data as draw_date
                    FROM imported_contests
                    WHERE contest_number = :contest_number
                    """
                    ),
                    {"contest_number": contest_number},
                )
                .mappings()
                .first()
            )

            if not row:
                return None

            # imported_contests não tem numbers diretamente, precisa buscar em lotofacil_official_history
            return None

        numbers_str = str(row["numbers"] or "")
        numbers = [
            int(n.strip()) for n in numbers_str.split(",") if n.strip().isdigit()
        ]

        return {
            "contest_number": int(row["contest_number"]),
            "numbers": sorted(numbers),
            "draw_date": str(row["draw_date"] or ""),
        }


def load_latest_official_contest() -> dict[str, Any] | None:
    """Carrega o concurso oficial mais recente."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT contest_number, numbers, draw_date
                FROM lotofacil_official_history
                ORDER BY contest_number DESC
                LIMIT 1
                """
                )
            )
            .mappings()
            .first()
        )

        if not row:
            return None

        numbers_str = str(row["numbers"] or "")
        numbers = [
            int(n.strip()) for n in numbers_str.split(",") if n.strip().isdigit()
        ]

        return {
            "contest_number": int(row["contest_number"]),
            "numbers": sorted(numbers),
            "draw_date": str(row["draw_date"] or ""),
        }


def load_unconfered_generation_events(
    target_contest: int | None = None,
) -> list[dict[str, Any]]:
    """Carrega generation_events que ainda não foram conferidos."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Busca events que NÃO estão em reconciliation_runs
        query = """
            SELECT ge.id, ge.lead_id, ge.generated_games, ge.seed, ge.strategy,
                   ge.ml_enabled, ge.context_json, ge.created_at
            FROM generation_events ge
            LEFT JOIN reconciliation_runs rr ON ge.id = rr.generation_event_id
            WHERE rr.id IS NULL
        """
        params = {}

        if target_contest is not None:
            # Filtra por target_contest no context_json ou generated_games
            query += """
                AND (
                    ge.context_json->>'target_contest' = :target_contest
                    OR ge.context_json::text LIKE :target_pattern
                )
            """
            params["target_contest"] = str(target_contest)
            params["target_pattern"] = f'%"target_contest":{target_contest}%'

        query += " ORDER BY ge.id DESC"

        rows = session.execute(text(query), params).mappings().all()

        events = []
        for row in rows:
            context = (
                row["context_json"] if isinstance(row["context_json"], dict) else {}
            )
            if isinstance(row["context_json"], str):
                try:
                    context = json.loads(row["context_json"])
                except:
                    context = {}

            events.append(
                {
                    "id": int(row["id"]),
                    "lead_id": row["lead_id"],
                    "generated_games": row["generated_games"],
                    "seed": row["seed"],
                    "strategy": row["strategy"],
                    "ml_enabled": row["ml_enabled"],
                    "context": context,
                    "created_at": str(row["created_at"]),
                }
            )

        return events


def load_generation_event_games(generation_event_id: int) -> list[dict[str, Any]]:
    """Carrega jogos de um generation_event específico."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id, game_index, numbers, profile_type, final_score, quadra_score, context_json
                FROM generated_games
                WHERE generation_event_id = :generation_event_id
                ORDER BY game_index
                """
                ),
                {"generation_event_id": generation_event_id},
            )
            .mappings()
            .all()
        )

        games = []
        for row in rows:
            numbers_raw = row["numbers"]
            if isinstance(numbers_raw, str):
                numbers = [
                    int(n.strip())
                    for n in numbers_raw.split(",")
                    if n.strip().isdigit()
                ]
            elif isinstance(numbers_raw, list):
                numbers = [int(n) for n in numbers_raw]
            else:
                numbers = []

            games.append(
                {
                    "id": int(row["id"]),
                    "game_index": int(row["game_index"]),
                    "numbers": sorted(numbers),
                    "profile_type": str(row["profile_type"] or ""),
                    "final_score": row["final_score"]
                    if isinstance(row["final_score"], dict)
                    else {},
                    "quadra_score": row["quadra_score"]
                    if isinstance(row["quadra_score"], dict)
                    else {},
                    "context_json": row["context_json"],
                }
            )

        return games


def compare_games_against_contest(
    games: list[dict[str, Any]], official_numbers: list[int]
) -> list[dict[str, Any]]:
    """Compara jogos contra resultado oficial e calcula acertos."""
    official_set = set(official_numbers)
    results = []

    for game in games:
        game_set = set(game.get("numbers", []))
        matched = sorted(game_set & official_set)
        hits = len(matched)

        prize_status = "premiado" if hits >= 11 else "nao_premiado"
        prize_tier = f"faixa_{hits}" if hits >= 11 else "sem_premio"

        results.append(
            {
                "game_index": game.get("game_index"),
                "numbers": game.get("numbers", []),
                "hits": hits,
                "matched_numbers": matched,
                "prize_status": prize_status,
                "prize_tier": prize_tier,
                "profile_type": game.get("profile_type", ""),
            }
        )

    return results


def persist_conference_result(
    *,
    generation_event_id: int,
    contest_number: int,
    game_results: list[dict[str, Any]],
    source: str = "m_conf_001_script",
) -> dict[str, Any]:
    """Persiste resultado da conferência no banco."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    prize_count = sum(1 for g in game_results if g["prize_status"] == "premiado")
    total_hits = sum(g["hits"] for g in game_results)
    best_hits = max((g["hits"] for g in game_results), default=0)
    status = "reconciled" if game_results else "sem_jogos"

    with get_session(DB_PATH) as session:
        # Cria reconciliation_run
        session.execute(
            text(
                """
                INSERT INTO reconciliation_runs (
                    generation_event_id, lead_id, contest_id, source, status,
                    prize_count, total_hits, best_hits, payload, created_at
                ) VALUES (
                    :generation_event_id, NULL, :contest_id, :source, :status,
                    :prize_count, :total_hits, :best_hits, :payload, CURRENT_TIMESTAMP
                ) RETURNING id
                """
            ),
            {
                "generation_event_id": generation_event_id,
                "contest_id": contest_number,
                "source": source,
                "status": status,
                "prize_count": prize_count,
                "total_hits": total_hits,
                "best_hits": best_hits,
                "payload": json.dumps(
                    {
                        "mission_id": MISSION_ID,
                        "total_games": len(game_results),
                        "prize_count": prize_count,
                        "best_hits": best_hits,
                        "average_hits": round(total_hits / len(game_results), 2)
                        if game_results
                        else 0,
                    }
                ),
            },
        )
        run_id = session.execute(text("SELECT LASTVAL()")).scalar()

        # Persiste jogos individuais
        for game_result in game_results:
            session.execute(
                text(
                    """
                    INSERT INTO reconciliation_games (
                        reconciliation_run_id, generation_event_id, lead_id, contest_id,
                        game_index, numbers, hits, matched_numbers, prize_status, prize_tier,
                        context_json
                    ) VALUES (
                        :run_id, :generation_event_id, NULL, :contest_id,
                        :game_index, :numbers, :hits, :matched_numbers, :prize_status, :prize_tier,
                        :context_json
                    )
                    """
                ),
                {
                    "run_id": run_id,
                    "generation_event_id": generation_event_id,
                    "contest_id": contest_number,
                    "game_index": game_result["game_index"],
                    "numbers": json.dumps(game_result["numbers"]),
                    "hits": game_result["hits"],
                    "matched_numbers": json.dumps(game_result["matched_numbers"]),
                    "prize_status": game_result["prize_status"],
                    "prize_tier": game_result["prize_tier"],
                    "context_json": json.dumps(
                        {
                            "source": MISSION_ID,
                            "profile_type": game_result.get("profile_type", ""),
                            "reconciliation_run_id": run_id,
                        }
                    ),
                },
            )

        # Marca generation_event como conferido no context_json
        session.execute(
            text(
                """
                UPDATE generation_events
                SET context_json = jsonb_set(
                    COALESCE(context_json, '{}')::jsonb,
                    '{conference_status}',
                    '"checked"'
                )
                WHERE id = :generation_event_id
                """
            ),
            {"generation_event_id": generation_event_id},
        )

        session.execute(
            text(
                """
                UPDATE generation_events
                SET context_json = jsonb_set(
                    context_json::jsonb,
                    '{checked_at}',
                    to_jsonb(CURRENT_TIMESTAMP::text)
                )
                WHERE id = :generation_event_id
                """
            ),
            {"generation_event_id": generation_event_id},
        )

        session.execute(
            text(
                """
                UPDATE generation_events
                SET context_json = jsonb_set(
                    context_json::jsonb,
                    '{checked_against_contest}',
                    :contest_number_json
                )
                WHERE id = :generation_event_id
                """
            ),
            {
                "generation_event_id": generation_event_id,
                "contest_number_json": json.dumps(contest_number),
            },
        )

        session.commit()

    return {
        "status": "persisted",
        "reconciliation_run_id": run_id,
        "generation_event_id": generation_event_id,
        "contest_number": contest_number,
        "total_games": len(game_results),
        "prize_count": prize_count,
        "best_hits": best_hits,
        "average_hits": round(total_hits / len(game_results), 2) if game_results else 0,
    }


def run_conference(
    *,
    contest_number: int,
    generation_event_id: int | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Executa conferência para um concurso e generation_event específico ou todos não conferidos."""
    started = datetime.now(UTC)

    # Carrega resultado oficial
    official = load_official_contest(contest_number)
    if not official:
        return {
            "status": "error",
            "reason": "contest_not_found",
            "contest_number": contest_number,
        }

    # Carrega events não conferidos
    if generation_event_id is not None:
        events = [{"id": generation_event_id}]
    else:
        # Quando não especificado, busca TODOS os events não conferidos
        events = load_unconfered_generation_events(target_contest=None)

    if not events:
        return {
            "status": "warning",
            "reason": "no_unconfered_events",
            "contest_number": contest_number,
            "message": "Nenhum generation_event não conferido encontrado",
        }

    results = []
    for event in events:
        event_id = event["id"]

        # Carrega jogos do event
        games = load_generation_event_games(event_id)
        if not games:
            results.append(
                {
                    "generation_event_id": event_id,
                    "status": "skipped",
                    "reason": "no_games",
                }
            )
            continue

        # Compara contra resultado oficial
        game_results = compare_games_against_contest(games, official["numbers"])

        result = {
            "generation_event_id": event_id,
            "status": "success",
            "total_games": len(game_results),
            "prize_count": sum(
                1 for g in game_results if g["prize_status"] == "premiado"
            ),
            "best_hits": max((g["hits"] for g in game_results), default=0),
            "average_hits": round(
                sum(g["hits"] for g in game_results) / len(game_results), 2
            ),
            "hit_distribution": {},
        }

        # Calcula distribuição de acertos
        from collections import Counter

        hit_counts = Counter(g["hits"] for g in game_results)
        result["hit_distribution"] = {str(k): v for k, v in sorted(hit_counts.items())}

        # Persiste se solicitado
        if persist:
            persistence_result = persist_conference_result(
                generation_event_id=event_id,
                contest_number=contest_number,
                game_results=game_results,
            )
            result["persistence"] = persistence_result

        results.append(result)

    execution_time_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "contest_number": contest_number,
        "official_numbers": official["numbers"],
        "draw_date": official.get("draw_date", ""),
        "events_confered": len(results),
        "results": results,
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": started.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Conferência institucional"
    )
    parser.add_argument("--contest", type=int, help="Número do concurso")
    parser.add_argument(
        "--latest", action="store_true", help="Usa concurso mais recente"
    )
    parser.add_argument(
        "--generation-event", type=int, help="Generation Event ID específico"
    )
    parser.add_argument(
        "--persist", action="store_true", help="Persiste resultado no banco"
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    if not args.contest and not args.latest:
        print("Erro: especifique --contest ou --latest", file=sys.stderr)
        return 1

    try:
        # Determina concurso
        if args.latest:
            latest = load_latest_official_contest()
            if not latest:
                print("Erro: nenhum concurso oficial encontrado", file=sys.stderr)
                return 1
            contest_number = latest["contest_number"]
        else:
            contest_number = int(args.contest)

        # Executa conferência
        result = run_conference(
            contest_number=contest_number,
            generation_event_id=args.generation_event,
            persist=args.persist,
        )

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if result.get("status") == "success":
                print(f"[{MISSION_ID}] Conferência — Concurso {contest_number}")
                print(
                    f"  Resultado oficial: {' '.join(f'{n:02d}' for n in result.get('official_numbers', []))}"
                )
                print(f"  Events conferidos: {result.get('events_confered', 0)}")
                for r in result.get("results", []):
                    ge_id = r.get("generation_event_id")
                    if r.get("status") == "success":
                        print(
                            f"    GE:{ge_id} — {r.get('total_games')} jogos, {r.get('prize_count')} prêmios, melhor={r.get('best_hits')}"
                        )
                    else:
                        print(
                            f"    GE:{ge_id} — {r.get('status')}: {r.get('reason', 'unknown')}"
                        )
                if args.persist:
                    print(f"  Persistência: OK")
            else:
                print(
                    f"[{MISSION_ID}] {result.get('status')}: {result.get('reason', 'unknown')}"
                )

        return 0 if result.get("status") in ("success", "warning") else 1

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
