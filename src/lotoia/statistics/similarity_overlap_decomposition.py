"""Decomposição da similaridade média entre cartões — diagnóstico M-STAT-002."""

from __future__ import annotations

import math
from collections import Counter
from itertools import combinations
from typing import Any, Mapping, Sequence

from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

DEFAULT_CORE_DEZENAS: frozenset[int] = frozenset({7, 12, 16, 23})
DEFAULT_PREFIX_DEZENAS: frozenset[int] = frozenset({1, 2, 3})
DEFAULT_HIGH_FREQUENCY_DEZENAS: frozenset[int] = frozenset(
    {1, 2, 3, 7, 12, 16, 20, 21, 22, 23, 24}
)
MIDDLE_BAND_DEZENAS: frozenset[int] = frozenset(range(6, 16))

EXCLUSIVE_COMPONENT_ORDER: tuple[str, ...] = (
    "shared_prefix_dezenas",
    "shared_core_dezenas",
    "shared_high_frequency_dezenas",
    "shared_suffix_dezenas",
    "shared_middle_band_dezenas",
    "shared_previous_draw_dezenas",
    "shared_other_dezenas",
)
STRUCTURAL_PREFIX_TRIPLE_LABEL = "01-02-03"
DOMINANT_STRUCTURAL_TRIPLE_LABEL = STRUCTURAL_PREFIX_TRIPLE_LABEL
PREFIX_TRIPLE_DEZENAS: tuple[int, ...] = (1, 2, 3)


def _cards_from_pool(pool: Sequence[Mapping[str, Any]]) -> list[set[int]]:
    cards: list[set[int]] = []
    for game in pool:
        numbers = resolve_cartao_final_from_game(dict(game))
        if numbers:
            cards.append(set(int(value) for value in numbers))
    return cards


def _prefix_label(card: set[int]) -> str:
    ordered = sorted(card)
    if len(ordered) < 3:
        return ""
    return format_dezena_group(compute_prefix(ordered, 3))


def _suffix_label(card: set[int]) -> str:
    ordered = sorted(card)
    if len(ordered) < 3:
        return ""
    return format_dezena_group(compute_suffix(ordered, 3))


def _suffix_dezenas(card: set[int]) -> set[int]:
    ordered = sorted(card)
    if len(ordered) < 3:
        return set()
    return set(int(value) for value in compute_suffix(ordered, 3))


def _exclusive_pair_breakdown(
    shared: set[int],
    left: set[int],
    right: set[int],
    *,
    core: set[int],
    prefix_nums: set[int],
    high_freq: set[int],
    middle: set[int],
    previous: set[int],
) -> Counter[str]:
    """Atribuição exclusiva por par — soma exata ao overlap do par."""
    remaining = set(shared)
    breakdown: Counter[str] = Counter()

    for key, bucket in (
        ("shared_prefix_dezenas", prefix_nums),
        ("shared_core_dezenas", core),
        ("shared_high_frequency_dezenas", high_freq),
    ):
        part = remaining & bucket
        breakdown[key] = len(part)
        remaining -= part

    if _suffix_label(left) and _suffix_label(left) == _suffix_label(right):
        suffix_nums = _suffix_dezenas(right)
        part = remaining & suffix_nums
        breakdown["shared_suffix_dezenas"] = len(part)
        remaining -= part
    else:
        breakdown["shared_suffix_dezenas"] = 0

    part = remaining & middle
    breakdown["shared_middle_band_dezenas"] = len(part)
    remaining -= part

    if previous:
        part = remaining & previous
        breakdown["shared_previous_draw_dezenas"] = len(part)
        remaining -= part
    else:
        breakdown["shared_previous_draw_dezenas"] = 0

    breakdown["shared_other_dezenas"] = len(remaining)
    return breakdown


def _component_summary(
    totals: Counter[str],
    *,
    pair_count: int,
    avg_overlap: float,
) -> dict[str, Any]:
    components: dict[str, Any] = {}
    for key in EXCLUSIVE_COMPONENT_ORDER:
        if key not in totals:
            continue
        mean_shared = round(totals[key] / pair_count, 4) if pair_count else 0.0
        share_of_overlap_pct = (
            round((mean_shared / avg_overlap) * 100, 2) if avg_overlap else 0.0
        )
        components[key] = {
            "mean_shared_dezenas": mean_shared,
            "share_of_avg_overlap_pct": share_of_overlap_pct,
        }
    return components


