#!/usr/bin/env python3
"""M-FEEDBACK-002 — Feedback loop automatizado pós-concurso.

Versão operacional sem import do dashboard/Streamlit para rodar no Railway shell.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSION_ID = "M-FEEDBACK-002"

from sqlalchemy import text
from lotoia.database.database import DEFAULT_DATABASE_PATH, get_session

DB_PATH = DEFAULT_DATABASE_PATH


def _ensure_feedback_loop_table() -> None:
    with get_session(DB_PATH) as session:
        session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS feedback_loop (
                    id SERIAL PRIMARY KEY,
                    contest_number INTEGER NOT NULL UNIQUE,
                    feedback_data JSONB NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        session.commit()


def _parse_numbers(raw: Any) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return sorted(int(n) for n in raw if str(n).strip().isdigit())
    value = str(raw).strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return sorted(int(n) for n in parsed if str(n).strip().isdigit())
    except Exception:
        pass
    return sorted(int(n.strip()) for n in value.split(",") if n.strip().isdigit())


def get_contests_without_feedback() -> list[int]:
    """Retorna concursos que têm jogos gerados, são oficiais e não têm feedback."""
    _ensure_feedback_loop_table()
    with get_session(DB_PATH) as session:
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
        contests_with_feedback = (
            session.execute(text("SELECT contest_number FROM feedback_loop"))
            .scalars()
            .all()
        )
        official_contests = (
            session.execute(text("SELECT contest_number FROM lotofacil_official_history"))
            .scalars()
            .all()
        )

    official_set = {int(c) for c in official_contests if c is not None}
    feedback_set = {int(c) for c in contests_with_feedback if c is not None}
    return sorted(
        int(c)
        for c in contests_with_games
        if c is not None and int(c) in official_set and int(c) not in feedback_set
    )


def load_official_contest(contest_number: int) -> dict[str, Any] | None:
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
    return {
        "contest_number": int(row["contest_number"]),
        "numbers": _parse_numbers(row["numbers"]),
        "draw_date": str(row["draw_date"] or ""),
    }


def load_generated_games_for_contest(target_contest: int) -> list[dict[str, Any]]:
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

    games: list[dict[str, Any]] = []
    for row in rows:
        games.append(
            {
                "id": int(row["id"]),
                "generation_event_id": int(row["generation_event_id"]),
                "game_index": int(row["game_index"]),
                "numbers": _parse_numbers(row["numbers"]),
                "profile_type": str(row["profile_type"] or ""),
                "final_score": row["final_score"] if isinstance(row["final_score"], dict) else {},
            }
        )
    return games


def analyze_hits_advanced(games: list[dict[str, Any]], official_numbers: list[int]) -> dict[str, Any]:
    official_set = set(official_numbers)
    hit_counts: list[int] = []
    per_profile_hits: dict[str, list[int]] = {}
    dezena_hit_freq: Counter[int] = Counter()

    for game in games:
        game_set = set(game.get("numbers", []))
        hits = len(game_set & official_set)
        hit_counts.append(hits)
        profile = str(game.get("profile_type") or "unknown")
        per_profile_hits.setdefault(profile, []).append(hits)
        for dezena in game_set & official_set:
            dezena_hit_freq[int(dezena)] += 1

    hit_distribution = Counter(hit_counts)
    average_hits = sum(hit_counts) / len(hit_counts) if hit_counts else 0.0
    profile_stats = {
        profile: {
            "count": len(values),
            "avg_hits": round(sum(values) / len(values), 2) if values else 0,
            "max_hits": max(values) if values else 0,
            "hits_11_plus": sum(1 for h in values if h >= 11),
        }
        for profile, values in per_profile_hits.items()
    }

    return {
        "games_analyzed": len(games),
        "hit_distribution": {str(k): v for k, v in sorted(hit_distribution.items())},
        "average_hits": round(average_hits, 3),
        "max_hits": max(hit_counts) if hit_counts else 0,
        "min_hits": min(hit_counts) if hit_counts else 0,
        "profile_stats": profile_stats,
        "top_hit_dezenas": [
            {"dezena": d, "hit_count": c} for d, c in dezena_hit_freq.most_common(10)
        ],
    }


def generate_smart_recommendations(hit_analysis: dict[str, Any], official_numbers: list[int]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    avg_hits = float(hit_analysis.get("average_hits", 0) or 0)
    profile_stats = hit_analysis.get("profile_stats", {}) or {}
    top_dezenas = hit_analysis.get("top_hit_dezenas", []) or []

    worst_profile = None
    worst_avg = 999.0
    for profile, stats in profile_stats.items():
        if int(stats.get("count", 0) or 0) >= 10 and float(stats.get("avg_hits", 0) or 0) < worst_avg:
            worst_avg = float(stats.get("avg_hits", 0) or 0)
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


def persist_feedback(*, contest_number: int, official_numbers: list[int], hit_analysis: dict[str, Any], recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    _ensure_feedback_loop_table()
    feedback_data = {
        "mission_id": MISSION_ID,
        "official_numbers": official_numbers,
        "hit_analysis": hit_analysis,
        "recommendations": recommendations,
        "version": "v2_smart_no_dashboard_import",
    }
    with get_session(DB_PATH) as session:
        row = session.execute(
            text(
                """
                INSERT INTO feedback_loop (contest_number, feedback_data)
                VALUES (:contest_number, :feedback_data)
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
        ).first()
        session.commit()
    return {"status": "persisted", "feedback_id": int(row[0]) if row else None}


def run_feedback_for_contest(contest_number: int, *, persist: bool = False) -> dict[str, Any]:
    started = datetime.now(UTC)
    official = load_official_contest(contest_number)
    if not official:
        return {"status": "error", "reason": "contest_not_found", "contest_number": contest_number}
    games = load_generated_games_for_contest(contest_number)
    if not games:
        return {"status": "warning", "reason": "no_games_for_contest", "contest_number": contest_number}

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
        result["persistence"] = persist_feedback(
            contest_number=contest_number,
            official_numbers=official["numbers"],
            hit_analysis=hit_analysis,
            recommendations=recommendations,
        )
    return result


def run_auto_feedback(*, persist: bool = False) -> dict[str, Any]:
    started = datetime.now(UTC)
    missing = get_contests_without_feedback()
    results = [run_feedback_for_contest(contest, persist=persist) for contest in missing]
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
    parser = argparse.ArgumentParser(description=f"{MISSION_ID} — Feedback loop automatizado pós-concurso")
    parser.add_argument("--auto", action="store_true", help="Processa todos os concursos pendentes")
    parser.add_argument("--contest", type=int, help="Concurso específico")
    parser.add_argument("--backfill", action="store_true", help="Equivalente a --auto")
    parser.add_argument("--persist", action="store_true", help="Persiste resultado no banco")
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        if args.auto or args.backfill:
            result = run_auto_feedback(persist=args.persist)
        elif args.contest:
            result = run_feedback_for_contest(args.contest, persist=args.persist)
        else:
            print("Erro: especifique --auto, --backfill ou --contest", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            print(f"[{MISSION_ID}] status={result.get('status')} concursos={result.get('contests_processed', 1)}")
        return 0
    except Exception as exc:
        error_result = {
            "status": "error",
            "mission_id": MISSION_ID,
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        print(json.dumps(error_result, indent=2, default=str, ensure_ascii=False)) if args.json else print(f"[{MISSION_ID}] Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
