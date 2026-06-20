#!/usr/bin/env python3
"""M-CORE-003 — análise da distribuição histórica de prefixo3/sufixo3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lotoia.data.loader import DEFAULT_HISTORY_PATH, load_draws_csv
from lotoia.generation.m_core_003_prefix_suffix_policy import (
    ALLOWED_PREFIXES,
    ALLOWED_SUFFIXES,
    HISTORICAL_PREFIX_FREQ_PCT,
    HISTORICAL_SUFFIX_FREQ_PCT,
    MISSION_ID,
    compute_historical_distribution_from_draws,
    historical_pattern_cap,
)


def _top_patterns(distribution: dict[str, float], *, limit: int = 20) -> list[dict[str, object]]:
    rows = [
        {
            "pattern": pattern,
            "pct": pct,
            "cap": historical_pattern_cap(pct),
        }
        for pattern, pct in distribution.items()
    ]
    rows.sort(key=lambda row: float(row["pct"]), reverse=True)
    return rows[:limit]


def run(*, csv_path: Path, min_pct: float, json_out: Path | None) -> dict[str, object]:
    draws = load_draws_csv(csv_path)
    prefix_distribution = compute_historical_distribution_from_draws(draws, kind="prefix")
    suffix_distribution = compute_historical_distribution_from_draws(draws, kind="suffix")

    allowed_prefix = {
        pattern: pct
        for pattern, pct in prefix_distribution.items()
        if float(pct) >= min_pct
    }
    allowed_suffix = {
        pattern: pct
        for pattern, pct in suffix_distribution.items()
        if float(pct) >= min_pct
    }

    report = {
        "mission_id": MISSION_ID,
        "csv_path": str(csv_path),
        "draws_count": len(draws),
        "min_pct_threshold": min_pct,
        "prefix_top": _top_patterns(prefix_distribution),
        "suffix_top": _top_patterns(suffix_distribution),
        "allowed_prefix_count": len(allowed_prefix),
        "allowed_suffix_count": len(allowed_suffix),
        "reference_allowlist_prefix_count": len(ALLOWED_PREFIXES),
        "reference_allowlist_suffix_count": len(ALLOWED_SUFFIXES),
        "reference_tables": {
            "prefix": HISTORICAL_PREFIX_FREQ_PCT,
            "suffix": HISTORICAL_SUFFIX_FREQ_PCT,
        },
    }
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=MISSION_ID)
    parser.add_argument("--csv", type=Path, default=DEFAULT_HISTORY_PATH)
    parser.add_argument("--min-pct", type=float, default=1.0)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()
    report = run(csv_path=args.csv, min_pct=args.min_pct, json_out=args.json_out)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
