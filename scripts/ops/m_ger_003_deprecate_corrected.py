#!/usr/bin/env python3
"""M-GER-003 — Deprecar perfil 'corrected' e migrar para CORE_002.

Problema identificado: 494 jogos com profile_type='corrected' têm 0% taxa 11+.
Esses jogos vêm do M-GER-001 que não usa o pipeline CORE_002 completo.

Solução:
1. Marca generation_events com profile='corrected' como deprecated
2. Modifica M-GER-001 para usar CORE_002 sovereign path
3. Re-classifica jogos existentes com scoring CORE_002

Uso:
  python scripts/ops/m_ger_003_deprecate_corrected.py --analyze --json
  python scripts/ops/m_ger_003_deprecate_corrected.py --deprecate --json
  python scripts/ops/m_ger_003_deprecate_corrected.py --rescore --json
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
MISSION_ID = "M-GER-003"


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


def analyze_corrected_profile() -> dict[str, Any]:
    """Analisa jogos com profile_type='corrected'."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Estatísticas gerais
        stats = (
            session.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(DISTINCT generation_event_id) as total_events,
                    AVG((final_score->>'sum')::float) as avg_sum,
                    MIN((final_score->>'sum')::float) as min_sum,
                    MAX((final_score->>'sum')::float) as max_sum
                FROM generated_games
                WHERE profile_type = 'corrected'
                """
                )
            )
            .mappings()
            .first()
        )

        # Conferência (se houver)
        conference = (
            session.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as total_checked,
                    AVG(rg.hits)::float as avg_hits,
                    MAX(rg.hits) as max_hits,
                    SUM(CASE WHEN rg.hits >= 11 THEN 1 ELSE 0 END) as hits_11_plus
                FROM reconciliation_games rg
                JOIN generated_games gg ON gg.generation_event_id = rg.generation_event_id 
                    AND gg.game_index = rg.game_index
                WHERE gg.profile_type = 'corrected'
                """
                )
            )
            .mappings()
            .first()
        )

        # Events associados
        events = (
            session.execute(
                text(
                    """
                SELECT 
                    ge.id,
                    ge.created_at,
                    ge.context_json->>'generation_mode' as gen_mode,
                    COUNT(gg.id) as game_count
                FROM generation_events ge
                JOIN generated_games gg ON gg.generation_event_id = ge.id
                WHERE gg.profile_type = 'corrected'
                GROUP BY ge.id, ge.created_at, ge.context_json->>'generation_mode'
                ORDER BY ge.id
                """
                )
            )
            .mappings()
            .all()
        )

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "summary": {
            "total_games": int(stats["total_games"]),
            "total_events": int(stats["total_events"]),
            "avg_sum": round(float(stats["avg_sum"] or 0), 2),
            "min_sum": float(stats["min_sum"] or 0),
            "max_sum": float(stats["max_sum"] or 0),
        },
        "conference": {
            "total_checked": int(conference["total_checked"] or 0),
            "avg_hits": round(float(conference["avg_hits"] or 0), 2),
            "max_hits": int(conference["max_hits"] or 0),
            "hits_11_plus": int(conference["hits_11_plus"] or 0),
            "hit_rate_11_plus": round(
                float(conference["hits_11_plus"] or 0)
                / max(1, int(conference["total_checked"] or 1))
                * 100,
                2,
            ),
        },
        "events": [
            {
                "event_id": int(e["id"]),
                "created_at": str(e["created_at"]),
                "generation_mode": e["gen_mode"],
                "game_count": int(e["game_count"]),
            }
            for e in events
        ],
    }


