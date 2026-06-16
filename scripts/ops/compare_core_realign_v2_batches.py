#!/usr/bin/env python3
"""Relatório comparativo 3 lotes: BASELINE vs V1 vs V2 (15D).

Fonte exclusiva: Railway PostgreSQL (DATABASE_URL).

Uso:
  python scripts/ops/compare_core_realign_v2_batches.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import psycopg

LABELS = (
    "STRUCT_TEST_15D_001",
    "STRUCT_REALIGN_V1_15D_001",
    "STRUCT_CORE_REALIGN_V2_15D_001",
)
SHORT = {
    "STRUCT_TEST_15D_001": "BASELINE",
    "STRUCT_REALIGN_V1_15D_001": "V1",
    "STRUCT_CORE_REALIGN_V2_15D_001": "V2",
}

url = os.environ.get("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not url:
    raise RuntimeError("DATABASE_URL não definida")


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def fmt_key(k) -> str:
    return "-".join(f"{x:02d}" for x in k)


with psycopg.connect(url) as conn:
    print("\n" + "=" * 72)
    print("RELATÓRIO COMPARATIVO MISSÃO VITÓRIA — 15D (BASELINE / V1 / V2)")
    print("=" * 72)

    rows = q(conn, """
        SELECT ge.analysis_batch_label,
               COUNT(DISTINCT ge.id) AS gen_events,
               COUNT(gg.id) AS jogos,
               COUNT(DISTINCT rr.id) AS recon_runs
        FROM generation_events ge
        LEFT JOIN generated_games gg ON gg.generation_event_id = ge.id
        LEFT JOIN reconciliation_runs rr ON rr.generation_event_id = ge.id
        WHERE ge.analysis_batch_label = ANY(%s)
        GROUP BY ge.analysis_batch_label
        ORDER BY ge.analysis_batch_label
    """, (list(LABELS),))

    print("\n--- RESUMO DOS LOTES ---")
    for label, gen_ev, jogos, recon in rows:
        print(f"  {SHORT[label]:<10} gen_events={gen_ev:>3}  jogos={jogos:>5}  recon_runs={recon:>4}")

    rows = q(conn, """
        SELECT ge.analysis_batch_label, rr.best_hits, COUNT(DISTINCT rr.id)
        FROM reconciliation_runs rr
        JOIN generation_events ge ON ge.id = rr.generation_event_id
        WHERE ge.analysis_batch_label = ANY(%s)
        GROUP BY ge.analysis_batch_label, rr.best_hits
        ORDER BY ge.analysis_batch_label, rr.best_hits DESC
    """, (list(LABELS),))

    hit_dist: dict[str, dict[int, int]] = defaultdict(dict)
    for label, best_hits, n in rows:
        hit_dist[label][best_hits] = n

    best_hit = {lb: max(hit_dist[lb].keys(), default=0) for lb in LABELS}
    avg_hit = {
        lb: sum(h * n for h, n in hit_dist[lb].items()) / max(sum(hit_dist[lb].values()), 1)
        for lb in LABELS
    }
    hit_14_plus = {lb: sum(n for h, n in hit_dist[lb].items() if h >= 14) for lb in LABELS}
    hit_13_plus = {lb: sum(n for h, n in hit_dist[lb].items() if h >= 13) for lb in LABELS}

    print("\n--- HITS ---")
    for lb in LABELS:
        print(
            f"  {SHORT[lb]:<10} melhor={best_hit[lb]}  media={avg_hit[lb]:.3f}  "
            f"14+={hit_14_plus[lb]}  13+={hit_13_plus[lb]}"
        )

    prefix3: dict[str, Counter] = defaultdict(Counter)
    suffix3: dict[str, Counter] = defaultdict(Counter)
    prefix4: dict[str, Counter] = defaultdict(Counter)
    suffix4: dict[str, Counter] = defaultdict(Counter)
    total_games: dict[str, int] = defaultdict(int)
    ge_games: dict[str, dict] = defaultdict(lambda: defaultdict(list))

    rows_games = q(conn, """
        SELECT ge.analysis_batch_label, ge.id, gg.numbers
        FROM generated_games gg
        JOIN generation_events ge ON ge.id = gg.generation_event_id
        WHERE ge.analysis_batch_label = ANY(%s) AND gg.numbers IS NOT NULL
    """, (list(LABELS),))

    for label, ge_id, numbers in rows_games:
        if not isinstance(numbers, list) or len(numbers) != 15:
            continue
        nums = sorted(int(x) for x in numbers)
        prefix3[label][tuple(nums[:3])] += 1
        prefix4[label][tuple(nums[:4])] += 1
        suffix3[label][tuple(nums[-3:])] += 1
        suffix4[label][tuple(nums[-4:])] += 1
        total_games[label] += 1
        ge_games[label][ge_id].append(set(nums))

    near_dup: dict[str, dict] = {}
    for label in LABELS:
        total_near_dup = 0
        total_mean_overlap = 0.0
        mean_cnt = 0
        for game_sets in ge_games[label].values():
            n = len(game_sets)
            if n < 2:
                continue
            overlaps = []
            for i in range(n):
                for j in range(i + 1, n):
                    ov = len(game_sets[i] & game_sets[j])
                    overlaps.append(ov)
                    if ov >= 13:
                        total_near_dup += 1
            if overlaps:
                total_mean_overlap += sum(overlaps) / len(overlaps)
                mean_cnt += 1
        near_dup[label] = {
            "total_near_dup_pairs": total_near_dup,
            "mean_overlap": total_mean_overlap / max(mean_cnt, 1),
        }

    def top_pct(counter: Counter, label: str) -> tuple[str, float]:
        total = total_games[label] or 1
        if not counter:
            return "-", 0.0
        k, n = counter.most_common(1)[0]
        return fmt_key(k), n / total * 100

    print("\n--- ESTRUTURA (TOP CONCENTRAÇÃO) ---")
    metrics = {}
    for lb in LABELS:
        p3k, p3p = top_pct(prefix3[lb], lb)
        p4k, p4p = top_pct(prefix4[lb], lb)
        s3k, s3p = top_pct(suffix3[lb], lb)
        s4k, s4p = top_pct(suffix4[lb], lb)
        metrics[lb] = {
            "p3": p3p, "p4": p4p, "s3": s3p, "s4": s4p,
            "overlap": near_dup[lb]["mean_overlap"],
        }
        print(
            f"  {SHORT[lb]:<10} p3={p3k}({p3p:.1f}%)  p4={p4k}({p4p:.1f}%)  "
            f"s3={s3k}({s3p:.1f}%)  s4={s4k}({s4p:.1f}%)  "
            f"gp_overlap={near_dup[lb]['mean_overlap']:.3f}"
        )

    v1 = "STRUCT_REALIGN_V1_15D_001"
    v2 = "STRUCT_CORE_REALIGN_V2_15D_001"
    m_v1 = metrics.get(v1, {})
    m_v2 = metrics.get(v2, {})

    print("\n--- CRITÉRIOS DE APROVAÇÃO V2 (vs V1) ---")
    checks = [
        ("melhor hit >= 14", best_hit.get(v2, 0) >= 14),
        ("media hits >= 12.143", avg_hit.get(v2, 0) >= 12.143),
        ("runs 14+ >= 5", hit_14_plus.get(v2, 0) >= 5),
        ("runs 13+ >= 47", hit_13_plus.get(v2, 0) >= 47),
        ("top prefixo_3 < 35%", m_v2.get("p3", 100) < 35),
        ("top prefixo_4 < V1", m_v2.get("p4", 100) < m_v1.get("p4", 100)),
        ("top sufixo_3 <= 27%", m_v2.get("s3", 100) <= 27),
        ("top sufixo_4 <= 17%", m_v2.get("s4", 100) <= 17),
        ("similaridade GP <= 9.717", near_dup.get(v2, {}).get("mean_overlap", 99) <= 9.717),
    ]
    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"  [{'OK' if ok else 'FALHA'}] {name}")
    print(f"\n  Resultado: {passed}/{len(checks)} critérios atendidos")

    print("\n" + "=" * 72)
    print("Fonte: Railway PostgreSQL | shadow_test only")
    print("=" * 72 + "\n")