def _analyze_dominant_structural_triple(
    cards: list[set[int]],
    *,
    pair_count: int,
    avg_overlap: float,
    prefix_top: Counter[str],
    structural_pattern: Counter[str],
    exclusive_totals: Counter[str],
    pair_overlap_by_both_triple: list[float],
    pair_overlap_other: list[float],
    per_dezena_shared_totals: Counter[int],
    dominance_cap: int | None = None,
) -> dict[str, Any]:
    """Separa frequência individual, trinca estrutural dominante e impacto na similaridade."""
    pool_size = len(cards)
    individual_presence: dict[str, Any] = {}
    for dezena in PREFIX_TRIPLE_DEZENAS:
        count = sum(1 for card in cards if dezena in card)
        individual_presence[f"{dezena:02d}"] = {
            "count": count,
            "share_pct": round((count / pool_size) * 100, 2) if pool_size else 0.0,
        }

    triple_count = int(prefix_top.get(DOMINANT_STRUCTURAL_TRIPLE_LABEL, 0))
    triple_share_pct = round((triple_count / pool_size) * 100, 2) if pool_size else 0.0
    # Cap proporcional à frequência histórica do triplet (21% — últimos 300 concursos)
    effective_cap = (
        int(dominance_cap)
        if dominance_cap is not None
        else max(1, math.ceil(pool_size * 0.21))
    )
    exceeds_dominance_cap = triple_count > effective_cap

    both_triple_rate = (
        round(
            structural_pattern.get("both_structural_triple_01_02_03", 0) / pair_count, 4
        )
        if pair_count
        else 0.0
    )
    mean_shared_triple = (
        round(
            exclusive_totals.get("shared_prefix_dezenas", 0) / pair_count,
            4,
        )
        if pair_count
        else 0.0
    )
    triple_share_of_overlap = (
        round((mean_shared_triple / avg_overlap) * 100, 2) if avg_overlap else 0.0
    )

    per_dezena_similarity: dict[str, Any] = {}
    for dezena in PREFIX_TRIPLE_DEZENAS:
        mean_shared = (
            round(per_dezena_shared_totals.get(dezena, 0) / pair_count, 4)
            if pair_count
            else 0.0
        )
        per_dezena_similarity[f"{dezena:02d}"] = {
            "mean_shared_dezenas": mean_shared,
            "share_of_avg_overlap_pct": round((mean_shared / avg_overlap) * 100, 2)
            if avg_overlap
            else 0.0,
        }

    avg_overlap_both_triple = (
        round(sum(pair_overlap_by_both_triple) / len(pair_overlap_by_both_triple), 4)
        if pair_overlap_by_both_triple
        else 0.0
    )
    avg_overlap_other_pairs = (
        round(sum(pair_overlap_other) / len(pair_overlap_other), 4)
        if pair_overlap_other
        else 0.0
    )
    clustering_lift = round(avg_overlap_both_triple - avg_overlap_other_pairs, 4)
    guaranteed_floor = round(both_triple_rate * len(PREFIX_TRIPLE_DEZENAS), 4)

    dominant_triple = {
        "label": DOMINANT_STRUCTURAL_TRIPLE_LABEL,
        "count": triple_count,
        "share_pct": triple_share_pct,
        "pool_size": pool_size,
        "dominance_cap": effective_cap,
        "exceeds_dominance_cap": exceeds_dominance_cap,
        "dominance_excess": max(triple_count - effective_cap, 0),
    }

    return {
        "individual_dezena_presence": individual_presence,
        "dominant_structural_triple": dominant_triple,
        "structural_prefix_triple": dominant_triple,
        "similarity_impact": {
            "avg_overlap": round(avg_overlap, 4),
            "similarity_score": round(avg_overlap / 15.0, 4) if avg_overlap else 0.0,
            "diversity_score": round(1.0 - (avg_overlap / 15.0), 4)
            if avg_overlap
            else 1.0,
            "mean_shared_triple_dezenas_123": mean_shared_triple,
            "mean_shared_prefix_dezenas_123": mean_shared_triple,
            "triple_123_share_of_avg_overlap_pct": triple_share_of_overlap,
            "prefix_123_share_of_avg_overlap_pct": triple_share_of_overlap,
            "per_dezena_mean_shared": per_dezena_similarity,
            "pairs_both_structural_triple_01_02_03_rate": both_triple_rate,
            "pairs_both_structural_prefix_01_02_03_rate": both_triple_rate,
            "pairs_both_structural_triple_01_02_03_count": int(
                structural_pattern.get("both_structural_triple_01_02_03", 0)
            ),
            "avg_overlap_when_both_triple_01_02_03": avg_overlap_both_triple,
            "avg_overlap_when_both_prefix_01_02_03": avg_overlap_both_triple,
            "avg_overlap_when_not_both_triple_01_02_03": avg_overlap_other_pairs,
            "avg_overlap_when_not_both_prefix_01_02_03": avg_overlap_other_pairs,
            "overlap_lift_from_triple_clustering": clustering_lift,
            "overlap_lift_from_prefix_clustering": clustering_lift,
            "guaranteed_overlap_floor_from_triple": guaranteed_floor,
            "guaranteed_overlap_floor_from_prefix_triple": guaranteed_floor,
            "non_triple_residual_overlap": round(
                max(avg_overlap - mean_shared_triple, 0.0), 4
            ),
            "non_prefix_residual_overlap": round(
                max(avg_overlap - mean_shared_triple, 0.0), 4
            ),
        },
        "interpretation": {
            "primary_blocker": "high_mean_pairwise_similarity",
            "generic_prefix_alert_is_secondary": True,
            "dominant_triple_explains_similarity_pct": triple_share_of_overlap,
            "corrective_action": "limit_triple_dominance_in_gp_top_slice",
            "corrective_action_not": "eliminate_triple_or_lower_diversity_threshold",
            "structural_triplet_policy": "allowed_until_cap_penalize_excess_only",
        },
    }


