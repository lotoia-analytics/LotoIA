#!/usr/bin/env python3
"""Gera rodadas de STRUCT_CORE_REALIGN_V2_15D_001 (GP:50) e valida core_realignment_v2_applied.

Modo de uso:
  python scripts/ops/run_core_realign_v2_test_15d.py                     # 1 geracao
  python scripts/ops/run_core_realign_v2_test_15d.py --generations 20   # fechar lote completo
  python scripts/ops/run_core_realign_v2_test_15d.py --validate-only    # validar DB

ADR: ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A
Missao: MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Feature flags V2 (shadow_test) + V1 (shadow_test — needed for observable metadata)
os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")

BATCH_LABEL = "STRUCT_CORE_REALIGN_V2_15D_001"
GAMES_COUNT = 50
CARD_FORMAT = 15
OFFICIAL_GROUP = "G50"
STEP_TIMEOUT_S = 90  # V2 may need slightly more time due to pool pre-filter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Generation — direto em generate_best_games com V2 ativo
# ---------------------------------------------------------------------------

def _generate_games_progressive(*, seed: int, pool_steps: list[int]) -> tuple[list[dict], int]:
    """Tenta gerar GAMES_COUNT jogos com pool_size progressivo."""
    from lotoia.generator.basic_generator import generate_best_games

    games: list[dict] = []
    used_pool = pool_steps[0]

    for pool_size in pool_steps:
        used_pool = pool_size
        t0 = time.monotonic()
        _log(f"  gerando: count={GAMES_COUNT} pool_size={pool_size} seed={seed} ...")

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

        elapsed = time.monotonic() - t0
        v2_applied = sum(
            1 for g in games
            if g.get("core_realignment_v2_applied") is True
            or (g.get("realignment_metadata") or {}).get("core_realignment_v2_applied") is True
        )
        v1_applied = sum(
            1 for g in games
            if (g.get("realignment_metadata") or {}).get("realignment_applied") is True
        )
        _log(f"  resultado: {len(games)} jogos em {elapsed:.2f}s | v2_applied={v2_applied} v1_applied={v1_applied}")

        if len(games) >= GAMES_COUNT:
            break

    return games, used_pool


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist(*, games: list[dict], seed: int, contest_number: int, created_by: str) -> dict:
    from datetime import UTC, datetime
    from lotoia.governance.analysis_batch_labels import build_batch_metadata
    from dashboard.institutional_app import _persist_generation_snapshot, _official_15_generation_context

    t0 = time.monotonic()
    meta = build_batch_metadata(BATCH_LABEL, game_size=CARD_FORMAT, created_by=created_by, runtime_max_format=20)
    created_at_raw = meta.get("analysis_batch_created_at")
    created_at = (
        datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        if isinstance(created_at_raw, str) else created_at_raw
    )
    batch_id = f"core-v2-15d-c{contest_number}-{uuid.uuid4().hex[:8]}"
    ctx = {
        **dict(_official_15_generation_context(OFFICIAL_GROUP) or {}),
        **meta,
        "structural_test_mission": "MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A",
        "structural_test_contest": contest_number,
        "generation_mode": "CORE_REALIGN_V2_SHADOW_TEST_HEADLESS",
        "core_realignment_v2_applied_count": sum(
            1 for g in games
            if g.get("core_realignment_v2_applied") is True
            or (g.get("realignment_metadata") or {}).get("core_realignment_v2_applied") is True
        ),
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
    _log(f"  persist: ge_id={snap.get('generation_event_id')} em {time.monotonic()-t0:.2f}s")
    return snap


def _reconcile(*, gen_event_id: int, games: list[dict], contest: dict) -> dict:
    from dashboard.institutional_app import _compare_games_against_contest
    t0 = time.monotonic()
    prepared = []
    for i, g in enumerate(games, 1):
        p = dict(g)
        p["generation_event_id"] = gen_event_id
        p["game_index"] = i
        p["formato_cartao"] = CARD_FORMAT
        p["card_format"] = CARD_FORMAT
        p["selected_card_format"] = CARD_FORMAT
        p.setdefault("final_card_numbers", list(p.get("numbers", []) or []))
        p.setdefault("core_numbers", list(p.get("numbers", []) or []))
        prepared.append(p)
    result = _compare_games_against_contest(
        generation_event_id=gen_event_id, games=prepared, contest=contest
    )
    _log(f"  reconcile: best_hits={result.get('best_hits')} em {time.monotonic()-t0:.2f}s")
    return result


# ---------------------------------------------------------------------------
# Validation query
# ---------------------------------------------------------------------------

def _validate_db() -> dict:
    import psycopg
    t0 = time.monotonic()
    url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  analysis_batch_label,
                  COUNT(*) AS total_events,
                  COUNT(*) FILTER (
                    WHERE context_json::text ILIKE '%%core_realignment_v2_applied%%true%%'
                  ) AS v2_applied_true,
                  COUNT(*) FILTER (
                    WHERE context_json::text ILIKE '%%realignment_applied%%true%%'
                  ) AS v1_applied_true
                FROM generation_events
                WHERE analysis_batch_label LIKE 'STRUCT_CORE_REALIGN_V2_%%'
                GROUP BY analysis_batch_label
                ORDER BY analysis_batch_label
            """)
            rows = cur.fetchall()
    results = [
        {"label": r[0], "total": r[1], "v2_applied_true": r[2], "v1_applied_true": r[3]}
        for r in rows
    ]
    ok = any(r["label"] == BATCH_LABEL and r["v2_applied_true"] > 0 for r in results)
    _log(f"  validate_db: {time.monotonic()-t0:.2f}s")
    return {"rows": results, "validation_ok": ok}


