#!/usr/bin/env python3
"""Auditoria M-ML-068 — concentração estrutural 17D (prefixos, sufixos, cobertura, diversidade)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, get_session
from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
from lotoia.ml.structural_concentration_audit import MISSION_ID, audit_structural_concentration
from lotoia.observability.card_structure_diagnostics import _load_official_cards
from lotoia.statistics.card_structure import resolve_cartao_final_from_game


def _serialize_game(row: GeneratedGame) -> dict[str, Any]:
    context = dict(row.context_json or {})
    numbers = [int(number) for number in (row.numbers or [])]
    return {
        "game_index": int(row.game_index or 0),
        "numbers": numbers,
        "final_card_numbers": list(context.get("final_card_numbers") or numbers),
        "core_numbers": list(context.get("core_numbers") or []),
        "audited_reserve_numbers": list(context.get("audited_reserve_numbers") or []),
        "origin": str(getattr(row, "origin", "") or ""),
        "profile_type": str(getattr(row, "profile_type", "") or ""),
        "generation_mode": str(getattr(row, "generation_mode", "") or ""),
        "decision_trace": dict(context.get("decision_trace") or {}),
    }


def _resolve_event(
    session,
    *,
    generation_event_id: int | None,
    game_size: int,
) -> tuple[GenerationEvent, list[dict[str, Any]], list[list[int]]]:
    if generation_event_id:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == int(generation_event_id)).one_or_none()
        if event is None:
            raise ValueError(f"generation_event_id={generation_event_id} não encontrado.")
    else:
        event = None
        for candidate in (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(200)
        ):
            label = str(getattr(candidate, "analysis_batch_label", "") or "")
            if not is_sovereign_core_label(label):
                continue
            rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == int(candidate.id))
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            games = [_serialize_game(row) for row in rows]
            cards = [resolve_cartao_final_from_game(game) for game in games]
            cards = [card for card in cards if card]
            if cards and len(cards[0]) == int(game_size):
                event = candidate
                break
        if event is None:
            raise ValueError(f"Nenhum lote {game_size}D CORE_002 encontrado no PostgreSQL.")

    rows = (
        session.query(GeneratedGame)
        .filter(GeneratedGame.generation_event_id == int(event.id))
        .order_by(GeneratedGame.game_index.asc())
        .all()
    )
    games = [_serialize_game(row) for row in rows]
    cards = [resolve_cartao_final_from_game(game) for game in games]
    cards = [card for card in cards if card]
    return event, games, cards


def audit_generation_event(
    db_path: Path | str,
    *,
    generation_event_id: int | None = None,
    game_size: int = 17,
) -> dict[str, Any]:
    with get_session(db_path) as session:
        event, games, cards = _resolve_event(
            session,
            generation_event_id=generation_event_id,
            game_size=game_size,
        )
        official_cards, _ = _load_official_cards(session, limit=50)
        event_context = dict(getattr(event, "context_json", {}) or {})

    resolved_size = len(cards[0]) if cards else int(game_size)
    report = audit_structural_concentration(
        games,
        game_size=resolved_size,
        event_context=event_context,
        official_cards=official_cards,
        generation_event_id=int(event.id),
    )
    report["analysis_batch_label"] = str(getattr(event, "analysis_batch_label", "") or "")
    report["strategy"] = str(getattr(event, "strategy", "") or "")
    report["ml_enabled"] = bool(getattr(event, "ml_enabled", 0))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria M-ML-068 concentração estrutural")
    parser.add_argument("--db", default=str(DEFAULT_DATABASE_PATH))
    parser.add_argument("--generation-event-id", type=int, default=None)
    parser.add_argument("--game-size", type=int, default=17)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_generation_event(
        args.db,
        generation_event_id=args.generation_event_id,
        game_size=args.game_size,
    )
    if args.json:
        print(json.dumps(report, indent=2, default=str))
        return 0

    diag = dict(report.get("diagnostico") or {})
    prefix = dict((report.get("prefixos_sufixos") or {}).get("prefixo_mais_dominante") or {})
    suffix = dict((report.get("prefixos_sufixos") or {}).get("sufixo_mais_dominante") or {})
    print(f"{MISSION_ID} — GE {report.get('generation_event_id')} ({report.get('formato')})")
    print(f"Jogos: {report.get('quantidade_jogos')} | Similaridade: {report.get('similaridade_media', 0):.4f}")
    print(f"Diversidade: {report.get('diversity_score', 0):.4f} | Subcobertas: {report.get('cobertura_dezenas', {}).get('subcobertura_count', 0)}")
    if prefix:
        print(
            f"Prefixo dominante: {prefix.get('estrutura')} — {prefix.get('frequencia')}/{prefix.get('total')} "
            f"({prefix.get('share_pct')}%) [{prefix.get('level_label')}]"
        )
    if suffix:
        print(
            f"Sufixo dominante: {suffix.get('estrutura')} — {suffix.get('frequencia')}/{suffix.get('total')} "
            f"({suffix.get('share_pct')}%) [{suffix.get('level_label')}]"
        )
    print(f"Causa provável: {diag.get('problema_detectado')}")
    for item in diag.get("acoes_recomendadas") or []:
        print(f"  → {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
