#!/usr/bin/env python3
"""M-FEEDBACK-002 — Feedback loop automatizado pós-concurso.

Executa automaticamente após cada concurso oficial:
1. Detecta novo concurso na lotofacil_official_history
2. Roda feedback loop para concursos sem feedback
3. Gera recomendações de calibração baseadas em dados reais
4. Persiste em feedback_loop
5. Opcionalmente ajusta pesos de geração automaticamente

Uso:
  python scripts/ops/m_feedback_002_auto_loop.py --auto --persist --json
  python scripts/ops/m_feedback_002_auto_loop.py --contest 3717 --persist --json
  python scripts/ops/m_feedback_002_auto_loop.py --backfill --persist --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-FEEDBACK-002"


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


def get_contests_without_feedback() -> list[int]:
    """Retorna concursos que têm jogos gerados mas não têm feedback."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Concursos com jogos gerados
        contests_with_games = (
            session.execute(
                text(
                    """
                SELECT DISTINCT target_contest
                FROM generated_games
                WHERE target_contest IS NOT NULL
                ORDER BY target_contest
                """
                )
            )
            .scalars()
            .all()
        )

        # Concursos com feedback
        contests_with_feedback = (
            session.execute(
                text(
                    """
                SELECT contest_number
                FROM feedback_loop
                ORDER BY contest_number
                """
                )
            )
            .scalars()
            .all()
        )

        # Concursos oficiais (para validar)
        official_contests = (
            session.execute(
                text(
                    """
                SELECT contest_number
                FROM lotofacil_official_history
                ORDER BY contest_number
                """
                )
            )
            .scalars()
            .all()
        )

    official_set = set(official_contests)
    feedback_set = set(contests_with_feedback)

    # Concursos que têm jogos, são oficiais, mas não têm feedback
    missing = [
        c for c in contests_with_games if c in official_set and c not in feedback_set
    ]

    return sorted(missing)


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


def load_generated_games_for_contest(target_contest: int) -> list[dict[str, Any]]:
    """Carrega jogos gerados para um concurso alvo."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id, generation_event_id, game_index, numbers, profile_type, final_score
                FROM generated_games
                WHERE target_contest = :target_contest
                ORDER BY generation_event_id, game_index
                """
                ),
                {"target_contest": target_contest},
            )
            .mappings()
            .all()
        )

        games = []
        for row in rows:
            numbers_raw = row["numbers"]
            if isinstance(numbers_raw, str):
                try:
                    numbers = json.loads(numbers_raw)
                except:
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
                    "generation_event_id": int(row["generation_event_id"]),
                    "game_index": int(row["game_index"]),
                    "numbers": sorted(numbers),
                    "profile_type": str(row["profile_type"] or ""),
                    "final_score": row["final_score"]
                    if isinstance(row["final_score"], dict)
                    else {},
                }
            )

        return games


def analyze_hits_advanced(
    games: list[dict[str, Any]], official_numbers: list[int]
) -> dict[str, Any]:
    """Análise avançada de acertos com decomposição por perfil e dezena."""
    official_set = set(official_numbers)
    hit_counts = []
    per_profile_hits: dict[str, list[int]] = {}
    dezena_hit_freq: Counter = Counter()

    for game in games:
        game_set = set(game.get("numbers", []))
        hits = len(game_set & official_set)
        hit_counts.append(hits)

        # Por perfil
        profile = game.get("profile_type", "unknown")
        if profile not in per_profile_hits:
            per_profile_hits[profile] = []
        per_profile_hits[profile].append(hits)

        # Dezenas que acertaram
        matched = game_set & official_set
        for d in matched:
            dezena_hit_freq[d] += 1

    hit_distribution = Counter(hit_counts)
    average_hits = sum(hit_counts) / len(hit_counts) if hit_counts else 0.0

    # Stats por perfil
    profile_stats = {}
    for profile, hits_list in per_profile_hits.items():
        profile_stats[profile] = {
            "count": len(hits_list),
            "avg_hits": round(sum(hits_list) / len(hits_list), 2) if hits_list else 0,
            "max_hits": max(hits_list) if hits_list else 0,
            "hits_11_plus": sum(1 for h in hits_list if h >= 11),
        }

    # Dezenas mais acertadas
    top_hit_dezenas = [
        {"dezena": d, "hit_count": c} for d, c in dezena_hit_freq.most_common(10)
    ]

    return {
        "games_analyzed": len(games),
        "hit_distribution": {str(k): v for k, v in sorted(hit_distribution.items())},
        "average_hits": round(average_hits, 3),
        "max_hits": max(hit_counts) if hit_counts else 0,
        "min_hits": min(hit_counts) if hit_counts else 0,
        "profile_stats": profile_stats,
        "top_hit_dezenas": top_hit_dezenas,
    }


