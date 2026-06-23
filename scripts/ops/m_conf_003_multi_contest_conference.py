#!/usr/bin/env python3
"""
M-CONF-003: Conferência Multi-Concurso
Confere jogos gerados contra os últimos 100 concursos oficiais para validar qualidade.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

# Adiciona o root do projeto ao path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text


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
    raise RuntimeError(f"[M-CONF-003] PostgreSQL não configurado. Defina DATABASE_URL.")


def load_last_n_contests(n: int = 100) -> List[Dict[str, Any]]:
    """Carrega os últimos N concursos oficiais."""
    db_url = _resolve_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        query = text("""
            SELECT contest_number, draw_date, numbers
            FROM lotofacil_official_history
            ORDER BY contest_number DESC
            LIMIT :n
        """)
        result = conn.execute(query, {"n": n})

        contests = []
        for row in result:
            numbers = row.numbers
            if isinstance(numbers, str):
                numbers = [int(n.strip()) for n in numbers.split(",")]
            elif isinstance(numbers, list):
                numbers = [int(n) for n in numbers]

            contests.append(
                {
                    "contest_number": row.contest_number,
                    "draw_date": row.draw_date,
                    "numbers": sorted(numbers),
                }
            )

        return contests


def load_unconfered_events() -> List[Dict[str, Any]]:
    """Carrega generation_events não conferidos."""
    db_url = _resolve_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        query = text("""
            SELECT ge.id, ge.created_at,
                   (SELECT COUNT(*) FROM generated_games WHERE generation_event_id = ge.id) as total_games
            FROM generation_events ge
            LEFT JOIN reconciliation_runs rr ON ge.id = rr.generation_event_id
            WHERE rr.id IS NULL
            ORDER BY ge.id DESC
        """)
        result = conn.execute(query)

        events = []
        for row in result:
            events.append(
                {
                    "id": row.id,
                    "created_at": row.created_at,
                    "total_games": row.total_games,
                }
            )

        return events


def load_games_for_event(event_id: int) -> List[List[int]]:
    """Carrega todos os jogos de um generation_event."""
    db_url = _resolve_database_url()
    engine = create_engine(db_url)

    with engine.connect() as conn:
        query = text("""
            SELECT numbers
            FROM generated_games
            WHERE generation_event_id = :event_id
            ORDER BY game_index
        """)
        result = conn.execute(query, {"event_id": event_id})

        games = []
        for row in result:
            numbers = row.numbers
            if isinstance(numbers, str):
                numbers = [int(n.strip()) for n in numbers.split(",")]
            elif isinstance(numbers, list):
                numbers = [int(n) for n in numbers]
            games.append(sorted(numbers))

        return games


def compare_games_against_contest(
    games: List[List[int]], contest_numbers: List[int]
) -> Dict[str, Any]:
    """Compara jogos contra um concurso específico."""
    contest_set = set(contest_numbers)

    hits_distribution = defaultdict(int)
    prize_count = 0
    total_hits = 0

    for game in games:
        game_set = set(game)
        hits = len(game_set & contest_set)
        hits_distribution[hits] += 1
        total_hits += hits

        if hits >= 11:
            prize_count += 1

    avg_hits = total_hits / len(games) if games else 0

    return {
        "hits_distribution": dict(hits_distribution),
        "prize_count": prize_count,
        "avg_hits": avg_hits,
        "best_hits": max(hits_distribution.keys()) if hits_distribution else 0,
    }


def run_multi_contest_conference(n_contests: int = 100):
    """
    Confere jogos gerados contra os últimos N concursos oficiais.
    """
    print(f"\n{'=' * 80}")
    print(f"M-CONF-003: Conferência Multi-Concurso")
    print(f"{'=' * 80}\n")

    # Carrega últimos N concursos
    print(f"Carregando últimos {n_contests} concursos oficiais...")
    contests = load_last_n_contests(n_contests)
    print(f"✓ {len(contests)} concursos carregados")
    print(
        f"  Range: #{contests[-1]['contest_number']} até #{contests[0]['contest_number']}\n"
    )

    # Carrega events não conferidos
    print("Carregando generation_events não conferidos...")
    events = load_unconfered_events()
    print(f"✓ {len(events)} events encontrados\n")

    if not events:
        print("Nenhum event não conferido encontrado.")
        return

    # Para cada event, confere contra todos os concursos
    results = []

    for event in events:
        event_id = event["id"]
        print(f"\nProcessando Event #{event_id}...")
        print(f"  Total de jogos: {event['total_games']}")

        # Carrega jogos do event
        games = load_games_for_event(event_id)
        print(f"  ✓ {len(games)} jogos carregados")

        # Confere contra cada concurso
        contest_results = []
        total_prizes = 0
        total_avg_hits = 0
        best_overall = 0

        for i, contest in enumerate(contests, 1):
            if i % 10 == 0:
                print(f"  Conferindo contra concursos... {i}/{len(contests)}")

            result = compare_games_against_contest(games, contest["numbers"])

            contest_results.append(
                {
                    "contest_number": contest["contest_number"],
                    "draw_date": contest["draw_date"],
                    **result,
                }
            )

            total_prizes += result["prize_count"]
            total_avg_hits += result["avg_hits"]
            best_overall = max(best_overall, result["best_hits"])

        # Calcula estatísticas agregadas
        avg_prizes_per_contest = total_prizes / len(contests)
        avg_hits_overall = total_avg_hits / len(contests)

        # Distribuição agregada de hits
        aggregated_hits = defaultdict(int)
        for cr in contest_results:
            for hits, count in cr["hits_distribution"].items():
                aggregated_hits[hits] += count

        event_result = {
            "event_id": event_id,
            "created_at": event["created_at"].isoformat()
            if event["created_at"]
            else None,
            "total_games": len(games),
            "contests_checked": len(contests),
            "total_prizes": total_prizes,
            "avg_prizes_per_contest": avg_prizes_per_contest,
            "avg_hits_overall": avg_hits_overall,
            "best_hits_overall": best_overall,
            "aggregated_hits_distribution": dict(aggregated_hits),
            "contest_results": contest_results,
        }

        results.append(event_result)

        print(f"\n  ✓ Event #{event_id} conferido contra {len(contests)} concursos")
        print(f"    Total de prêmios: {total_prizes}")
        print(f"    Média de prêmios por concurso: {avg_prizes_per_contest:.2f}")
        print(f"    Média de acertos geral: {avg_hits_overall:.2f}")
        print(f"    Melhor resultado: {best_overall} acertos")

    # Salva resultados
    output_file = (
        project_root
        / "data"
        / "processed"
        / f"multi_contest_conference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'=' * 80}")
    print(f"✓ Resultados salvos em: {output_file}")
    print(f"{'=' * 80}\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Conferência Multi-Concurso")
    parser.add_argument(
        "--n",
        type=int,
        default=100,
        help="Número de concursos para conferir (default: 100)",
    )

    args = parser.parse_args()
    run_multi_contest_conference(n_contests=args.n)
