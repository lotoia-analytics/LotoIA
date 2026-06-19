"""Seleção estatística diversa do top slice pré-GP — M-STAT-002.

Substitui o recorte requested_count×3 por score puro por seleção com teto
de família estrutural (prefixo/sufixo/overlap) antes do portão M-ML-073.
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD
from lotoia.ml.structural_policy_15d import is_structural_policy_15d_format
from lotoia.ml.supervised_output_calibration import analyze_pool_structural_issues
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-STAT-002"
SELECTION_VERSION = "M-STAT-002-v1"
ENV_DIVERSE_TOP_SLICE_ENABLED = "LOTOIA_DIVERSE_TOP_SLICE_ENABLED"
MIN_MATERIAL_DIVERSITY_GAIN = 0.20
MAX_PREFIX_SUFFIX_SHARE = 0.14
NEAR_CLONE_OVERLAP_15D = 14
MAX_FAMILY_SHARE = 0.10


def is_diverse_top_slice_enabled() -> bool:
    raw = os.getenv(ENV_DIVERSE_TOP_SLICE_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def slice_limit(*, requested_count: int) -> int:
    count = max(int(requested_count), 1)
    return max(count * 3, count, 20)


def _game_signature(game: Mapping[str, Any]) -> tuple[int, ...]:
    card = resolve_cartao_final_from_game(dict(game))
    return tuple(sorted(int(value) for value in card)) if card else tuple()


def _prefix_key(game: Mapping[str, Any]) -> str:
    card = list(_game_signature(game))
    if not card:
        return ""
    return format_dezena_group(compute_prefix(card, 3))


def _suffix_key(game: Mapping[str, Any]) -> str:
    card = list(_game_signature(game))
    if not card:
        return ""
    return format_dezena_group(compute_suffix(card, 3))


def _family_key(game: Mapping[str, Any]) -> str:
    prefix = _prefix_key(game)
    suffix = _suffix_key(game)
    if not prefix and not suffix:
        return ""
    return f"{prefix}|{suffix}"


def _score_based_slice(
    pool: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        [dict(game) for game in pool],
        key=lambda row: float(row.get("profile_score", 0.0) or 0.0),
        reverse=True,
    )
    return ranked[: min(int(limit), len(ranked))]


def _measure_slice_diversity(
    candidate_pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    batch_label: str | None,
    requested_count: int,
) -> dict[str, Any]:
    diagnostics = analyze_pool_structural_issues(
        list(candidate_pool),
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=int(requested_count),
    )
    redundancy = dict(diagnostics.get("redundancy") or {})
    diversity_score = round(
        1.0 - float(redundancy.get("similaridade_media_entre_jogos", 0.0) or 0.0),
        4,
    )
    prefix_top = list(redundancy.get("prefix_top") or [])
    suffix_top = list(redundancy.get("suffix_top") or [])
    families: Counter[str] = Counter(_family_key(game) for game in candidate_pool if _family_key(game))
    return {
        "diversity_score": diversity_score,
        "similarity_score": float(redundancy.get("similaridade_media_entre_jogos", 0.0) or 0.0),
        "max_overlap": int(redundancy.get("sobreposicao_maxima", 0) or 0),
        "candidate_pool_size": len(candidate_pool),
        "top_prefix": prefix_top[0] if prefix_top else ("", 0),
        "top_suffix": suffix_top[0] if suffix_top else ("", 0),
        "dominant_family": families.most_common(1)[0] if families else ("", 0),
        "family_count": len(families),
    }


def _family_caps(limit: int) -> dict[str, int]:
    size = max(int(limit), 1)
    prefix_suffix_cap = max(3, int(size * MAX_PREFIX_SUFFIX_SHARE))
    family_cap = max(2, int(size * MAX_FAMILY_SHARE))
    return {
        "prefix_cap": prefix_suffix_cap,
        "suffix_cap": prefix_suffix_cap,
        "family_cap": family_cap,
        "overlap_limit": NEAR_CLONE_OVERLAP_15D,
    }


def _is_near_clone(
    card: Sequence[int],
    selected_cards: Sequence[Sequence[int]],
    *,
    overlap_limit: int,
) -> bool:
    card_set = set(card)
    return any(len(card_set & set(other)) >= int(overlap_limit) for other in selected_cards)


def _count_structural_families(
    games: Sequence[Mapping[str, Any]],
) -> tuple[Counter[str], Counter[str], Counter[str]]:
    prefix_counts: Counter[str] = Counter()
    suffix_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    for game in games:
        prefix = _prefix_key(game)
        suffix = _suffix_key(game)
        family = _family_key(game)
        if prefix:
            prefix_counts[prefix] += 1
        if suffix:
            suffix_counts[suffix] += 1
        if family:
            family_counts[family] += 1
    return prefix_counts, suffix_counts, family_counts


def _structural_cap_violations(
    games: Sequence[Mapping[str, Any]],
    *,
    prefix_cap: int,
    suffix_cap: int,
    family_cap: int,
) -> list[tuple[str, str, int, int]]:
    prefix_counts, suffix_counts, family_counts = _count_structural_families(games)
    violations: list[tuple[str, str, int, int]] = []
    for label, counter, cap in (
        ("suffix", suffix_counts, suffix_cap),
        ("prefix", prefix_counts, prefix_cap),
        ("family", family_counts, family_cap),
    ):
        for key, count in counter.items():
            if key and count > cap:
                violations.append((label, key, count, cap))
    violations.sort(
        key=lambda row: (
            row[0] == "suffix",
            row[0] == "family",
            row[2] - row[3],
        ),
        reverse=True,
    )
    return violations


def select_diverse_pre_gp_top_slice(
    pool: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    game_size: int = 15,
    batch_label: str | None = None,
    requested_count: int | None = None,
    relax_level: int = 0,
) -> list[dict[str, Any]]:
    """Seleciona top slice com diversidade obrigatória de famílias estruturais."""
    _ = (batch_label, requested_count, game_size)
    rows = [dict(game) for game in pool if _game_signature(game)]
    if not rows:
        return []
    target = min(int(limit), len(rows))
    caps = _family_caps(target)
    relax = max(0, int(relax_level))
    prefix_cap = caps["prefix_cap"] + relax
    suffix_cap = caps["suffix_cap"] + relax
    family_cap = caps["family_cap"] + max(0, relax // 2)

    ranked = sorted(
        rows,
        key=lambda row: float(row.get("profile_score", 0.0) or 0.0),
        reverse=True,
    )
    selected = [dict(game) for game in _score_based_slice(ranked, limit=target)]
    used_signatures = {_game_signature(game) for game in selected if _game_signature(game)}
    reserve = [dict(game) for game in ranked if _game_signature(game) not in used_signatures]

    distinct_prefixes = len({_prefix_key(game) for game in rows if _prefix_key(game)})
    distinct_suffixes = len({_suffix_key(game) for game in rows if _suffix_key(game)})

    def _replacement_allowed(
        candidate: Mapping[str, Any],
        *,
        prefix_counts: Counter[str],
        suffix_counts: Counter[str],
        family_counts: Counter[str],
    ) -> bool:
        prefix = _prefix_key(candidate)
        suffix = _suffix_key(candidate)
        family = _family_key(candidate)
        if distinct_prefixes > 1 and prefix and prefix_counts[prefix] >= prefix_cap:
            return False
        if distinct_suffixes > 1 and suffix and suffix_counts[suffix] >= suffix_cap:
            return False
        if family and family_counts[family] >= family_cap:
            return False
        return True

    max_swaps = target * 3
    swaps = 0
    while swaps < max_swaps:
        violations = _structural_cap_violations(
            selected,
            prefix_cap=prefix_cap,
            suffix_cap=suffix_cap,
            family_cap=family_cap,
        )
        if distinct_prefixes <= 1:
            violations = [row for row in violations if row[0] != "prefix"]
        if distinct_suffixes <= 1:
            violations = [row for row in violations if row[0] != "suffix"]
        if not violations:
            break

        prefix_counts, suffix_counts, family_counts = _count_structural_families(selected)
        violation_type, violation_key, _count, _cap = violations[0]

        removal_index: int | None = None
        for index in range(len(selected) - 1, -1, -1):
            game = selected[index]
            if violation_type == "suffix" and _suffix_key(game) == violation_key:
                removal_index = index
                break
            if violation_type == "prefix" and _prefix_key(game) == violation_key:
                removal_index = index
                break
            if violation_type == "family" and _family_key(game) == violation_key:
                removal_index = index
                break
        if removal_index is None:
            break

        removed = selected.pop(removal_index)
        removed_signature = _game_signature(removed)
        if removed_signature:
            used_signatures.discard(removed_signature)
            reserve.append(removed)

        prefix_counts, suffix_counts, family_counts = _count_structural_families(selected)
        replacement: dict[str, Any] | None = None
        for candidate in sorted(
            reserve,
            key=lambda row: (
                suffix_counts.get(_suffix_key(row), 0),
                prefix_counts.get(_prefix_key(row), 0),
                family_counts.get(_family_key(row), 0),
                -float(row.get("profile_score", 0.0) or 0.0),
            ),
        ):
            signature = _game_signature(candidate)
            if not signature or signature in used_signatures:
                continue
            if not _replacement_allowed(
                candidate,
                prefix_counts=prefix_counts,
                suffix_counts=suffix_counts,
                family_counts=family_counts,
            ):
                continue
            replacement = dict(candidate)
            break

        if replacement is None:
            selected.insert(removal_index, removed)
            if removed_signature:
                used_signatures.add(removed_signature)
            break

        replacement_signature = _game_signature(replacement)
        reserve = [game for game in reserve if _game_signature(game) != replacement_signature]
        replacement["diverse_top_slice_selected"] = True
        replacement["m_stat_002_selection_rank"] = removal_index + 1
        replacement["m_stat_002_replacement_swap"] = True
        selected.insert(removal_index, replacement)
        if replacement_signature:
            used_signatures.add(replacement_signature)
        swaps += 1

    for index, row in enumerate(selected):
        row.setdefault("diverse_top_slice_selected", True)
        row.setdefault("m_stat_002_selection_rank", index + 1)
    return selected[:target]


def reorder_pool_with_diverse_top_slice(
    pool: Sequence[Mapping[str, Any]],
    selected_slice: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Promove o slice diverso ao topo do pool para avaliação pré-GP e compose."""
    if not selected_slice:
        return [dict(game) for game in pool]

    selected_rows = [dict(game) for game in selected_slice]
    skip_counter: Counter[tuple[int, ...]] = Counter(
        _game_signature(game) for game in selected_slice if _game_signature(game)
    )
    tail: list[dict[str, Any]] = []
    for game in pool:
        signature = _game_signature(game)
        if signature and skip_counter.get(signature, 0) > 0:
            skip_counter[signature] -= 1
            continue
        tail.append(dict(game))

    base_score = max(
        float(row.get("profile_score", 0.0) or 0.0) for row in selected_rows + tail
    )
    for index, row in enumerate(selected_rows):
        row["profile_score"] = round(base_score + (len(selected_rows) - index) * 2.5, 4)
        row["diverse_top_slice_promoted"] = True
    for index, row in enumerate(tail):
        row["profile_score"] = round((index + 1) * 0.001, 4)
    return selected_rows + tail


