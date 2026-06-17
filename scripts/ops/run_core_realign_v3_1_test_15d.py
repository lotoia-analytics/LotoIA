#!/usr/bin/env python3
"""Gera rodadas de STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001 (GP:50) e valida v3_1_applied.

Modo de uso:
  python scripts/ops/run_core_realign_v3_1_test_15d.py --generations 1
  python scripts/ops/run_core_realign_v3_1_test_15d.py --validate-only
  python scripts/ops/run_core_realign_v3_1_test_15d.py --target-total 20
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

os.environ.setdefault("LOTOIA_LEI15_CORE_REALIGNMENT_V3_1", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")
os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "off")

BATCH_LABEL = "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001"
GAMES_COUNT = 50
CARD_FORMAT = 15
OFFICIAL_GROUP = "G50"
STEP_TIMEOUT_S = 90
DEFAULT_LOT_TARGET = 20
PROTECTED_SLOTS = 12


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def _log(msg: str) -> None:
    print(f"[{_ts()}] {msg}", flush=True)


class _TimeoutError(RuntimeError):
    pass


def _run_with_timeout(fn, *, timeout_s: float, label: str):
    result_box: list[Any] = [None]
    exc_box: list[BaseException | None] = [None]

    def _target():
        try:
            result_box[0] = fn()
        except BaseException as exc:  # noqa: BLE001
            exc_box[0] = exc

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        raise _TimeoutError(f"[timeout] {label} > {timeout_s:.0f}s")
    if exc_box[0] is not None:
        raise exc_box[0]
    return result_box[0]


def _is_v3_1_applied(game: dict) -> bool:
    return bool(
        game.get("core_realignment_v3_1_applied") is True
        or (game.get("realignment_metadata") or {}).get("v3_1_applied") is True
    )


def _generate_games_progressive(*, seed: int, pool_steps: list[int]) -> tuple[list[dict], int]:
    from lotoia.generator.basic_generator import generate_best_games

    games: list[dict] = []
    used_pool = pool_steps[0]

    for pool_size in pool_steps:
        used_pool = pool_size

        def _gen(ps=pool_size):
            return generate_best_games(
                count=GAMES_COUNT,
                pool_size=ps,
                ml_enabled=False,
                seed=seed,
                batch_label=BATCH_LABEL,
            )

        try:
            result = _run_with_timeout(_gen, timeout_s=STEP_TIMEOUT_S, label=f"generate(pool={pool_size})")
            games = result.get("games") or []
        except _TimeoutError:
            _log(f"  TIMEOUT em pool={pool_size} ({STEP_TIMEOUT_S}s) — escalando")
            games = []
        except RuntimeError as exc:
            _log(f"  ERRO pool={pool_size}: {exc} — escalando")
            games = []

        v31 = sum(1 for g in games if _is_v3_1_applied(g))
        protected = sum(
            1 for g in games if (g.get("realignment_metadata") or {}).get("protected_top_score") is True
        )
        _log(f"  resultado: {len(games)} jogos | v3_1={v31} protected={protected}")

        if len(games) >= GAMES_COUNT:
            break

    return games, used_pool


def _persist(*, games: list[dict], seed: int, contest_number: int, created_by: str) -> dict:
    from lotoia.governance.analysis_batch_labels import build_batch_metadata
    from dashboard.institutional_app import _persist_generation_snapshot, _official_15_generation_context

    meta = build_batch_metadata(BATCH_LABEL, game_size=CARD_FORMAT, created_by=created_by, runtime_max_format=20)
    created_at_raw = meta.get("analysis_batch_created_at")
    created_at = (
        datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        if isinstance(created_at_raw, str)
        else created_at_raw
    )
    batch_id = f"core-v3_1-15d-c{contest_number}-{uuid.uuid4().hex[:8]}"
    ctx = {
        **dict(_official_15_generation_context(OFFICIAL_GROUP) or {}),
        **meta,
        "structural_test_mission": "MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A",
        "structural_test_contest": contest_number,
        "generation_mode": "LEI15_CORE_REALIGNMENT_V3_1_PROTECTED_SHADOW_TEST_HEADLESS",
        "core_realignment_v3_1_applied_count": sum(1 for g in games if _is_v3_1_applied(g)),
        "protected_top_score_count": sum(
            1 for g in games if (g.get("realignment_metadata") or {}).get("protected_top_score") is True
        ),
        "core_realignment_v3_1_applied": any(_is_v3_1_applied(g) for g in games),
        "protected_top_score_slots": PROTECTED_SLOTS,
    }
    snap = _persist_generation_snapshot(
        games=games,
        seed=int(seed),
        target_contest=int(contest_number),
        batch_id=batch_id,
        generation_context=ctx,
        analysis_batch_label=meta.get("analysis_batch_label"),
        analysis_batch_type=meta.get("analysis_batch_type"),
        analysis_batch_created_by=meta.get("analysis_batch_created_by"),
        analysis_batch_created_at=created_at,
    )
    _log(f"  persist: ge_id={snap.get('generation_event_id')}")
    return snap


def _count_existing_events(label: str = BATCH_LABEL) -> int:
    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM generation_events WHERE analysis_batch_label = %s",
                (label,),
            )
            row = cur.fetchone()
    return int(row[0] if row else 0)


def _resolve_generation_plan(*, generations: int, target_total: int | None, lot_target: int = DEFAULT_LOT_TARGET):
    existing = _count_existing_events()
    if target_total is not None:
        if target_total < 1:
            raise ValueError("--target-total deve ser >= 1")
        to_run = max(0, target_total - existing)
        return existing, to_run, existing + to_run
    if generations < 1:
        raise ValueError("--generations deve ser >= 1")
    final_total = existing + generations
    if final_total > lot_target:
        remaining = max(0, lot_target - existing)
        raise RuntimeError(
            f"Lote {BATCH_LABEL} ja tem {existing} event(s). "
            f"--generations {generations} fecharia com {final_total} (max {lot_target}). "
            f"Use --target-total {lot_target} ou --generations {remaining}."
        )
    return existing, generations, final_total


def _validate_db() -> dict:
    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  ge.analysis_batch_label,
                  COUNT(DISTINCT ge.id) AS total_events,
                  COUNT(gg.id) AS total_games,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"v3_1_applied": true%%'
                       OR gg.context_json::text ILIKE '%%"core_realignment_v3_1_applied": true%%'
                  ) AS games_v3_1_applied,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"protected_top_score": true%%'
                  ) AS games_protected,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"v3_applied": true%%'
                  ) AS games_v3_legacy
                FROM generation_events ge
                LEFT JOIN generated_games gg ON gg.generation_event_id = ge.id
                WHERE ge.analysis_batch_label = %s
                GROUP BY ge.analysis_batch_label
            """, (BATCH_LABEL,))
            row = cur.fetchone()

    batch = None
    if row:
        batch = {
            "label": row[0],
            "total": row[1],
            "games": row[2],
            "games_v3_1_applied": row[3],
            "games_protected": row[4],
            "games_v3_legacy": row[5],
        }
    ok = bool(
        batch
        and batch["total"] >= 1
        and batch["games"] >= GAMES_COUNT
        and batch["games_v3_1_applied"] == batch["games"]
        and batch["games_protected"] == batch["total"] * PROTECTED_SLOTS
        and batch["games_v3_legacy"] == 0
    )
    return {"validation_ok": ok, "batch": batch}


