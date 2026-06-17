#!/usr/bin/env python3
"""Piloto Core Candidate 001 — STRUCT_LEI15_CORE_CANDIDATE_001_15D_001 (variant A: N-C4+N-C5).

Uso:
  python scripts/ops/run_core_candidate_001_test_15d.py --generations 1
  python scripts/ops/run_core_candidate_001_test_15d.py --validate-only
  python scripts/ops/run_core_candidate_001_test_15d.py --pilot-hits-check
  python scripts/ops/run_core_candidate_001_test_15d.py --variant B --generations 1
"""

from __future__ import annotations

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

os.environ.setdefault("LOTOIA_LEI15_CORE_CANDIDATE_001", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
os.environ.setdefault("LOTOIA_LEI15_CORE_REALIGNMENT_V4", "off")
os.environ.setdefault("LOTOIA_LEI15_CORE_REALIGNMENT_V3_1", "off")
os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "off")
os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2", "off")

VARIANT_LABELS = {
    "A": "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001",
    "B": "STRUCT_LEI15_CORE_CANDIDATE_001_B_15D_001",
    "C": "STRUCT_LEI15_CORE_CANDIDATE_001_C_15D_001",
    "D": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
}
GAMES_COUNT = 50
CARD_FORMAT = 15
OFFICIAL_GROUP = "G50"
STEP_TIMEOUT_S = 120
DEFAULT_LOT_TARGET = 20
TARGET_CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
BASELINE_AVG = 9.286
BASELINE_LABEL = "STRUCT_TEST_15D_001"
PILOT_GATE_BEST_HIT = 13
PILOT_GATE_RUNS_13_PLUS = 1


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


def _batch_label(variant: str) -> str:
    key = variant.strip().upper()
    if key not in VARIANT_LABELS:
        raise ValueError(f"Variant invalida: {variant!r}. Use A, B, C ou D.")
    return VARIANT_LABELS[key]


def _is_candidate_applied(game: dict) -> bool:
    return bool(game.get("core_candidate_001_applied") is True)


def _generate_games_progressive(*, batch_label: str, seed: int, pool_steps: list[int]) -> tuple[list[dict], int]:
    from lotoia.generator.basic_generator import generate_best_games

    used_pool = pool_steps[0]
    for pool_size in pool_steps:
        used_pool = pool_size
        _log(f"  gerando: pool_size={pool_size} seed={seed} label={batch_label}")

        def _gen(ps=pool_size):
            return generate_best_games(
                count=GAMES_COUNT,
                pool_size=ps,
                ml_enabled=False,
                seed=seed,
                batch_label=batch_label,
            )

        result = _run_with_timeout(_gen, timeout_s=STEP_TIMEOUT_S, label=f"generate(pool={pool_size})")
        games = result.get("games") or []
        _log(
            f"  resultado: {len(games)} jogos | candidate={sum(1 for g in games if _is_candidate_applied(g))}"
        )
        if len(games) >= GAMES_COUNT:
            break
    return games, used_pool


def _persist(*, batch_label: str, games: list[dict], seed: int, contest_number: int, created_by: str) -> dict:
    from lotoia.governance.analysis_batch_labels import build_batch_metadata
    from dashboard.institutional_app import _persist_generation_snapshot, _official_15_generation_context

    meta = build_batch_metadata(batch_label, game_size=CARD_FORMAT, created_by=created_by, runtime_max_format=20)
    created_at_raw = meta.get("analysis_batch_created_at")
    created_at = (
        datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        if isinstance(created_at_raw, str)
        else created_at_raw
    )
    ctx = {
        **dict(_official_15_generation_context(OFFICIAL_GROUP) or {}),
        **meta,
        "structural_test_mission": "ADR_NUCLEO_LEI15_CANDIDATE_001",
        "structural_test_contest": contest_number,
        "generation_mode": "LEI15_CORE_CANDIDATE_001_SHADOW_TEST_HEADLESS",
        "core_candidate_001_applied_count": sum(1 for g in games if _is_candidate_applied(g)),
        "core_candidate_001_applied": any(_is_candidate_applied(g) for g in games),
    }
    snap = _persist_generation_snapshot(
        games=games,
        seed=int(seed),
        target_contest=int(contest_number),
        batch_id=f"core-candidate-001-15d-c{contest_number}-{uuid.uuid4().hex[:8]}",
        generation_context=ctx,
        analysis_batch_label=meta.get("analysis_batch_label"),
        analysis_batch_type=meta.get("analysis_batch_type"),
        analysis_batch_created_by=meta.get("analysis_batch_created_by"),
        analysis_batch_created_at=created_at,
    )
    _log(f"  persist: ge_id={snap.get('generation_event_id')}")
    return snap


