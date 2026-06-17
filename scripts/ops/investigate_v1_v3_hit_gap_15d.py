#!/usr/bin/env python3
"""Investigação preliminar: por que V3 = V2 em hits e ambos << V1 (baseline 15D).

Uso:
  python scripts/ops/investigate_v1_v3_hit_gap_15d.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

from lotoia.generation.core_realignment_v3 import filter_pool_soft
from lotoia.governance.lei15_15a_core_realignment_v3 import CoreRealignmentV3Config

LABELS = {
    "V1": "STRUCT_REALIGN_V1_15D_001",
    "V2": "STRUCT_CORE_REALIGN_V2_15D_001",
    "V3": "STRUCT_CORE_REALIGN_V3_BALANCED_15D_001",
}
CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)

DEDUPED_RUNS_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (rr.generation_event_id, rr.contest_id)
        rr.id AS run_id,
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


def fmt_key(nums: tuple[int, ...]) -> str:
    return "-".join(f"{x:02d}" for x in nums)


def gaps(nums: list[int]) -> list[int]:
    s = sorted(nums)
    return [s[i + 1] - s[i] for i in range(len(s) - 1)]


def gap_signature(nums: list[int]) -> str:
    return ",".join(str(g) for g in gaps(nums))


@dataclass
class GameRow:
    label: str
    ge_id: int
    contest_number: int
    game_index: int
    hits: int
    numbers: list[int]
    context: dict[str, Any]

    @property
    def prefix3(self) -> tuple[int, ...]:
        s = sorted(self.numbers)
        return tuple(s[:3])

    @property
    def suffix3(self) -> tuple[int, ...]:
        s = sorted(self.numbers)
        return tuple(s[-3:])


def q(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def load_high_hit_games(conn, batch_label: str, min_hits: int) -> list[GameRow]:
    rows = q(
        conn,
        f"""
        {DEDUPED_RUNS_SQL}
        SELECT d.generation_event_id, d.contest_id, rg.game_index, rg.hits,
               rg.numbers, rg.context_json
        FROM deduped d
        JOIN reconciliation_games rg ON rg.reconciliation_run_id = d.run_id
        WHERE rg.hits >= %s
        ORDER BY rg.hits DESC, d.contest_id, d.generation_event_id, rg.game_index
        """,
        (batch_label, list(CONTESTS), min_hits),
    )
    out: list[GameRow] = []
    for ge_id, contest_id, game_index, hits, numbers, ctx in rows:
        nums = [int(x) for x in (numbers if isinstance(numbers, list) else json.loads(numbers))]
        out.append(
            GameRow(
                label=batch_label,
                ge_id=int(ge_id),
                contest_number=int(contest_id),
                game_index=int(game_index),
                hits=int(hits),
                numbers=nums,
                context=dict(ctx or {}),
            )
        )
    return out


def load_all_games(conn, batch_label: str) -> list[GameRow]:
    rows = q(
        conn,
        """
        SELECT ge.id, gg.game_index, gg.numbers, gg.context_json
        FROM generated_games gg
        JOIN generation_events ge ON ge.id = gg.generation_event_id
        WHERE ge.analysis_batch_label = %s
        ORDER BY ge.id, gg.game_index
        """,
        (batch_label,),
    )
    out: list[GameRow] = []
    for ge_id, game_index, numbers, ctx in rows:
        nums = [int(x) for x in (numbers if isinstance(numbers, list) else json.loads(numbers))]
        out.append(
            GameRow(
                label=batch_label,
                ge_id=int(ge_id),
                contest_number=0,
                game_index=int(game_index),
                hits=0,
                numbers=nums,
                context=dict(ctx or {}),
            )
        )
    return out


def counter_pct(counter: Counter, total: int) -> list[tuple[str, int, float]]:
    return [(k, n, n / max(total, 1) * 100) for k, n in counter.most_common()]


def game_to_pool_dict(g: GameRow) -> dict:
    ctx = g.context
    return {
        "numbers": g.numbers,
        "profile_score": float(ctx.get("profile_score", 0) or 0),
        "final_score": {"final_score": float((ctx.get("final_score") or {}).get("final_score", ctx.get("final_score", 0)) or 0)},
    }


def simulate_v3_prefilter(games: list[GameRow]) -> dict[str, Any]:
    cfg = CoreRealignmentV3Config()
    pool = [game_to_pool_dict(g) for g in games]
    filtered, applied, _ = filter_pool_soft(pool, config=cfg)
    kept = {tuple(sorted(x["numbers"])) for x in filtered}
    removed = [g for g in games if tuple(sorted(g.numbers)) not in kept]
    cap = max(2, int(len(pool) * cfg.max_pool_prefix3_ratio))
    prefix_groups = Counter(fmt_key(g.prefix3) for g in games)
    return {
        "pool_size": len(pool),
        "filtered_size": len(filtered),
        "pre_filter_applied": applied,
        "cap_per_prefix3": cap,
        "removed_count": len(removed),
        "removed_by_prefix3": Counter(fmt_key(g.prefix3) for g in removed),
        "prefix_groups_over_cap": {
            k: v for k, v in prefix_groups.items() if v > cap
        },
    }


def score_order_analysis(games: list[GameRow]) -> dict[str, Any]:
    scored = []
    for g in games:
        ctx = g.context
        base = float(ctx.get("profile_score", 0) or 0) * 100.0
        fs = ctx.get("final_score")
        if isinstance(fs, dict):
            base += float(fs.get("final_score", 0) or 0)
        elif fs is not None:
            base += float(fs)
        scored.append((base, g))
    scored.sort(key=lambda x: x[0], reverse=True)
    top50 = scored[:50]
    return {
        "has_scores": sum(1 for s, _ in scored if s > 0),
        "top50_prefix3": Counter(fmt_key(g.prefix3) for _, g in top50),
        "top50_suffix3": Counter(fmt_key(g.suffix3) for _, g in top50),
    }


def compare_game_sets(v1_games: list[GameRow], other_games: list[GameRow]) -> dict[str, Any]:
    v1_sigs = {tuple(sorted(g.numbers)) for g in v1_games}
    other_sigs = {tuple(sorted(g.numbers)) for g in other_games}
    return {
        "v1_unique_cards": len(v1_sigs),
        "other_unique_cards": len(other_sigs),
        "intersection": len(v1_sigs & other_sigs),
        "v1_only": len(v1_sigs - other_sigs),
        "other_only": len(other_sigs - v1_sigs),
    }


def structural_profile(games: list[GameRow], *, title: str) -> dict[str, Any]:
    prefix3 = Counter(fmt_key(g.prefix3) for g in games)
    suffix3 = Counter(fmt_key(g.suffix3) for g in games)
    digits = Counter(d for g in games for d in g.numbers)
    gap_sig = Counter(gap_signature(g.numbers) for g in games)
    total = len(games) or 1
    return {
        "title": title,
        "count": len(games),
        "prefix3_top5": counter_pct(prefix3, total)[:5],
        "suffix3_top5": counter_pct(suffix3, total)[:5],
        "digits_top10": counter_pct(digits, len(games) * 15 if games else 1)[:10],
        "gap_top5": gap_sig.most_common(5),
    }


def print_section(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        v1_13 = load_high_hit_games(conn, LABELS["V1"], 13)
        v1_14 = [g for g in v1_13 if g.hits >= 14]
        v2_13 = load_high_hit_games(conn, LABELS["V2"], 13)
        v3_13 = load_high_hit_games(conn, LABELS["V3"], 13)
        v3_best = load_high_hit_games(conn, LABELS["V3"], 11)

        v1_all = load_all_games(conn, LABELS["V1"])
        v2_all = load_all_games(conn, LABELS["V2"])
        v3_all = load_all_games(conn, LABELS["V3"])

        # Per-run best hits distribution
        hit_rows = q(
            conn,
            f"""
            {DEDUPED_RUNS_SQL}
            SELECT analysis_batch_label, best_hits, COUNT(*)
            FROM deduped
            GROUP BY analysis_batch_label, best_hits
            ORDER BY analysis_batch_label, best_hits DESC
            """,
            (list(LABELS.values()), list(CONTESTS)),
        )

    print_section("RELATÓRIO TÉCNICO PRELIMINAR — V1 vs V2/V3 (15D baseline 3705-3711)")
    print("Objetivo: identificar o que V1 preservou e V2/V3 destruíram.")
    print("Status: PRELIMINAR — não substitui ADR-045.")

    print_section("1. Jogos V1 com 13+ e 14+ hits")
    print(f"  V1 jogos >=13 hits (por jogo×concurso): {len(v1_13)}")
    print(f"  V1 jogos >=14 hits: {len(v1_14)}")
    print(f"  V2 jogos >=13 hits: {len(v2_13)}")
    print(f"  V3 jogos >=13 hits: {len(v3_13)}")
    print(f"  V3 jogos >=11 hits (melhor faixa observada): {len(v3_best)}")

    if v1_14:
        print("\n  Amostra V1 14+ (concurso | GE | idx | hits | cartão | p3 | s3 | gaps):")
        for g in v1_14[:12]:
            print(
                f"    C{g.contest_number} GE{g.ge_id} #{g.game_index} H{g.hits} "
                f"{fmt_key(tuple(g.numbers))} p3={fmt_key(g.prefix3)} s3={fmt_key(g.suffix3)} "
                f"gaps=[{gap_signature(g.numbers)}]"
            )

    print_section("2. Estrutura dos jogos V1 13+ (prefixo/sufixo/dezenas/gaps)")
    prof_v1_13 = structural_profile(v1_13, title="V1 >=13")
    prof_v1_all = structural_profile(v1_all, title="V1 all GP")
    for key in ("prefix3_top5", "suffix3_top5", "digits_top10", "gap_top5"):
        print(f"\n  V1 >=13 {key}:")
        print(f"    {prof_v1_13[key]}")
        print(f"  V1 all  {key}:")
        print(f"    {prof_v1_all[key]}")

    print_section("3. V2/V3 eliminaram padrões V1 13+?")
    v1_13_sigs = {tuple(sorted(g.numbers)) for g in v1_13}
    v2_sigs = {tuple(sorted(g.numbers)) for g in v2_all}
    v3_sigs = {tuple(sorted(g.numbers)) for g in v3_all}
    print(f"  Cartões únicos V1 >=13 hits: {len(v1_13_sigs)}")
    print(f"  Presentes em V2 GP (1000 jogos): {len(v1_13_sigs & v2_sigs)}")
    print(f"  Presentes em V3 GP (1000 jogos): {len(v1_13_sigs & v3_sigs)}")
    print(f"  Ausentes em V2: {len(v1_13_sigs - v2_sigs)}")
    print(f"  Ausentes em V3: {len(v1_13_sigs - v3_sigs)}")

    v1_p3_13 = Counter(fmt_key(g.prefix3) for g in v1_13)
    v3_p3_all = Counter(fmt_key(g.prefix3) for g in v3_all)
    print("\n  Prefixo-3 em V1>=13 vs freq no GP V3:")
    for p3, n in v1_p3_13.most_common(8):
        v3_n = v3_p3_all.get(p3, 0)
        v3_pct = v3_n / max(len(v3_all), 1) * 100
        print(f"    p3={p3}  V1_13+={n}  V3_GP={v3_n} ({v3_pct:.1f}%)")

    v2v3 = compare_game_sets(v2_all, v3_all)
    print("\n  Similaridade V2 vs V3 (GP completo):")
    print(f"    {v2v3}")

    print_section("4. Pre-filter V3 — impacto simulado no GP V1")
    # Simulate on one representative GE from V1
    sample_ge = v1_all[0].ge_id if v1_all else 0
    ge_games = [g for g in v1_all if g.ge_id == sample_ge]
    sim = simulate_v3_prefilter(ge_games)
    print(f"  GE amostra V1={sample_ge} pool={sim['pool_size']} cap_p3={sim['cap_per_prefix3']}")
    print(f"  pre_filter_applied={sim['pre_filter_applied']} removed={sim['removed_count']}")
    print(f"  grupos p3 acima do cap: {sim['prefix_groups_over_cap']}")
    if sim["removed_by_prefix3"]:
        print(f"  removidos por p3: {dict(sim['removed_by_prefix3'].most_common(5))}")

    # Would V1 13+ cards survive pre-filter in their source GE?
    removed_high = 0
    checked = 0
    cfg = CoreRealignmentV3Config()
    for g in v1_13:
        ge_games = [x for x in v1_all if x.ge_id == g.ge_id]
        if len(ge_games) < 10:
            continue
        filtered_pool, _, _ = filter_pool_soft(
            [game_to_pool_dict(x) for x in ge_games],
            config=cfg,
        )
        kept = {tuple(sorted(x["numbers"])) for x in filtered_pool}
        checked += 1
        if tuple(sorted(g.numbers)) not in kept:
            removed_high += 1
    print(f"\n  V1>=13 testados contra pre-filter no GE origem: {checked}")
    print(f"  V1>=13 que seriam REMOVIDOS pelo pre-filter V3: {removed_high}")

    print_section("5. base_score_weight=0.002 — ordem vs composição")
    v3_scores = score_order_analysis(v3_all)
    v1_scores = score_order_analysis(v1_all)
    print(f"  V1 jogos com score>0 no context: {v1_scores['has_scores']}/1000")
    print(f"  V3 jogos com score>0 no context: {v3_scores['has_scores']}/1000")
    print(f"  Top50 V1 prefix3: {dict(v1_scores['top50_prefix3'].most_common(5))}")
    print(f"  Top50 V3 prefix3: {dict(v3_scores['top50_prefix3'].most_common(5))}")
    cfg = CoreRealignmentV3Config()
    print(
        f"  Peso estrutural vs base: concentration_penalty_weight={cfg.concentration_penalty_weight} "
        f"base_score_weight={cfg.base_score_weight}"
    )
    print(
        "  Leitura: penalidade estrutural (~42× excesso ratio) domina base_score×0.002 "
        "(tipicamente <0.2 por jogo)."
    )

    print_section("6. max_prefix3_ratio=0.32 — concentração GP V3")
    for name, games in [("V1", v1_all), ("V2", v2_all), ("V3", v3_all)]:
        by_ge: dict[int, list[GameRow]] = defaultdict(list)
        for g in games:
            by_ge[g.ge_id].append(g)
        over_cap = 0
        for ge_id, ge_g in by_ge.items():
            c = Counter(fmt_key(x.prefix3) for x in ge_g)
            cap = int(len(ge_g) * 0.32)
            if any(n > max(cap, 1) for n in c.values()):
                over_cap += 1
        top_p3 = Counter(fmt_key(g.prefix3) for g in games)
        top = top_p3.most_common(1)[0] if top_p3 else ("-", 0)
        pct = top[1] / max(len(games), 1) * 100
        print(f"  {name}: p3 dominante {top[0]}={pct:.1f}%  GEs com p3>32%={over_cap}/{len(by_ge)}")

    print_section("7. Dezenas nos bons jogos V1 ausentes na V3")
    v1_13_digits = Counter(d for g in v1_13 for d in g.numbers)
    v3_digits = Counter(d for g in v3_all for d in g.numbers)
    v1_all_digits = Counter(d for g in v1_all for d in g.numbers)
    print("  Dezena | freq V1>=13 | freq V1 GP | freq V3 GP | delta V3 vs V1>=13")
    for d, n13 in v1_13_digits.most_common(15):
        v1gp = v1_all_digits.get(d, 0) / max(len(v1_all) * 15, 1) * 100
        v3gp = v3_digits.get(d, 0) / max(len(v3_all) * 15, 1) * 100
        p13 = n13 / max(len(v1_13) * 15, 1) * 100
        print(f"    {d:02d}   {p13:5.1f}%       {v1gp:5.1f}%       {v3gp:5.1f}%       {v3gp - p13:+5.1f}pp")

    missing_in_v3 = []
    for d, n13 in v1_13_digits.items():
        v3_rate = v3_digits.get(d, 0) / max(len(v3_all) * 15, 1)
        v1_13_rate = n13 / max(len(v1_13) * 15, 1)
        if v1_13_rate - v3_rate > 0.02:
            missing_in_v3.append((d, v1_13_rate - v3_rate))
    missing_in_v3.sort(key=lambda x: x[1], reverse=True)
    print(f"\n  Dezenas sub-representadas na V3 vs V1>=13 (>2pp): {[d for d, _ in missing_in_v3[:10]]}")

    print_section("8. V1 14+ vs melhores hits V3 (11)")
    v3_11 = [g for g in v3_best if g.hits == 11]
    print(f"  V1 14+ jogos: {len(v1_14)}")
    print(f"  V3 melhor hit=11 jogos: {len(v3_11)}")
    if v1_14 and v3_11:
        print("\n  V1 14+ exemplo vs V3 H11 exemplo (concurso 3707 — melhor V3):")
        v1_ex = next((g for g in v1_14 if g.contest_number == 3707), v1_14[0])
        v3_ex = next((g for g in v3_11 if g.contest_number == 3707), v3_11[0])
        off = set()  # filled below
        print(f"    V1 H{v1_ex.hits} C{v1_ex.contest_number}: {sorted(v1_ex.numbers)}")
        print(f"      p3={fmt_key(v1_ex.prefix3)} s3={fmt_key(v1_ex.suffix3)} gaps={gap_signature(v1_ex.numbers)}")
        print(f"    V3 H{v3_ex.hits} C{v3_ex.contest_number}: {sorted(v3_ex.numbers)}")
        print(f"      p3={fmt_key(v3_ex.prefix3)} s3={fmt_key(v3_ex.suffix3)} gaps={gap_signature(v3_ex.numbers)}")
        shared = set(v1_ex.numbers) & set(v3_ex.numbers)
        print(f"    Interseção dezenas: {len(shared)} -> {sorted(shared)}")

    print_section("DISTRIBUIÇÃO best_hits por run (oficial)")
    by_label: dict[str, Counter] = defaultdict(Counter)
    for label, best_hits, n in hit_rows:
        by_label[label][best_hits] = n
    for short, lb in LABELS.items():
        c = by_label[lb]
        total = sum(c.values())
        print(f"  {short}: {dict(sorted(c.items(), reverse=True))} (n={total})")

    print_section("HIPÓTESE + PROPOSTA PRELIMINAR (V3.1 / V4)")
    print(
        """
  Achados prováveis:
  • V2 e V3 compartilham pool pre-filter + penalidades estruturais agressivas.
  • V1>=13/14 cartões quase nunca aparecem no GP V2/V3 (recomposição elimina padrões).
  • base_score_weight=0.002 não recupera candidatos de alto score Lei15.
  • max_prefix3_ratio=0.32 ainda permite diversificar, mas compose prioriza bonus/penalty.
  • Dezenas que V1 usa nos near-miss fortes ficam sub-representadas na V3.

  V3.1 (ajuste fino, mesmo ADR):
    - base_score_weight: 0.002 → 0.008..0.015
    - max_prefix3_ratio: 0.32 → 0.38 (aproximar V1 0.25→efetivo 40%)
    - max_pool_prefix3_ratio: 0.42 → 0.50 (menos corte no pool)
    - Manter hits-first: não retighten suffix se hits caírem

  V4 (se V3.1 falhar):
    - Camada híbrida: reservar 20-30% do GP por top base_score (sem penalty)
    - Restante composto com diversidade V3
    - Ou: pre-filter só quando p3>45% no pool (gatilho condicional)
"""
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
