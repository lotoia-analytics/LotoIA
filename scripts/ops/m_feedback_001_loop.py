#!/usr/bin/env python3
"""M-FEEDBACK-001 — Feedback loop pós-concurso oficial.

Após cada concurso oficial:
1. Carrega resultado oficial da lotofacil_official_history
2. Compara com jogos gerados (generated_games)
3. Calcula acertos por jogo
4. Identifica padrões de viés (prefixos excessivos, dezenas subcobertas)
5. Gera relatório de calibração para próxima geração
6. Persiste em feedback_loop (tabela nova)

Uso:
  python scripts/ops/m_feedback_001_loop.py --contest 3717 --json
  python scripts/ops/m_feedback_001_loop.py --latest --persist --json
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
MISSION_ID = "M-FEEDBACK-001"


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


def _ensure_feedback_loop_table() -> None:
    """Cria tabela feedback_loop se não existir."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

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


def analyze_hits(
    games: list[dict[str, Any]], official_numbers: list[int]
) -> dict[str, Any]:
    """Analisa acertos dos jogos gerados contra resultado oficial."""
    official_set = set(official_numbers)
    hit_counts = []
    per_game_hits = []

    for game in games:
        game_set = set(game.get("numbers", []))
        hits = len(game_set & official_set)
        hit_counts.append(hits)
        per_game_hits.append(
            {
                "game_index": game.get("game_index"),
                "generation_event_id": game.get("generation_event_id"),
                "hits": hits,
                "numbers": game.get("numbers", []),
            }
        )

    hit_distribution = Counter(hit_counts)
    average_hits = sum(hit_counts) / len(hit_counts) if hit_counts else 0.0

    return {
        "games_analyzed": len(games),
        "hit_distribution": {str(k): v for k, v in sorted(hit_distribution.items())},
        "average_hits": round(average_hits, 3),
        "max_hits": max(hit_counts) if hit_counts else 0,
        "min_hits": min(hit_counts) if hit_counts else 0,
        "per_game_hits": per_game_hits,
    }


def analyze_prefixes(
    games: list[dict[str, Any]], official_numbers: list[int]
) -> dict[str, Any]:
    """Analisa distribuição de prefixos nos jogos gerados."""
    prefix_counter = Counter()
    for game in games:
        numbers = sorted(game.get("numbers", []))
        if len(numbers) >= 3:
            prefix = tuple(numbers[:3])
            prefix_counter[prefix] += 1

    official_prefix = (
        tuple(sorted(official_numbers)[:3]) if len(official_numbers) >= 3 else ()
    )

    # Identifica prefixos excessivos
    excessive_prefixes = []
    for prefix, count in prefix_counter.most_common(10):
        if count >= 5:
            excessive_prefixes.append(
                {
                    "prefix": list(prefix),
                    "count": count,
                    "percentage": round(count / len(games) * 100, 2) if games else 0,
                }
            )

    return {
        "total_prefixes": len(prefix_counter),
        "most_common": [
            {"prefix": list(p), "count": c} for p, c in prefix_counter.most_common(10)
        ],
        "official_prefix": list(official_prefix),
        "official_prefix_in_games": prefix_counter.get(official_prefix, 0),
        "excessive_prefixes": excessive_prefixes,
    }


def analyze_dezena_frequency(
    games: list[dict[str, Any]], official_numbers: list[int]
) -> dict[str, Any]:
    """Analisa frequência de dezenas nos jogos gerados."""
    dezena_counter = Counter()
    for game in games:
        for number in game.get("numbers", []):
            dezena_counter[int(number)] += 1

    official_set = set(official_numbers)
    all_dezenas = set(range(1, 26))

    # Dezenas oficiais que apareceram pouco nos jogos
    undercovered_official = []
    for dezena in sorted(official_set):
        count = dezena_counter.get(dezena, 0)
        if count < len(games) * 0.3:  # Aparece em menos de 30% dos jogos
            undercovered_official.append({"dezena": dezena, "count": count})

    # Dezenas excessivamente usadas
    excessive_dezenas = []
    for dezena, count in dezena_counter.most_common(10):
        if count > len(games) * 0.8:  # Aparece em mais de 80% dos jogos
            excessive_dezenas.append({"dezena": dezena, "count": count})

    return {
        "dezena_frequency": {str(k): v for k, v in sorted(dezena_counter.items())},
        "undercovered_official_dezenas": undercovered_official,
        "excessive_dezenas": excessive_dezenas,
        "most_used_dezenas": [
            {"dezena": d, "count": c} for d, c in dezena_counter.most_common(10)
        ],
    }