def _count_existing_events(batch_label: str) -> int:
    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM generation_events WHERE analysis_batch_label = %s",
                (batch_label,),
            )
            row = cur.fetchone()
    return int(row[0] if row else 0)


def _validate_db(batch_label: str) -> dict:
    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(DISTINCT ge.id), COUNT(gg.id),
                       COUNT(gg.id) FILTER (
                         WHERE gg.context_json::text ILIKE '%%"core_candidate_001_applied": true%%'
                       ),
                       COUNT(gg.id) FILTER (
                         WHERE gg.context_json::text ILIKE '%%"profile_relabeling_applied": true%%'
                       )
                FROM generation_events ge
                LEFT JOIN generated_games gg ON gg.generation_event_id = ge.id
                WHERE ge.analysis_batch_label = %s
                """,
                (batch_label,),
            )
            total, games, candidate, relabeled = cur.fetchone()

    batch = {
        "label": batch_label,
        "total": int(total or 0),
        "games": int(games or 0),
        "games_candidate": int(candidate or 0),
        "games_relabeled": int(relabeled or 0),
    }
    ok = bool(
        batch["total"] >= 1
        and batch["games"] >= GAMES_COUNT
        and batch["games_candidate"] == batch["games"]
        and batch["games_relabeled"] == 0
    )
    return {"validation_ok": ok, "batch": batch}


def _print_validation(val: dict) -> None:
    batch = val.get("batch") or {}
    status = "OK" if val.get("validation_ok") else "CHECK"
    _log(
        f"  {batch.get('label', ''):<46} events={batch.get('total', 0):>3} "
        f"games={batch.get('games', 0):>4} candidate={batch.get('games_candidate', 0):>4} "
        f"relabel={batch.get('games_relabeled', 0):>3} [{status}]"
    )


def _structural_metrics(batch_label: str) -> dict[str, float]:
    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT gg.numbers FROM generated_games gg
                JOIN generation_events ge ON ge.id = gg.generation_event_id
                WHERE ge.analysis_batch_label = %s
                """,
                (batch_label,),
            )
            rows = cur.fetchall()
    from collections import Counter

    p3c: Counter = Counter()
    s3c: Counter = Counter()
    for (numbers,) in rows:
        if not isinstance(numbers, list) or len(numbers) != 15:
            continue
        nums = sorted(int(x) for x in numbers)
        p3c[tuple(nums[:3])] += 1
        s3c[tuple(nums[-3:])] += 1
    total = sum(p3c.values()) or 1
    tp = p3c.most_common(1)[0]
    ts = s3c.most_common(1)[0]
    return {
        "p3_pct": tp[1] / total * 100,
        "s3_pct": ts[1] / total * 100,
        "p3_key": tp[0],
        "s3_key": ts[0],
    }


