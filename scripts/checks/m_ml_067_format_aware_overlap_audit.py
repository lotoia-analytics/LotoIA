#!/usr/bin/env python3
"""Auditoria M-ML-067 — distribuição de pares por overlap (format-aware 15D–23D)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, get_session
from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
from lotoia.ml.overlap_format_thresholds import (
    LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
    MISSION_ID_067,
    build_ml_format_aware_memory,
    classify_similarity_for_format,
)
from lotoia.statistics.card_structure import compute_gp_redundancy, resolve_cartao_final_from_game


def _resolve_cards(session, generation_event_id: int) -> tuple[list[list[int]], str, int]:
    event = session.query(GenerationEvent).filter(GenerationEvent.id == generation_event_id).one_or_none()
    if event is None:
        raise ValueError(f"generation_event_id={generation_event_id} não encontrado.")
    rows = (
        session.query(GeneratedGame)
        .filter(GeneratedGame.generation_event_id == generation_event_id)
        .order_by(GeneratedGame.game_index.asc())
        .all()
    )
    cards: list[list[int]] = []
    for row in rows:
        payload = {
            "numbers": list(row.numbers or []),
            "final_card_numbers": list((row.context_json or {}).get("final_card_numbers") or row.numbers or []),
        }
        card = resolve_cartao_final_from_game(payload)
        if card:
            cards.append(card)
    batch_label = str(getattr(event, "analysis_batch_label", "") or "")
    game_size = len(cards[0]) if cards else 0
    return cards, batch_label, game_size


def audit_generation_event(
    db_path: Path | str,
    *,
    generation_event_id: int | None = None,
    game_size: int = 17,
) -> dict:
    with get_session(db_path) as session:
        if generation_event_id:
            ge_id = int(generation_event_id)
        else:
            query = (
                session.query(GenerationEvent)
                .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            )
            event = None
            for candidate in query.limit(200):
                label = str(getattr(candidate, "analysis_batch_label", "") or "")
                if not is_sovereign_core_label(label):
                    continue
                cards, _, size = _resolve_cards(session, int(candidate.id))
                if cards and size == int(game_size):
                    event = candidate
                    break
            if event is None:
                raise ValueError(f"Nenhum lote {game_size}D CORE_002 encontrado.")
            ge_id = int(event.id)
        cards, batch_label, resolved_size = _resolve_cards(session, ge_id)

    redundancy = compute_gp_redundancy(cards, game_size=resolved_size or game_size)
    similarity = classify_similarity_for_format(
        float(redundancy.get("similaridade_media_entre_jogos", 0.0) or 0.0),
        resolved_size or game_size,
    )
    distribution = dict(redundancy.get("distribuicao_por_overlap") or {})
    size = int(resolved_size or game_size)
    buckets = {
        f"overlap_{size}": int(distribution.get(str(size), 0)),
        f"overlap_{size - 1}": int(distribution.get(str(size - 1), 0)),
        f"overlap_{size - 2}": int(distribution.get(str(size - 2), 0)),
        f"overlap_{size - 3}_ou_menor": sum(
            int(count) for key, count in distribution.items() if int(key) <= size - 3
        ),
    }
    return {
        "mission_id": MISSION_ID_067,
        "generation_event_id": ge_id,
        "analysis_batch_label": batch_label,
        "formato": f"{size}D",
        "quantidade_jogos": len(cards),
        "pares_possiveis": int(redundancy.get("pares_possiveis", 0) or 0),
        "legacy_threshold_overlap_15d": LEGACY_NEAR_DUPLICATE_OVERLAP_15D,
        "format_aware_critical_threshold": size - 1,
        "format_aware_attention_threshold": size - 2,
        "similaridade_media": float(redundancy.get("similaridade_media_entre_jogos", 0.0) or 0.0),
        "similarity_band": similarity,
        "sobreposicao_maxima": int(redundancy.get("sobreposicao_maxima", 0) or 0),
        "distribuicao_por_overlap": distribution,
        "buckets": buckets,
        "pares_clone_total": int(redundancy.get("pares_clone_total", 0) or 0),
        "pares_quase_clone": int(redundancy.get("pares_quase_clone", 0) or 0),
        "pares_atencao": int(redundancy.get("pares_atencao", 0) or 0),
        "pares_aceitavel": int(redundancy.get("pares_aceitavel", 0) or 0),
        "quase_repetidos_criticos": int(redundancy.get("quase_repetidos_criticos", 0) or 0),
        "legacy_near_duplicate_pairs_count": int(redundancy.get("legacy_near_duplicate_pairs_count", 0) or 0),
        "overlap_composition_rows": list(redundancy.get("overlap_composition_rows") or []),
        "ml_format_aware_memory": build_ml_format_aware_memory(),
        "overlap_15_em_17d_e_critico": (
            size == 17
            and int(redundancy.get("sobreposicao_maxima", 0) or 0) == 15
            and int(redundancy.get("quase_repetidos_criticos", 0) or 0)
            > int(distribution.get("16", 0) or 0) + int(distribution.get("17", 0) or 0)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoria M-ML-067 overlap format-aware")
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
    else:
        print(f"M-ML-067 audit — GE {report['generation_event_id']} ({report['formato']})")
        print(f"Jogos: {report['quantidade_jogos']} | Pares: {report['pares_possiveis']}")
        print(f"Similaridade média: {report['similaridade_media']:.4f} — {report['similarity_band']['band_label']}")
        print(f"Sobreposição máxima: {report['sobreposicao_maxima']}")
        print(f"Quase repetidos críticos: {report['quase_repetidos_criticos']}")
        print(f"Pares em atenção: {report['pares_atencao']}")
        print(f"Legado (overlap>=13): {report['legacy_near_duplicate_pairs_count']}")
        for row in report.get("overlap_composition_rows") or []:
            print(f"  Overlap {row.get('overlap')}: {row.get('pares')} — {row.get('classificacao')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
