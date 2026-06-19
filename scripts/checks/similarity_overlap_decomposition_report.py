#!/usr/bin/env python3
"""Relatório CLI da decomposição de similaridade média — M-STAT-002 diagnóstico."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from typing import Any

from lotoia.generator.basic_generator import _attach_scores, _build_game
from lotoia.statistics.diverse_top_slice_selection import (
    _score_based_slice,
    apply_diverse_top_slice_pre_gp,
    slice_limit,
)
from lotoia.statistics.similarity_overlap_decomposition import (
    decompose_pool_similarity,
    format_similarity_decomposition_report,
)


def _unique_cards_with_fixed_numbers(
    count: int,
    *,
    fixed: tuple[int, ...],
    tail_pool: tuple[int, ...] = tuple(range(4, 26)),
) -> list[list[int]]:
    fixed_set = set(fixed)
    available = sorted(value for value in tail_pool if value not in fixed_set)
    head_needed = 15 - len(fixed_set)
    cards: list[list[int]] = []
    for combo in combinations(available, head_needed):
        cards.append(sorted(list(combo) + list(fixed)))
        if len(cards) >= count:
            break
    return cards


def build_blocked_like_pool(*, pool_size: int = 100, requested_count: int = 20) -> list[dict[str, Any]]:
    """Pool sintético calibrado para ~9.47 overlap médio no top-60 (GP:20)."""
    prefix = (1, 2, 3)
    core = (7, 12, 16, 23)
    high_freq_tail = (20, 21, 22, 24)
    dominant_count = 55
    diverse_count = pool_size - dominant_count

    dominant_cards = _unique_cards_with_fixed_numbers(
        dominant_count,
        fixed=prefix + core + high_freq_tail,
        tail_pool=tuple(range(4, 20)),
    )
    diverse_cards = _unique_cards_with_fixed_numbers(
        diverse_count,
        fixed=(4, 5, 6, 8, 9, 10, 11, 13, 14, 15, 17, 18, 19, 25),
        tail_pool=tuple(range(1, 26)),
    )

    pool: list[dict[str, Any]] = []
    for index, numbers in enumerate(dominant_cards):
        game = _build_game(numbers)
        game["profile_score"] = 1200 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    for index, numbers in enumerate(diverse_cards):
        game = _build_game(numbers)
        game["profile_score"] = 200 - index
        _attach_scores(game, profile_type="recorrente")
        pool.append(game)
    pool.sort(key=lambda row: float(row.get("profile_score", 0.0) or 0.0), reverse=True)
    _ = requested_count
    return pool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requested-count", type=int, default=20)
    parser.add_argument("--pool-size", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Saída JSON em vez de relatório texto")
    parser.add_argument(
        "--apply-mstat-002",
        action="store_true",
        help="Aplica M-STAT-002 antes da decomposição do slice final",
    )
    parser.add_argument(
        "--previous-draw",
        type=str,
        default="",
        help="15 dezenas do concurso anterior separadas por espaço/vírgula",
    )
    args = parser.parse_args(argv)

    previous_numbers: list[int] | None = None
    if args.previous_draw.strip():
        tokens = [token.strip() for token in args.previous_draw.replace(",", " ").split() if token.strip()]
        previous_numbers = [int(token) for token in tokens]

    pool = build_blocked_like_pool(pool_size=args.pool_size, requested_count=args.requested_count)
    limit = slice_limit(requested_count=args.requested_count)

    if args.apply_mstat_002:
        pool, bundle = apply_diverse_top_slice_pre_gp(
            pool,
            game_size=15,
            requested_count=args.requested_count,
            previous_contest_numbers=previous_numbers,
        )
        top_slice = pool[:limit]
        decomposition = dict(bundle.get("similarity_decomposition_after") or {})
        label = "after_mstat_002"
    else:
        top_slice = _score_based_slice(pool, limit=limit)
        decomposition = decompose_pool_similarity(
            top_slice,
            game_size=15,
            previous_contest_numbers=previous_numbers,
        )
        label = "score_top_slice"

    if args.json:
        payload = {"label": label, "slice_size": len(top_slice), "decomposition": decomposition}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"=== Decomposição similaridade ({label}, n={len(top_slice)}) ===")
    print(format_similarity_decomposition_report(decomposition))
    return 0


if __name__ == "__main__":
    sys.exit(main())
