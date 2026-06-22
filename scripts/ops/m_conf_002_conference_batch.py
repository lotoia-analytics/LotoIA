#!/usr/bin/env python3
"""M-CONF-002 — Conferência institucional em lote por baterias.

Confere TODAS as gerações não conferidas de uma vez, agrupadas por baterias:
1. Carrega resultado oficial do concurso
2. Agrupa generation_events em baterias (como o painel ADM)
3. Confere cada bateria completa
4. Persiste resultados em blocos
5. Mostra resultado consolidado por bateria

Uso:
  python scripts/ops/m_conf_002_conference_batch.py --latest --persist --json
  python scripts/ops/m_conf_002_conference_batch.py --contest 3717 --persist
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-CONF-002"


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


def load_all_unconfered_generation_events() -> list[dict[str, Any]]:
    """Carrega TODOS os generation_events não conferidos."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT ge.id, ge.lead_id, ge.generated_games, ge.seed, ge.strategy,
                       ge.ml_enabled, ge.context_json, ge.created_at
                FROM generation_events ge
                LEFT JOIN reconciliation_runs rr ON ge.id = rr.generation_event_id
                WHERE rr.id IS NULL
                ORDER BY ge.id DESC
                """
                )
            )
            .mappings()
            .all()
        )

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

            # Extrai batch_id/battery_id do context
            batch_id = (
                context.get("batch_id")
                or context.get("battery_id")
                or f"GE:{row['id']}"
            )

            events.append(
                {
                    "id": int(row["id"]),
                    "lead_id": row["lead_id"],
                    "generated_games": row["generated_games"],
                    "seed": row["seed"],
                    "strategy": row["strategy"],
                    "ml_enabled": row["ml_enabled"],
                    "context": context,
                    "batch_id": batch_id,
                    "created_at": str(row["created_at"]),
                }
            )

        return events


def group_events_into_batteries(
    events: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Agrupa generation_events em baterias por batch_id."""
    batteries = defaultdict(list)
    for event in events:
        battery_id = event.get("batch_id", f"GE:{event['id']}")
        batteries[battery_id].append(event)
    return dict(batteries)


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


