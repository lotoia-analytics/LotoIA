#!/usr/bin/env python3
"""Reconcilia lotes STRUCT_LEI15_CORE_CANDIDATE_001_* contra baseline 3705-3711."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

os.environ.setdefault("LOTOIA_LEI15_CORE_CANDIDATE_001", "shadow_test")

DEFAULT_BATCH_LABEL = "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001"
TARGET_CONTESTS = [3705, 3706, 3707, 3708, 3709, 3710, 3711]
CARD_FORMAT = 15


def _ts() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-label", default=DEFAULT_BATCH_LABEL)
    args = parser.parse_args()

    import psycopg
    from dashboard.institutional_app import _compare_games_against_contest, get_official_contest

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM generation_events WHERE analysis_batch_label = %s ORDER BY id",
                (args.batch_label,),
            )
            ge_rows = cur.fetchall()
            cur.execute(
                """
                SELECT ge.id, rr.contest_id FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s
                """,
                (args.batch_label,),
            )
            existing = {(a, b) for a, b in cur.fetchall()}

    if not ge_rows:
        raise RuntimeError(f"Nenhum GE para {args.batch_label}")

    for (ge_id,) in ge_rows:
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT game_index, numbers FROM generated_games WHERE generation_event_id = %s ORDER BY game_index",
                    (ge_id,),
                )
                game_rows = cur.fetchall()
        games = [
            {
                "generation_event_id": ge_id,
                "game_index": gi,
                "numbers": list(nums) if isinstance(nums, list) else nums,
                "final_card_numbers": list(nums) if isinstance(nums, list) else nums,
                "core_numbers": list(nums) if isinstance(nums, list) else nums,
                "formato_cartao": CARD_FORMAT,
                "card_format": CARD_FORMAT,
                "selected_card_format": CARD_FORMAT,
            }
            for gi, nums in game_rows
        ]
        for concurso in TARGET_CONTESTS:
            if (ge_id, int(concurso)) in existing:
                continue
            official = get_official_contest(concurso)
            if not official:
                continue
            result = _compare_games_against_contest(
                generation_event_id=ge_id, games=games, contest=official
            )
            _log(f"ge_id={ge_id} concurso={concurso} best_hits={result.get('best_hits')}")

    _log(f"[OK] reconcile {args.batch_label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