def _print_validation(val: dict) -> None:
    batch = val.get("batch")
    if not batch:
        _log(f"  Nenhum dado para {BATCH_LABEL}")
        return
    status = "OK" if val.get("validation_ok") else "CHECK"
    _log(
        f"  {batch['label']:<44} events={batch['total']:>3} games={batch['games']:>4} "
        f"v3_1={batch['games_v3_1_applied']:>4} protected={batch['games_protected']:>4} "
        f"v3_legacy={batch['games_v3_legacy']:>3} [{status}]"
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--contests", type=int, default=1)
    parser.add_argument("--generations", type=int, default=1)
    parser.add_argument("--target-total", type=int, default=0)
    parser.add_argument("--pool", type=int, default=0)
    parser.add_argument("--created-by", default="ops/run_core_realign_v3_1_test_15d")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    if args.validate_only:
        ensure_database_url(root=ROOT)
        _log("=== VALIDATE ONLY ===")
        val = _validate_db()
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    v31_mode = os.environ.get("LOTOIA_LEI15_CORE_REALIGNMENT_V3_1", "off")
    _log(f"LOTOIA_LEI15_CORE_REALIGNMENT_V3_1={v31_mode!r}")
    if v31_mode != "shadow_test":
        raise RuntimeError("V3.1 exige shadow_test. Active bloqueado.")

    ensure_database_url(root=ROOT)
    pool_steps = [args.pool] if args.pool > 0 else [100, 200]
    target_total = args.target_total if args.target_total > 0 else None
    existing, n_gens, final_total = _resolve_generation_plan(
        generations=args.generations,
        target_total=target_total,
    )

    if n_gens == 0:
        val = _validate_db()
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH
    from dashboard.institutional_app import get_official_contest, _load_official_history_rows

    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError("Requer PostgreSQL (DATABASE_URL).")

    rows_oficial = _load_official_history_rows(limit=args.contests, descending=True)
    contests = []
    for row in rows_oficial:
        n = int(row.get("concurso", 0) or 0)
        nums_str = str(row.get("dezenas_sorteadas", "") or "")
        nums = [int(t) for t in nums_str.split() if t.strip().lstrip("+").isdigit()]
        if n > 0 and len(nums) == 15:
            contests.append({"concurso": n})
    contests = sorted(contests, key=lambda x: x["concurso"])
    if len(contests) < args.contests:
        raise RuntimeError(f"Apenas {len(contests)} concursos validos.")

    base_seed = int(time.time()) % 1_000_000
    ge_ids = []

    for contest in contests:
        cn = int(contest["concurso"])
        official = get_official_contest(cn)
        if not official:
            raise RuntimeError(f"Concurso {cn} nao encontrado.")

        for run_i in range(1, n_gens + 1):
            global_run = existing + run_i
            seed = base_seed + cn * 10 + global_run
            _log(f"--- concurso={cn} run={global_run}/{final_total} seed={seed} ---")
            games, _ = _generate_games_progressive(seed=seed, pool_steps=pool_steps)
            if len(games) < GAMES_COUNT:
                raise RuntimeError(f"Falhou: gerados={len(games)}/{GAMES_COUNT}")
            snap = _persist(games=games, seed=seed, contest_number=cn, created_by=args.created_by)
            ge_ids.append(int(snap.get("generation_event_id", 0) or 0))

    val = _validate_db()
    _print_validation(val)
    _log(f"generation_event_ids={ge_ids}")
    return 0 if val["validation_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
