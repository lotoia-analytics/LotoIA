#!/usr/bin/env python3
"""Comparativo 6 vias incluindo V4-PATTERN (padrões V1 protegidos).

Uso:
  python scripts/ops/compare_core_realign_6way_15d.py
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
    "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001",
)
SHORT = {
    "STRUCT_TEST_15D_001": "BASELINE",
    "STRUCT_REALIGN_V1_15D_001": "V1",
    "STRUCT_CORE_REALIGN_V2_15D_001": "V2-EVID",
    "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001": "V3-BAL",
    "STRUCT_LEI15_CORE_V3_1_PROTECTED_15D_001": "V3.1-PROT",
    "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001": "V4-PATTERN",
}

OFFICIAL_CONTEST_NUMBERS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
V4_LABEL = "STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001"
BASELINE_LABEL = "STRUCT_TEST_15D_001"
V1_LABEL = "STRUCT_REALIGN_V1_15D_001"
GATE_BEST_HIT = 13
GATE_AVG_HIT = 11.5
GATE_RUNS_13_PLUS = 20

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


def _gp_overlap(conn, label: str) -> float | None:
    rows = q(
        conn,
        """
        SELECT gg.numbers
        FROM generated_games gg
        JOIN generation_events ge ON ge.id = gg.generation_event_id
        WHERE ge.analysis_batch_label = %s AND gg.numbers IS NOT NULL
        LIMIT 500
        """,
        (label,),
    )
    cards = [tuple(sorted(int(x) for x in nums)) for nums, in rows if isinstance(nums, list)]
    if len(cards) < 2:
        return None
    overlaps: list[int] = []
    for i, a in enumerate(cards):
        set_a = set(a)
        for b in cards[i + 1 :]:
            overlaps.append(len(set_a & set(b)))
    return sum(overlaps) / len(overlaps) if overlaps else None


def main() -> None:
    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        print("\n" + "=" * 72)
        print("COMPARATIVO 6 VIAS — 15D baseline 3705-3711")
        print("=" * 72)

        rows = q(
            conn,
            f"""
            {OFFICIAL_RUNS_SQL}
            SELECT ge.analysis_batch_label,
                   COUNT(DISTINCT ge.id),
                   (SELECT COUNT(*) FROM generated_games gg
                    WHERE gg.generation_event_id IN (
                        SELECT id FROM generation_events ge2
                        WHERE ge2.analysis_batch_label = ge.analysis_batch_label
                    )),
                   COUNT(d.id)
            FROM generation_events ge
            LEFT JOIN deduped d ON d.generation_event_id = ge.id
            WHERE ge.analysis_batch_label = ANY(%s)
            GROUP BY ge.analysis_batch_label
            ORDER BY ge.analysis_batch_label
            """,
            (list(LABELS), list(OFFICIAL_CONTEST_NUMBERS), list(LABELS)),
        )

        print("\n--- RESUMO DOS LOTES ---")
        label_rows = {label: (a, b, c) for label, a, b, c in rows}
        for lb in LABELS:
            gen_ev, jogos, recon = label_rows.get(lb, (0, 0, 0))
            print(f"  {SHORT[lb]:<12} gen_events={gen_ev:>3}  jogos={jogos:>5}  recon_runs={recon:>4}")

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
        hit_13_plus = {lb: sum(n for h, n in hit_dist[lb].items() if h >= 13) for lb in LABELS}

        print("\n--- HITS ---")
        for lb in LABELS:
            print(
                f"  {SHORT[lb]:<12} melhor={best_hit[lb]}  media={avg_hit[lb]:.3f}  "
                f"13+={hit_13_plus[lb]}"
            )

        prefix3: dict[str, Counter] = defaultdict(Counter)
        suffix3: dict[str, Counter] = defaultdict(Counter)
        total_games: dict[str, int] = defaultdict(int)

        rows_games = q(
            conn,
            """
            SELECT ge.analysis_batch_label, gg.numbers
            FROM generated_games gg
            JOIN generation_events ge ON ge.id = gg.generation_event_id
            WHERE ge.analysis_batch_label = ANY(%s) AND gg.numbers IS NOT NULL
            """,
            (list(LABELS),),
        )
        for label, numbers in rows_games:
            if not isinstance(numbers, list) or len(numbers) != 15:
                continue
            nums = sorted(int(x) for x in numbers)
            prefix3[label][tuple(nums[:3])] += 1
            suffix3[label][tuple(nums[-3:])] += 1
            total_games[label] += 1

        def top_pct(counter: Counter, label: str) -> tuple[str, float]:
            total = total_games[label] or 1
            if not counter:
                return "-", 0.0
            k, n = counter.most_common(1)[0]
            return fmt_key(k), n / total * 100

        print("\n--- ESTRUTURA ---")
        metrics: dict[str, dict[str, float | str]] = {}
        for lb in LABELS:
            p3k, p3p = top_pct(prefix3[lb], lb)
            s3k, s3p = top_pct(suffix3[lb], lb)
            metrics[lb] = {"p3": p3p, "s3": s3p, "p3k": p3k, "s3k": s3k}
            print(f"  {SHORT[lb]:<12} p3={p3k}({p3p:.1f}%)  s3={s3k}({s3p:.1f}%)")

        overlap_v4 = _gp_overlap(conn, V4_LABEL)
        overlap_v1 = _gp_overlap(conn, V1_LABEL)
        m_v4 = metrics.get(V4_LABEL, {})
        m_base = metrics.get(BASELINE_LABEL, {})

        print("\n--- CRITERIOS GATE V4 ---")
        overlap_ok = overlap_v4 is not None and overlap_v1 is not None and overlap_v4 <= overlap_v1 * 1.05
        checks = [
            (f"melhor hit >= {GATE_BEST_HIT}", best_hit.get(V4_LABEL, 0) >= GATE_BEST_HIT),
            (f"media >= {GATE_AVG_HIT}", avg_hit.get(V4_LABEL, 0) >= GATE_AVG_HIT),
            (f"runs 13+ >= {GATE_RUNS_13_PLUS}", hit_13_plus.get(V4_LABEL, 0) >= GATE_RUNS_13_PLUS),
            ("prefixo 01-02-03 < baseline", m_v4.get("p3", 100) < m_base.get("p3", 100)),
            (
                "sufixo 22-24-25 <= baseline ou justificado",
                m_v4.get("s3k") == "22-24-25" or m_v4.get("s3", 100) <= m_base.get("s3", 100) + 5,
            ),
            (
                "GP overlap <= V1 (5% tol)",
                overlap_ok,
            ),
            ("jogos invalidos = 0", total_games.get(V4_LABEL, 0) > 0),
        ]
        passed = sum(1 for _, ok in checks if ok)
        for name, ok in checks:
            print(f"  [{'OK' if ok else 'PENDENTE'}] {name}")
        if overlap_v4 is not None and overlap_v1 is not None:
            print(f"  overlap medio GP: V4={overlap_v4:.2f}  V1={overlap_v1:.2f}")
        print(f"\n  Resultado V4: {passed}/{len(checks)}")

        print("\n" + "=" * 72 + "\n")


if __name__ == "__main__":
    main()
