#!/usr/bin/env python3
"""M-GER-001 — Geração corrigida com viés estrutural eliminado.

Gera jogos usando o path soberano LEI15_CORE_002 com correções de viés:
- Remove prefixos excessivos (01-02-05, 03-06-07, 01-02-06, 03-04-06)
- Promove prefixos oficiais raros ausentes (01-03-05, 03-04-05, 02-04-05, 01-03-07)
- Persiste em generation_events e generated_games

Uso:
  python scripts/ops/m_ger_001_corrected_generation.py --count 20 --json
  python scripts/ops/m_ger_001_corrected_generation.py --count 50 --target-contest 3718 --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MISSION_ID = "M-GER-001"

# Prefixos problemáticos identificados no relatório
EXCESSIVE_PREFIXES = [
    (1, 2, 5),
    (3, 6, 7),
    (1, 2, 6),
    (3, 4, 6),
]

# Prefixos oficiais raros que devem ser promovidos
RARE_OFFICIAL_PREFIXES = [
    (1, 3, 5),
    (3, 4, 5),
    (2, 4, 5),
    (1, 3, 7),
]


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


def _setup_environment() -> None:
    """Configura variáveis de ambiente para geração soberana."""
    os.environ.setdefault("LOTOIA_LEI15_CORE_002", "sovereign")
    os.environ.setdefault("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    os.environ.setdefault("LOTOIA_GENERATION_ENABLED", "1")


def _filter_excessive_prefixes(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove jogos com prefixos excessivamente repetidos."""
    filtered = []
    for game in games:
        numbers = sorted(game.get("numbers", []))
        if len(numbers) < 3:
            continue
        prefix = tuple(numbers[:3])
        if prefix in EXCESSIVE_PREFIXES:
            continue
        filtered.append(game)
    return filtered


def _promote_rare_prefixes(
    games: list[dict[str, Any]], target_count: int
) -> list[dict[str, Any]]:
    """Promove jogos com prefixos oficiais raros."""
    promoted = []
    for game in games:
        numbers = sorted(game.get("numbers", []))
        if len(numbers) < 3:
            continue
        prefix = tuple(numbers[:3])
        if prefix in RARE_OFFICIAL_PREFIXES:
            # Aumenta score para promover
            game["profile_score"] = float(game.get("profile_score", 0) or 0) + 15.0
            game["rare_prefix_promoted"] = True
        promoted.append(game)
    return promoted


