#!/usr/bin/env python3
"""Relatório comparativo 5 vias: BASELINE / V1 / V2 / V3-BAL / V3.1-PROTECTED (15D).

Uso:
  python scripts/ops/compare_core_realign_5way_15d.py
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

LABELS = (
    "STRUCT_TEST_15D_001",
    "STRUCT_REALIGN_V1_15D_001",
    "STRUCT_CORE_REALIGN_V2_15D_001",
    "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001",
    "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001",
)
SHORT = {
    "STRUCT_TEST_15D_001": "BASELINE",
    "STRUCT_REALIGN_V1_15D_001": "V1",
    "STRUCT_CORE_REALIGN_V2_15D_001": "V2-EVID",
    "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001": "V3-BAL",
    "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001": "V3.1-PROT",
}

OFFICIAL_CONTEST_NUMBERS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
OFFICIAL_RUNS_PER_GE = len(OFFICIAL_CONTEST_NUMBERS)

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
    WHERE ge.analysis_batch_label = ANY(%s)
      AND rr.contest_id = ANY(%s)
    ORDER BY rr.generation_event_id, rr.contest_id, rr.id DESC
)
"""


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def fmt_key(k) -> str:
    return "-".join(f"{x:02d}" for x in k)


def main() -> None:
    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        print("\n" + "=" * 72)
        print("COMPARATIVO 5 VIAS — MISSAO VITORIA 15D")
        print("BASELINE | V1 | V2-EVID | V3-BAL | V3.1-PROTECTED")
        print("=" * 72)
        print(
            f"Reconciliacao oficial: {OFFICIAL_CONTEST_NUMBERS[0]}-{OFFICIAL_CONTEST_NUMBERS[-1]} | "
            f"meta lote completo={20 * OFFICIAL_RUNS_PER_GE} runs"
        )

        rows = q(
            conn,
            f"""
            {OFFICIAL_RUNS_SQL}
            SELECT ge.analysis_batch_label,
                   COUNT(DISTINCT ge.id) AS gen_events,
                   (SELECT COUNT(*) FROM generated_games gg
                    WHERE gg.generation_event_id IN (
                        SELECT id FROM generation_events ge2
                        WHERE ge2.analysis_batch_label = ge.analysis_batch_label
                    )) AS jogos,
                   COUNT(d.id) AS recon_runs
            FROM generation_events ge
            LEFT JOIN deduped d ON d.generation_event_id = ge.id
            WHERE ge.analysis_batch_label = ANY(%s)
            GROUP BY ge.analysis_batch_label
            ORDER BY ge.analysis_batch_label
            """,
            (list(LABELS), list(OFFICIAL_CONTEST_NUMBERS), list(LABELS)),
        )

        print("\n--- RESUMO DOS LOTES ---")
        label_rows = {label: (gen_ev, jogos, recon) for label, gen_ev, jogos, recon in rows}
        for lb in LABELS:
            gen_ev, jogos, recon = label_rows.get(lb, (0, 0, 0))
            print(f"  {SHORT[lb]:<10} gen_events={gen_ev:>3}  jogos={jogos:>5}  recon_runs={recon:>4}")

        rows = q(
            conn,
            f"""
            {OFFICIAL_RUNS_SQL}
            SELECT analysis_batch_label, best_hits, COUNT(*)
            FROM deduped
            GROUP BY analysis_batch_label, best_hits
            ORDER BY analysis_batch_label, best_hits DESC
            """,
            (list(LABELS), list(OFFICIAL_CONTEST_NUMBERS)),
        )

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

        print("\n--- HITS (140 runs oficiais quando lote=20 GEs) ---")
        for lb in LABELS:
            print(
                f"  {SHORT[lb]:<10} melhor={best_hit[lb]}  media={avg_hit[lb]:.3f}  "
                f"14+={hit_14_plus[lb]}  13+={hit_13_plus[lb]}"
            )

        prefix3: dict[str, Counter] = defaultdict(Counter)
        suffix3: dict[str, Counter] = defaultdict(Counter)
        total_games: dict[str, int] = defaultdict(int)
        ge_games: dict[str, dict] = defaultdict(lambda: defaultdict(list))

        rows_games = q(
            conn,
            """
            SELECT ge.analysis_batch_label, ge.id, gg.numbers
            FROM generated_games gg
            JOIN generation_events ge ON ge.id = gg.generation_event_id
            WHERE ge.analysis_batch_label = ANY(%s) AND gg.numbers IS NOT NULL
            """,
            (list(LABELS),),
        )

        for label, ge_id, numbers in rows_games:
            if not isinstance(numbers, list) or len(numbers) != 15:
                continue
            nums = sorted(int(x) for x in numbers)
            prefix3[label][tuple(nums[:3])] += 1
            suffix3[label][tuple(nums[-3:])] += 1
            total_games[label] += 1
            ge_games[label][ge_id].append(set(nums))

        near_dup: dict[str, float] = {}
        for label in LABELS:
            total_mean_overlap = 0.0
            mean_cnt = 0
            for game_sets in ge_games[label].values():
                n = len(game_sets)
                if n < 2:
                    continue
                overlaps = []
                for i in range(n):
                    for j in range(i + 1, n):
                        overlaps.append(len(game_sets[i] & game_sets[j]))
                if overlaps:
                    total_mean_overlap += sum(overlaps) / len(overlaps)
                    mean_cnt += 1
            near_dup[label] = total_mean_overlap / max(mean_cnt, 1)

        def top_pct(counter: Counter, label: str) -> tuple[str, float]:
            total = total_games[label] or 1
            if not counter:
                return "-", 0.0
            k, n = counter.most_common(1)[0]
            return fmt_key(k), n / total * 100

        print("\n--- ESTRUTURA ---")
        metrics: dict[str, dict[str, float]] = {}
        for lb in LABELS:
            p3k, p3p = top_pct(prefix3[lb], lb)
            s3k, s3p = top_pct(suffix3[lb], lb)
            metrics[lb] = {"p3": p3p, "s3": s3p, "overlap": near_dup[lb]}
            print(
                f"  {SHORT[lb]:<10} p3={p3k}({p3p:.1f}%)  s3={s3k}({s3p:.1f}%)  "
                f"gp_overlap={near_dup[lb]:.3f}"
            )

        baseline = "STRUCT_TEST_15D_001"
        v31 = "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001"
        m_base = metrics.get(baseline, {})
        m_v31 = metrics.get(v31, {})

        print("\n--- CRITERIOS MINIMOS V3.1-PROTECTED ---")
        v31_checks = [
            ("melhor hit >= 13", best_hit.get(v31, 0) >= 13),
            ("media hits >= 11.5", avg_hit.get(v31, 0) >= 11.5),
            ("runs 13+ >= 20", hit_13_plus.get(v31, 0) >= 20),
            (
                "sufixo 22-24-25 < baseline",
                m_v31.get("s3", 100) < m_base.get("s3", 100),
            ),
            (
                "prefixo 01-02-03 < baseline",
                m_v31.get("p3", 100) < m_base.get("p3", 100),
            ),
        ]
        passed = sum(1 for _, ok in v31_checks if ok)
        for name, ok in v31_checks:
            print(f"  [{'OK' if ok else 'PENDENTE'}] {name}")
        print(f"\n  Resultado V3.1: {passed}/{len(v31_checks)} criterios")

        print("\n" + "=" * 72)
        print("Fonte: Railway PostgreSQL | LOTOIA_LEI15_CORE_REALIGNMENT_V3_1=shadow_test")
        print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