def persist_battery_conference(
    *,
    battery_id: str,
    generation_event_ids: list[int],
    contest_number: int,
    all_game_results: list[dict[str, Any]],
    source: str = "m_conf_002_batch_script",
) -> dict[str, Any]:
    """Persiste resultado da conferência de uma bateria completa."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    prize_count = sum(1 for g in all_game_results if g["prize_status"] == "premiado")
    total_hits = sum(g["hits"] for g in all_game_results)
    best_hits = max((g["hits"] for g in all_game_results), default=0)
    status = "reconciled" if all_game_results else "sem_jogos"

    with get_session(DB_PATH) as session:
        # Cria reconciliation_run para cada generation_event da bateria
        run_ids = []
        for ge_id in generation_event_ids:
            # Filtra jogos deste event específico
            event_games = [
                g for g in all_game_results if g.get("generation_event_id") == ge_id
            ]
            event_prize_count = sum(
                1 for g in event_games if g["prize_status"] == "premiado"
            )
            event_total_hits = sum(g["hits"] for g in event_games)
            event_best_hits = max((g["hits"] for g in event_games), default=0)

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
                    "generation_event_id": ge_id,
                    "contest_id": contest_number,
                    "source": source,
                    "status": status,
                    "prize_count": event_prize_count,
                    "total_hits": event_total_hits,
                    "best_hits": event_best_hits,
                    "payload": json.dumps(
                        {
                            "mission_id": MISSION_ID,
                            "battery_id": battery_id,
                            "total_games": len(event_games),
                            "prize_count": event_prize_count,
                            "best_hits": event_best_hits,
                            "average_hits": round(
                                event_total_hits / len(event_games), 2
                            )
                            if event_games
                            else 0,
                        }
                    ),
                },
            )
            run_id = session.execute(text("SELECT LASTVAL()")).scalar()
            run_ids.append(run_id)

            # Persiste jogos individuais
            for game_result in event_games:
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
                        "generation_event_id": ge_id,
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
                                "battery_id": battery_id,
                                "profile_type": game_result.get("profile_type", ""),
                                "reconciliation_run_id": run_id,
                            }
                        ),
                    },
                )

            # Marca generation_event como conferido
            session.execute(
                text(
                    """
                    UPDATE generation_events
                    SET context_json = jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                COALESCE(context_json, '{}')::jsonb,
                                '{conference_status}',
                                '"checked"'
                            ),
                            '{checked_at}',
                            to_jsonb(CURRENT_TIMESTAMP::text)
                        ),
                        '{checked_against_contest}',
                        :contest_number_json
                    )
                    WHERE id = :generation_event_id
                    """
                ),
                {
                    "generation_event_id": ge_id,
                    "contest_number_json": json.dumps(contest_number),
                },
            )

        session.commit()

    return {
        "status": "persisted",
        "battery_id": battery_id,
        "reconciliation_run_ids": run_ids,
        "generation_event_ids": generation_event_ids,
        "contest_number": contest_number,
        "total_games": len(all_game_results),
        "prize_count": prize_count,
        "best_hits": best_hits,
        "average_hits": round(total_hits / len(all_game_results), 2)
        if all_game_results
        else 0,
    }


def run_batch_conference(
    *,
    contest_number: int,
    persist: bool = False,
) -> dict[str, Any]:
    """Executa conferência em lote para TODAS as gerações não conferidas."""
    started = datetime.now(UTC)

    # Carrega resultado oficial
    official = load_official_contest(contest_number)
    if not official:
        return {
            "status": "error",
            "reason": "contest_not_found",
            "contest_number": contest_number,
        }

    # Carrega TODOS os events não conferidos
    events = load_all_unconfered_generation_events()
    if not events:
        return {
            "status": "warning",
            "reason": "no_unconfered_events",
            "contest_number": contest_number,
            "message": "Nenhum generation_event não conferido encontrado",
        }

    # Agrupa em baterias
    batteries = group_events_into_batteries(events)

    battery_results = []
    for battery_id, battery_events in batteries.items():
        # Carrega jogos de todos os events da bateria
        all_games = []
        for event in battery_events:
            games = load_generation_event_games(event["id"])
            for game in games:
                game["generation_event_id"] = event["id"]
            all_games.extend(games)

        if not all_games:
            battery_results.append(
                {
                    "battery_id": battery_id,
                    "generation_event_ids": [e["id"] for e in battery_events],
                    "status": "skipped",
                    "reason": "no_games",
                }
            )
            continue

        # Compara todos os jogos da bateria contra resultado oficial
        game_results = compare_games_against_contest(all_games, official["numbers"])

        # Adiciona generation_event_id aos resultados
        for i, game in enumerate(all_games):
            game_results[i]["generation_event_id"] = game["generation_event_id"]

        result = {
            "battery_id": battery_id,
            "generation_event_ids": [e["id"] for e in battery_events],
            "status": "success",
            "total_games": len(game_results),
            "prize_count": sum(
                1 for g in game_results if g["prize_status"] == "premiado"
            ),
            "best_hits": max((g["hits"] for g in game_results), default=0),
            "average_hits": round(
                sum(g["hits"] for g in game_results) / len(game_results), 2
            ),
        }

        # Distribuição de acertos
        hit_counts = Counter(g["hits"] for g in game_results)
        result["hit_distribution"] = {str(k): v for k, v in sorted(hit_counts.items())}

        # Persiste se solicitado
        if persist:
            persistence_result = persist_battery_conference(
                battery_id=battery_id,
                generation_event_ids=[e["id"] for e in battery_events],
                contest_number=contest_number,
                all_game_results=game_results,
            )
            result["persistence"] = persistence_result

        battery_results.append(result)

    execution_time_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "contest_number": contest_number,
        "official_numbers": official["numbers"],
        "draw_date": official.get("draw_date", ""),
        "total_batteries": len(battery_results),
        "total_events_confered": sum(
            len(b.get("generation_event_ids", [])) for b in battery_results
        ),
        "total_games_confered": sum(b.get("total_games", 0) for b in battery_results),
        "total_prizes": sum(b.get("prize_count", 0) for b in battery_results),
        "overall_best_hits": max(
            (b.get("best_hits", 0) for b in battery_results), default=0
        ),
        "battery_results": battery_results,
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": started.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Conferência institucional em lote por baterias"
    )
    parser.add_argument("--contest", type=int, help="Número do concurso")
    parser.add_argument(
        "--latest", action="store_true", help="Usa concurso mais recente"
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

        # Executa conferência em lote
        result = run_batch_conference(
            contest_number=contest_number,
            persist=args.persist,
        )

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if result.get("status") == "success":
                print(
                    f"\n[{MISSION_ID}] Conferência em Lote — Concurso {contest_number}"
                )
                print(
                    f"  Resultado oficial: {' '.join(f'{n:02d}' for n in result.get('official_numbers', []))}"
                )
                print(f"  Data: {result.get('draw_date', '')}")
                print(f"  Total de baterias: {result.get('total_batteries', 0)}")
                print(
                    f"  Total de events conferidos: {result.get('total_events_confered', 0)}"
                )
                print(
                    f"  Total de jogos conferidos: {result.get('total_games_confered', 0)}"
                )
                print(f"  Total de prêmios: {result.get('total_prizes', 0)}")
                print(
                    f"  Melhor resultado: {result.get('overall_best_hits', 0)} acertos"
                )
                print(f"  Tempo: {result.get('execution_time_ms', 0)}ms")
                print()
                print("  BATERIAS CONFERIDAS:")
                print("  " + "=" * 70)
                for b in result.get("battery_results", []):
                    battery_id = b.get("battery_id", "?")
                    ge_ids = b.get("generation_event_ids", [])
                    status = b.get("status", "?")

                    if status == "success":
                        total = b.get("total_games", 0)
                        prizes = b.get("prize_count", 0)
                        best = b.get("best_hits", 0)
                        avg = b.get("average_hits", 0)
                        print(
                            f"  {battery_id:40s} | GE:{ge_ids} | {total:4d} jogos | {prizes:3d} prêmios | melhor={best:2d} | média={avg:.1f}"
                        )
                    else:
                        reason = b.get("reason", "unknown")
                        print(f"  {battery_id:40s} | GE:{ge_ids} | {status}: {reason}")

                if args.persist:
                    print(
                        f"\n  Persistência: OK — {result.get('total_events_confered', 0)} events marcados como conferidos"
                    )
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