_analyze_prefix_triple_dimensions = _analyze_dominant_structural_triple


def decompose_pool_similarity(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int = 15,
    previous_contest_numbers: Sequence[int] | None = None,
    core_dezenas: frozenset[int] | None = None,
    prefix_dezenas: frozenset[int] | None = None,
    high_frequency_dezenas: frozenset[int] | None = None,
    structural_triple_dominance_cap: int | None = None,
) -> dict[str, Any]:
    """Decompõe overlap médio par-a-par por blocos estruturais.

    Retorna duas visões:
    - ``components``: médias por bloco com atribuição exclusiva (soma ≈ avg_overlap).
    - ``overlapping_components``: médias sobrepostas (útil para ver concentração bruta).
    """
    cards = _cards_from_pool(pool)
    if len(cards) < 2:
        return {
            "pair_count": 0,
            "avg_overlap": 0.0,
            "similarity_score": 0.0,
            "diversity_score": 1.0,
            "components": {},
            "overlapping_components": {},
            "exclusive_sum_check": 0.0,
        }

    core = set(core_dezenas or DEFAULT_CORE_DEZENAS)
    prefix_nums = set(prefix_dezenas or DEFAULT_PREFIX_DEZENAS)
    high_freq = set(high_frequency_dezenas or DEFAULT_HIGH_FREQUENCY_DEZENAS)
    previous = set(int(value) for value in (previous_contest_numbers or ()))
    middle = set(MIDDLE_BAND_DEZENAS)

    exclusive_totals: Counter[str] = Counter()
    overlapping_totals: Counter[str] = Counter()
    structural_pattern: Counter[str] = Counter()
    per_dezena_shared_totals: Counter[int] = Counter()
    pair_overlap_by_both_triple: list[float] = []
    pair_overlap_other: list[float] = []
    pair_count = 0
    overlap_total = 0

    for left, right in combinations(cards, 2):
        shared = left & right
        overlap = len(shared)
        pair_count += 1
        if overlap <= 0:
            left_prefix = _prefix_label(left)
            right_prefix = _prefix_label(right)
            if (
                left_prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL
                and right_prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL
            ):
                pair_overlap_by_both_triple.append(0.0)
            else:
                pair_overlap_other.append(0.0)
            continue

        overlap_total += overlap
        for dezena in PREFIX_TRIPLE_DEZENAS:
            if dezena in shared:
                per_dezena_shared_totals[dezena] += 1

        exclusive_totals.update(
            _exclusive_pair_breakdown(
                shared,
                left,
                right,
                core=core,
                prefix_nums=prefix_nums,
                high_freq=high_freq,
                middle=middle,
                previous=previous,
            )
        )

        overlapping_totals["shared_prefix_dezenas"] += len(shared & prefix_nums)
        overlapping_totals["shared_core_dezenas"] += len(shared & core)
        overlapping_totals["shared_high_frequency_dezenas"] += len(shared & high_freq)
        overlapping_totals["shared_middle_band_dezenas"] += len(shared & middle)
        if previous:
            overlapping_totals["shared_previous_draw_dezenas"] += len(shared & previous)
        if _suffix_label(left) and _suffix_label(left) == _suffix_label(right):
            overlapping_totals["shared_suffix_dezenas"] += len(
                shared & _suffix_dezenas(right)
            )

        if _suffix_label(left) and _suffix_label(left) == _suffix_label(right):
            structural_pattern["same_suffix_family"] += 1
        left_prefix = _prefix_label(left)
        right_prefix = _prefix_label(right)
        if left_prefix and left_prefix == right_prefix:
            structural_pattern["same_prefix_family"] += 1
        if (
            left_prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL
            and right_prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL
        ):
            structural_pattern["both_structural_triple_01_02_03"] += 1
            structural_pattern["both_prefix_01_02_03"] += 1
            pair_overlap_by_both_triple.append(float(overlap))
        else:
            pair_overlap_other.append(float(overlap))

    avg_overlap = overlap_total / pair_count if pair_count else 0.0
    similarity_score = round(avg_overlap / max(int(game_size), 1), 4)
    diversity_score = round(1.0 - similarity_score, 4)
    exclusive_sum = (
        round(
            sum(exclusive_totals[key] for key in EXCLUSIVE_COMPONENT_ORDER)
            / pair_count,
            4,
        )
        if pair_count
        else 0.0
    )

    prefix_top = Counter(_prefix_label(card) for card in cards if _prefix_label(card))
    suffix_top = Counter(_suffix_label(card) for card in cards if _suffix_label(card))
    triple_analysis = _analyze_dominant_structural_triple(
        cards,
        pair_count=pair_count,
        avg_overlap=avg_overlap,
        prefix_top=prefix_top,
        structural_pattern=structural_pattern,
        exclusive_totals=exclusive_totals,
        pair_overlap_by_both_triple=pair_overlap_by_both_triple,
        pair_overlap_other=pair_overlap_other,
        per_dezena_shared_totals=per_dezena_shared_totals,
        dominance_cap=structural_triple_dominance_cap,
    )

    return {
        "pair_count": pair_count,
        "pool_size": len(cards),
        "avg_overlap": round(avg_overlap, 4),
        "similarity_score": similarity_score,
        "diversity_score": diversity_score,
        "components": _component_summary(
            exclusive_totals,
            pair_count=pair_count,
            avg_overlap=avg_overlap,
        ),
        "overlapping_components": _component_summary(
            overlapping_totals,
            pair_count=pair_count,
            avg_overlap=avg_overlap,
        ),
        "exclusive_sum_check": exclusive_sum,
        "structural_pattern_rates": {
            key: round(value / pair_count, 4) if pair_count else 0.0
            for key, value in structural_pattern.items()
        },
        "dominant_prefix": prefix_top.most_common(1)[0] if prefix_top else ("", 0),
        "dominant_suffix": suffix_top.most_common(1)[0] if suffix_top else ("", 0),
        "core_dezenas": sorted(core),
        "prefix_dezenas": sorted(prefix_nums),
        "high_frequency_dezenas": sorted(high_freq),
        "previous_draw_size": len(previous),
        "attribution_mode": "exclusive_priority",
        "attribution_priority": list(EXCLUSIVE_COMPONENT_ORDER),
        "dominant_structural_triple_analysis": triple_analysis,
        "prefix_triple_analysis": triple_analysis,
    }