def generate_smart_recommendations(
    hit_analysis: dict[str, Any],
    official_numbers: list[int],
) -> list[dict[str, Any]]:
    """Gera recomendações inteligentes baseadas em dados reais."""
    recommendations = []

    avg_hits = hit_analysis.get("average_hits", 0)
    profile_stats = hit_analysis.get("profile_stats", {})
    top_dezenas = hit_analysis.get("top_hit_dezenas", [])

    # Recomendação: perfil com pior desempenho
    worst_profile = None
    worst_avg = 999
    for profile, stats in profile_stats.items():
        if stats["count"] >= 10 and stats["avg_hits"] < worst_avg:
            worst_avg = stats["avg_hits"]
            worst_profile = profile

    if worst_profile and worst_avg < avg_hits * 0.85:
        recommendations.append(
            {
                "action": "reduce_profile_weight",
                "parameter": f"{worst_profile}_ratio",
                "current_value": "default",
                "suggested_value": "reduce_by_50%",
                "reason": f"Perfil '{worst_profile}' tem média {worst_avg} vs média geral {avg_hits:.2f}",
            }
        )

    # Recomendação: dezenas quentes (mais acertaram)
    if top_dezenas:
        hot_dezenas = [d["dezena"] for d in top_dezenas[:5]]
        recommendations.append(
            {
                "action": "boost_hot_dezenas",
                "parameter": "hot_dezenas_boost",
                "current_value": 1.0,
                "suggested_value": 1.3,
                "reason": f"Dezenas {hot_dezenas} tiveram maior taxa de acerto",
                "hot_dezenas": hot_dezenas,
            }
        )

    # Recomendação: soma média
    if avg_hits < 9.0:
        recommendations.append(
            {
                "action": "increase_sum_target",
                "parameter": "sum_score_target",
                "current_value": 195,
                "suggested_value": 210,
                "reason": f"Média de acertos {avg_hits:.2f} abaixo de 9.0 — aumentar target de soma",
            }
        )

    return recommendations


def persist_feedback(
    *,
    contest_number: int,
    official_numbers: list[int],
    hit_analysis: dict[str, Any],
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persiste feedback loop no banco."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    feedback_data = {
        "mission_id": MISSION_ID,
        "official_numbers": official_numbers,
        "hit_analysis": hit_analysis,
        "recommendations": recommendations,
        "version": "v2_smart",
    }

    with get_session(DB_PATH) as session:
        session.execute(
            text(
                """
            INSERT INTO feedback_loop (
                contest_number, feedback_data
            ) VALUES (
                :contest_number, :feedback_data
            )
            ON CONFLICT (contest_number) DO UPDATE SET
                feedback_data = EXCLUDED.feedback_data,
                created_at = CURRENT_TIMESTAMP
            RETURNING id
            """
            ),
            {
                "contest_number": contest_number,
                "feedback_data": json.dumps(feedback_data, default=str),
            },
        )
        feedback_id = session.execute(text("SELECT LASTVAL()")).scalar()
        session.commit()

    return {"status": "persisted", "feedback_id": feedback_id}


def run_feedback_for_contest(
    contest_number: int, *, persist: bool = False
) -> dict[str, Any]:
    """Executa feedback loop para um concurso específico."""
    started = datetime.now(UTC)

    official = load_official_contest(contest_number)
    if not official:
        return {
            "status": "error",
            "reason": "contest_not_found",
            "contest_number": contest_number,
        }

    games = load_generated_games_for_contest(contest_number)
    if not games:
        return {
            "status": "warning",
            "reason": "no_games_for_contest",
            "contest_number": contest_number,
        }

    hit_analysis = analyze_hits_advanced(games, official["numbers"])
    recommendations = generate_smart_recommendations(hit_analysis, official["numbers"])

    result = {
        "status": "success",
        "mission_id": MISSION_ID,
        "contest_number": contest_number,
        "official_numbers": official["numbers"],
        "hit_analysis": hit_analysis,
        "recommendations": recommendations,
        "timestamp": started.isoformat(),
    }

    if persist:
        persistence = persist_feedback(
            contest_number=contest_number,
            official_numbers=official["numbers"],
            hit_analysis=hit_analysis,
            recommendations=recommendations,
        )
        result["persistence"] = persistence

    return result


def run_auto_feedback(*, persist: bool = False) -> dict[str, Any]:
    """Executa feedback para todos os concursos pendentes."""
    started = datetime.now(UTC)

    missing = get_contests_without_feedback()

    results = []
    for contest in missing:
        result = run_feedback_for_contest(contest, persist=persist)
        results.append(result)

    execution_time_ms = (datetime.now(UTC) - started).total_seconds() * 1000

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "contests_processed": len(results),
        "contests_missing": len(missing),
        "results": results,
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": started.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Feedback loop automatizado pós-concurso"
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Processa todos os concursos pendentes",
    )
    parser.add_argument("--contest", type=int, help="Concurso específico")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Equivalente a --auto (processa pendentes)",
    )
    parser.add_argument(
        "--persist", action="store_true", help="Persiste resultado no banco"
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        if args.auto or args.backfill:
            result = run_auto_feedback(persist=args.persist)
        elif args.contest:
            result = run_feedback_for_contest(args.contest, persist=args.persist)
        else:
            print(
                "Erro: especifique --auto, --backfill ou --contest",
                file=sys.stderr,
            )
            return 1

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if result.get("status") == "success":
                if "contests_processed" in result:
                    print(
                        f"[{MISSION_ID}] Auto-Feedback: {result.get('contests_processed')} concursos processados"
                    )
                    for r in result.get("results", []):
                        contest = r.get("contest_number")
                        avg = r.get("hit_analysis", {}).get("average_hits", 0)
                        max_h = r.get("hit_analysis", {}).get("max_hits", 0)
                        recs = len(r.get("recommendations", []))
                        print(
                            f"  Concurso {contest}: avg={avg} max={max_h} recs={recs}"
                        )
                else:
                    contest = result.get("contest_number")
                    avg = result.get("hit_analysis", {}).get("average_hits", 0)
                    max_h = result.get("hit_analysis", {}).get("max_hits", 0)
                    print(f"[{MISSION_ID}] Feedback — Concurso {contest}")
                    print(f"  Média acertos: {avg}")
                    print(f"  Max acertos: {max_h}")
                    print(f"  Recomendações: {len(result.get('recommendations', []))}")
                    if result.get("persistence"):
                        print(
                            f"  Feedback ID: {result['persistence'].get('feedback_id')}"
                        )
            else:
                print(
                    f"[{MISSION_ID}] {result.get('status')}: {result.get('reason', 'unknown')}"
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
