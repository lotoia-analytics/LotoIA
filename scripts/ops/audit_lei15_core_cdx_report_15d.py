#!/usr/bin/env python3
"""Relatório CDX — Núcleo Lei 15 antes/depois (R-03/R-04, padrões, V1≥13, hits).

Uso:
  python scripts/ops/audit_lei15_core_cdx_report_15d.py
  python scripts/ops/audit_lei15_core_cdx_report_15d.py --variant D
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

from lotoia.data.loader import load_draws_csv
from lotoia.generation.lei15_core_candidate_001 import audit_profile_pattern_frequencies, build_candidate_pool
from lotoia.generation.lei15_core_structural_payload import apply_core_traceability_payload, is_v1_strong_pattern
from lotoia.generator.basic_generator import (
    GENERATION_PROFILE_RATIOS,
    _attach_scores,
    _compose_profiled_games,
    _generate_profile_candidate,
    _is_valid_game,
)
from lotoia.governance.lei15_core_candidate_001 import resolve_candidate_config
from lotoia.statistics.historical_intelligence import profile_quota
from random import Random

BASELINE_LABEL = "STRUCT_TEST_15D_001"
V1_LABEL = "STRUCT_REALIGN_V1_15D_001"
VARIANT_LABELS = {
    "A": "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001",
    "D": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
}
CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
POOL_SIZE = 100
GP_SIZE = 50


def _legacy_pool(pool_size: int, seed: int, history) -> list[dict]:
    games: list[dict] = []
    seen: set[tuple[int, ...]] = set()
    profiles = list(GENERATION_PROFILE_RATIOS)
    for attempts in range(1, pool_size * 20):
        if len(games) >= pool_size:
            break
        pt = profiles[attempts % len(profiles)]
        cand = _generate_profile_candidate(Random(attempts + seed), pt, history)
        if not _is_valid_game(cand, profile_type=pt):
            continue
        g = _attach_scores(cand, history=history, profile_type=pt)
        apply_core_traceability_payload(g, profile_origin=pt)
        key = tuple(g["numbers"])
        if key in seen:
            continue
        seen.add(key)
        games.append(g)
    return games


def _gp(games: list[dict], *, relabel: bool) -> list[dict]:
    return _compose_profiled_games(games, GP_SIZE, allow_profile_relabeling=relabel)


def _label_dist(games: list[dict], field: str) -> Counter:
    return Counter(str(g.get(field) or "") for g in games)


def _load_v1_strong_cards(conn) -> set[tuple[int, ...]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH deduped AS (
                SELECT DISTINCT ON (rr.generation_event_id, rr.contest_id)
                    rr.id AS run_id
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s AND rr.contest_id = ANY(%s)
                ORDER BY rr.generation_event_id, rr.contest_id, rr.id DESC
            )
            SELECT rg.numbers
            FROM deduped d
            JOIN reconciliation_games rg ON rg.reconciliation_run_id = d.run_id
            WHERE rg.hits >= 13
            """,
            (V1_LABEL, list(CONTESTS)),
        )
        rows = cur.fetchall()
    out: set[tuple[int, ...]] = set()
    for (numbers,) in rows:
        if isinstance(numbers, list) and len(numbers) == 15:
            out.add(tuple(sorted(int(x) for x in numbers)))
    return out