def build_similarity_decomposition_trace(
    bundle: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = dict(bundle or {})
    components = dict(source.get("components") or {})
    pattern_rates = dict(source.get("structural_pattern_rates") or {})
    trace: dict[str, Any] = {
        "avg_overlap": float(source.get("avg_overlap", 0.0) or 0.0),
        "similarity_score": float(source.get("similarity_score", 0.0) or 0.0),
        "diversity_score": float(source.get("diversity_score", 0.0) or 0.0),
        "both_structural_triple_01_02_03_pair_rate": float(
            pattern_rates.get("both_structural_triple_01_02_03", 0.0)
            or pattern_rates.get("both_prefix_01_02_03", 0.0)
            or 0.0
        ),
        "both_prefix_01_02_03_pair_rate": float(
            pattern_rates.get("both_prefix_01_02_03", 0.0) or 0.0
        ),
        "same_suffix_family_pair_rate": float(
            pattern_rates.get("same_suffix_family", 0.0) or 0.0
        ),
        "same_prefix_family_pair_rate": float(
            pattern_rates.get("same_prefix_family", 0.0) or 0.0
        ),
        "exclusive_sum_check": float(source.get("exclusive_sum_check", 0.0) or 0.0),
    }
    for key in EXCLUSIVE_COMPONENT_ORDER:
        short_key = key.removeprefix("shared_")
        trace[f"{short_key}_mean"] = float(
            dict(components.get(key) or {}).get("mean_shared_dezenas", 0.0) or 0.0
        )
        trace[f"{short_key}_share_pct"] = float(
            dict(components.get(key) or {}).get("share_of_avg_overlap_pct", 0.0) or 0.0
        )

    triple_analysis = dict(
        source.get("dominant_structural_triple_analysis")
        or source.get("prefix_triple_analysis")
        or {}
    )
    individual = dict(triple_analysis.get("individual_dezena_presence") or {})
    structural = dict(
        triple_analysis.get("dominant_structural_triple")
        or triple_analysis.get("structural_prefix_triple")
        or {}
    )
    impact = dict(triple_analysis.get("similarity_impact") or {})
    interpretation = dict(triple_analysis.get("interpretation") or {})
    trace["dezena_01_presence_pct"] = float(
        dict(individual.get("01") or {}).get("share_pct", 0.0) or 0.0
    )
    trace["dezena_02_presence_pct"] = float(
        dict(individual.get("02") or {}).get("share_pct", 0.0) or 0.0
    )
    trace["dezena_03_presence_pct"] = float(
        dict(individual.get("03") or {}).get("share_pct", 0.0) or 0.0
    )
    trace["structural_triplet_010203_count"] = int(structural.get("count", 0) or 0)
    trace["structural_triplet_010203_cap"] = int(
        structural.get("dominance_cap", 0) or 0
    )
    trace["structural_triplet_010203_excess"] = int(
        structural.get("dominance_excess", 0) or 0
    )
    trace["structural_triplet_policy"] = str(
        interpretation.get("structural_triplet_policy")
        or "allowed_until_cap_penalize_excess_only"
    )
    trace["structural_triple_01_02_03_count"] = trace["structural_triplet_010203_count"]
    trace["structural_triple_01_02_03_share_pct"] = float(
        structural.get("share_pct", 0.0) or 0.0
    )
    trace["structural_triple_01_02_03_dominance_cap"] = int(
        structural.get("dominance_cap", 0) or 0
    )
    trace["structural_triple_01_02_03_exceeds_cap"] = bool(
        structural.get("exceeds_dominance_cap")
    )
    trace["structural_triple_01_02_03_dominance_excess"] = int(
        structural.get("dominance_excess", 0) or 0
    )
    trace["structural_prefix_01_02_03_count"] = int(structural.get("count", 0) or 0)
    trace["structural_prefix_01_02_03_share_pct"] = float(
        structural.get("share_pct", 0.0) or 0.0
    )
    trace["triple_123_mean_shared_overlap"] = float(
        impact.get("mean_shared_triple_dezenas_123", 0.0)
        or impact.get("mean_shared_prefix_dezenas_123", 0.0)
        or 0.0
    )
    trace["prefix_123_mean_shared_overlap"] = trace["triple_123_mean_shared_overlap"]
    trace["triple_123_share_of_avg_overlap_pct"] = float(
        impact.get("triple_123_share_of_avg_overlap_pct", 0.0)
        or impact.get("prefix_123_share_of_avg_overlap_pct", 0.0)
        or 0.0
    )
    trace["prefix_123_share_of_avg_overlap_pct"] = trace[
        "triple_123_share_of_avg_overlap_pct"
    ]
    trace["avg_overlap_when_both_triple_01_02_03"] = float(
        impact.get("avg_overlap_when_both_triple_01_02_03", 0.0)
        or impact.get("avg_overlap_when_both_prefix_01_02_03", 0.0)
        or 0.0
    )
    trace["avg_overlap_when_both_prefix_01_02_03"] = trace[
        "avg_overlap_when_both_triple_01_02_03"
    ]
    trace["avg_overlap_when_not_both_triple_01_02_03"] = float(
        impact.get("avg_overlap_when_not_both_triple_01_02_03", 0.0)
        or impact.get("avg_overlap_when_not_both_prefix_01_02_03", 0.0)
        or 0.0
    )
    trace["avg_overlap_when_not_both_prefix_01_02_03"] = trace[
        "avg_overlap_when_not_both_triple_01_02_03"
    ]
    trace["non_triple_residual_overlap"] = float(
        impact.get("non_triple_residual_overlap", 0.0)
        or impact.get("non_prefix_residual_overlap", 0.0)
        or 0.0
    )
    trace["non_prefix_residual_overlap"] = trace["non_triple_residual_overlap"]
    trace["corrective_action"] = str(interpretation.get("corrective_action") or "")
    return trace


def format_similarity_decomposition_report(bundle: Mapping[str, Any] | None) -> str:
    """Relatório legível para painel/log — foco na causa primária (overlap médio)."""
    source = dict(bundle or {})
    if not source.get("components"):
        return "Decomposição indisponível (pool < 2 cartões)."

    lines = [
        f"avg_overlap={float(source.get('avg_overlap', 0.0) or 0.0):.4f} "
        f"| similarity={float(source.get('similarity_score', 0.0) or 0.0):.4f} "
        f"| diversity={float(source.get('diversity_score', 0.0) or 0.0):.4f}",
        "",
        "=== 1) Frequência individual de 01, 02, 03 (presença no cartão) ===",
    ]
    triple_analysis = dict(
        source.get("dominant_structural_triple_analysis")
        or source.get("prefix_triple_analysis")
        or {}
    )
    for dezena_label, row in dict(
        triple_analysis.get("individual_dezena_presence") or {}
    ).items():
        count = int(dict(row).get("count", 0) or 0)
        share = float(dict(row).get("share_pct", 0.0) or 0.0)
        lines.append(
            f"  - dezena {dezena_label}: {count}/{source.get('pool_size', 0)} cartões ({share:.1f}%)"
        )

    structural = dict(
        triple_analysis.get("dominant_structural_triple")
        or triple_analysis.get("structural_prefix_triple")
        or {}
    )
    interpretation = dict(triple_analysis.get("interpretation") or {})
    lines.extend(
        [
            "",
            "=== 2) Trinca estrutural dominante 01-02-03 (bloco recorrente, não prefixo genérico) ===",
            (
                f"  - trinca {structural.get('label', '01-02-03')}: "
                f"{int(structural.get('count', 0) or 0)}/{int(structural.get('pool_size', 0) or 0)} "
                f"({float(structural.get('share_pct', 0.0) or 0.0):.1f}%)"
            ),
            (
                f"  - teto de dominância no GP: {int(structural.get('dominance_cap', 0) or 0)} "
                f"| excede: {bool(structural.get('exceeds_dominance_cap'))} "
                f"| excesso: {int(structural.get('dominance_excess', 0) or 0)}"
            ),
        ]
    )

    impact = dict(triple_analysis.get("similarity_impact") or {})
    mean_triple = float(
        impact.get("mean_shared_triple_dezenas_123", 0.0)
        or impact.get("mean_shared_prefix_dezenas_123", 0.0)
        or 0.0
    )
    triple_overlap_pct = float(
        impact.get("triple_123_share_of_avg_overlap_pct", 0.0)
        or impact.get("prefix_123_share_of_avg_overlap_pct", 0.0)
        or 0.0
    )
    residual = float(
        impact.get("non_triple_residual_overlap", 0.0)
        or impact.get("non_prefix_residual_overlap", 0.0)
        or 0.0
    )
    lines.extend(
        [
            "",
            "=== 3) Impacto da trinca na similaridade média do GP (bloqueio real) ===",
            (
                f"  - overlap médio total: {float(impact.get('avg_overlap', 0.0) or 0.0):.4f} dezenas "
                f"(diversity={float(impact.get('diversity_score', 0.0) or 0.0):.4f})"
            ),
            (
                f"  - contribuição média do bloco 01-02-03 no overlap: {mean_triple:.4f} "
                f"({triple_overlap_pct:.1f}% do overlap)"
            ),
            f"  - overlap residual fora do bloco 01-02-03: {residual:.4f} dezenas",
            (
                f"  - ação corretiva: {interpretation.get('corrective_action', 'limit_triple_dominance_in_gp_top_slice')} "
                f"(não {interpretation.get('corrective_action_not', 'eliminate_triple')})"
            ),
        ]
    )
    per_dezena = dict(impact.get("per_dezena_mean_shared") or {})
    for dezena_label, row in per_dezena.items():
        mean = float(dict(row).get("mean_shared_dezenas", 0.0) or 0.0)
        share = float(dict(row).get("share_of_avg_overlap_pct", 0.0) or 0.0)
        lines.append(
            f"    · dezena {dezena_label} isolada no overlap par-a-par: {mean:.4f} ({share:.1f}%)"
        )
    lines.extend(
        [
            (
                f"  - pares com ambas trincas 01-02-03: "
                f"{float(impact.get('pairs_both_structural_triple_01_02_03_rate', 0.0) or impact.get('pairs_both_structural_prefix_01_02_03_rate', 0.0) or 0.0):.1%} "
                f"| overlap médio nesses pares: "
                f"{float(impact.get('avg_overlap_when_both_triple_01_02_03', 0.0) or impact.get('avg_overlap_when_both_prefix_01_02_03', 0.0) or 0.0):.4f}"
            ),
            (
                f"  - demais pares: overlap médio "
                f"{float(impact.get('avg_overlap_when_not_both_triple_01_02_03', 0.0) or impact.get('avg_overlap_when_not_both_prefix_01_02_03', 0.0) or 0.0):.4f} "
                f"| lift por clustering da trinca: "
                f"{float(impact.get('overlap_lift_from_triple_clustering', 0.0) or impact.get('overlap_lift_from_prefix_clustering', 0.0) or 0.0):+.4f}"
            ),
            "",
            "Contribuição exclusiva total da similaridade (soma = avg_overlap):",
        ]
    )
    labels = {
        "shared_prefix_dezenas": "bloco trinca 01-02-03",
        "shared_core_dezenas": "core 07/12/16/23",
        "shared_high_frequency_dezenas": "alta frequência",
        "shared_suffix_dezenas": "sufixo (mesma família)",
        "shared_middle_band_dezenas": "miolo 06-15",
        "shared_previous_draw_dezenas": "repetição concurso anterior",
        "shared_other_dezenas": "outros",
    }
    components = dict(source.get("components") or {})
    for key in EXCLUSIVE_COMPONENT_ORDER:
        row = dict(components.get(key) or {})
        mean = float(row.get("mean_shared_dezenas", 0.0) or 0.0)
        share = float(row.get("share_of_avg_overlap_pct", 0.0) or 0.0)
        lines.append(
            f"  - {labels.get(key, key)}: {mean:.4f} dezenas ({share:.1f}% do overlap)"
        )
    pattern_rates = dict(source.get("structural_pattern_rates") or {})
    lines.append(
        "Padrões estruturais (taxa par-a-par): "
        f"both_prefix_01_02_03={float(pattern_rates.get('both_prefix_01_02_03', 0.0) or 0.0):.4f} "
        f"same_suffix_family={float(pattern_rates.get('same_suffix_family', 0.0) or 0.0):.4f}"
    )
    dominant_prefix = source.get("dominant_prefix") or ("", 0)
    dominant_suffix = source.get("dominant_suffix") or ("", 0)
    if isinstance(dominant_prefix, (list, tuple)) and len(dominant_prefix) >= 2:
        lines.append(
            f"Dominante prefixo: {dominant_prefix[0]} ({dominant_prefix[1]}/{source.get('pool_size', 0)})"
        )
    if isinstance(dominant_suffix, (list, tuple)) and len(dominant_suffix) >= 2:
        lines.append(
            f"Dominante sufixo: {dominant_suffix[0]} ({dominant_suffix[1]}/{source.get('pool_size', 0)})"
        )
    return "\n".join(lines)