def generate_corrected_games(
    *,
    count: int,
    target_contest: int | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Gera jogos corrigidos usando path soberano LEI15_CORE_002."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    _setup_environment()

    started = time.monotonic()
    if seed is None:
        seed = int(time.time_ns() % 1_000_000_000)

    # Importa módulos institucionais
    from dashboard.institutional_app import (
        _invoke_sovereign_adm_generate_best_games,
        _run_clean_law15_generation,
        get_latest_official_contest,
    )
    from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL

    # Determina target_contest
    if target_contest is None:
        latest = get_latest_official_contest() or {}
        latest_number = int(latest.get("contest_number", 0) or 0)
        target_contest = latest_number + 1 if latest_number > 0 else None

    # Gera pool maior para filtrar
    pool_size = max(count * 3, 60)
    sovereign_payload = _invoke_sovereign_adm_generate_best_games(
        requested_count=pool_size,
        batch_label=BATCH_LABEL,
        seed=seed,
    )

    if sovereign_payload.get("hierarchy_blocked"):
        return {
            "status": "blocked",
            "reason": "hierarchy_blocked",
            "message": str(sovereign_payload.get("hierarchy_block_message", "")),
        }

    games = list(sovereign_payload.get("games") or [])
    if not games:
        return {"status": "error", "reason": "no_games_generated"}

    # Aplica correções de viés
    games_filtered = _filter_excessive_prefixes(games)
    games_promoted = _promote_rare_prefixes(games_filtered, count)

    # Ordena por score e seleciona top N
    games_sorted = sorted(
        games_promoted,
        key=lambda g: float(g.get("profile_score", 0) or 0),
        reverse=True,
    )
    selected_games = games_sorted[:count]

    execution_time_ms = (time.monotonic() - started) * 1000

    return {
        "status": "success",
        "mission_id": MISSION_ID,
        "generation_event_id": None,  # Será preenchido após persistência
        "requested_count": count,
        "generated_count": len(games),
        "filtered_count": len(games_filtered),
        "promoted_count": sum(
            1 for g in selected_games if g.get("rare_prefix_promoted")
        ),
        "selected_count": len(selected_games),
        "games": selected_games,
        "target_contest": target_contest,
        "seed": seed,
        "batch_label": BATCH_LABEL,
        "execution_time_ms": round(execution_time_ms, 2),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def persist_generated_games(result: dict[str, Any]) -> dict[str, Any]:
    """Persiste jogos gerados no banco de dados."""
    if result.get("status") != "success":
        return {"status": "skipped", "reason": "generation_not_successful"}

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from sqlalchemy import text
    from dashboard.institutional_app import DB_PATH, get_session

    games = result.get("games", [])
    if not games:
        return {"status": "skipped", "reason": "no_games_to_persist"}

    target_contest = result.get("target_contest")
    seed = int(result.get("seed", 0) or 0)
    batch_label = str(result.get("batch_label", ""))

    with get_session(DB_PATH) as session:
        # Cria generation_event
        event_context = {
            "source": "m_ger_001_corrected_generation",
            "mission_id": MISSION_ID,
            "target_contest": target_contest,
            "batch_label": batch_label,
            "bias_correction_applied": True,
            "excessive_prefixes_filtered": len(result.get("games", []))
            - result.get("filtered_count", 0),
            "rare_prefixes_promoted": result.get("promoted_count", 0),
            "generation_hierarchy": "LOTOIA_LAW_ONLY",
            "scientific_law_role": "COMMANDER",
        }

        session.execute(
            text(
                """
                INSERT INTO generation_events (
                    lead_id, first_name, whatsapp, generated_games, seed, strategy,
                    ranking_score, execution_time_ms, ml_enabled, analysis_batch_label,
                    context_json, created_at
                ) VALUES (
                    NULL, 'm_ger_001_script', '', :generated_games, :seed, 'corrected_sovereign',
                    0.0, :execution_time_ms, 0, :batch_label,
                    :context_json, CURRENT_TIMESTAMP
                ) RETURNING id
                """
            ),
            {
                "generated_games": json.dumps(games, default=str),
                "seed": seed,
                "execution_time_ms": float(result.get("execution_time_ms", 0) or 0),
                "batch_label": batch_label,
                "context_json": json.dumps(event_context, default=str),
            },
        )
        generation_event_id = session.execute(text("SELECT LASTVAL()")).scalar()

        # Persiste jogos individuais
        for index, game in enumerate(games, start=1):
            numbers = list(game.get("numbers", []))
            session.execute(
                text(
                    """
                    INSERT INTO generated_games (
                        generation_event_id, lead_id, target_contest, origin, generation_mode,
                        game_index, numbers, profile_type, final_score, quadra_score, context_json, created_at
                    ) VALUES (
                        :generation_event_id, NULL, :target_contest, 'm_ger_001_script', 'corrected_sovereign',
                        :game_index, :numbers, :profile_type, :final_score, :quadra_score, :context_json, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {
                    "generation_event_id": generation_event_id,
                    "target_contest": target_contest,
                    "game_index": index,
                    "numbers": json.dumps(numbers),
                    "profile_type": str(game.get("profile_type", "")),
                    "final_score": json.dumps(game.get("final_score", {}), default=str),
                    "quadra_score": json.dumps(
                        game.get("quadra_score", {}), default=str
                    ),
                    "context_json": json.dumps(
                        {
                            "source": MISSION_ID,
                            "rare_prefix_promoted": bool(
                                game.get("rare_prefix_promoted")
                            ),
                            "generation_event_id": generation_event_id,
                        },
                        default=str,
                    ),
                },
            )

        session.commit()

    return {
        "status": "persisted",
        "generation_event_id": generation_event_id,
        "games_persisted": len(games),
        "target_contest": target_contest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"{MISSION_ID} — Geração corrigida com viés estrutural eliminado"
    )
    parser.add_argument(
        "--count", type=int, default=20, help="Quantidade de jogos a gerar"
    )
    parser.add_argument(
        "--target-contest",
        type=int,
        default=None,
        help="Concurso alvo (default: próximo)",
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Seed para reprodutibilidade"
    )
    parser.add_argument(
        "--persist", action="store_true", help="Persiste no banco de dados"
    )
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    args = parser.parse_args()

    try:
        # Gera jogos
        result = generate_corrected_games(
            count=args.count,
            target_contest=args.target_contest,
            seed=args.seed,
        )

        if result.get("status") != "success":
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"[{MISSION_ID}] Falha: {result.get('reason', 'unknown')}")
            return 1

        # Persiste se solicitado
        if args.persist:
            persistence_result = persist_generated_games(result)
            result["persistence"] = persistence_result
            if persistence_result.get("status") == "persisted":
                result["generation_event_id"] = persistence_result.get(
                    "generation_event_id"
                )

        if args.json:
            print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
        else:
            print(f"[{MISSION_ID}] Sucesso:")
            print(f"  Jogos gerados: {result.get('generated_count')}")
            print(f"  Jogos filtrados: {result.get('filtered_count')}")
            print(f"  Jogos promovidos: {result.get('promoted_count')}")
            print(f"  Jogos selecionados: {result.get('selected_count')}")
            if result.get("generation_event_id"):
                print(f"  Generation Event ID: {result.get('generation_event_id')}")
            print(f"  Target Contest: {result.get('target_contest')}")
            print(f"  Tempo: {result.get('execution_time_ms')}ms")

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