def generate_bias_alerts(
    hit_analysis: dict[str, Any],
    prefix_analysis: dict[str, Any],
    dezena_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Gera alertas de viés estrutural."""
    alerts = []

    # Alerta: média de acertos baixa
    if hit_analysis.get("average_hits", 0) < 8.0:
        alerts.append(
            {
                "severity": "high",
                "category": "low_average_hits",
                "message": f"Média de acertos baixa: {hit_analysis.get('average_hits')}",
                "recommendation": "Revisar estratégia de geração — considerar mais dezenas quentes",
            }
        )

    # Alerta: prefixos excessivos
    excessive = prefix_analysis.get("excessive_prefixes", [])
    if excessive:
        alerts.append(
            {
                "severity": "medium",
                "category": "excessive_prefixes",
                "message": f"{len(excessive)} prefixos excessivamente repetidos",
                "recommendation": "Filtrar prefixos com >5 ocorrências na próxima geração",
                "details": excessive[:5],
            }
        )

    # Alerta: prefixo oficial ausente
    if prefix_analysis.get("official_prefix_in_games", 0) == 0:
        alerts.append(
            {
                "severity": "medium",
                "category": "official_prefix_absent",
                "message": "Prefixo oficial não apareceu nos jogos gerados",
                "recommendation": "Promover jogos com prefixo oficial na próxima geração",
                "official_prefix": prefix_analysis.get("official_prefix"),
            }
        )

    # Alerta: dezenas oficiais subcobertas
    undercovered = dezena_analysis.get("undercovered_official_dezenas", [])
    if undercovered:
        alerts.append(
            {
                "severity": "medium",
                "category": "undercovered_official_dezenas",
                "message": f"{len(undercovered)} dezenas oficiais subcobertas",
                "recommendation": "Aumentar peso de dezenas oficiais subcobertas",
                "details": undercovered[:10],
            }
        )

    return alerts


def generate_calibration_recommendations(
    bias_alerts: list[dict[str, Any]],
    hit_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Gera recomendações de calibração para próxima geração."""
    recommendations = []

    for alert in bias_alerts:
        category = alert.get("category", "")

        if category == "low_average_hits":
            recommendations.append(
                {
                    "action": "increase_hot_dezenas_weight",
                    "parameter": "hot_dezenas_boost",
                    "current_value": 1.0,
                    "suggested_value": 1.3,
                    "reason": "Média de acertos baixa — aumentar peso de dezenas quentes",
                }
            )

        elif category == "excessive_prefixes":
            recommendations.append(
                {
                    "action": "filter_excessive_prefixes",
                    "parameter": "max_prefix_occurrences",
                    "current_value": 10,
                    "suggested_value": 4,
                    "reason": "Prefixos excessivamente repetidos — reduzir limite",
                }
            )

        elif category == "official_prefix_absent":
            recommendations.append(
                {
                    "action": "promote_official_prefix",
                    "parameter": "official_prefix_boost",
                    "current_value": 0.0,
                    "suggested_value": 15.0,
                    "reason": "Prefixo oficial ausente — promover jogos com prefixo oficial",
                }
            )

        elif category == "undercovered_official_dezenas":
            recommendations.append(
                {
                    "action": "boost_undercovered_dezenas",
                    "parameter": "undercovered_dezenas_boost",
                    "current_value": 1.0,
                    "suggested_value": 1.5,
                    "reason": "Dezenas oficiais subcobertas — aumentar peso",
                }
            )

    return recommendations


def persist_feedback_loop(
    *,
    contest_number: int,
    official_numbers: list[int],
    generation_event_id: int | None,
    hit_analysis: dict[str, Any],
    prefix_analysis: dict[str, Any],
    dezena_analysis: dict[str, Any],
    bias_alerts: list[dict[str, Any]],
    calibration_recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persiste resultado do feedback loop no banco."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    _ensure_feedback_loop_table()

    feedback_data = {
        "official_numbers": official_numbers,
        "generation_event_id": generation_event_id,
        "hit_analysis": hit_analysis,
        "prefix_analysis": prefix_analysis,
        "dezena_analysis": dezena_analysis,
        "bias_alerts": bias_alerts,
        "calibration_recommendations": calibration_recommendations,
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


def run_feedback_loop(
    *,
    contest_number: int,
    persist: bool = False,
) -> dict[str, Any]:
    """Executa feedback loop completo para um concurso."""
    started = datetime.now(UTC)

    # Carrega resultado oficial
    official = load_official_contest(contest_number)
    if not official:
        return {
            "status": "error",
            "reason": "contest_not_found",
            "contest_number": contest_number,
        }

    # Carrega jogos gerados para esse concurso
    games = load_generated_games_for_contest(contest_number)
    if not games:
        return {
            "status": "warning",
            "reason": "no_games_for_contest",
            "contest_number": contest_number,
            "message": "Nenhum jogo gerado para este concurso",
        }

    # Análises
    hit_analysis = analyze_hits(games, official["numbers"])
    prefix_analysis = analyze_prefixes(games, official["numbers"])
    dezena_analysis = analyze_dezena_frequency(games, official["numbers"])

    # Gera alertas e recomendações
    bias_alerts = generate_bias_alerts(hit_analysis, prefix_analysis, dezena_analysis)
    calibration_recommendations = generate_calibration_recommendations(
        bias_alerts, hit_analysis
    )

    # Determina generation_event_id (usa o mais recente se houver múltiplos)
    generation_event_ids = list(
        {g.get("generation_event_id") for g in games if g.get("generation_event_id")}
    )
    generation_event_id = max(generation_event_ids) if generation_event_ids else None

    result = {
        "status": "success",
        "mission_id": MISSION_ID,
        "contest_number": contest_number,
        "official_numbers": official["numbers"],
        "draw_date": official.get("draw_date", ""),
        "generation_event_id": generation_event_id,
        "hit_analysis": hit_analysis,
        "prefix_analysis": prefix_analysis,
        "dezena_analysis": {
            "undercovered_official_dezenas": dezena_analysis.get(
                "undercovered_official_dezenas", []
            ),
            "excessive_dezenas": dezena_analysis.get("excessive_dezenas", []),
            "most_used_dezenas": dezena_analysis.get("most_used_dezenas", []),
        },
        "bias_alerts": bias_alerts,
        "calibration_recommendations": calibration_recommendations,
        "timestamp": started.isoformat(),
    }

    # Persiste se solicitado
    if persist:
        persistence_result = persist_feedback_loop(
            contest_number=contest_number,
            official_numbers=official["numbers"],
            generation_event_id=generation_event_id,
            hit_analysis=hit_analysis,
            prefix_analysis=prefix_analysis,
            dezena_analysis=dezena_analysis,
            bias_alerts=bias_alerts,
            calibration_recommendations=calibration_recommendations,
        )
        result["persistence"] = persistence_result

    return result


def run_feedback_loop_programmatic(
    *, contest_number: int | None = None, persist: bool = True
) -> dict[str, Any]:
    """Execute feedback loop programmatically (for scheduler integration).

    Args:
        contest_number: Specific contest to analyze. If None, uses latest.
        persist: Whether to persist results to feedback_loop table.

    Returns:
        Dictionary with feedback analysis results.
    """
    if contest_number is None:
        latest = load_latest_official_contest()
        if not latest:
            return {
                "status": "error",
                "reason": "no_official_contest",
                "mission_id": MISSION_ID,
            }
        contest_number = latest["contest_number"]

    try:
        return run_feedback_loop(contest_number=contest_number, persist=persist)
    except Exception as exc:
        return {
            "status": "error",
            "reason": "execution_failed",
            "error": str(exc),
            "contest_number": contest_number,
            "mission_id": MISSION_ID,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Feedback loop pós-concurso oficial"
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

        # Executa feedback loop
        result = run_feedback_loop(contest_number=contest_number, persist=args.persist)

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if result.get("status") == "success":
                print(f"[{MISSION_ID}] Feedback Loop — Concurso {contest_number}")
                print(
                    f"  Resultado oficial: {' '.join(f'{n:02d}' for n in result.get('official_numbers', []))}"
                )
                print(
                    f"  Jogos analisados: {result.get('hit_analysis', {}).get('games_analyzed', 0)}"
                )
                print(
                    f"  Média de acertos: {result.get('hit_analysis', {}).get('average_hits', 0)}"
                )
                print(
                    f"  Máximo de acertos: {result.get('hit_analysis', {}).get('max_hits', 0)}"
                )
                print(f"  Alertas de viés: {len(result.get('bias_alerts', []))}")
                print(
                    f"  Recomendações: {len(result.get('calibration_recommendations', []))}"
                )
                if result.get("persistence"):
                    print(f"  Feedback ID: {result['persistence'].get('feedback_id')}")
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
