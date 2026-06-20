#!/usr/bin/env python3
"""M-CORE-003 — validação walk-forward anti-viés prefixo/sufixo (10×10 jogos)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.generation.lei15_core_002 import build_sovereign_pool, compose_sovereign_gp
from lotoia.generation.m_core_003_prefix_suffix_policy import (
    HISTORICAL_PREFIX_FREQ_PCT,
    HISTORICAL_SUFFIX_FREQ_PCT,
    MISSION_ID,
    WALKFORWARD_VALIDATION_SEEDS,
    compare_pattern_ratios,
    compute_pattern_distribution,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, get_core_002_config


def _configure_runtime() -> None:
    os.environ.setdefault("LOTOIA_LEI15_CORE_002", "sovereign")
    os.environ.setdefault("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "active")
    os.environ.setdefault("LOTOIA_LEI15_CORE_CANDIDATE_001", "shadow_test")


def run(
    *,
    csv_path: Path,
    games_per_batch: int,
    pool_size: int,
    ratio_threshold: float,
    json_out: Path | None,
) -> dict[str, object]:
    _configure_runtime()
    history = load_draws_csv(csv_path)
    config = get_core_002_config(BATCH_LABEL)
    generated_cards: list[list[int]] = []
    batch_reports: list[dict[str, object]] = []

    for seed in WALKFORWARD_VALIDATION_SEEDS:
        pool = build_sovereign_pool(pool_size, seed=seed, history=history, config=config)
        gp = compose_sovereign_gp(pool, games_per_batch, config, game_size=15)
        cards = [list(game.get("numbers") or []) for game in gp]
        generated_cards.extend(cards)
        batch_reports.append(
            {
                "seed": seed,
                "pool_size": len(pool),
                "gp_size": len(gp),
            }
        )

    generated_prefix = compute_pattern_distribution(generated_cards, kind="prefix")
    generated_suffix = compute_pattern_distribution(generated_cards, kind="suffix")
    prefix_over = compare_pattern_ratios(
        generated_prefix,
        HISTORICAL_PREFIX_FREQ_PCT,
        ratio_threshold=ratio_threshold,
    )
    suffix_over = compare_pattern_ratios(
        generated_suffix,
        HISTORICAL_SUFFIX_FREQ_PCT,
        ratio_threshold=ratio_threshold,
    )
    critical = next((row for row in prefix_over if row["pattern"] == "01-04-06"), None)

    report = {
        "mission_id": MISSION_ID,
        "csv_path": str(csv_path),
        "batches": len(WALKFORWARD_VALIDATION_SEEDS),
        "games_per_batch": games_per_batch,
        "pool_size": pool_size,
        "total_generated_games": len(generated_cards),
        "ratio_threshold": ratio_threshold,
        "prefix_patterns_over_threshold": prefix_over,
        "suffix_patterns_over_threshold": suffix_over,
        "prefix_over_threshold_count": len(prefix_over),
        "suffix_over_threshold_count": len(suffix_over),
        "critical_pattern_01_04_06": critical,
        "batch_reports": batch_reports,
        "verdict": (
            "M-CORE-003 VALIDAÇÃO APROVADA"
            if critical is None or float(critical.get("ratio", 99.0)) < 3.0
            else "M-CORE-003 VIÉS RESIDUAL — revisar calibração"
        ),
    }
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=MISSION_ID)
    parser.add_argument("--csv", type=Path, default=DEFAULT_HISTORY_PATH)
    parser.add_argument("--games-per-batch", type=int, default=10)
    parser.add_argument("--pool-size", type=int, default=100)
    parser.add_argument("--ratio-threshold", type=float, default=2.0)
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path("reports/m_core_003_walkforward_validation.json"),
    )
    args = parser.parse_args()
    report = run(
        csv_path=args.csv,
        games_per_batch=args.games_per_batch,
        pool_size=args.pool_size,
        ratio_threshold=args.ratio_threshold,
        json_out=args.json_out,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