def _pilot_hits_check(batch_label: str) -> int:
    import subprocess

    _log("=== PILOT CHECK CANDIDATE 001 ===")
    val = _validate_db(batch_label)
    _print_validation(val)
    if not val.get("validation_ok"):
        return 1

    struct = _structural_metrics(batch_label)
    baseline = _structural_metrics(BASELINE_LABEL)
    _log(
        f"  estrutura candidate p3={struct['p3_key']}({struct['p3_pct']:.1f}%) "
        f"s3={struct['s3_key']}({struct['s3_pct']:.1f}%)"
    )
    _log(
        f"  estrutura baseline p3={baseline['p3_pct']:.1f}% s3={baseline['s3_pct']:.1f}%"
    )

    rc = subprocess.call(
        [
            sys.executable,
            str(ROOT / "scripts" / "ops" / "reconcile_core_candidate_001_baseline_contests.py"),
            "--batch-label",
            batch_label,
        ],
        cwd=str(ROOT),
    )
    if rc != 0:
        return rc

    import psycopg

    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rr.best_hits
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s AND rr.contest_id = ANY(%s)
                """,
                (batch_label, list(TARGET_CONTESTS)),
            )
            hits = [int(row[0]) for row in cur.fetchall()]

    if not hits:
        _log("[PILOT] nenhuma reconciliation_run")
        return 1

    best = max(hits)
    avg = sum(hits) / len(hits)
    runs_13 = sum(1 for h in hits if h >= 13)
    checks = [
        ("jogos invalidos = 0", val["validation_ok"]),
        ("profile relabeling = 0", val["batch"]["games_relabeled"] == 0),
        ("prefixo 01-02-03 < baseline", struct["p3_pct"] < baseline["p3_pct"]),
        ("sufixo 22-24-25 controlado", struct["s3_pct"] <= baseline["s3_pct"] + 5),
        (f"melhor hit >= {PILOT_GATE_BEST_HIT}", best >= PILOT_GATE_BEST_HIT),
        (f"media > {BASELINE_AVG}", avg > BASELINE_AVG),
        (f"runs 13+ >= {PILOT_GATE_RUNS_13_PLUS}", runs_13 >= PILOT_GATE_RUNS_13_PLUS),
    ]
    _log(f"  runs={len(hits)} melhor={best} media={avg:.3f} runs_13+={runs_13}")
    passed = 0
    for name, ok in checks:
        _log(f"  [{'OK' if ok else 'PENDENTE'}] {name}")
        passed += int(ok)
    _log(f"[PILOT] {passed}/{len(checks)}")
    return 0 if passed == len(checks) else 1


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="A", choices=["A", "B", "C", "D"])
    parser.add_argument("--contests", type=int, default=1)
    parser.add_argument("--generations", type=int, default=1)
    parser.add_argument("--target-total", type=int, default=0)
    parser.add_argument("--pool", type=int, default=0)
    parser.add_argument("--created-by", default="ops/run_core_candidate_001_test_15d")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pilot-hits-check", action="store_true")
    args = parser.parse_args()

    batch_label = _batch_label(args.variant)

    if args.pilot_hits_check:
        ensure_database_url(root=ROOT)
        return _pilot_hits_check(batch_label)

    if args.validate_only:
        ensure_database_url(root=ROOT)
        _log("=== VALIDATE ONLY ===")
        val = _validate_db(batch_label)
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    if os.environ.get("LOTOIA_LEI15_CORE_CANDIDATE_001", "off") != "shadow_test":
        raise RuntimeError("Candidate 001 exige LOTOIA_LEI15_CORE_CANDIDATE_001=shadow_test")

    ensure_database_url(root=ROOT)
    existing = _count_existing_events(batch_label)
    target_total = args.target_total if args.target_total > 0 else None
    if target_total is not None:
        n_gens = max(0, target_total - existing)
        final_total = target_total
    else:
        n_gens = args.generations
        final_total = existing + n_gens
        if final_total > DEFAULT_LOT_TARGET and existing >= DEFAULT_LOT_TARGET:
            raise RuntimeError(f"Lote {batch_label} ja tem {existing} events.")

    if n_gens == 0:
        val = _validate_db(batch_label)
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH
    from dashboard.institutional_app import get_official_contest, _load_official_history_rows

    if evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH).backend != "postgresql":
        raise RuntimeError("Requer PostgreSQL.")

    pool_steps = [args.pool] if args.pool > 0 else [100, 200]
    rows_oficial = _load_official_history_rows(limit=args.contests, descending=True)
    contests = []
    for row in rows_oficial:
        n = int(row.get("concurso", 0) or 0)
        nums_str = str(row.get("dezenas_sorteadas", "") or "")
        nums = [int(t) for t in nums_str.split() if t.strip().lstrip("+").isdigit()]
        if n > 0 and len(nums) == 15:
            contests.append({"concurso": n})
    contests = sorted(contests, key=lambda x: x["concurso"])

    base_seed = int(time.time()) % 1_000_000
    ge_ids = []
    for contest in contests:
        cn = int(contest["concurso"])
        official = get_official_contest(cn)
        if not official:
            raise RuntimeError(f"Concurso {cn} nao encontrado.")
        for run_i in range(1, n_gens + 1):
            seed = base_seed + cn * 10 + existing + run_i
            _log(f"--- variant={args.variant} concurso={cn} run={existing + run_i}/{final_total} ---")
            games, _ = _generate_games_progressive(batch_label=batch_label, seed=seed, pool_steps=pool_steps)
            if len(games) < GAMES_COUNT:
                raise RuntimeError(f"Falhou: {len(games)}/{GAMES_COUNT}")
            snap = _persist(
                batch_label=batch_label,
                games=games,
                seed=seed,
                contest_number=cn,
                created_by=args.created_by,
            )
            ge_ids.append(int(snap.get("generation_event_id", 0) or 0))

    val = _validate_db(batch_label)
    _print_validation(val)
    _log(f"generation_event_ids={ge_ids}")
    return 0 if val["validation_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
