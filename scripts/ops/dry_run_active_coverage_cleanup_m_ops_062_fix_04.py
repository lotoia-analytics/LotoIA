#!/usr/bin/env python3
"""Dry-run da limpeza lógica da leitura ativa da Cobertura Estrutural (M-OPS-062-FIX-04)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lotoia.database.database import DEFAULT_DATABASE_PATH  # noqa: E402
from lotoia.governance.batch_operational_scope import (  # noqa: E402
    apply_active_coverage_logical_cleanup,
    dry_run_active_coverage_cleanup,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run limpeza lógica Cobertura ativa")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument("--apply", action="store_true", help="Aplica limpeza lógica (sem purge)")
    parser.add_argument("--limit", type=int, default=500, help="Máximo de eventos analisados")
    args = parser.parse_args()

    if args.apply:
        report = apply_active_coverage_logical_cleanup(
            DEFAULT_DATABASE_PATH,
            dry_run=False,
            limit=args.limit,
        )
    else:
        report = dry_run_active_coverage_cleanup(DEFAULT_DATABASE_PATH, limit=args.limit)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"M-OPS-062-FIX-04: {'APPLY' if args.apply else 'DRY-RUN'}")
        print(f"  candidates: {report.get('candidates_count', 0)}")
        for row in (report.get("candidates") or [])[:20]:
            print(
                f"  GE {row.get('generation_event_id')} | "
                f"{row.get('analysis_batch_label')} | "
                f"{row.get('games_count')} jogos | "
                f"{row.get('exclusion_reason')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
