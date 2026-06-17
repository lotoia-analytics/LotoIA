#!/usr/bin/env python3
"""Relatório final — Piloto CDX Variante D (agent_qualidade).

Compara baseline, V1, V2, V3, V4, CAND-A, CAND-D com métricas institucionais
e emite veredicto: APROVADA / REPROVADA / INCONCLUSIVA.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
BASELINE_AVG = 9.286
PILOT_BEST = 13

LANES = (
    ("STRUCT_TEST_15D_001", "BASELINE"),
    ("STRUCT_REALIGN_V1_15D_001", "V1"),
    ("STRUCT_CORE_REALIGN_V2_15D_001", "V2"),
    ("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001", "V3"),
    ("STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001", "V4"),
    ("STRUCT_LEI15_CORE_CANDIDATE_001_15D_001", "CAND-A"),
    ("STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001", "CAND-D"),
)
LABEL_A = "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001"
LABEL_D = "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001"
LABEL_V1 = "STRUCT_REALIGN_V1_15D_001"

OFFICIAL_RUNS_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (rr.generation_event_id, rr.contest_id)
        rr.id,
        rr.generation_event_id,
        rr.contest_id,
        rr.best_hits,
        ge.analysis_batch_label
    FROM reconciliation_runs rr
    JOIN generation_events ge ON ge.id = rr.generation_event_id
    WHERE ge.analysis_batch_label = %s
      AND rr.contest_id = ANY(%s)
    ORDER BY rr.generation_event_id, rr.contest_id, rr.id DESC
)
"""


def _ctx_field(ctx, key: str, default=None):
    if isinstance(ctx, dict):
        return ctx.get(key, default)
    if isinstance(ctx, str):
        try:
            parsed = json.loads(ctx)
            if isinstance(parsed, dict):
                return parsed.get(key, default)
        except json.JSONDecodeError:
            pass
    return default


def _hits(conn, label: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"{OFFICIAL_RUNS_SQL} SELECT best_hits FROM deduped", (label, list(CONTESTS)))
        hits = [int(r[0]) for r in cur.fetchall()]
    if not hits:
        return {"runs": 0, "best": 0, "avg": 0.0, "runs_13_plus": 0, "dist": {}}
    dist = Counter(hits)
    return {
        "runs": len(hits),
        "best": max(hits),
        "avg": sum(hits) / len(hits),
        "runs_13_plus": sum(1 for h in hits if h >= 13),
        "dist": dict(sorted(dist.items())),
    }


