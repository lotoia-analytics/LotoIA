#!/usr/bin/env python3
"""Reconcilia STRUCT_CORE_REALIGN_V3_BALANCED_15D_001 contra os 7 concursos baseline (3705-3711).

Garante que todos os 20 generation_events tenham reconciliation_runs para cada concurso.
Meta: 20 GEs × 7 concursos = 140 reconciliation_runs.

ADR: ADR-045-CORE-REALIGNMENT-V3-BALANCED
Missao: MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
"""

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

os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")

BATCH_LABEL = "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001"
TARGET_CONTESTS = [3705, 3706, 3707, 3708, 3709, 3710, 3711]
CARD_FORMAT = 15
EXPECTED_GES = 20
EXPECTED_TOTAL_RUNS = EXPECTED_GES * len(TARGET_CONTESTS)  # 140


def _ts() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


def _load_ge_and_games(conn) -> list[dict]:
    """Load all generation_events and their games for BATCH_LABEL."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, context_json
            FROM generation_events
            WHERE analysis_batch_label = %s
            ORDER BY id
        """, (BATCH_LABEL,))
        ge_rows = cur.fetchall()

    _log(f"generation_events: {len(ge_rows)}")
    if len(ge_rows) == 0:
        raise RuntimeError(f"Nenhum GE para {BATCH_LABEL}. Rode o script de geração primeiro.")

    result = []
    for ge_id, ctx in ge_rows:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT game_index, numbers
                FROM generated_games
                WHERE generation_event_id = %s
                ORDER BY game_index
            """, (ge_id,))
            game_rows = cur.fetchall()

        games = []
        for game_index, numbers in game_rows:
            nums = list(numbers) if isinstance(numbers, list) else numbers
            games.append({
                "generation_event_id": ge_id,
                "game_index": game_index,
                "numbers": nums,
                "final_card_numbers": nums,
                "core_numbers": nums,
                "formato_cartao": CARD_FORMAT,
                "card_format": CARD_FORMAT,
                "selected_card_format": CARD_FORMAT,
            })

        result.append({"ge_id": ge_id, "games": games})

    return result


def _existing_runs(conn) -> set[tuple[int, int]]:
    """Return set of (ge_id, contest_id) already reconciled."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ge.id, rr.contest_id
            FROM reconciliation_runs rr
            JOIN generation_events ge ON ge.id = rr.generation_event_id
            WHERE ge.analysis_batch_label = %s
        """, (BATCH_LABEL,))
        return {(row[0], row[1]) for row in cur.fetchall()}


def _load_contest_id(conn, concurso: int) -> int | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM contests WHERE contest_number = %s", (concurso,))
        row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    import psycopg
    from dashboard.institutional_app import _compare_games_against_contest, get_official_contest

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]
    t_start = time.monotonic()

    with psycopg.connect(url) as conn:
        # Pre-validation
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) AS total,
                       COUNT(*) FILTER (WHERE context_json::text ILIKE '%%core_realignment_v3_applied%%true%%') AS v3_true
                FROM generation_events
                WHERE analysis_batch_label = %s
            """, (BATCH_LABEL,))
            row = cur.fetchone()
        total_ges, v3_true = row
        _log(f"Pre-validacao: total_ges={total_ges} v3_applied_true={v3_true}")

        if total_ges < EXPECTED_GES:
            _log(f"AVISO: apenas {total_ges}/{EXPECTED_GES} GEs. Complete a geracao primeiro.")

        ges = _load_ge_and_games(conn)
        existing = _existing_runs(conn)
        _log(f"existing reconciliation_runs: {len(existing)}")

    # Build reconciliation tasks
    tasks: list[tuple[dict, dict]] = []
    for ge_data in ges:
        ge_id = ge_data["ge_id"]
        for concurso in TARGET_CONTESTS:
            official = get_official_contest(concurso)
            if not official:
                _log(f"AVISO: concurso {concurso} não encontrado — pulando")
                continue
            contest_id = int(official.get("id", 0) or 0)
            if (ge_id, contest_id) in existing:
                _log(f"  SKIP ge_id={ge_id} concurso={concurso} (já reconciliado)")
                continue
            tasks.append((ge_data, official))

    _log(f"\nTarefas pendentes: {len(tasks)} de {EXPECTED_TOTAL_RUNS} esperadas")

    created = 0
    for ge_data, official in tasks:
        ge_id = ge_data["ge_id"]
        games = ge_data["games"]
        concurso = official.get("concurso") or official.get("contest_number")
        t0 = time.monotonic()
        result = _compare_games_against_contest(
            generation_event_id=ge_id,
            games=games,
            contest=official,
        )
        elapsed = time.monotonic() - t0
        _log(f"  ge_id={ge_id} concurso={concurso} best_hits={result.get('best_hits')} [{elapsed:.2f}s]")
        created += 1

    _log(f"\nCriados: {created} reconciliation_runs")

    # Post-validation
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT rr.id)
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s
            """, (BATCH_LABEL,))
            total_runs = cur.fetchone()[0]

    ok = total_runs >= EXPECTED_TOTAL_RUNS
    elapsed_total = time.monotonic() - t_start
    _log(f"\nPos-validacao: {total_runs}/{EXPECTED_TOTAL_RUNS} reconciliation_runs em {elapsed_total:.2f}s")

    if ok:
        _log(f"[APROVADO] {total_runs}/{EXPECTED_TOTAL_RUNS} runs confirmadas para {BATCH_LABEL}")
    else:
        _log(f"[PENDENTE] apenas {total_runs}/{EXPECTED_TOTAL_RUNS} — rode novamente para completar")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