def _print_validation(val: dict) -> None:
    if not val["rows"]:
        _log("  Nenhum dado para STRUCT_CORE_REALIGN_V2_*")
        return
    for r in val["rows"]:
        status = "OK - V2 confirmado" if r["v2_applied_true"] > 0 else "FALHA - v2_applied_true=0"
        _log(
            f"  {r['label']:<40}  total={r['total']:>3}  "
            f"v2_applied={r['v2_applied_true']:>3}  v1_applied={r['v1_applied_true']:>3}  [{status}]"
        )
    if val["validation_ok"]:
        _log(f"[RESULTADO] core_realignment_v2_applied=true CONFIRMADO para {BATCH_LABEL}")
    else:
        _log(f"[RESULTADO] FALHA: v2_applied_true=0 para {BATCH_LABEL}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--contests", type=int, default=1)
    parser.add_argument("--generations", type=int, default=1)
    parser.add_argument("--pool", type=int, default=0, help="pool_size inicial (0=progressivo [50,100,200])")
    parser.add_argument("--created-by", default="ops/run_core_realign_v2_test_15d")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    t_start = time.monotonic()

    if args.validate_only:
        _log("=== VALIDATE ONLY ===")
        val = _validate_db()
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    # flag check
    v2_mode = os.environ.get("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2", "off")
    v1_mode = os.environ.get("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    _log(f"LOTOIA_LEI15_15A_CORE_REALIGNMENT_V2={v2_mode!r}")
    _log(f"LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1={v1_mode!r}")
    if v2_mode not in ("shadow_test", "active"):
        raise RuntimeError(f"V2 flag inativa: {v2_mode!r}. Defina shadow_test ou active.")

    # pool steps
    pool_steps = [args.pool] if args.pool > 0 else [50, 100, 200]

    n_gens = args.generations
    n_contests = args.contests

    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH
    from dashboard.institutional_app import DB_PATH, get_official_contest, _load_official_history_rows

    t0 = time.monotonic()
    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError("Requer PostgreSQL. Configure DATABASE_URL.")
    _log(f"backend=postgresql ({time.monotonic()-t0:.2f}s)")

    t0 = time.monotonic()
    rows_oficial = _load_official_history_rows(limit=n_contests, descending=True)
    contests = []
    for row in rows_oficial:
        n = int(row.get("concurso", 0) or 0)
        nums_str = str(row.get("dezenas_sorteadas", "") or "")
        nums = [int(t) for t in nums_str.split() if t.strip().lstrip("+").isdigit()]
        if n > 0 and len(nums) == 15:
            contests.append({"concurso": n})
    contests = sorted(contests, key=lambda x: x["concurso"])
    _log(f"concursos={[c['concurso'] for c in contests]} ({time.monotonic()-t0:.2f}s)")

    if len(contests) < n_contests:
        raise RuntimeError(f"Apenas {len(contests)} concursos válidos ({n_contests} necessários).")

    _log(f"\n=== {BATCH_LABEL} | v2_mode={v2_mode} | gens={n_gens} | pool_steps={pool_steps} | GP={GAMES_COUNT} ===\n")

    base_seed = int(time.time()) % 1_000_000
    ge_ids = []
    report_events = []

    for contest in contests:
        cn = int(contest["concurso"])
        official = get_official_contest(cn)
        if not official:
            raise RuntimeError(f"Concurso {cn} não encontrado.")

        for run_i in range(1, n_gens + 1):
            seed = base_seed + cn * 10 + run_i
            t_run = time.monotonic()
            _log(f"--- concurso={cn} run={run_i}/{n_gens} seed={seed} ---")

            games, used_pool = _generate_games_progressive(seed=seed, pool_steps=pool_steps)

            if len(games) < GAMES_COUNT:
                raise RuntimeError(f"Falhou após todos os steps. gerados={len(games)}/{GAMES_COUNT}")

            snap = _persist(games=games, seed=seed, contest_number=cn, created_by=args.created_by)
            ge_id = int(snap.get("generation_event_id", 0) or 0)
            ge_ids.append(ge_id)

            rec = _reconcile(gen_event_id=ge_id, games=games, contest=official)
            t_run_total = time.monotonic() - t_run
            _log(f"run concluída: ge_id={ge_id} best_hits={rec.get('best_hits')} total={t_run_total:.2f}s\n")

            report_events.append({
                "ge_id": ge_id,
                "contest": cn,
                "run": run_i,
                "pool_used": used_pool,
                "games": len(games),
                "best_hits": rec.get("best_hits"),
                "elapsed_s": round(t_run_total, 2),
            })

    _log(f"generation_event_ids={ge_ids}")
    _log("\n=== QUERY DE VALIDAÇÃO ===")
    val = _validate_db()
    _print_validation(val)

    elapsed_total = time.monotonic() - t_start
    _log(f"\n=== CONCLUÍDO em {elapsed_total:.2f}s ===")

    if args.json_out:
        out = {
            "batch_label": BATCH_LABEL,
            "generation_event_ids": ge_ids,
            "events": report_events,
            "validation": val,
            "elapsed_s": round(elapsed_total, 2),
        }
        print(json.dumps(out, indent=2, default=str))

    return 0 if val["validation_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