def _structural_from_db(conn, label: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT gg.numbers, gg.context_json, gg.profile_type
            FROM generated_games gg
            JOIN generation_events ge ON ge.id = gg.generation_event_id
            WHERE ge.analysis_batch_label = %s
            """,
            (label,),
        )
        rows = cur.fetchall()

    prefix_sig: Counter = Counter()
    suffix_sig: Counter = Counter()
    origin: Counter = Counter()
    label_final: Counter = Counter()
    bias_scores: list[float] = []
    relabel_count = 0
    p3_123 = 0
    s3_222425 = 0
    total = 0

    from lotoia.generation.lei15_core_structural_payload import apply_core_traceability_payload

    for numbers, ctx_raw, profile_type_col in rows:
        if not isinstance(numbers, list) or len(numbers) != 15:
            continue
        total += 1
        nums = sorted(int(x) for x in numbers)
        if nums[:3] == [1, 2, 3]:
            p3_123 += 1
        if nums[-3:] == [22, 24, 25]:
            s3_222425 += 1

        ctx = ctx_raw if isinstance(ctx_raw, dict) else {}
        origin_val = str(
            _ctx_field(ctx, "perfil_origem_real")
            or profile_type_col
            or _ctx_field(ctx, "profile_type")
            or ""
        )
        if not _ctx_field(ctx, "prefix_signature"):
            derived = apply_core_traceability_payload(
                {"numbers": nums, "profile_type": origin_val},
                profile_origin=origin_val,
            )
            ps = str(derived.get("prefix_signature") or "")
            ss = str(derived.get("suffix_signature") or "")
            bias = float(derived.get("structural_bias_score") or 0)
            relabel = bool(derived.get("relabeling_applied"))
            label_val = str(derived.get("perfil_label_final") or origin_val)
        else:
            trace = _ctx_field(ctx, "core_traceability") or {}
            ps = str(_ctx_field(ctx, "prefix_signature") or trace.get("prefix_signature") or "")
            ss = str(_ctx_field(ctx, "suffix_signature") or trace.get("suffix_signature") or "")
            bias = float(_ctx_field(ctx, "structural_bias_score") or 0)
            relabel = _ctx_field(ctx, "relabeling_applied") is True
            label_val = str(_ctx_field(ctx, "perfil_label_final") or origin_val)

        if ps:
            prefix_sig[ps] += 1
        if ss:
            suffix_sig[ss] += 1
        origin[origin_val] += 1
        label_final[label_val] += 1
        bias_scores.append(bias)
        if relabel:
            relabel_count += 1

    n = total or 1
    return {
        "games": total,
        "prefix_01_02_03_pct": p3_123 / n * 100,
        "suffix_22_24_25_pct": s3_222425 / n * 100,
        "prefix_signature_top": prefix_sig.most_common(3),
        "suffix_signature_top": suffix_sig.most_common(3),
        "perfil_origem_real": dict(origin),
        "perfil_label_final": dict(label_final),
        "avg_structural_bias_score": mean(bias_scores) if bias_scores else 0.0,
        "relabeling_applied_count": relabel_count,
        "relabeling_reasons": [],
    }


def _v1_13_overlap(conn, label: str) -> dict:
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
            ),
            v1_cards AS (
                SELECT DISTINCT rg.numbers::text AS numbers_key
                FROM deduped d
                JOIN reconciliation_games rg ON rg.reconciliation_run_id = d.run_id
                WHERE rg.hits >= 13
            )
            SELECT COUNT(*) FROM v1_cards
            """,
            (LABEL_V1, list(CONTESTS)),
        )
        v1_unique = int(cur.fetchone()[0] or 0)

        cur.execute(
            """
            SELECT gg.numbers::text FROM generated_games gg
            JOIN generation_events ge ON ge.id = gg.generation_event_id
            WHERE ge.analysis_batch_label = %s
            """,
            (label,),
        )
        pool = {row[0] for row in cur.fetchall() if row[0]}

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
            SELECT DISTINCT rg.numbers::text
            FROM deduped d
            JOIN reconciliation_games rg ON rg.reconciliation_run_id = d.run_id
            WHERE rg.hits >= 13
            """,
            (LABEL_V1, list(CONTESTS)),
        )
        v1_keys = {row[0] for row in cur.fetchall() if row[0]}
    overlap = len(v1_keys & pool)
    return {"v1_13_unique": v1_unique, "overlap_in_pool": overlap}


def _verdict(h_a: dict, s_a: dict, h_d: dict, s_d: dict) -> str:
    if s_d["relabeling_applied_count"] > 0 or (
        s_d["perfil_origem_real"] != s_d["perfil_label_final"]
        and any(k for k in s_d["perfil_label_final"] if k)
    ):
        # mismatch only if relabeling count > 0 is hard gate
        if s_d["relabeling_applied_count"] > 0:
            return "REPROVADA POR MASCARAMENTO"

    struct_better = (
        s_d["prefix_01_02_03_pct"] < s_a["prefix_01_02_03_pct"]
        and s_d["suffix_22_24_25_pct"] <= s_a["suffix_22_24_25_pct"] + 1
    )
    if not struct_better:
        return "REPROVADA POR ESTRUTURA"

    hits_ok = (
        h_d["best"] >= PILOT_BEST
        and h_d["avg"] > BASELINE_AVG
        and h_d["runs_13_plus"] >= 1
    )
    if hits_ok and s_d["relabeling_applied_count"] == 0:
        return "APROVADA PARA NOVO PILOTO"
    if not hits_ok:
        return "REPROVADA POR HITS"

    if h_d["runs"] < 7:
        return "INCONCLUSIVA"
    return "INCONCLUSIVA"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        print("=" * 78)
        print("RELATORIO FINAL — PILOTO CDX VARIANTE D (shadow_test)")
        print("=" * 78)

        hits_map: dict[str, dict] = {}
        struct_map: dict[str, dict] = {}

        print("\n## HITS (concursos 3705-3711)")
        print(f"{'Lane':<10} {'runs':>5} {'best':>5} {'avg':>8} {'13+':>5}")
        for label, short in LANES:
            h = _hits(conn, label)
            hits_map[label] = h
            print(
                f"{short:<10} {h['runs']:>5} {h['best']:>5} {h['avg']:>8.3f} "
                f"{h['runs_13_plus']:>5}"
            )

        print("\n## ESTRUTURA (jogos persistidos)")
        print(f"{'Lane':<10} {'n':>4} {'p3_123%':>8} {'s3_222425%':>10} {'bias':>6} {'relabel':>7}")
        for label, short in LANES:
            s = _structural_from_db(conn, label)
            struct_map[label] = s
            print(
                f"{short:<10} {s['games']:>4} {s['prefix_01_02_03_pct']:>7.1f}% "
                f"{s['suffix_22_24_25_pct']:>9.1f}% {s['avg_structural_bias_score']:>6.1f} "
                f"{s['relabeling_applied_count']:>7}"
            )

        for short_label in (LABEL_A, LABEL_D):
            s = struct_map.get(short_label, {})
            short = "CAND-A" if short_label == LABEL_A else "CAND-D"
            print(f"\n## PAYLOAD CDX — {short}")
            print(f"  perfil_origem_real:  {s.get('perfil_origem_real')}")
            print(f"  perfil_label_final:  {s.get('perfil_label_final')}")
            print(f"  prefix_signature top: {s.get('prefix_signature_top')}")
            print(f"  suffix_signature top: {s.get('suffix_signature_top')}")
            print(f"  relabeling_applied:  {s.get('relabeling_applied_count', 0)}")

        print("\n## CAND-D vs CAND-A")
        sa, sd = struct_map.get(LABEL_A, {}), struct_map.get(LABEL_D, {})
        ha, hd = hits_map.get(LABEL_A, {}), hits_map.get(LABEL_D, {})
        print(
            f"  prefixo 01-02-03: {sa.get('prefix_01_02_03_pct', 0):.1f}% -> "
            f"{sd.get('prefix_01_02_03_pct', 0):.1f}% "
            f"({sd.get('prefix_01_02_03_pct', 0) - sa.get('prefix_01_02_03_pct', 0):+.1f}pp)"
        )
        print(
            f"  sufixo 22-24-25: {sa.get('suffix_22_24_25_pct', 0):.1f}% -> "
            f"{sd.get('suffix_22_24_25_pct', 0):.1f}% "
            f"({sd.get('suffix_22_24_25_pct', 0) - sa.get('suffix_22_24_25_pct', 0):+.1f}pp)"
        )
        print(
            f"  melhor hit: {ha.get('best', 0)} -> {hd.get('best', 0)} | "
            f"media: {ha.get('avg', 0):.3f} -> {hd.get('avg', 0):.3f} | "
            f"runs 13+: {ha.get('runs_13_plus', 0)} -> {hd.get('runs_13_plus', 0)}"
        )

        print("\n## OVERLAP V1>=13 no pool piloto")
        for short_label, short in ((LABEL_A, "CAND-A"), (LABEL_D, "CAND-D")):
            ov = _v1_13_overlap(conn, short_label)
            print(f"  {short}: {ov['overlap_in_pool']}/{ov['v1_13_unique']} cartoes V1>=13")

        print("\n## GATE INSTITUCIONAL (CAND-D)")
        checks = [
            (
                "Reducao estrutural > CAND-A (prefixo)",
                sd.get("prefix_01_02_03_pct", 100) < sa.get("prefix_01_02_03_pct", 100),
            ),
            (
                "Sufixo controlado vs CAND-A",
                sd.get("suffix_22_24_25_pct", 100) <= sa.get("suffix_22_24_25_pct", 100) + 1,
            ),
            ("Sem relabeling", sd.get("relabeling_applied_count", 0) == 0),
            (f"Melhor hit >= {PILOT_BEST}", hd.get("best", 0) >= PILOT_BEST),
            (f"Media > {BASELINE_AVG}", hd.get("avg", 0) > BASELINE_AVG),
            ("Runs 13+ >= 1", hd.get("runs_13_plus", 0) >= 1),
        ]
        passed = 0
        for name, ok in checks:
            print(f"  [{'OK' if ok else 'FALHA'}] {name}")
            passed += int(ok)
        print(f"  Gate: {passed}/{len(checks)}")

        verdict = _verdict(ha, sa, hd, sd)
        print(f"\n## VEREDICTO: {verdict}")
        print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