def deprecate_corrected_events() -> dict[str, Any]:
    """Marca generation_events com profile='corrected' como deprecated."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    with get_session(DB_PATH) as session:
        # Busca events com jogos corrected
        event_ids = (
            session.execute(
                text(
                    """
                SELECT DISTINCT ge.id
                FROM generation_events ge
                JOIN generated_games gg ON gg.generation_event_id = ge.id
                WHERE gg.profile_type = 'corrected'
                """
                )
            )
            .scalars()
            .all()
        )

        # Marca como deprecated no context_json
        deprecated_count = 0
        for event_id in event_ids:
            session.execute(
                text(
                    """
                UPDATE generation_events
                SET context_json = jsonb_set(
                    COALESCE(context_json, '{}')::jsonb,
                    '{deprecated}',
                    'true'
                ) || jsonb_build_object(
                    'deprecated_reason', 'corrected_profile_0_percent_hit_rate',
                    'deprecated_at', CURRENT_TIMESTAMP::text,
                    'deprecated_by', :mission_id
                )
                WHERE id = :event_id
                """
                ),
                {"event_id": event_id, "mission_id": MISSION_ID},
            )
            deprecated_count += 1

        session.commit()

    return {
        "status": "success",
        "events_deprecated": deprecated_count,
        "event_ids": list(event_ids),
    }


def rescore_corrected_games() -> dict[str, Any]:
    """Re-classifica jogos corrected com scoring CORE_002."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    # Importa scoring
    from lotoia.statistics.scoring import score_candidate_from_history
    from lotoia.statistics.temporal import build_history_model

    with get_session(DB_PATH) as session:
        # Carrega histórico oficial
        history_rows = (
            session.execute(
                text(
                    """
                SELECT contest_number, numbers, draw_date
                FROM lotofacil_official_history
                ORDER BY contest_number DESC
                LIMIT 500
                """
                )
            )
            .mappings()
            .all()
        )

        # Constrói histórico
        from lotoia.models import DrawLike

        history = []
        for row in history_rows:
            numbers_str = str(row["numbers"] or "")
            numbers = [
                int(n.strip()) for n in numbers_str.split(",") if n.strip().isdigit()
            ]
            if len(numbers) == 15:
                history.append(
                    DrawLike(
                        contest=int(row["contest_number"]),
                        numbers=sorted(numbers),
                        draw_date=str(row["draw_date"] or ""),
                    )
                )

        # Busca jogos corrected
        games = (
            session.execute(
                text(
                    """
                SELECT id, numbers::text, profile_type, final_score
                FROM generated_games
                WHERE profile_type = 'corrected'
                ORDER BY id
                """
                )
            )
            .mappings()
            .all()
        )

        rescored_count = 0
        profile_changes = {}

        for game in games:
            numbers = json.loads(game["numbers"])
            if isinstance(numbers, str):
                numbers = json.loads(numbers)

            # Re-scoring com CORE_002
            score_result = score_candidate_from_history(numbers, history)
            new_profile = score_result["profile_type"]
            new_score = score_result["final_score"]

            # Atualiza no banco
            session.execute(
                text(
                    """
                UPDATE generated_games
                SET profile_type = :new_profile,
                    final_score = :new_score,
                    context_json = jsonb_set(
                        COALESCE(context_json, '{}')::jsonb,
                        '{rescored}',
                        'true'
                    ) || jsonb_build_object(
                        'rescored_at', CURRENT_TIMESTAMP::text,
                        'rescored_by', :mission_id,
                        'old_profile', :old_profile
                    )
                WHERE id = :game_id
                """
                ),
                {
                    "game_id": game["id"],
                    "new_profile": new_profile,
                    "new_score": json.dumps(new_score, default=str),
                    "mission_id": MISSION_ID,
                    "old_profile": game["profile_type"],
                },
            )
            rescored_count += 1
            profile_changes[new_profile] = profile_changes.get(new_profile, 0) + 1

        session.commit()

    return {
        "status": "success",
        "games_rescored": rescored_count,
        "profile_changes": profile_changes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Deprecar perfil 'corrected' e migrar para CORE_002"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Apenas analisa jogos corrected",
    )
    parser.add_argument(
        "--deprecate",
        action="store_true",
        help="Marca events corrected como deprecated",
    )
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Re-classifica jogos corrected com scoring CORE_002",
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        if args.analyze:
            result = analyze_corrected_profile()
        elif args.deprecate:
            result = deprecate_corrected_events()
        elif args.rescore:
            result = rescore_corrected_games()
        else:
            print(
                "Erro: especifique --analyze, --deprecate ou --rescore",
                file=sys.stderr,
            )
            return 1

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            if args.analyze:
                summary = result.get("summary", {})
                conference = result.get("conference", {})
                print(f"[{MISSION_ID}] Análise do Perfil 'corrected':")
                print(f"  Total de jogos: {summary.get('total_games')}")
                print(f"  Total de events: {summary.get('total_events')}")
                print(f"  Soma média: {summary.get('avg_sum')}")
                print(f"  Conferidos: {conference.get('total_checked')}")
                print(f"  Média acertos: {conference.get('avg_hits')}")
                print(f"  Max acertos: {conference.get('max_hits')}")
                print(f"  Taxa 11+: {conference.get('hit_rate_11_plus')}%")
                print()
                print(f"  Events associados: {len(result.get('events', []))}")
            elif args.deprecate:
                print(f"[{MISSION_ID}] Deprecação:")
                print(f"  Events deprecados: {result.get('events_deprecated')}")
            elif args.rescore:
                print(f"[{MISSION_ID}] Re-scoring:")
                print(f"  Jogos re-classificados: {result.get('games_rescored')}")
                print(f"  Mudanças de perfil: {result.get('profile_changes')}")

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