def _hits_summary(conn, label: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH deduped AS (
                SELECT DISTINCT ON (rr.generation_event_id, rr.contest_id)
                    rr.best_hits
                FROM reconciliation_runs rr
                JOIN generation_events ge ON ge.id = rr.generation_event_id
                WHERE ge.analysis_batch_label = %s AND rr.contest_id = ANY(%s)
                ORDER BY rr.generation_event_id, rr.contest_id, rr.id DESC
            )
            SELECT best_hits FROM deduped
            """,
            (label, list(CONTESTS)),
        )
        rows = cur.fetchall()
    hits = [int(r[0]) for r in rows]
    if not hits:
        return {"runs": 0, "best": 0, "avg": 0.0, "runs_13_plus": 0}
    return {
        "runs": len(hits),
        "best": max(hits),
        "avg": sum(hits) / len(hits),
        "runs_13_plus": sum(1 for h in hits if h >= 13),
    }


def _print_audit(title: str, audit: dict) -> None:
    print(f"\n--- {title} ---")
    for profile in ("recorrente", "hibrido", "caotico", "all"):
        if profile not in audit:
            continue
        r = audit[profile]
        print(
            f"  {profile:<10} n={int(r.get('count', 0)):>3} "
            f"p3_123={r.get('prefix_01_02_03_pct', 0):5.1f}% "
            f"s3_222425={r.get('suffix_22_24_25_pct', 0):5.1f}% "
            f"bias={r.get('avg_bias_score', 0):5.1f}"
        )


def main() -> int:
    import argparse

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="D", choices=["A", "D"])
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    history = load_draws_csv()
    seed = args.seed
    candidate_label = VARIANT_LABELS[args.variant]
    cfg = resolve_candidate_config(candidate_label)

    legacy_pool = _legacy_pool(POOL_SIZE, seed, history)
    candidate_pool = build_candidate_pool(POOL_SIZE, seed=seed, history=history, config=cfg)

    legacy_gp_relabel = _gp(legacy_pool, relabel=True)
    legacy_gp_honest = _gp(legacy_pool, relabel=False)
    candidate_gp = _gp(candidate_pool, relabel=False)

    for g in legacy_pool + candidate_pool + legacy_gp_relabel + legacy_gp_honest + candidate_gp:
        if "perfil_origem_real" not in g:
            apply_core_traceability_payload(g, profile_origin=str(g.get("profile_type") or ""))

    audit_before_pool = audit_profile_pattern_frequencies(legacy_pool)
    audit_after_pool = audit_profile_pattern_frequencies(candidate_pool)
    audit_before_gp = audit_profile_pattern_frequencies(legacy_gp_relabel)
    audit_after_gp = audit_profile_pattern_frequencies(candidate_gp)

    v1_strong_in_before = sum(1 for g in legacy_pool if is_v1_strong_pattern(g["numbers"]))
    v1_strong_in_after = sum(1 for g in candidate_pool if is_v1_strong_pattern(g["numbers"]))

    print("=" * 72)
    print("RELATÓRIO CDX — NÚCLEO LEI 15 (simulação + PostgreSQL)")
    print(f"Variante candidata: {args.variant} | label={candidate_label}")
    print("=" * 72)

    print("\n## 1. Auditoria R-03 / R-04 — pool bruto")
    _print_audit("ANTES (round-robin legacy)", audit_before_pool)
    _print_audit("DEPOIS (CDX candidate pool)", audit_after_pool)

    print("\n## 2. Composição R-06 — GP50")
    _print_audit("ANTES GP (relabeling ON)", audit_before_gp)
    _print_audit("ANTES GP (relabeling OFF)", audit_profile_pattern_frequencies(legacy_gp_honest))
    _print_audit("DEPOIS GP (N-C5 no relabel)", audit_after_gp)

    print("\n## 3. Perfil real vs label final")
    print("  ANTES GP relabel ON:")
    print(f"    origem_real: {dict(_label_dist(legacy_gp_relabel, 'perfil_origem_real'))}")
    print(f"    label_final: {dict(_label_dist(legacy_gp_relabel, 'perfil_label_final'))}")
    print(f"    relabeling:  {sum(1 for g in legacy_gp_relabel if g.get('relabeling_applied'))} jogos")
    print("  DEPOIS GP (CDX):")
    print(f"    origem_real: {dict(_label_dist(candidate_gp, 'perfil_origem_real'))}")
    print(f"    label_final: {dict(_label_dist(candidate_gp, 'perfil_label_final'))}")
    print(f"    relabeling:  {sum(1 for g in candidate_gp if g.get('relabeling_applied'))} jogos")

    print("\n## 4. Padrões monitorados (pool)")
    keys = (
        "prefix_01_02_03_pct",
        "prefix_01_02_pct",
        "prefix_02_03_pct",
        "suffix_22_24_25_pct",
        "suffix_22_24_pct",
        "suffix_24_25_pct",
        "suffix_22_25_pct",
    )
    for k in keys:
        b = audit_before_pool.get("all", {}).get(k, 0)
        a = audit_after_pool.get("all", {}).get(k, 0)
        print(f"  {k:<28} antes={b:5.1f}%  depois={a:5.1f}%  delta={a-b:+5.1f}pp")

    print("\n## 5. Preservação padrões V1 fortes (pool, shield)")
    print(f"  cartões padrão V1 forte no pool: antes={v1_strong_in_before} depois={v1_strong_in_after}")

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]
    with psycopg.connect(url) as conn:
        v1_cards = _load_v1_strong_cards(conn)
        before_set = {tuple(sorted(g["numbers"])) for g in legacy_pool}
        after_set = {tuple(sorted(g["numbers"])) for g in candidate_pool}
        overlap_before = len(v1_cards & before_set)
        overlap_after = len(v1_cards & after_set)
        hits_baseline = _hits_summary(conn, BASELINE_LABEL)
        hits_v1 = _hits_summary(conn, V1_LABEL)
        hits_cand = _hits_summary(conn, candidate_label)

    print("\n## 6. Impacto cartões V1≥13 únicos (PostgreSQL)")
    print(f"  V1≥13 únicos baseline concursos: {len(v1_cards)}")
    print(f"  presentes no pool ANTES: {overlap_before}")
    print(f"  presentes no pool DEPOIS: {overlap_after}")

    print("\n## 7. Hits concursos 3705-3711 (lotes persistidos)")
    print(f"  BASELINE: {hits_baseline}")
    print(f"  V1:       {hits_v1}")
    print(f"  CAND-{args.variant}: {hits_cand}")

    print("\n## 8. Conclusão CDX")
    p3_before = audit_before_gp.get("all", {}).get("prefix_01_02_03_pct", 0)
    p3_after = audit_after_gp.get("all", {}).get("prefix_01_02_03_pct", 0)
    s3_before = audit_before_gp.get("all", {}).get("suffix_22_24_25_pct", 0)
    s3_after = audit_after_gp.get("all", {}).get("suffix_22_24_25_pct", 0)
    print(f"  prefixo 01-02-03 GP: {p3_before:.1f}% -> {p3_after:.1f}%")
    print(f"  sufixo 22-24-25 GP: {s3_before:.1f}% -> {s3_after:.1f}%")
    print(f"  relabeling eliminado no CDX: N-C5 ativo={cfg.disable_profile_relabeling}")
    print(f"  diversidade na geração: N-C4 quota={cfg.pool_sampling_by_quota}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
