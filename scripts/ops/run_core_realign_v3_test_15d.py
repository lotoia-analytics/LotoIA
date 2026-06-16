#!/usr/bin/env python3
"""Gera rodadas de STRUCT_CORE_REALIGN_V3_BALANCED_15D_001 (GP:50) e valida core_realignment_v3_applied.

Modo de uso:
  # Teste inicial (1ª geração do lote)
  python scripts/ops/run_core_realign_v3_test_15d.py --generations 1
  python scripts/ops/run_core_realign_v3_test_15d.py --validate-only

  # Completar lote até 20 events totais (recomendado após validar 1x)
  python scripts/ops/run_core_realign_v3_test_15d.py --target-total 20

  # Ou manualmente, se já existir 1 event: --generations 19 (NÃO --generations 20)

ADR: ADR-045-CORE-REALIGNMENT-V3-BALANCED
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
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, normalize_database_url, resolve_database_url

# Feature flags V3 (shadow_test) + V1 (shadow_test — needed for observable metadata)
os.environ.setdefault("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "shadow_test")
os.environ.setdefault("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "shadow_test")

BATCH_LABEL = "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001"
GAMES_COUNT = 50
CARD_FORMAT = 15
OFFICIAL_GROUP = "G50"
STEP_TIMEOUT_S = 90  # V3 balanced compose
DEFAULT_LOT_TARGET = 20


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
# Generation — direto em generate_best_games com V3 BALANCED ativo
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
        v3_applied = sum(
            1 for g in games
            if g.get("core_realignment_v3_applied") is True
            or (g.get("realignment_metadata") or {}).get("core_realignment_v3_applied") is True
        )
        v1_applied = sum(
            1 for g in games
            if (g.get("realignment_metadata") or {}).get("realignment_applied") is True
        )
        _log(f"  resultado: {len(games)} jogos em {elapsed:.2f}s | v3_applied={v3_applied} v1_applied={v1_applied}")

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
    batch_id = f"core-v3-15d-c{contest_number}-{uuid.uuid4().hex[:8]}"
    ctx = {
        **dict(_official_15_generation_context(OFFICIAL_GROUP) or {}),
        **meta,
        "structural_test_mission": "MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A",
        "structural_test_contest": contest_number,
        "generation_mode": "CORE_REALIGN_V3_BALANCED_SHADOW_TEST_HEADLESS",
        "core_realignment_v3_applied_count": sum(
            1 for g in games
            if g.get("core_realignment_v3_applied") is True
            or (g.get("realignment_metadata") or {}).get("v3_applied") is True
        ),
        "pool_pre_filter_applied_count": sum(
            1 for g in games
            if (g.get("realignment_metadata") or {}).get("pool_pre_filter_applied") is True
        ),
        "v3_fallback_to_v1_count": sum(
            1 for g in games
            if (g.get("realignment_metadata") or {}).get("v3_fallback_to_v1") is True
        ),
        "core_realignment_v3_applied": any(
            g.get("core_realignment_v3_applied") is True
            or (g.get("realignment_metadata") or {}).get("v3_applied") is True
            for g in games
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
# Batch progress (PostgreSQL)
# ---------------------------------------------------------------------------

def _count_existing_events(label: str = BATCH_LABEL) -> int:
    import psycopg

    url = resolve_database_url()[0]
    if not url:
        return 0
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM generation_events WHERE analysis_batch_label = %s",
                (label,),
            )
            row = cur.fetchone()
    return int(row[0] if row else 0)


def _resolve_generation_plan(
    *,
    generations: int,
    target_total: int | None,
    lot_target: int = DEFAULT_LOT_TARGET,
) -> tuple[int, int, int]:
    """Return (existing, to_run, final_total_expected).

    When target_total is set, to_run = max(0, target_total - existing).
    Without target_total, uses generations but blocks overflow past lot_target.
    """
    existing = _count_existing_events()
    if target_total is not None:
        if target_total < 1:
            raise ValueError("--target-total deve ser >= 1")
        to_run = max(0, target_total - existing)
        final_total = existing + to_run
        return existing, to_run, final_total

    if generations < 1:
        raise ValueError("--generations deve ser >= 1")

    final_total = existing + generations
    if final_total > lot_target:
        remaining = max(0, lot_target - existing)
        raise RuntimeError(
            f"Lote {BATCH_LABEL} já tem {existing} event(s). "
            f"--generations {generations} fecharia com {final_total} (max {lot_target}). "
            f"Use --target-total {lot_target} ou --generations {remaining}."
        )
    return existing, generations, final_total


# ---------------------------------------------------------------------------
# Validation query
# ---------------------------------------------------------------------------

def _validate_db() -> dict:
    import psycopg
    t0 = time.monotonic()
    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  ge.analysis_batch_label,
                  COUNT(DISTINCT ge.id) AS total_events,
                  COUNT(gg.id) AS total_games,
                  COUNT(DISTINCT ge.id) FILTER (
                    WHERE ge.context_json::text ILIKE '%%core_realignment_v3_applied%%true%%'
                  ) AS ge_v3_flagged,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"v3_applied": true%%'
                       OR gg.context_json::text ILIKE '%%"core_realignment_v3_applied": true%%'
                  ) AS games_v3_applied,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"pool_pre_filter_applied": true%%'
                  ) AS games_pool_pre_filter,
                  COUNT(gg.id) FILTER (
                    WHERE gg.context_json::text ILIKE '%%"v3_fallback_to_v1": true%%'
                  ) AS games_v3_fallback
                FROM generation_events ge
                LEFT JOIN generated_games gg ON gg.generation_event_id = ge.id
                WHERE ge.analysis_batch_label LIKE 'STRUCT_CORE_REALIGN_V3_BALANCED_%%'
                GROUP BY ge.analysis_batch_label
                ORDER BY ge.analysis_batch_label
            """)
            rows = cur.fetchall()
    results = [
        {
            "label": r[0],
            "total": r[1],
            "games": r[2],
            "ge_v3_flagged": r[3],
            "games_v3_applied": r[4],
            "games_pool_pre_filter": r[5],
            "games_v3_fallback": r[6],
        }
        for r in rows
    ]
    batch = next((r for r in results if r["label"] == BATCH_LABEL), None)
    ok = bool(
        batch
        and batch["total"] >= 1
        and batch["games"] >= GAMES_COUNT
        and batch["games_v3_applied"] == batch["games"]
        and batch["games_pool_pre_filter"] == batch["games"]
        and batch["games_v3_fallback"] == 0
    )
    _log(f"  validate_db: {time.monotonic()-t0:.2f}s")
    return {"rows": results, "validation_ok": ok, "batch": batch}


