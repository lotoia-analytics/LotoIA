#!/usr/bin/env python3
"""Reconcilia STRUCT_REALIGN_V1_15D_001 contra os 7 concursos do baseline.

Mission: RECONCILE_REALIGN_V1_15D_BASELINE_CONTESTS

Regras:
  - NÃO gera novos jogos.
  - NÃO apaga generation_events existentes.
  - NÃO altera Lei 15 ou realinhamento.
  - Apenas persiste reconciliation_runs ausentes (skip duplicatas).
  - Fonte: Railway PostgreSQL (DATABASE_URL).

Resultado esperado:
  20 gen_events × 7 concursos = 140 reconciliation_runs
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

BATCH_LABEL = "STRUCT_REALIGN_V1_15D_001"
CARD_FORMAT = 15
TARGET_CONTESTS = [3705, 3706, 3707, 3708, 3709, 3710, 3711]
EXPECTED_GEN_EVENTS = 20
EXPECTED_RECON_RUNS = EXPECTED_GEN_EVENTS * len(TARGET_CONTESTS)  # 140


def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]


def _log(msg: str, *, indent: int = 0) -> None:
    print(f"[{_ts()}] {'  ' * indent}{msg}", flush=True)


# ---------------------------------------------------------------------------
# Pre-validation
# ---------------------------------------------------------------------------

def pre_validate(conn) -> dict[str, Any]:
    """Verifica estado do lote antes de executar."""
    _log("=== PRÉ-VALIDAÇÃO ===")

    with conn.cursor() as cur:
        # Batch check
        cur.execute("""
            SELECT
                COUNT(*) AS total_events,
                COUNT(*) FILTER (
                    WHERE context_json::text ILIKE '%%realignment_applied%%true%%'
                ) AS applied_true
            FROM generation_events
            WHERE analysis_batch_label = %s
        """, (BATCH_LABEL,))
        row = cur.fetchone()
        total_events = row[0]
        applied_true = row[1]
        _log(f"  gen_events={total_events}  applied_true={applied_true}", indent=1)

        if total_events != EXPECTED_GEN_EVENTS:
            raise RuntimeError(
                f"Esperado {EXPECTED_GEN_EVENTS} gen_events, encontrado {total_events}. Abortando."
            )
        if applied_true != EXPECTED_GEN_EVENTS:
            raise RuntimeError(
                f"Esperado applied_true={EXPECTED_GEN_EVENTS}, encontrado {applied_true}. Abortando."
            )

        # Reconciliações existentes
        cur.execute("""
            SELECT rr.contest_id,
                   COUNT(DISTINCT rr.generation_event_id) AS ge_count,
                   COUNT(*) AS run_count
            FROM reconciliation_runs rr
            JOIN generation_events ge ON ge.id = rr.generation_event_id
            WHERE ge.analysis_batch_label = %s
            GROUP BY rr.contest_id
            ORDER BY rr.contest_id
        """, (BATCH_LABEL,))
        existing = {row[0]: {"ge_count": row[1], "run_count": row[2]} for row in cur.fetchall()}
        _log("  Reconciliações existentes:", indent=1)
        if existing:
            for cn, info in sorted(existing.items()):
                _log(f"    concurso={cn}  ge_conferidos={info['ge_count']}  runs={info['run_count']}", indent=1)
        else:
            _log("    (nenhuma)", indent=1)

        # Gen event IDs
        cur.execute("""
            SELECT id FROM generation_events
            WHERE analysis_batch_label = %s
            ORDER BY id
        """, (BATCH_LABEL,))
        ge_ids = [r[0] for r in cur.fetchall()]
        _log(f"  gen_event_ids={ge_ids}", indent=1)

        # Existing pairs set: (ge_id, contest_id)
        existing_pairs: set[tuple[int, int]] = set()
        if existing:
            cur.execute("""
                SELECT rr.generation_event_id, rr.contest_id
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s
            """, (BATCH_LABEL,))
            existing_pairs = {(r[0], r[1]) for r in cur.fetchall()}

    _log(f"  pairs já reconciliados: {len(existing_pairs)}", indent=1)
    _log(f"  pairs a criar: {EXPECTED_GEN_EVENTS * len(TARGET_CONTESTS) - len(existing_pairs)}", indent=1)

    return {"ge_ids": ge_ids, "existing_pairs": existing_pairs}


# ---------------------------------------------------------------------------
# Load games from DB
# ---------------------------------------------------------------------------

def load_games_for_ge(ge_id: int) -> list[dict[str, Any]]:
    """Carrega jogos do generated_games para um generation_event_id."""
    from lotoia.database.database import GeneratedGame, get_session
    from dashboard.institutional_app import DB_PATH

    with get_session(DB_PATH) as session:
        rows = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == ge_id)
            .order_by(GeneratedGame.game_index.asc())
            .all()
        )

    games = []
    for row in rows:
        nums = list(row.numbers or [])
        if len(nums) != CARD_FORMAT:
            continue
        game = {
            "numbers": nums,
            "game_index": row.game_index,
            "profile_type": row.profile_type or "",
            "final_score": dict(row.final_score or {}),
            "generation_event_id": ge_id,
            "formato_cartao": CARD_FORMAT,
            "card_format": CARD_FORMAT,
            "selected_card_format": CARD_FORMAT,
            "final_card_numbers": nums,
            "core_numbers": nums,
        }
        games.append(game)

    return games


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile_batch(ge_ids: list[int], existing_pairs: set[tuple[int, int]]) -> dict[str, Any]:
    """Reconcilia todos os pares (ge_id, contest_id) faltantes."""
    from dashboard.institutional_app import get_official_contest, _compare_games_against_contest

    total_created = 0
    total_skipped = 0
    total_errors = 0
    error_log: list[str] = []

    _log("\n=== RECONCILIAÇÃO ===")
    _log(f"  alvo: {len(ge_ids)} gen_events × {len(TARGET_CONTESTS)} concursos = {len(ge_ids) * len(TARGET_CONTESTS)} pares")

    # Pré-carregar concursos oficiais
    _log("  carregando concursos oficiais...", indent=1)
    t0 = time.monotonic()
    official_contests: dict[int, Any] = {}
    for cn in TARGET_CONTESTS:
        contest = get_official_contest(cn)
        if not contest:
            raise RuntimeError(f"Concurso oficial {cn} não encontrado no PostgreSQL.")
        official_contests[cn] = contest
    _log(f"  {len(official_contests)} concursos carregados em {time.monotonic()-t0:.2f}s", indent=1)

    for ge_id in ge_ids:
        t_ge = time.monotonic()
        games = load_games_for_ge(ge_id)
        if not games:
            _log(f"  ge_id={ge_id}: AVISO — nenhum jogo encontrado, pulando", indent=1)
            continue

        ge_results = []
        for cn in TARGET_CONTESTS:
            pair = (ge_id, cn)
            if pair in existing_pairs:
                total_skipped += 1
                continue

            contest = official_contests[cn]
            try:
                result = _compare_games_against_contest(
                    generation_event_id=ge_id,
                    games=games,
                    contest=contest,
                )
                status = str(result.get("status", "")).lower()
                if status == "error":
                    msg = result.get("message", result.get("persistence_guard_status", "erro"))
                    _log(f"    ge_id={ge_id} concurso={cn}: ERROR — {msg}", indent=2)
                    total_errors += 1
                    error_log.append(f"ge={ge_id} cn={cn}: {msg}")
                else:
                    total_created += 1
                    ge_results.append(f"cn={cn}:hits={result.get('best_hits','?')}")
            except Exception as exc:  # noqa: BLE001
                _log(f"    ge_id={ge_id} concurso={cn}: EXCECAO — {exc}", indent=2)
                total_errors += 1
                error_log.append(f"ge={ge_id} cn={cn}: {exc}")

        elapsed_ge = time.monotonic() - t_ge
        _log(
            f"  ge_id={ge_id}: {len(games)} jogos | {' '.join(ge_results) or 'tudo pulado'} | {elapsed_ge:.2f}s",
            indent=1,
        )

    return {
        "created": total_created,
        "skipped": total_skipped,
        "errors": total_errors,
        "error_log": error_log,
    }


# ---------------------------------------------------------------------------
# Post-validation
# ---------------------------------------------------------------------------

def post_validate(conn) -> dict[str, Any]:
    """Valida resultado final após reconciliação."""
    _log("\n=== PÓS-VALIDAÇÃO ===")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(DISTINCT ge.id)         AS gen_events,
                COUNT(DISTINCT rr.contest_id) AS concursos,
                COUNT(DISTINCT rr.id)         AS recon_runs
            FROM generation_events ge
            LEFT JOIN reconciliation_runs rr ON rr.generation_event_id = ge.id
            WHERE ge.analysis_batch_label = %s
        """, (BATCH_LABEL,))
        row = cur.fetchone()
        gen_events = row[0]
        concursos = row[1]
        recon_runs = row[2]

        _log(f"  gen_events={gen_events}  concursos={concursos}  reconciliation_runs={recon_runs}", indent=1)

        cur.execute("""
            SELECT rr.contest_id,
                   COUNT(DISTINCT rr.generation_event_id) AS ge_count,
                   COUNT(DISTINCT rr.id) AS run_count
            FROM reconciliation_runs rr
            JOIN generation_events ge ON ge.id = rr.generation_event_id
            WHERE ge.analysis_batch_label = %s
            GROUP BY rr.contest_id
            ORDER BY rr.contest_id
        """, (BATCH_LABEL,))

        _log("  Por concurso:", indent=1)
        per_contest = {}
        all_ok = True
        for r in cur.fetchall():
            cn, ge_c, run_c = r[0], r[1], r[2]
            per_contest[cn] = {"ge_count": ge_c, "run_count": run_c}
            ok = ge_c == EXPECTED_GEN_EVENTS and run_c == EXPECTED_GEN_EVENTS
            status = "OK" if ok else "INCOMPLETO"
            if not ok:
                all_ok = False
            _log(f"    concurso={cn}  ge={ge_c:>3}/{EXPECTED_GEN_EVENTS}  runs={run_c:>3}  [{status}]", indent=1)

    # Check all 7 target contests present
    for cn in TARGET_CONTESTS:
        if cn not in per_contest:
            _log(f"    concurso={cn}: AUSENTE", indent=1)
            all_ok = False

    checks = {
        "gen_events_ok": gen_events == EXPECTED_GEN_EVENTS,
        "concursos_ok": concursos == len(TARGET_CONTESTS),
        "recon_runs_ok": recon_runs == EXPECTED_RECON_RUNS,
        "all_contests_ok": all_ok,
    }
    overall = all(checks.values())

    _log(f"\n  {'APROVADO' if overall else 'FALHOU'}: gen_events={checks['gen_events_ok']} "
         f"concursos={checks['concursos_ok']} recon_runs={checks['recon_runs_ok']} "
         f"all_contests={checks['all_contests_ok']}", indent=1)

    return {
        "gen_events": gen_events,
        "concursos": concursos,
        "recon_runs": recon_runs,
        "per_contest": per_contest,
        "checks": checks,
        "approved": overall,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse
    import psycopg

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Só pré-valida, não reconcilia")
    parser.add_argument("--json-out", action="store_true")
    args = parser.parse_args()

    t_start = time.monotonic()

    url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
    if not url:
        raise RuntimeError("DATABASE_URL não definida. Configure Railway.")

    _log(f"Mission: RECONCILE_REALIGN_V1_15D_BASELINE_CONTESTS")
    _log(f"Batch:   {BATCH_LABEL}")
    _log(f"Alvo:    {len(TARGET_CONTESTS)} concursos {TARGET_CONTESTS}")
    _log(f"Esperado: {EXPECTED_RECON_RUNS} reconciliation_runs ({EXPECTED_GEN_EVENTS} × {len(TARGET_CONTESTS)})")

    from lotoia.governance.cloud_runtime_policy import evaluate_cloud_runtime_policy
    from lotoia.database.database import DEFAULT_DATABASE_PATH

    policy = evaluate_cloud_runtime_policy(DEFAULT_DATABASE_PATH)
    if policy.backend != "postgresql":
        raise RuntimeError("Requer PostgreSQL. Configure DATABASE_URL.")

    with psycopg.connect(url) as conn:
        pre = pre_validate(conn)

        if args.dry_run:
            _log("\n[DRY-RUN] Pré-validação concluída. Nenhuma reconciliação executada.")
            return 0

        result = reconcile_batch(
            ge_ids=pre["ge_ids"],
            existing_pairs=pre["existing_pairs"],
        )
        _log(f"\n  criados={result['created']}  pulados={result['skipped']}  erros={result['errors']}")
        if result["error_log"]:
            for err in result["error_log"]:
                _log(f"  ERROR: {err}", indent=1)

        post = post_validate(conn)

    total = time.monotonic() - t_start
    _log(f"\ntotal elapsed: {total:.2f}s")

    if args.json_out:
        print(json.dumps({
            "batch_label": BATCH_LABEL,
            "pre_validation": {"ge_ids": pre["ge_ids"]},
            "reconciliation": result,
            "post_validation": post,
            "elapsed_s": round(total, 2),
        }, ensure_ascii=False, indent=2, default=str))

    if not post["approved"]:
        _log("\n[RESULTADO] FALHA na pós-validação.", indent=0)
        return 1

    _log(f"\n[RESULTADO] APROVADO — {post['recon_runs']}/{EXPECTED_RECON_RUNS} reconciliation_runs confirmados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
