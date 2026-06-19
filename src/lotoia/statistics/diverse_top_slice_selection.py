"""Seleção estatística diversa do top slice pré-GP — M-STAT-002.

Substitui o recorte requested_count×3 por score puro por swap determinístico
alinhado ao detector de conformidade (teto de sufixo + anti-clone por overlap).
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD
from lotoia.ml.structural_policy_15d import is_structural_policy_15d_format
from lotoia.ml.supervised_output_calibration import (
    DOMINANCE_CALIBRATION_THRESHOLD,
    DEFAULT_PREFIX_SHARE_LIMIT,
    analyze_pool_structural_issues,
)
from lotoia.statistics.card_structure import (
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)

MISSION_ID = "M-STAT-002"
SELECTION_VERSION = "M-STAT-002-v3"
ENV_DIVERSE_TOP_SLICE_ENABLED = "LOTOIA_DIVERSE_TOP_SLICE_ENABLED"
ENV_MSTAT_002_SUFFIX_CAP = "LOTOIA_MSTAT_002_SUFFIX_CAP"
ENV_MSTAT_002_MAX_OVERLAP = "LOTOIA_MSTAT_002_MAX_OVERLAP"
MIN_MATERIAL_DIVERSITY_GAIN = 0.20
MAX_PREFIX_SUFFIX_SHARE = 0.14
MAX_FAMILY_SHARE = 0.10
MAX_SWAP_ITERATIONS = 200
DEFAULT_MAX_OVERLAP_15D = 12


def is_diverse_top_slice_enabled() -> bool:
    raw = os.getenv(ENV_DIVERSE_TOP_SLICE_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _suffix_cap_for_pool(pool_size: int) -> int:
    raw = os.getenv(ENV_MSTAT_002_SUFFIX_CAP, str(DOMINANCE_CALIBRATION_THRESHOLD)).strip()
    try:
        configured = int(raw)
    except ValueError:
        configured = DOMINANCE_CALIBRATION_THRESHOLD
    issue_limit = _structural_issue_limit(pool_size)
    return max(3, min(configured, issue_limit - 1))


def _max_overlap_for_game_size(game_size: int) -> int:
    raw = os.getenv(ENV_MSTAT_002_MAX_OVERLAP, str(DEFAULT_MAX_OVERLAP_15D)).strip()
    try:
        configured = int(raw)
    except ValueError:
        configured = DEFAULT_MAX_OVERLAP_15D
    return max(int(game_size) - 5, min(configured, int(game_size) - 2))


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


def _profile_score(game: Mapping[str, Any]) -> float:
    return float(game.get("profile_score", 0.0) or 0.0)


def _score_based_slice(
    pool: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        [dict(game) for game in pool],
        key=_profile_score,
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


def _structural_issue_limit(pool_size: int) -> int:
    size = max(int(pool_size), 1)
    return max(DOMINANCE_CALIBRATION_THRESHOLD, int(size * DEFAULT_PREFIX_SHARE_LIMIT))


def _family_caps(limit: int) -> dict[str, int]:
    size = max(int(limit), 1)
    suffix_cap = _suffix_cap_for_pool(size)
    family_cap = max(2, int(size * MAX_FAMILY_SHARE))
    return {
        "prefix_cap": suffix_cap,
        "suffix_cap": suffix_cap,
        "family_cap": family_cap,
        "structural_issue_limit": _structural_issue_limit(size),
        "max_overlap_permitted": DEFAULT_MAX_OVERLAP_15D,
    }


def _overlap_between_cards(
    left: Sequence[int],
    right: Sequence[int],
) -> int:
    return len(set(left) & set(right))


def _suffix_count_map(batch: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for game in batch:
        suffix = _suffix_key(game)
        if suffix:
            counts[suffix] = counts.get(suffix, 0) + 1
    return counts


def _family_count_map(batch: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for game in batch:
        family = _family_key(game)
        if family:
            counts[family] = counts.get(family, 0) + 1
    return counts


def _candidate_fits_structural_caps(
    candidate: Mapping[str, Any],
    *,
    suffix_counts: Mapping[str, int],
    family_counts: Mapping[str, int],
    suffix_cap: int,
    family_cap: int,
) -> bool:
    suffix = _suffix_key(candidate)
    family = _family_key(candidate)
    if suffix and suffix_counts.get(suffix, 0) + 1 > suffix_cap:
        return False
    if family and family_counts.get(family, 0) + 1 > family_cap:
        return False
    return True


def _candidate_fits_overlap(
    candidate: Mapping[str, Any],
    batch: Sequence[Mapping[str, Any]],
    *,
    max_overlap: int,
    skip_index: int | None = None,
) -> bool:
    signature = _game_signature(candidate)
    if not signature:
        return False
    for index, game in enumerate(batch):
        if skip_index is not None and index == skip_index:
            continue
        other = _game_signature(game)
        if other and _overlap_between_cards(signature, other) > max_overlap:
            return False
    return True


def run_mstat_002_swap_engine(
    pool: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    game_size: int = 15,
    suffix_cap: int | None = None,
    family_cap: int | None = None,
    max_overlap: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Motor de swap M-STAT-002 — baseline por score + camadas sufixo/família e anti-clone."""
    rows = [dict(game) for game in pool if _game_signature(game)]
    target = min(int(limit), len(rows))
    if not rows or target <= 0:
        return [], {
            "structural_swaps": 0,
            "overlap_swaps": 0,
            "iterations": 0,
            "swap_exhausted": False,
        }

    effective_suffix_cap = int(suffix_cap if suffix_cap is not None else _suffix_cap_for_pool(target))
    effective_family_cap = int(
        family_cap if family_cap is not None else max(2, int(target * MAX_FAMILY_SHARE))
    )
    effective_max_overlap = int(
        max_overlap if max_overlap is not None else _max_overlap_for_game_size(int(game_size))
    )

    ranked = sorted(rows, key=_profile_score, reverse=True)
    batch = [dict(game) for game in ranked[:target]]
    reserve = [dict(game) for game in ranked[target:]]

    structural_swaps = 0
    overlap_swaps = 0
    iteration = 0
    executing_swaps = True

    while executing_swaps and iteration < MAX_SWAP_ITERATIONS:
        executing_swaps = False
        iteration += 1

        suffix_counts = _suffix_count_map(batch)
        family_counts = _family_count_map(batch)
        violating_suffixes = {suffix for suffix, count in suffix_counts.items() if count > effective_suffix_cap}
        violating_families = {family for family, count in family_counts.items() if count > effective_family_cap}

        if violating_suffixes or violating_families:
            for batch_index in range(len(batch) - 1, -1, -1):
                game = batch[batch_index]
                suffix = _suffix_key(game)
                family = _family_key(game)
                if suffix not in violating_suffixes and family not in violating_families:
                    continue

                for reserve_index, candidate in enumerate(reserve):
                    if not _candidate_fits_structural_caps(
                        candidate,
                        suffix_counts=suffix_counts,
                        family_counts=family_counts,
                        suffix_cap=effective_suffix_cap,
                        family_cap=effective_family_cap,
                    ):
                        continue
                    removed = batch.pop(batch_index)
                    replacement = dict(candidate)
                    replacement["m_stat_002_structural_swap"] = True
                    removed.setdefault("m_stat_002_demoted_to_reserve", True)
                    batch.append(replacement)
                    reserve.pop(reserve_index)
                    reserve.append(removed)
                    reserve.sort(key=_profile_score, reverse=True)
                    structural_swaps += 1
                    executing_swaps = True
                    break
                if executing_swaps:
                    break
            continue

        violator_candidates: list[int] = []
        for left in range(len(batch)):
            left_card = list(_game_signature(batch[left]))
            if not left_card:
                continue
            for right in range(left + 1, len(batch)):
                right_card = list(_game_signature(batch[right]))
                if not right_card:
                    continue
                if _overlap_between_cards(left_card, right_card) <= effective_max_overlap:
                    continue
                if _profile_score(batch[right]) < _profile_score(batch[left]):
                    violator_candidates.append(right)
                else:
                    violator_candidates.append(left)

        swapped_overlap = False
        for violator_index in sorted(set(violator_candidates), key=lambda idx: _profile_score(batch[idx])):
            suffix_counts = _suffix_count_map(batch)
            family_counts = _family_count_map(batch)
            ejected = batch[violator_index]
            ranked_reserve = sorted(
                enumerate(reserve),
                key=lambda item: (
                    max(
                        (
                            _overlap_between_cards(list(_game_signature(item[1])), list(_game_signature(game)))
                            for game in batch
                            if _game_signature(item[1]) and _game_signature(game)
                        ),
                        default=int(game_size),
                    ),
                    -_profile_score(item[1]),
                ),
            )
            for reserve_index, candidate in ranked_reserve:
                if not _candidate_fits_structural_caps(
                    candidate,
                    suffix_counts=suffix_counts,
                    family_counts=family_counts,
                    suffix_cap=effective_suffix_cap,
                    family_cap=effective_family_cap,
                ):
                    continue
                if not _candidate_fits_overlap(
                    candidate,
                    batch,
                    max_overlap=effective_max_overlap,
                    skip_index=violator_index,
                ):
                    continue
                batch.pop(violator_index)
                replacement = dict(candidate)
                replacement["m_stat_002_overlap_swap"] = True
                ejected.setdefault("m_stat_002_demoted_to_reserve", True)
                batch.append(replacement)
                reserve.pop(reserve_index)
                reserve.append(dict(ejected))
                reserve.sort(key=_profile_score, reverse=True)
                overlap_swaps += 1
                executing_swaps = True
                swapped_overlap = True
                break
            if swapped_overlap:
                break

        if not swapped_overlap and violator_candidates:
            break

    batch.sort(key=_profile_score, reverse=True)
    for index, row in enumerate(batch):
        row.setdefault("diverse_top_slice_selected", True)
        row["m_stat_002_selection_rank"] = index + 1

    return batch[:target], {
        "structural_swaps": structural_swaps,
        "overlap_swaps": overlap_swaps,
        "iterations": iteration,
        "swap_exhausted": iteration >= MAX_SWAP_ITERATIONS,
        "suffix_cap": effective_suffix_cap,
        "family_cap": effective_family_cap,
        "max_overlap_permitted": effective_max_overlap,
    }