def _print_validation(val: dict) -> None:
    if not val["rows"]:
        _log("  Nenhum dado para STRUCT_CORE_REALIGN_V3_BALANCED_*")
        return
    for r in val["rows"]:
        status = "OK" if r["label"] == BATCH_LABEL and val.get("validation_ok") else "CHECK"
        _log(
            f"  {r['label']:<40}  events={r['total']:>3}  games={r['games']:>4}  "
            f"v3_games={r['games_v3_applied']:>3}  pre_filter={r['games_pool_pre_filter']:>3}  "
            f"fallback={r['games_v3_fallback']:>3}  [{status}]"
        )
    batch = val.get("batch")
    if val["validation_ok"] and batch:
        _log(
            f"[RESULTADO] {BATCH_LABEL} validado: "
            f"events={batch['total']} games={batch['games']} "
            f"v3_applied={batch['games_v3_applied']} "
            f"pool_pre_filter={batch['games_pool_pre_filter']} "
            f"v3_fallback={batch['games_v3_fallback']}"
        )
    else:
        _log(f"[RESULTADO] FALHA na validacao de {BATCH_LABEL}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--contests", type=int, default=1)
    parser.add_argument(
        "--generations",
        type=int,
        default=1,
        help="Quantidade de novas gerações nesta execução (default: 1)",
    )
    parser.add_argument(
        "--target-total",
        type=int,
        default=0,
        help=f"Fechar lote até N generation_events totais (ex.: 20). Calcula restante automaticamente.",
    )
    parser.add_argument("--pool", type=int, default=0, help="pool_size inicial (0=progressivo [100,200])")
    parser.add_argument("--created-by", default="ops/run_core_realign_v3_test_15d")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    t_start = time.monotonic()

    if args.validate_only:
        ensure_database_url(root=ROOT)
        _log("=== VALIDATE ONLY ===")
        val = _validate_db()
        _print_validation(val)
        return 0 if val["validation_ok"] else 1

    # flag check
    v3_mode = os.environ.get("LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3", "off")
    v1_mode = os.environ.get("LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1", "off")
    _log(f"LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3={v3_mode!r}")
    _log(f"LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1={v1_mode!r}")
    if v3_mode not in ("shadow_test", "active"):
        raise RuntimeError(f"V3 flag inativa: {v3_mode!r}. Defina shadow_test ou active.")

    ensure_database_url(root=ROOT)
    _log(f"DATABASE_URL source: {os.environ.get('LOTOIA_DOTENV_LOADED', 'environment')}")

    # pool steps
    pool_steps = [args.pool] if args.pool > 0 else [100, 200]

    target_total = args.target_total if args.target_total > 0 else None
    existing, n_gens, final_total = _resolve_generation_plan(
        generations=args.generations,
        target_total=target_total,
    )
    n_contests = args.contests

    if n_gens == 0:
        _log(
            f"Lote {BATCH_LABEL} já completo: existing={existing} "
            f"target={target_total or DEFAULT_LOT_TARGET} — nada a gerar."
        )
        val = _validate_db()
        _print_validation(val)
        return 0

    _log(
        f"Lote {BATCH_LABEL}: existing={existing}  run_now={n_gens}  "
        f"final_expected={final_total}"
    )

    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH
    from dashboard.institutional_app import DB_PATH, get_official_contest, _load_official_history_rows

    t0 = time.monotonic()
    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError(
            "Requer PostgreSQL. Configure DATABASE_URL em .env "
            "(copie .env.example e cole a URL do Railway)."
        )
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

    _log(
        f"\n=== {BATCH_LABEL} | v3_mode={v3_mode} | existing={existing} | "
        f"run={n_gens} | final={final_total} | pool_steps={pool_steps} | GP={GAMES_COUNT} ===\n"
    )

    base_seed = int(time.time()) % 1_000_000
    ge_ids = []
    report_events = []

    for contest in contests:
        cn = int(contest["concurso"])
        official = get_official_contest(cn)
        if not official:
            raise RuntimeError(f"Concurso {cn} não encontrado.")

        for run_i in range(1, n_gens + 1):
            global_run = existing + run_i
            seed = base_seed + cn * 10 + global_run
            t_run = time.monotonic()
            _log(f"--- concurso={cn} run={global_run}/{final_total} seed={seed} ---")

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
                "run": global_run,
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
