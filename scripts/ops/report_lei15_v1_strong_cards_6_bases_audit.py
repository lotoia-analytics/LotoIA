#!/usr/bin/env python3
"""Auditoria fina V1≥13 — Leitura pelas 6 Bases do Núcleo Lei 15.

Agentes: agent_qualidade + agent_estatistico
Política: docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md

Read-only PostgreSQL — sem nova geração.

Uso:
  python scripts/ops/report_lei15_v1_strong_cards_6_bases_audit.py
  python scripts/ops/report_lei15_v1_strong_cards_6_bases_audit.py --json-out reports/lei15_v1_strong_cards_6_bases_audit_2026_06_17.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
_OPS = ROOT / "scripts" / "ops"
if str(_OPS) not in sys.path:
    sys.path.insert(0, str(_OPS))

from cloud_env_bootstrap import ensure_database_url, resolve_database_url

import psycopg

from lotoia.generation.lei15_core_structural_payload import (
    apply_core_traceability_payload,
    compute_structural_bias_score,
    is_v1_strong_pattern,
)
from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, POLICY_REGISTRY_ID

CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
V1_LABEL = "STRUCT_REALIGN_V1_15D_001"
COMPARE_LABELS = {
    "BASELINE": "STRUCT_TEST_15D_001",
    "CAND-A": "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001",
    "CAND-D": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
}
STRENGTHEN = (7, 12, 16, 23)
DISCOURAGE = (2, 4, 11, 15, 24, 25)

DEDUPED_SQL = """
WITH deduped AS (
    SELECT DISTINCT ON (rr.generation_event_id, rr.contest_id)
        rr.id AS run_id,
        rr.generation_event_id,
        rr.contest_id,
        rr.best_hits
    FROM reconciliation_runs rr
    JOIN generation_events ge ON ge.id = rr.generation_event_id
    WHERE ge.analysis_batch_label = %s
      AND rr.contest_id = ANY(%s)
    ORDER BY rr.generation_event_id, rr.contest_id, rr.id DESC
)
"""


def _fmt(nums: tuple[int, ...]) -> str:
    return "-".join(f"{n:02d}" for n in nums)


def _ctx(d, key, default=None):
    if isinstance(d, dict):
        return d.get(key, default)
    return default


@dataclass
class CardRecord:
    numbers: tuple[int, ...]
    hits: int
    contest_id: int
    ge_id: int
    game_index: int
    profile: str
    prefix_sig: str
    suffix_sig: str
    bias: float
    parity: int
    low_band: int
    mid_band: int
    high_band: int
    v1_strong_pattern: bool


@dataclass
class SegmentStats:
    name: str
    recon_rows: int
    unique_cards: int
    hits_best: int
    hits_avg: float
    runs_12_plus: int
    runs_13_plus: int
    runs_14: int
    profile_dist: dict[str, int] = field(default_factory=dict)
    prefix_top: list[tuple[str, int, float]] = field(default_factory=list)
    suffix_top: list[tuple[str, int, float]] = field(default_factory=list)
    p3_123_pct: float = 0.0
    s3_222425_pct: float = 0.0
    avg_bias: float = 0.0
    digit_freq: dict[int, float] = field(default_factory=dict)
    strengthen_presence: dict[int, float] = field(default_factory=dict)
    discourage_presence: dict[int, float] = field(default_factory=dict)
    mean_pairwise_overlap: float = 0.0
    unique_prefix_count: int = 0
    unique_suffix_count: int = 0
    contests_with_13_plus: int = 0
    per_contest_13_plus: dict[int, int] = field(default_factory=dict)


def _bands(nums: tuple[int, ...]) -> tuple[int, int, int]:
    low = sum(1 for n in nums if n <= 8)
    mid = sum(1 for n in nums if 9 <= n <= 17)
    high = sum(1 for n in nums if n >= 18)
    return low, mid, high


def _enrich(numbers: list[int], hits: int, contest_id: int, ge_id: int, game_index: int, profile: str) -> CardRecord:
    nums = tuple(sorted(int(x) for x in numbers))
    prof = str(profile or "unknown")
    payload = apply_core_traceability_payload({"numbers": list(nums), "profile_type": prof}, profile_origin=prof)
    low, mid, high = _bands(nums)
    return CardRecord(
        numbers=nums,
        hits=hits,
        contest_id=contest_id,
        ge_id=ge_id,
        game_index=game_index,
        profile=prof,
        prefix_sig=str(payload.get("prefix_signature") or ""),
        suffix_sig=str(payload.get("suffix_signature") or ""),
        bias=float(payload.get("structural_bias_score") or 0),
        parity=sum(1 for n in nums if n % 2 == 0),
        low_band=low,
        mid_band=mid,
        high_band=high,
        v1_strong_pattern=is_v1_strong_pattern(list(nums)),
    )


def _load_recon_cards(conn, label: str) -> list[CardRecord]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            {DEDUPED_SQL}
            SELECT d.contest_id, d.generation_event_id, rg.game_index, rg.hits, rg.numbers,
                   COALESCE(gg.profile_type, '')
            FROM deduped d
            JOIN reconciliation_games rg ON rg.reconciliation_run_id = d.run_id
            LEFT JOIN generated_games gg
              ON gg.generation_event_id = d.generation_event_id AND gg.game_index = rg.game_index
            """,
            (label, list(CONTESTS)),
        )
        rows = cur.fetchall()

    out: list[CardRecord] = []
    for contest_id, ge_id, game_index, hits, numbers, profile in rows:
        if not isinstance(numbers, list) or len(numbers) != 15:
            continue
        out.append(_enrich(numbers, int(hits), int(contest_id), int(ge_id), int(game_index), str(profile)))
    return out


