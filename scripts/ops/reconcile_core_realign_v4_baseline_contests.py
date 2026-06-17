#!/usr/bin/env python3
"""Reconcilia STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001 contra baseline 3705-3711."""

from __future__ import annotations

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

os.environ.setdefault("LOTOIA_LEI15_CORE_REALIGNMENT_V4", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")

BATCH_LABEL = "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001"
TARGET_CONTESTS = [3705, 3706, 3707, 3708, 3709, 3710, 3711]
CARD_FORMAT = 15
LOT_TARGET_GES = 20


def _ts() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _load_ge_and_games(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM generation_events WHERE analysis_batch_label = %s ORDER BY id",
            (BATCH_LABEL,),
        )
        ge_rows = cur.fetchall()
    if not ge_rows:
        raise RuntimeError(f"Nenhum GE para {BATCH_LABEL}. Rode run_core_realign_v4_test_15d.py primeiro.")

    result = []
    for (ge_id,) in ge_rows:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT game_index, numbers FROM generated_games
                WHERE generation_event_id = %s ORDER BY game_index
                """,
                (ge_id,),
            )
            game_rows = cur.fetchall()
        games = []
        for game_index, numbers in game_rows:
            nums = list(numbers) if isinstance(numbers, list) else numbers
            games.append(
                {
                    "generation_event_id": ge_id,
                    "game_index": game_index,
                    "numbers": nums,
                    "final_card_numbers": nums,
                    "core_numbers": nums,
                    "formato_cartao": CARD_FORMAT,
                    "card_format": CARD_FORMAT,
                    "selected_card_format": CARD_FORMAT,
                }
            )
        result.append({"ge_id": ge_id, "games": games})
    _log(f"generation_events: {len(result)}")
    return result


def _existing_runs(conn) -> set[tuple[int, int]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ge.id, rr.contest_id
            FROM reconciliation_runs rr
            JOIN generation_events ge ON ge.id = rr.generation_event_id
            WHERE ge.analysis_batch_label = %s
            """,
            (BATCH_LABEL,),
        )
        return {(row[0], row[1]) for row in cur.fetchall()}


def main() -> int:
    import psycopg
    from dashboard.institutional_app import _compare_games_against_contest, get_official_contest

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]
    t_start = time.monotonic()

    with psycopg.connect(url) as conn:
        ges = _load_ge_and_games(conn)
        existing = _existing_runs(conn)
        _log(f"existing reconciliation_runs: {len(existing)}")

    expected_runs = len(ges) * len(TARGET_CONTESTS)
    tasks: list[tuple[dict, dict]] = []
    for ge_data in ges:
        ge_id = ge_data["ge_id"]
        for concurso in TARGET_CONTESTS:
            official = get_official_contest(concurso)
            if not official:
                continue
            if (ge_id, int(concurso)) in existing:
                continue
            tasks.append((ge_data, official))

    _log(f"Tarefas pendentes: {len(tasks)} de {expected_runs}")
    for ge_data, official in tasks:
        ge_id = ge_data["ge_id"]
        concurso = official.get("contest_number") or official.get("concurso")
        result = _compare_games_against_contest(
            generation_event_id=ge_id,
            games=ge_data["games"],
            contest=official,
        )
        _log(f"  ge_id={ge_id} concurso={concurso} best_hits={result.get('best_hits')}")

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(DISTINCT rr.id)
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s
                """,
                (BATCH_LABEL,),
            )
            total_runs = cur.fetchone()[0]

    lot_ok = len(ges) >= LOT_TARGET_GES and total_runs >= LOT_TARGET_GES * len(TARGET_CONTESTS)
    partial_ok = total_runs >= expected_runs
    _log(f"Pos-validacao: {total_runs}/{expected_runs} em {time.monotonic()-t_start:.2f}s")
    if lot_ok:
        _log(f"[APROVADO LOTE] {BATCH_LABEL} {len(ges)}/{LOT_TARGET_GES} GEs")
    elif partial_ok:
        _log(f"[APROVADO PARCIAL] {BATCH_LABEL} ({len(ges)} GE(s))")
    else:
        _log(f"[PENDENTE] {BATCH_LABEL}")
    return 0 if partial_ok else 1


if __name__ == "__main__":
    sys.exit(main())