def select_diverse_pre_gp_top_slice(
    pool: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    game_size: int = 15,
    batch_label: str | None = None,
    requested_count: int | None = None,
    relax_level: int = 0,
) -> list[dict[str, Any]]:
    """Seleciona top slice com swap engine M-STAT-002."""
    _ = (batch_label, requested_count, relax_level)
    caps = _family_caps(limit)
    selected, _stats = run_mstat_002_swap_engine(
        pool,
        limit=limit,
        game_size=int(game_size),
        suffix_cap=caps["suffix_cap"],
        family_cap=caps["family_cap"] + max(0, int(relax_level) // 2),
        max_overlap=_max_overlap_for_game_size(int(game_size)),
    )
    return selected


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

    base_score = max(_profile_score(row) for row in selected_rows + tail)
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

    selected_slice, swap_stats = run_mstat_002_swap_engine(
        pool,
        limit=limit,
        game_size=int(game_size),
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
    suffix_top = after_metrics.get("top_suffix") or ("", 0)
    suffix_label = str(suffix_top[0] or "") if isinstance(suffix_top, (list, tuple)) else ""
    suffix_share = int(suffix_top[1] or 0) if isinstance(suffix_top, (list, tuple)) and len(suffix_top) >= 2 else 0
    bundle: dict[str, Any] = {
        "mission_id": MISSION_ID,
        "selection_version": SELECTION_VERSION,
        "diverse_top_slice_applied": True,
        "requested_count": int(requested_count),
        "candidate_pool_size": limit,
        "selection_mode": "mstat_002_swap_engine",
        "family_caps": caps,
        "swap_stats": swap_stats,
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
        "dominant_suffix_after": suffix_label,
        "dominant_suffix_share_after": suffix_share,
        "dominant_suffix_within_cap": suffix_share <= caps["suffix_cap"],
    }
    return reordered_pool, bundle


def build_diverse_top_slice_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    criteria = dict(source.get("criteria") or {})
    swap_stats = dict(source.get("swap_stats") or {})
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
        "structural_swaps": int(swap_stats.get("structural_swaps", 0) or 0),
        "overlap_swaps": int(swap_stats.get("overlap_swaps", 0) or 0),
        "suffix_cap": int(swap_stats.get("suffix_cap", 0) or 0),
        "max_overlap_permitted": int(swap_stats.get("max_overlap_permitted", 0) or 0),
        "dominant_family_after": str(source.get("dominant_family_after") or ""),
        "dominant_family_share_after": int(source.get("dominant_family_share_after", 0) or 0),
        "dominant_family_within_cap": bool(source.get("dominant_family_within_cap")),
        "dominant_suffix_after": str(source.get("dominant_suffix_after") or ""),
        "dominant_suffix_share_after": int(source.get("dominant_suffix_share_after", 0) or 0),
        "dominant_suffix_within_cap": bool(source.get("dominant_suffix_within_cap")),
    }