def evaluate_top_slice_criteria(
    *,
    diversity_before: float,
    diversity_after: float,
) -> dict[str, Any]:
    gain = round(float(diversity_after) - float(diversity_before), 4)
    target_met = float(diversity_after) >= float(DIVERSITY_LOW_THRESHOLD)
    material_gain_met = gain >= MIN_MATERIAL_DIVERSITY_GAIN
    return {
        "diversity_threshold": float(DIVERSITY_LOW_THRESHOLD),
        "min_material_gain": MIN_MATERIAL_DIVERSITY_GAIN,
        "diversity_before": round(float(diversity_before), 4),
        "diversity_after": round(float(diversity_after), 4),
        "diversity_gain_absolute": gain,
        "diversity_target_met": target_met,
        "material_gain_met": material_gain_met,
        "criteria_met": target_met or material_gain_met,
    }


def apply_diverse_top_slice_pre_gp(
    pool: Sequence[Mapping[str, Any]],
    *,
    game_size: int,
    requested_count: int,
    batch_label: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Aplica seleção diversa ao pool antes do portão M-ML-073."""
    empty_bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "selection_version": SELECTION_VERSION,
        "diverse_top_slice_applied": False,
    }
    if not is_diverse_top_slice_enabled() or not is_structural_policy_15d_format(int(game_size)):
        return [dict(game) for game in pool], empty_bundle

    limit = slice_limit(requested_count=int(requested_count))
    before_slice = _score_based_slice(pool, limit=limit)
    before_metrics = _measure_slice_diversity(
        before_slice,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=int(requested_count),
    )

    selected_slice = select_diverse_pre_gp_top_slice(
        pool,
        limit=limit,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=int(requested_count),
    )
    if not selected_slice:
        return [dict(game) for game in pool], empty_bundle

    reordered_pool = reorder_pool_with_diverse_top_slice(pool, selected_slice)
    after_slice = reordered_pool[:limit]
    after_metrics = _measure_slice_diversity(
        after_slice,
        game_size=int(game_size),
        batch_label=batch_label,
        requested_count=int(requested_count),
    )
    criteria = evaluate_top_slice_criteria(
        diversity_before=float(before_metrics.get("diversity_score", 0.0) or 0.0),
        diversity_after=float(after_metrics.get("diversity_score", 0.0) or 0.0),
    )
    caps = _family_caps(limit)
    dominant_pair = after_metrics.get("dominant_family") or ("", 0)
    if isinstance(dominant_pair, (list, tuple)) and len(dominant_pair) >= 2:
        dominant_label = str(dominant_pair[0] or "")
        dominant_count = int(dominant_pair[1] or 0)
    else:
        dominant_label, dominant_count = "", 0
    bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "selection_version": SELECTION_VERSION,
        "diverse_top_slice_applied": True,
        "requested_count": int(requested_count),
        "candidate_pool_size": limit,
        "selection_mode": "family_capped_diversity",
        "family_caps": caps,
        "metrics_before": before_metrics,
        "metrics_after": after_metrics,
        "criteria": criteria,
        "top_slice_changed": {_game_signature(game) for game in before_slice}
        != {_game_signature(game) for game in after_slice},
        "candidates_replaced": len(
            {_game_signature(game) for game in before_slice}
            - {_game_signature(game) for game in selected_slice}
        ),
        "selected_count": len(selected_slice),
        "dominant_family_after": dominant_label,
        "dominant_family_share_after": dominant_count,
        "dominant_family_within_cap": dominant_count <= caps["family_cap"],
    }
    return reordered_pool, bundle


def build_diverse_top_slice_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    criteria = dict(source.get("criteria") or {})
    return {
        "mission_id": MISSION_ID,
        "selection_version": SELECTION_VERSION,
        "diverse_top_slice_applied": bool(source.get("diverse_top_slice_applied")),
        "requested_count": int(source.get("requested_count", 0) or 0),
        "candidate_pool_size": int(source.get("candidate_pool_size", 0) or 0),
        "selection_mode": str(source.get("selection_mode") or ""),
        "diversity_score_before": float(
            dict(source.get("metrics_before") or {}).get("diversity_score", 0.0) or 0.0
        ),
        "diversity_score_after": float(
            dict(source.get("metrics_after") or {}).get("diversity_score", 0.0) or 0.0
        ),
        "diversity_gain_absolute": float(criteria.get("diversity_gain_absolute", 0.0) or 0.0),
        "diversity_target_met": bool(criteria.get("diversity_target_met")),
        "material_gain_met": bool(criteria.get("material_gain_met")),
        "criteria_met": bool(criteria.get("criteria_met")),
        "top_slice_changed": bool(source.get("top_slice_changed")),
        "candidates_replaced": int(source.get("candidates_replaced", 0) or 0),
        "dominant_family_after": str(source.get("dominant_family_after") or ""),
        "dominant_family_share_after": int(source.get("dominant_family_share_after", 0) or 0),
        "dominant_family_within_cap": bool(source.get("dominant_family_within_cap")),
    }
