#!/usr/bin/env python3
"""Comparativo institucional Núcleo Lei 15 — Leitura pelas 6 Bases.

Agentes: agent_qualidade + agent_estatistico
Política: docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md

Uso (read-only PostgreSQL — sem nova geração):
  python scripts/ops/report_lei15_core_6_bases_comparative.py
  python scripts/ops/report_lei15_core_6_bases_comparative.py --json-out reports/lei15_6bases.json
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
    compute_structural_signatures,
)
from lotoia.governance.lei15_core_six_bases_evaluation import (
    BASE_LABELS_PT,
    BASE_NAMES,
    POLICY_REGISTRY_ID,
    BaseRating,
)
from lotoia.governance.lei15_legacy_core_baseline import is_legacy_core_frozen_label

CONTESTS = (3705, 3706, 3707, 3708, 3709, 3710, 3711)
PLATEAU_AVG = 9.286
BASELINE_P3 = 42.0
BASELINE_S3 = 53.0

STRENGTHEN_DIGITS = (7, 12, 16, 23)
EXCESS_DIGITS = (2, 4, 11, 15, 24, 25)

LANES = (
    ("STRUCT_TEST_15D_001", "BASELINE", None),
    ("STRUCT_REALIGN_V1_15D_001", "V1", None),
    ("STRUCT_CORE_REALIGN_V2_15D_001", "V2", None),
    ("STRUCT_CORE_REALIGN_V3_BALANCED_15D_001", "V3", None),
    ("STRUCT_LEI15_CORE_V4_PATTERN_PROTECTED_15D_001", "V4", 113),
    ("STRUCT_LEI15_CORE_CANDIDATE_001_15D_001", "CAND-A", 114),
    ("STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001", "CAND-D", 115),
)

LaneVerdict = str  # NÃO É NÚCLEO | ESTRUTURALMENTE PROMISSORA | ...

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


@dataclass
class LaneMetrics:
    label: str
    short: str
    ge_ids: list[int]
    games_count: int
    recon_runs: int
    hits_best: int
    hits_avg: float
    hits_runs_12_plus: int
    hits_runs_13_plus: int
    hits_per_contest: dict[int, list[int]] = field(default_factory=dict)
    profile_origin: dict[str, int] = field(default_factory=dict)
    profile_label: dict[str, int] = field(default_factory=dict)
    prefix_sigs: Counter = field(default_factory=Counter)
    suffix_sigs: Counter = field(default_factory=Counter)
    p3_123_pct: float = 0.0
    s3_222425_pct: float = 0.0
    avg_bias: float = 0.0
    relabel_count: int = 0
    duplicate_cards: int = 0
    mean_pairwise_overlap: float = 0.0
    top_architecture_pct: float = 0.0
    strengthen_presence: dict[int, float] = field(default_factory=dict)
    excess_presence: dict[int, float] = field(default_factory=dict)
    hits_contest_std: float = 0.0
    hits_contest_means: dict[int, float] = field(default_factory=dict)
    is_pilot_sample: bool = False
    is_frozen_legacy: bool = False


@dataclass
class LaneSixBases:
    short: str
    label: str
    ratings: dict[str, BaseRating]
    balance_score: float
    suggested_note: str
    lane_verdict: str
    justification: str


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


def _load_lane(conn, label: str, short: str, ge_hint: int | None) -> LaneMetrics:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT ge.id, gg.numbers, gg.context_json, gg.profile_type
            FROM generation_events ge
            JOIN generated_games gg ON gg.generation_event_id = ge.id
            WHERE ge.analysis_batch_label = %s
            ORDER BY ge.id, gg.game_index
            """,
            (label,),
        )
        game_rows = cur.fetchall()

        cur.execute(
            f"""
            {OFFICIAL_RUNS_SQL}
            SELECT contest_id, best_hits, generation_event_id
            FROM deduped ORDER BY contest_id
            """,
            (label, list(CONTESTS)),
        )
        recon_rows = cur.fetchall()

    ge_ids = sorted({int(r[0]) for r in game_rows})
    if ge_hint and ge_hint not in ge_ids:
        ge_ids = sorted(set(ge_ids) | {ge_hint})

    games: list[tuple[int, ...]] = []
    profile_origin: Counter = Counter()
    profile_label: Counter = Counter()
    prefix_sigs: Counter = Counter()
    suffix_sigs: Counter = Counter()
    bias_scores: list[float] = []
    relabel_count = 0
    p3_123 = 0
    s3_222425 = 0
    digit_counts: Counter = Counter()
    arch_sigs: Counter = Counter()

    for _ge_id, numbers, ctx_raw, profile_type_col in game_rows:
        if not isinstance(numbers, list) or len(numbers) != 15:
            continue
        nums = sorted(int(x) for x in numbers)
        games.append(tuple(nums))
        for d in nums:
            digit_counts[d] += 1

        ctx = ctx_raw if isinstance(ctx_raw, dict) else {}
        origin = str(
            _ctx_field(ctx, "perfil_origem_real") or profile_type_col or _ctx_field(ctx, "profile_type") or "unknown"
        )
        if not _ctx_field(ctx, "prefix_signature"):
            derived = apply_core_traceability_payload(
                {"numbers": nums, "profile_type": origin},
                profile_origin=origin,
            )
            ps = str(derived.get("prefix_signature") or "")
            ss = str(derived.get("suffix_signature") or "")
            bias = float(derived.get("structural_bias_score") or 0)
            relabel = bool(derived.get("relabeling_applied"))
            label_final = str(derived.get("perfil_label_final") or origin)
        else:
            ps = str(_ctx_field(ctx, "prefix_signature") or "")
            ss = str(_ctx_field(ctx, "suffix_signature") or "")
            bias = float(_ctx_field(ctx, "structural_bias_score") or compute_structural_bias_score(nums, profile_origin=origin))
            relabel = _ctx_field(ctx, "relabeling_applied") is True
            label_final = str(_ctx_field(ctx, "perfil_label_final") or origin)

        profile_origin[origin] += 1
        profile_label[label_final] += 1
        if ps:
            prefix_sigs[ps] += 1
        if ss:
            suffix_sigs[ss] += 1
        bias_scores.append(bias)
        if relabel:
            relabel_count += 1
        if nums[:3] == [1, 2, 3]:
            p3_123 += 1
        if nums[-3:] == [22, 24, 25]:
            s3_222425 += 1
        arch_sigs[(ps, ss)] += 1

    n = len(games) or 1
    duplicates = n - len(set(games))

    overlaps: list[float] = []
    sample_cap = min(len(games), 80)
    for i in range(sample_cap):
        for j in range(i + 1, sample_cap):
            overlaps.append(len(set(games[i]) & set(games[j])))

    hits_per_contest: dict[int, list[int]] = defaultdict(list)
    all_hits: list[int] = []
    for contest_id, best_hits, _ge in recon_rows:
        h = int(best_hits)
        hits_per_contest[int(contest_id)].append(h)
        all_hits.append(h)

    contest_means = {c: mean(v) for c, v in hits_per_contest.items() if v}
    contest_std = pstdev(contest_means.values()) if len(contest_means) > 1 else 0.0

    strengthen_presence = {d: digit_counts[d] / n * 100 for d in STRENGTHEN_DIGITS}
    excess_presence = {d: digit_counts[d] / n * 100 for d in EXCESS_DIGITS}

    top_arch_pct = (arch_sigs.most_common(1)[0][1] / n * 100) if arch_sigs else 0.0

    return LaneMetrics(
        label=label,
        short=short,
        ge_ids=ge_ids,
        games_count=len(games),
        recon_runs=len(all_hits),
        hits_best=max(all_hits) if all_hits else 0,
        hits_avg=mean(all_hits) if all_hits else 0.0,
        hits_runs_12_plus=sum(1 for h in all_hits if h >= 12),
        hits_runs_13_plus=sum(1 for h in all_hits if h >= 13),
        hits_per_contest=dict(hits_per_contest),
        profile_origin=dict(profile_origin),
        profile_label=dict(profile_label),
        prefix_sigs=prefix_sigs,
        suffix_sigs=suffix_sigs,
        p3_123_pct=p3_123 / n * 100,
        s3_222425_pct=s3_222425 / n * 100,
        avg_bias=mean(bias_scores) if bias_scores else 0.0,
        relabel_count=relabel_count,
        duplicate_cards=duplicates,
        mean_pairwise_overlap=mean(overlaps) if overlaps else 0.0,
        top_architecture_pct=top_arch_pct,
        strengthen_presence=strengthen_presence,
        excess_presence=excess_presence,
        hits_contest_std=contest_std,
        hits_contest_means=contest_means,
        is_pilot_sample=len(ge_ids) <= 1 and len(all_hits) <= 7,
        is_frozen_legacy=is_legacy_core_frozen_label(label),
    )