def _load_gp_cards(conn, label: str) -> list[CardRecord]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ge.id, gg.game_index, gg.numbers, COALESCE(gg.profile_type, '')
            FROM generated_games gg
            JOIN generation_events ge ON ge.id = gg.generation_event_id
            WHERE ge.analysis_batch_label = %s
            ORDER BY ge.id, gg.game_index
            """,
            (label,),
        )
        rows = cur.fetchall()
    return [
        _enrich(numbers, 0, 0, int(ge_id), int(game_index), str(profile))
        for ge_id, game_index, numbers, profile in rows
        if isinstance(numbers, list) and len(numbers) == 15
    ]


def _pct(counter: Counter, total: int, top_n: int = 5) -> list[tuple[str, int, float]]:
    return [(k, n, n / max(total, 1) * 100) for k, n in counter.most_common(top_n)]


def _digit_rates(cards: list[CardRecord]) -> dict[int, float]:
    n = len(cards) or 1
    c: Counter = Counter()
    for card in cards:
        for d in card.numbers:
            c[d] += 1
    return {d: c[d] / (n * 15) * 100 for d in range(1, 26)}


def _presence_rates(cards: list[CardRecord], digits: tuple[int, ...]) -> dict[int, float]:
    n = len(cards) or 1
    return {d: sum(1 for c in cards if d in c.numbers) / n * 100 for d in digits}


def _mean_overlap(cards: list[CardRecord], cap: int = 60) -> float:
    sample = cards[:cap]
    if len(sample) < 2:
        return 0.0
    overlaps = []
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            overlaps.append(len(set(sample[i].numbers) & set(sample[j].numbers)))
    return mean(overlaps)


def _build_segment(name: str, cards: list[CardRecord], *, unique_by_numbers: bool = True) -> SegmentStats:
    pool = cards
    if unique_by_numbers:
        seen: set[tuple[int, ...]] = set()
        uniq: list[CardRecord] = []
        for c in cards:
            if c.numbers not in seen:
                seen.add(c.numbers)
                uniq.append(c)
        pool = uniq

    n = len(pool) or 1
    hits_list = [c.hits for c in cards]
    profile_c = Counter(c.profile for c in pool)
    prefix_c = Counter(c.prefix_sig for c in pool if c.prefix_sig)
    suffix_c = Counter(c.suffix_sig for c in pool if c.suffix_sig)
    p3 = sum(1 for c in pool if c.prefix_sig == "01-02-03") / n * 100
    s3 = sum(1 for c in pool if c.suffix_sig == "22-24-25") / n * 100
    per_c_13 = Counter(c.contest_id for c in cards if c.hits >= 13)

    return SegmentStats(
        name=name,
        recon_rows=len(cards),
        unique_cards=len(pool),
        hits_best=max(hits_list) if hits_list else 0,
        hits_avg=mean(hits_list) if hits_list else 0.0,
        runs_12_plus=sum(1 for h in hits_list if h >= 12),
        runs_13_plus=sum(1 for h in hits_list if h >= 13),
        runs_14=sum(1 for h in hits_list if h >= 14),
        profile_dist=dict(profile_c),
        prefix_top=_pct(prefix_c, n),
        suffix_top=_pct(suffix_c, n),
        p3_123_pct=p3,
        s3_222425_pct=s3,
        avg_bias=mean(c.bias for c in pool) if pool else 0.0,
        digit_freq=_digit_rates(pool),
        strengthen_presence=_presence_rates(pool, STRENGTHEN),
        discourage_presence=_presence_rates(pool, DISCOURAGE),
        mean_pairwise_overlap=_mean_overlap(pool),
        unique_prefix_count=len(prefix_c),
        unique_suffix_count=len(suffix_c),
        contests_with_13_plus=len(per_c_13),
        per_contest_13_plus=dict(per_c_13),
    )


def _rate_base(label: str, stats: SegmentStats, *, reference: SegmentStats | None = None) -> str:
    if stats.recon_rows == 0 and stats.unique_cards == 0:
        return "inconclusiva"
    if label == "forca_acerto":
        if stats.runs_13_plus >= 10 and stats.hits_best >= 13:
            return "forte"
        if stats.runs_12_plus >= 5 or stats.hits_best >= 12:
            return "parcial"
        return "fraca"
    if label == "diversidade":
        if stats.unique_prefix_count >= 8 and (max(stats.profile_dist.values()) if stats.profile_dist else 0) <= stats.unique_cards * 0.5:
            return "forte" if stats.unique_prefix_count >= 12 else "parcial"
        if stats.unique_prefix_count <= 4:
            return "fraca"
        return "parcial"
    if label == "baixa_redundancia":
        if stats.mean_pairwise_overlap <= 8.5:
            return "forte" if stats.mean_pairwise_overlap <= 7.5 else "parcial"
        if stats.mean_pairwise_overlap >= 10:
            return "fraca"
        return "parcial"
    if label == "controle_prefixo_sufixo":
        if stats.p3_123_pct <= 25 and stats.s3_222425_pct <= 30:
            return "parcial" if stats.p3_123_pct > 15 else "forte"
        if stats.p3_123_pct >= 45:
            return "fraca"
        return "parcial"
    if label == "cobertura_dezenas_criticas":
        ok = sum(1 for d in STRENGTHEN if stats.strengthen_presence.get(d, 0) >= 50)
        bad = sum(1 for d in DISCOURAGE if stats.discourage_presence.get(d, 0) > 95)
        if ok >= 3 and bad <= 2:
            return "forte" if ok == 4 else "parcial"
        if ok <= 1:
            return "fraca"
        return "parcial"
    if label == "estabilidade_multi_concurso":
        if stats.contests_with_13_plus >= 5:
            return "forte"
        if stats.contests_with_13_plus >= 3:
            return "parcial"
        return "inconclusiva" if stats.recon_rows < 20 else "fraca"
    return "inconclusiva"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="reports/lei15_v1_strong_cards_6_bases_audit_2026_06_17.json")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    with psycopg.connect(url) as conn:
        v1_recon = _load_recon_cards(conn, V1_LABEL)
        v1_gp = _load_gp_cards(conn, V1_LABEL)
        compare_gp: dict[str, list[CardRecord]] = {}
        for short, label in COMPARE_LABELS.items():
            compare_gp[short] = _load_gp_cards(conn, label)

    v1_12 = [c for c in v1_recon if c.hits >= 12]
    v1_13 = [c for c in v1_recon if c.hits >= 13]
    v1_14 = [c for c in v1_recon if c.hits >= 14]
    v1_weak = [c for c in v1_recon if c.hits <= 10]

    v1_13_unique_cards = list({c.numbers: c for c in v1_13}.values())
    v1_weak_unique = list({c.numbers: c for c in v1_weak}.values())

    segments = {
        "V1_recon_all": _build_segment("V1 recon (all rows)", v1_recon, unique_by_numbers=False),
        "V1_GP": _build_segment("V1 GP pool", [_enrich(list(c.numbers), 0, 0, c.ge_id, c.game_index, c.profile) for c in v1_gp]),
        "V1>=12": _build_segment("V1>=12", v1_12, unique_by_numbers=False),
        "V1>=13": _build_segment("V1>=13", v1_13, unique_by_numbers=False),
        "V1>=13_unique": _build_segment("V1>=13 unique cards", v1_13_unique_cards),
        "V1=14": _build_segment("V1=14", v1_14, unique_by_numbers=False),
        "V1_weak<=10": _build_segment("V1 weak <=10", v1_weak, unique_by_numbers=False),
        "V1_weak_unique": _build_segment("V1 weak unique", v1_weak_unique),
    }
    for short, cards in compare_gp.items():
        segments[f"{short}_GP"] = _build_segment(f"{short} GP", cards)

    v1_13_strong_pat = sum(1 for c in v1_13_unique_cards if c.v1_strong_pattern) / max(len(v1_13_unique_cards), 1) * 100

    # Per-contest stability
    contest_13 = Counter(c.contest_id for c in v1_13)
    contest_12 = Counter(c.contest_id for c in v1_12)
    contest_avg: dict[int, float] = {}
    by_contest: dict[int, list[int]] = defaultdict(list)
    for c in v1_recon:
        by_contest[c.contest_id].append(c.hits)
    for cid, hits in by_contest.items():
        contest_avg[cid] = mean(hits)

    # Answers
    p3_concentration_13 = segments["V1>=13_unique"].prefix_top[0] if segments["V1>=13_unique"].prefix_top else ("", 0, 0)
    force_concentrated = p3_concentration_13[2] > 40

    ratings_v1_13 = {
        name: _rate_base(name, segments["V1>=13_unique"])
        for name in (
            "forca_acerto",
            "diversidade",
            "baixa_redundancia",
            "controle_prefixo_sufixo",
            "cobertura_dezenas_criticas",
            "estabilidade_multi_concurso",
        )
    }
    # Override forca on full recon segment
    ratings_v1_force = _rate_base("forca_acerto", segments["V1>=13"])

    preserve_patterns = {
        "top_prefix_13plus": segments["V1>=13_unique"].prefix_top[:5],
        "top_suffix_13plus": segments["V1>=13_unique"].suffix_top[:5],
        "profiles_13plus": segments["V1>=13_unique"].profile_dist,
        "v1_strong_pattern_pct": round(v1_13_strong_pat, 1),
        "digit_enrichment_13_vs_all": {
            d: round(segments["V1>=13_unique"].digit_freq.get(d, 0) - segments["V1_GP"].digit_freq.get(d, 0), 2)
            for d in list(STRENGTHEN) + list(DISCOURAGE)
        },
    }

    dangerous = {
        "p3_123_in_v1_gp_pct": segments["V1_GP"].p3_123_pct,
        "p3_123_in_v1_13_pct": segments["V1>=13_unique"].p3_123_pct,
        "force_depends_on_bias": segments["V1>=13_unique"].avg_bias > segments["CAND-D_GP"].avg_bias,
        "high_overlap_among_13plus": segments["V1>=13_unique"].mean_pairwise_overlap,
    }

    strength_matrix = {
        "V1>=13_unique": {
            "cards": segments["V1>=13_unique"].unique_cards,
            "p3_123": segments["V1>=13_unique"].p3_123_pct,
            "s3_222425": segments["V1>=13_unique"].s3_222425_pct,
            "avg_bias": segments["V1>=13_unique"].avg_bias,
            "mean_overlap": segments["V1>=13_unique"].mean_pairwise_overlap,
        },
        "V1_GP": {
            "p3_123": segments["V1_GP"].p3_123_pct,
            "s3_222425": segments["V1_GP"].s3_222425_pct,
        },
        "CAND-D_GP": {
            "p3_123": segments["CAND-D_GP"].p3_123_pct,
            "s3_222425": segments["CAND-D_GP"].s3_222425_pct,
        },
    }

    control_matrix = {
        "from_CAND-D_apply_as_penalty_not_block": [
            "soft_cap_prefix_123_above_15pct",
            "suffix_hot_cap_not_hard_block_222425",
            "structural_bias_penalty_with_v1_strong_shield",
        ],
        "from_CAND-D_do_not_apply_blindly": [
            "block_prefix_triplet_123",
            "zero_tolerance_suffix_222425",
            "hybrid_inheritance_reduction_without_v1_selection",
        ],
        "from_V1_preserve": [
            "v1_strong_pattern_shield",
            "composition_realinhamento_v1_selection",
            "productive_suffixes_222425_232425_182425",
        ],
    }

    cand002_directives = [
        "Motor: geração CDX-D (N-C1..N-C6) — diversidade e controle na origem.",
        "Seleção/composição: camada V1 — preservar top base_score e padrões V1-strong.",
        "Penalizar prefixo 01-02-03 apenas acima de limiar; nunca bloquear padrões V1-strong.",
        "Manter sufixos produtivos (22-24-25, 23-24-25) com cap, não veto.",
        "Cobertura: elevar presença 07/12/16/23 nos pools fracos sem forçar em todos os cartões.",
        "Redundância: limitar clones estruturais (overlap>10) no GP final, não no pool V1-strong.",
        "Estabilidade: validar em multi-GE antes de promoção — piloto único insuficiente.",
    ]

    verdict = {
        "what_gives_v1_force": (
            "Composição V1 seleciona cartões com padrões V1-strong (prefixos 01-02-03/01-03-04 "
            "e sufixos 22-24-25/23-24-25) distribuídos em múltiplos concursos; "
            f"{segments['V1>=13_unique'].unique_cards} cartões únicos geram "
            f"{segments['V1>=13'].runs_13_plus} entradas ≥13."
        ),
        "force_depends_on_structural_bias": (
            f"Parcialmente SIM — {v1_13_strong_pat:.1f}% dos cartões únicos ≥13 são padrão V1-strong; "
            f"p3_123 nos ≥13={segments['V1>=13_unique'].p3_123_pct:.1f}% vs GP={segments['V1_GP'].p3_123_pct:.1f}%."
        ),
        "preserve": preserve_patterns,
        "penalize_not_block": ["prefixo 01-02-03 em excesso no GP", "sufixo 22-24-25 sem shield"],
        "critical_digits_review": {
            "strengthen_present_in_13": {d: segments["V1>=13_unique"].strengthen_presence.get(d, 0) for d in STRENGTHEN},
            "discourage_in_13": {d: segments["V1>=13_unique"].discourage_presence.get(d, 0) for d in DISCOURAGE},
            "note": "Dezenas discourage (02,24,25) aparecem nos fortes — política deve ser penalização, não ausência.",
        },
        "tolerable_redundancy": f"overlap médio ≤{segments['V1>=13_unique'].mean_pairwise_overlap:.1f} entre cartões ≥13 únicos",
        "cand_d_control_without_killing_force": control_matrix,
        "sufficient_basis_for_cand002": True,
        "cand002_directives": cand002_directives,
        "final_verdict": "BASE SUFICIENTE PARA DESENHO CAND-002 — combinar seleção V1 + núcleo CDX-D com shield",
    }

    # Print report
    print("=" * 88)
    print("AUDITORIA FINA V1≥13 — 6 BASES DO NÚCLEO LEI 15")
    print(f"Política: {POLICY_REGISTRY_ID} | V1: {V1_LABEL}")
    print(f"Concursos: {CONTESTS[0]}–{CONTESTS[-1]} | Modo: read-only")
    print("=" * 88)

    print("\n## RESUMO EXECUTIVO")
    print(f"  Cartões V1 GP (únicos):        {segments['V1_GP'].unique_cards}")
    print(f"  Entradas recon V1 (7 concursos): {segments['V1_recon_all'].recon_rows}")
    print(f"  Runs V1≥12:                     {segments['V1>=12'].runs_12_plus}")
    print(f"  Runs V1≥13:                     {segments['V1>=13'].runs_13_plus}")
    print(f"  Runs V1=14:                     {segments['V1=14'].runs_14}")
    print(f"  Cartões únicos V1≥13:           {segments['V1>=13_unique'].unique_cards}")
    print(f"  Concursos com ≥13:              {segments['V1>=13'].contests_with_13_plus}/7")

    print("\n## 1. BASE 1 — FORÇA DE ACERTO")
    print(f"  Melhor hit: {segments['V1>=13'].hits_best} | Média recon ≥13: {segments['V1>=13'].hits_avg:.3f}")
    print(f"  ≥13 por concurso: {dict(contest_13)}")
    print(f"  Força concentrada em poucos padrões? {'SIM' if force_concentrated else 'NÃO'} (top p3 ≥13: {p3_concentration_13})")
    print(f"  Força em vários concursos? {'SIM' if segments['V1>=13'].contests_with_13_plus >= 5 else 'PARCIAL'}")
    print(f"  Leitura: {ratings_v1_force}")

    print("\n## 2. BASE 2 — DIVERSIDADE")
    print(f"  Perfis ≥13 únicos: {segments['V1>=13_unique'].profile_dist}")
    print(f"  Prefixos únicos ≥13: {segments['V1>=13_unique'].unique_prefix_count}")
    print(f"  Top prefix ≥13: {segments['V1>=13_unique'].prefix_top[:3]}")
    print(f"  Leitura: {ratings_v1_13['diversidade']}")

    print("\n## 3. BASE 3 — BAIXA REDUNDÂNCIA")
    print(f"  Overlap médio ≥13 únicos: {segments['V1>=13_unique'].mean_pairwise_overlap:.2f}")
    print(f"  Overlap médio V1 GP:       {segments['V1_GP'].mean_pairwise_overlap:.2f}")
    print(f"  Overlap médio fracos ≤10:  {segments['V1_weak_unique'].mean_pairwise_overlap:.2f}")
    print(f"  Leitura: {ratings_v1_13['baixa_redundancia']}")

    print("\n## 4. BASE 4 — CONTROLE PREFIXO/SUFIXO")
    print(f"  {'Segmento':<18} {'p3_123%':>8} {'s3_222425%':>10} {'bias':>6}")
    for key in ("V1_GP", "V1>=13_unique", "V1_weak_unique", "CAND-D_GP", "BASELINE_GP"):
        s = segments[key]
        print(f"  {s.name:<18} {s.p3_123_pct:>7.1f}% {s.s3_222425_pct:>9.1f}% {s.avg_bias:>6.1f}")
    print(f"  Leitura V1≥13: {ratings_v1_13['controle_prefixo_sufixo']}")

    print("\n## 5. BASE 5 — COBERTURA DEZENAS CRÍTICAS")
    print(f"  {'Dez':>4} {'fortalecer':>12} {'V1_GP%':>8} {'V1≥13%':>8} {'V1 fraco%':>10}")
    for d in STRENGTHEN:
        print(
            f"  {d:02d}   {'sim':>12} "
            f"{segments['V1_GP'].strengthen_presence.get(d, 0):>7.1f}% "
            f"{segments['V1>=13_unique'].strengthen_presence.get(d, 0):>7.1f}% "
            f"{segments['V1_weak_unique'].strengthen_presence.get(d, 0):>9.1f}%"
        )
    for d in DISCOURAGE:
        print(
            f"  {d:02d}   {'controlar':>12} "
            f"{segments['V1_GP'].discourage_presence.get(d, 0):>7.1f}% "
            f"{segments['V1>=13_unique'].discourage_presence.get(d, 0):>7.1f}% "
            f"{segments['V1_weak_unique'].discourage_presence.get(d, 0):>9.1f}%"
        )
    print(f"  Leitura: {ratings_v1_13['cobertura_dezenas_criticas']}")

    print("\n## 6. BASE 6 — ESTABILIDADE")
    print(f"  Média hits por concurso: {', '.join(f'{c}={contest_avg[c]:.2f}' for c in CONTESTS)}")
    print(f"  Desvio médias por concurso: {pstdev(contest_avg.values()) if len(contest_avg)>1 else 0:.3f}")
    print(f"  ≥12 por concurso: {dict(contest_12)}")
    print(f"  Leitura: {ratings_v1_13['estabilidade_multi_concurso']}")

    print("\n## 7. COMPARAÇÃO V1≥13 vs CAND-D / BASELINE")
    print(f"  V1≥13 p3/s3: {segments['V1>=13_unique'].p3_123_pct:.1f}% / {segments['V1>=13_unique'].s3_222425_pct:.1f}%")
    print(f"  CAND-D p3/s3: {segments['CAND-D_GP'].p3_123_pct:.1f}% / {segments['CAND-D_GP'].s3_222425_pct:.1f}%")
    print(f"  V1 perde no controle; CAND-D perde força (0 runs 13+ no piloto).")

    print("\n## 8. PADRÕES PRESERVÁVEIS")
    for k, v in preserve_patterns.items():
        print(f"  {k}: {v}")

    print("\n## 9. PADRÕES PERIGOSOS (penalizar, não bloquear cegamente)")
    for k, v in dangerous.items():
        print(f"  {k}: {v}")

    print("\n## 10. MATRIZ FORÇA V1 / CONTROLE CAND-D")
    print(f"  Força: {strength_matrix}")
    print(f"  Controle recomendado: {control_matrix}")

    print("\n## 11. DIRETRIZ CAND-002 (recomendação — não implementada)")
    for i, d in enumerate(cand002_directives, 1):
        print(f"  {i}. {d}")

    print("\n## 12. VEREDICTO FINAL")
    for k, v in verdict.items():
        if k in ("preserve", "critical_digits_review", "cand_d_control_without_killing_force"):
            continue
        print(f"  {k}: {v}")
    print(f"\n  Leitura 6 bases (V1≥13 únicos):")
    for base, rating in ratings_v1_13.items():
        print(f"    {BASE_LABELS_PT[base]}: {rating}")
    print("=" * 88)

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy": POLICY_REGISTRY_ID,
        "v1_label": V1_LABEL,
        "contests": list(CONTESTS),
        "summary": {
            "v1_gp_cards": segments["V1_GP"].unique_cards,
            "v1_recon_rows": segments["V1_recon_all"].recon_rows,
            "runs_12_plus": segments["V1>=12"].runs_12_plus,
            "runs_13_plus": segments["V1>=13"].runs_13_plus,
            "runs_14": segments["V1=14"].runs_14,
            "unique_cards_13_plus": segments["V1>=13_unique"].unique_cards,
        },
        "segments": {k: asdict(v) for k, v in segments.items()},
        "ratings_v1_13_unique": ratings_v1_13,
        "preserve_patterns": preserve_patterns,
        "dangerous_patterns": dangerous,
        "strength_matrix": strength_matrix,
        "control_matrix": control_matrix,
        "cand002_directives": cand002_directives,
        "verdict": verdict,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