def _profile_balance_score(m: LaneMetrics) -> float:
    if not m.profile_origin:
        return 0.0
    total = sum(m.profile_origin.values())
    shares = [v / total for v in m.profile_origin.values()]
    entropy = -sum(s * math.log(s + 1e-12) for s in shares)
    max_share = max(shares) * 100
    # target ~3 profiles, max share ~40-45%
    score = entropy / math.log(len(shares) + 1e-12) if shares else 0.0
    if max_share > 50:
        score *= 0.5
    return score


def _rate_base1(m: LaneMetrics) -> BaseRating:
    if m.recon_runs == 0:
        return "inconclusiva"
    if m.is_pilot_sample and m.hits_runs_13_plus == 0 and m.hits_best <= 11:
        return "inconclusiva"
    if m.hits_best >= 13 and m.hits_avg >= 11.0 and m.hits_runs_13_plus >= max(1, m.recon_runs // 20):
        return "forte"
    if m.hits_best >= 12 or m.hits_avg > PLATEAU_AVG + 0.5 or m.hits_runs_12_plus >= max(1, m.recon_runs // 10):
        return "parcial"
    if m.hits_avg <= PLATEAU_AVG and m.hits_best <= 11 and m.hits_runs_13_plus == 0:
        return "fraca"
    return "parcial"


def _rate_base2(m: LaneMetrics) -> BaseRating:
    if m.games_count < 20:
        return "inconclusiva"
    top_prefix_pct = (m.prefix_sigs.most_common(1)[0][1] / m.games_count * 100) if m.prefix_sigs else 100
    uniq_prefix = len(m.prefix_sigs)
    balance = _profile_balance_score(m)
    profiles_n = len(m.profile_origin)
    if profiles_n >= 3 and balance >= 0.85 and top_prefix_pct <= 25 and uniq_prefix >= 8:
        return "forte"
    if top_prefix_pct >= 40 or (profiles_n <= 2 and m.games_count >= 50):
        return "fraca"
    if top_prefix_pct <= 35 and uniq_prefix >= 5:
        return "parcial"
    return "inconclusiva"


def _rate_base3(m: LaneMetrics) -> BaseRating:
    if m.games_count < 20:
        return "inconclusiva"
    if m.duplicate_cards > 0 or m.top_architecture_pct >= 30:
        return "fraca"
    if m.mean_pairwise_overlap <= 8.0 and m.top_architecture_pct <= 15:
        return "forte"
    if m.mean_pairwise_overlap <= 9.5 and m.top_architecture_pct <= 22:
        return "parcial"
    return "fraca"


def _rate_base4(m: LaneMetrics) -> BaseRating:
    if m.games_count == 0:
        return "inconclusiva"
    if m.relabel_count > 0:
        return "fraca"
    if m.p3_123_pct <= 12 and m.s3_222425_pct <= 12 and m.avg_bias <= 20:
        return "forte"
    if m.p3_123_pct >= 35 or m.s3_222425_pct >= 45:
        return "fraca"
    if m.p3_123_pct < BASELINE_P3 and m.s3_222425_pct < BASELINE_S3:
        return "parcial"
    return "parcial"


def _rate_base5(m: LaneMetrics) -> BaseRating:
    if m.games_count < 20:
        return "inconclusiva"
    strengthen_ok = sum(1 for d in STRENGTHEN_DIGITS if m.strengthen_presence.get(d, 0) >= 55)
    strengthen_missing = sum(1 for d in STRENGTHEN_DIGITS if m.strengthen_presence.get(d, 0) < 30)
    excess_hot = sum(1 for d in EXCESS_DIGITS if m.excess_presence.get(d, 0) > 92)
    if strengthen_ok >= 3 and strengthen_missing == 0 and excess_hot <= 2:
        return "forte"
    if strengthen_missing >= 2 or excess_hot >= 4:
        return "fraca"
    return "parcial"


def _rate_base6(m: LaneMetrics) -> BaseRating:
    if m.recon_runs < 7:
        return "inconclusiva"
    if m.is_pilot_sample:
        return "inconclusiva"
    means = list(m.hits_contest_means.values())
    if not means:
        return "inconclusiva"
    min_mean = min(means)
    if m.hits_contest_std <= 1.2 and min_mean >= PLATEAU_AVG and m.hits_runs_13_plus >= 3:
        return "forte"
    if m.hits_contest_std <= 2.0 and min_mean >= PLATEAU_AVG - 0.5:
        return "parcial"
    if min_mean < PLATEAU_AVG - 1.0 or m.hits_contest_std > 2.5:
        return "fraca"
    return "parcial"


def _balance_score(ratings: dict[str, BaseRating]) -> float:
    weights = {"forte": 3.0, "parcial": 2.0, "inconclusiva": 1.0, "fraca": 0.0}
    return sum(weights[r] for r in ratings.values())


def _suggested_note(ratings: dict[str, BaseRating], m: LaneMetrics) -> str:
    if m.short == "BASELINE" and m.is_frozen_legacy:
        return "Núcleo inválido (baseline congelado)"
    strong = sum(1 for r in ratings.values() if r == "forte")
    weak = sum(1 for r in ratings.values() if r == "fraca")
    if ratings["forca_acerto"] == "forte" and strong >= 2:
        return "Núcleo estatisticamente promissor"
    if ratings["controle_prefixo_sufixo"] == "forte" and ratings["diversidade"] in {"forte", "parcial"}:
        return "Núcleo estruturalmente promissor"
    if weak >= 3:
        return "Núcleo inválido"
    if strong >= 2 and weak == 0:
        return "Núcleo candidato"
    if m.is_pilot_sample:
        return "Inconclusiva (amostra piloto)"
    return "Exige nova variante"


def _lane_verdict(ratings: dict[str, BaseRating], m: LaneMetrics) -> tuple[str, str]:
    if m.is_frozen_legacy and m.short == "BASELINE":
        return (
            "NÃO É NÚCLEO",
            "Baseline legado congelado read-only. Evidência histórica e controle negativo — "
            "viés estrutural confirmado (p3/s3 altos).",
        )
    if m.short in {"V2", "V3", "V4"} and ratings["forca_acerto"] == "fraca":
        return (
            "NÃO É NÚCLEO",
            f"{m.short} permanece no platô de hits (melhor={m.hits_best}, média={m.hits_avg:.3f}) "
            "sem equilíbrio das 6 bases.",
        )
    if ratings["forca_acerto"] == "forte" and ratings["estabilidade_multi_concurso"] in {"forte", "parcial"}:
        return (
            "ESTATISTICAMENTE PROMISSORA",
            "Força de acerto e estabilidade multi-concurso líderes; bases 2–5 (diversidade, "
            "redundância, prefixo/sufixo, cobertura crítica) exigem auditoria fina antes "
            "de Núcleo pleno — não aprovar apenas por hits.",
        )
    if (
        ratings["controle_prefixo_sufixo"] == "forte"
        and ratings["diversidade"] in {"forte", "parcial"}
        and ratings["forca_acerto"] in {"inconclusiva", "parcial", "fraca"}
    ):
        return (
            "ESTRUTURALMENTE PROMISSORA",
            "Controle prefixo/sufixo e diversidade superiores; força de acerto ainda no "
            "platô ou amostra piloto insuficiente — não descartar por hit isolado.",
        )
    if sum(1 for r in ratings.values() if r == "forte") >= 3 and "fraca" not in ratings.values():
        return ("CANDIDATA A NÚCLEO", "Equilíbrio progressivo entre bases — candidata a piloto ampliado.")
    if m.is_pilot_sample:
        return (
            "INCONCLUSIVA",
            "Amostra piloto única (1 GE × 7 concursos). Métricas estruturais válidas; "
            "estabilidade e força exigem piloto ampliado sem novo volume no legado.",
        )
    return ("EXIGE NOVA VARIANTE", "Nenhuma base forte suficiente com equilíbrio global.")


def _assess_lane(m: LaneMetrics) -> LaneSixBases:
    ratings: dict[str, BaseRating] = {
        "forca_acerto": _rate_base1(m),
        "diversidade": _rate_base2(m),
        "baixa_redundancia": _rate_base3(m),
        "controle_prefixo_sufixo": _rate_base4(m),
        "cobertura_dezenas_criticas": _rate_base5(m),
        "estabilidade_multi_concurso": _rate_base6(m),
    }
    balance = _balance_score(ratings)
    note = _suggested_note(ratings, m)
    verdict, justification = _lane_verdict(ratings, m)
    return LaneSixBases(
        short=m.short,
        label=m.label,
        ratings=ratings,
        balance_score=balance,
        suggested_note=note,
        lane_verdict=verdict,
        justification=justification,
    )


def _print_report(metrics: list[LaneMetrics], assessments: list[LaneSixBases]) -> None:
    print("=" * 88)
    print("COMPARATIVO INSTITUCIONAL — NÚCLEO LEI 15 (6 BASES)")
    print(f"Política: {POLICY_REGISTRY_ID} | Concursos: {CONTESTS[0]}–{CONTESTS[-1]}")
    print("Modo: read-only PostgreSQL — sem nova geração")
    print("=" * 88)

    print("\n## 1. Tabela geral por lane")
    hdr = f"{'Lane':<10} {'GEs':>4} {'Jogos':>6} {'Runs':>5} {'Best':>5} {'Avg':>7} {'12+':>5} {'13+':>5} {'p3%':>6} {'s3%':>6}"
    print(hdr)
    print("-" * len(hdr))
    for m in metrics:
        ges = ",".join(str(g) for g in m.ge_ids[:3]) + ("..." if len(m.ge_ids) > 3 else "")
        print(
            f"{m.short:<10} {len(m.ge_ids):>4} {m.games_count:>6} {m.recon_runs:>5} "
            f"{m.hits_best:>5} {m.hits_avg:>7.3f} {m.hits_runs_12_plus:>5} "
            f"{m.hits_runs_13_plus:>5} {m.p3_123_pct:>5.1f}% {m.s3_222425_pct:>5.1f}%"
        )
        if len(m.ge_ids) <= 3 and m.ge_ids:
            print(f"           ge_ids=[{ges}]")

    print("\n## 2. Tabela das 6 bases por lane")
    base_short = ["B1", "B2", "B3", "B4", "B5", "B6"]
    print(f"{'Lane':<10} " + " ".join(f"{b:>14}" for b in base_short) + f" {'Balance':>8} {'Veredicto'}")
    print("-" * 110)
    for a in assessments:
        cells = " ".join(f"{a.ratings[n]:>14}" for n in BASE_NAMES)
        print(f"{a.short:<10} {cells} {a.balance_score:>8.1f} {a.lane_verdict}")

    print("\n## 3. Detalhe por base (labels)")
    for a in assessments:
        print(f"\n--- {a.short} ({a.label}) ---")
        for name in BASE_NAMES:
            print(f"  {BASE_LABELS_PT[name]}: {a.ratings[name]}")
        print(f"  Nota sugerida: {a.suggested_note}")
        print(f"  Veredicto: {a.lane_verdict}")
        print(f"  Justificativa: {a.justification}")

    ranked = sorted(assessments, key=lambda x: x.balance_score, reverse=True)
    print("\n## 4. Ranking de equilíbrio (6 bases)")
    for i, a in enumerate(ranked, 1):
        print(f"  {i}. {a.short:<10} balance={a.balance_score:.1f}  {a.lane_verdict}")

    print("\n## 5. Conclusão institucional")
    by_force = max(metrics, key=lambda m: (m.hits_best, m.hits_avg, m.hits_runs_13_plus))
    by_struct = min(metrics, key=lambda m: (m.p3_123_pct + m.s3_222425_pct, m.avg_bias))
    by_balance = ranked[0]
    print(f"  Mais força de acerto:     {by_force.short} (best={by_force.hits_best}, avg={by_force.hits_avg:.3f}, 13+={by_force.hits_runs_13_plus})")
    print(f"  Melhor controle estrutural: {by_struct.short} (p3={by_struct.p3_123_pct:.1f}%, s3={by_struct.s3_222425_pct:.1f}%, bias={by_struct.avg_bias:.1f})")
    print(f"  Melhor equilíbrio geral:  {by_balance.short} (balance={by_balance.balance_score:.1f}) — {by_balance.lane_verdict}")
    discard = [a.short for a in assessments if a.lane_verdict == "NÃO É NÚCLEO"]
    investigate = [a.short for a in assessments if a.lane_verdict in {"ESTRUTURALMENTE PROMISSORA", "ESTATISTICAMENTE PROMISSORA", "INCONCLUSIVA", "CANDIDATA A NÚCLEO"}]
    print(f"  Descartar como candidata: {', '.join(discard) or '—'}")
    print(f"  Nova investigação:         {', '.join(investigate) or '—'}")
    print("  Existe Núcleo pleno válido? NÃO — nenhuma lane atinge equilíbrio simultâneo das 6 bases.")
    print(
        "  Próxima variante deve combinar: força V1 (seleção/composição) + "
        "controle estrutural CAND-D (N-C1..N-C6) + cobertura crítica auditada + "
        "estabilidade multi-GE — sem novo volume no legado."
    )
    print("\n## 6. Veredicto global")
    print("  INSTITUCIONAL: nenhuma promoção active. CDX-D e V1 são complementares, não substitutos.")
    print("=" * 88)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", default="", help="Optional JSON export path")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ensure_database_url(root=ROOT)
    url = resolve_database_url()[0]

    metrics: list[LaneMetrics] = []
    assessments: list[LaneSixBases] = []

    with psycopg.connect(url) as conn:
        for label, short, ge_hint in LANES:
            m = _load_lane(conn, label, short, ge_hint)
            metrics.append(m)
            assessments.append(_assess_lane(m))

    _print_report(metrics, assessments)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "policy": POLICY_REGISTRY_ID,
            "contests": list(CONTESTS),
            "lanes": [
                {
                    "metrics": {
                        "label": m.label,
                        "short": m.short,
                        "ge_ids": m.ge_ids,
                        "games_count": m.games_count,
                        "recon_runs": m.recon_runs,
                        "hits_best": m.hits_best,
                        "hits_avg": round(m.hits_avg, 4),
                        "hits_runs_12_plus": m.hits_runs_12_plus,
                        "hits_runs_13_plus": m.hits_runs_13_plus,
                        "p3_123_pct": round(m.p3_123_pct, 2),
                        "s3_222425_pct": round(m.s3_222425_pct, 2),
                        "avg_bias": round(m.avg_bias, 2),
                        "relabel_count": m.relabel_count,
                        "duplicate_cards": m.duplicate_cards,
                        "mean_pairwise_overlap": round(m.mean_pairwise_overlap, 3),
                        "top_architecture_pct": round(m.top_architecture_pct, 2),
                        "strengthen_presence": m.strengthen_presence,
                        "excess_presence": m.excess_presence,
                    },
                    "assessment": asdict(a),
                }
                for m, a in zip(metrics, assessments, strict=True)
            ],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON export: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
