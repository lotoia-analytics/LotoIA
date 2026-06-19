"""Seleção estatística diversa do top slice pré-GP — M-STAT-002.

Substitui o recorte requested_count×3 por score puro por swap determinístico
alinhado ao detector de conformidade (teto de trinca estrutural dominante 01-02-03,
sufixo e anti-clone por overlap).
"""

from __future__ import annotations

import os
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.governance.institutional_agent_routing_matrix import AGENT_GERACAO
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
from lotoia.statistics.similarity_overlap_decomposition import (
    DOMINANT_STRUCTURAL_TRIPLE_LABEL,
    build_similarity_decomposition_trace,
    decompose_pool_similarity,
)

MISSION_ID = "M-STAT-002"
SELECTION_VERSION = "M-STAT-002-v4"
ENV_DIVERSE_TOP_SLICE_ENABLED = "LOTOIA_DIVERSE_TOP_SLICE_ENABLED"
ENV_MSTAT_002_SUFFIX_CAP = "LOTOIA_MSTAT_002_SUFFIX_CAP"
ENV_MSTAT_002_PREFIX_CAP = "LOTOIA_MSTAT_002_PREFIX_CAP"
ENV_MSTAT_002_MAX_OVERLAP = "LOTOIA_MSTAT_002_MAX_OVERLAP"
MIN_MATERIAL_DIVERSITY_GAIN = 0.20
MAX_PREFIX_SUFFIX_SHARE = 0.14
MAX_FAMILY_SHARE = 0.10
MAX_SWAP_ITERATIONS = 200
DEFAULT_MAX_OVERLAP_15D = 12


def is_diverse_top_slice_enabled() -> bool:
    raw = os.getenv(ENV_DIVERSE_TOP_SLICE_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _structural_cap_for_pool(pool_size: int, *, env_var: str) -> int:
    default = str(DOMINANCE_CALIBRATION_THRESHOLD)
    raw = os.getenv(env_var, default).strip()
    try:
        configured = int(raw)
    except ValueError:
        configured = DOMINANCE_CALIBRATION_THRESHOLD
    issue_limit = _structural_issue_limit(pool_size)
    return max(3, min(configured, issue_limit - 1))


def _suffix_cap_for_pool(pool_size: int) -> int:
    return _structural_cap_for_pool(pool_size, env_var=ENV_MSTAT_002_SUFFIX_CAP)


def _prefix_cap_for_pool(pool_size: int) -> int:
    """Teto de dominância da trinca estrutural 01-02-03 no top-slice (não prefixo genérico)."""
    return _structural_cap_for_pool(pool_size, env_var=ENV_MSTAT_002_PREFIX_CAP)


def _structural_triple_cap_for_pool(pool_size: int) -> int:
    return _prefix_cap_for_pool(pool_size)


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


def _count_non_triplet_cards(games: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        1
        for game in games
        if _prefix_key(game) and _prefix_key(game) != DOMINANT_STRUCTURAL_TRIPLE_LABEL
    )


def _non_triplet_reserve_requirements(*, target: int, triple_cap: int) -> dict[str, int]:
    """Quantidade mínima de candidatos não-trinca no pool para cumprir o teto."""
    required = max(0, int(target) - int(triple_cap))
    ideal = max(required * 2, required + 1)
    return {
        "required": required,
        "ideal": ideal,
    }


def _evaluate_non_triplet_reserve(
    *,
    target: int,
    triple_cap: int,
    pool_rows: Sequence[Mapping[str, Any]],
    reserve_rows: Sequence[Mapping[str, Any]],
    final_triple_count: int,
) -> dict[str, Any]:
    requirements = _non_triplet_reserve_requirements(target=target, triple_cap=triple_cap)
    non_triplet_pool = _count_non_triplet_cards(pool_rows)
    non_triplet_reserve = _count_non_triplet_cards(reserve_rows)
    final_excess = max(int(final_triple_count) - int(triple_cap), 0)
    insufficient = final_excess > 0 and non_triplet_pool < int(requirements["required"])
    return {
        "non_triplet_pool_count": non_triplet_pool,
        "non_triplet_reserve_count": non_triplet_reserve,
        "non_triplet_required_count": int(requirements["required"]),
        "non_triplet_ideal_count": int(requirements["ideal"]),
        "structural_triplet_010203_excess": final_excess,
        "pool_insufficient_non_triplet_reserve": insufficient,
        "responsible_agent": AGENT_GERACAO if insufficient else "",
        "next_mission_hint": "M-ML-072" if insufficient else "",
    }


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
    prefix_cap = _prefix_cap_for_pool(size)
    suffix_cap = _suffix_cap_for_pool(size)
    family_cap = max(2, int(size * MAX_FAMILY_SHARE))
    return {
        "prefix_cap": prefix_cap,
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


def _prefix_count_map(batch: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for game in batch:
        prefix = _prefix_key(game)
        if prefix:
            counts[prefix] = counts.get(prefix, 0) + 1
    return counts


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
    prefix_counts: Mapping[str, int],
    suffix_counts: Mapping[str, int],
    family_counts: Mapping[str, int],
    prefix_cap: int,
    suffix_cap: int,
    family_cap: int,
    removed_prefix: str | None = None,
    removed_suffix: str | None = None,
    removed_family: str | None = None,
) -> bool:
    prefix = _prefix_key(candidate)
    suffix = _suffix_key(candidate)
    family = _family_key(candidate)

    triple_count = int(prefix_counts.get(DOMINANT_STRUCTURAL_TRIPLE_LABEL, 0) or 0)
    if removed_prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL:
        triple_count = max(triple_count - 1, 0)
    if prefix == DOMINANT_STRUCTURAL_TRIPLE_LABEL and triple_count + 1 > prefix_cap:
        return False

    if suffix:
        suffix_count = int(suffix_counts.get(suffix, 0) or 0)
        if removed_suffix and removed_suffix == suffix:
            suffix_count = max(suffix_count - 1, 0)
        if suffix_count + 1 > suffix_cap:
            return False

    if family:
        family_count = int(family_counts.get(family, 0) or 0)
        if removed_family and removed_family == family:
            family_count = max(family_count - 1, 0)
        if family_count + 1 > family_cap:
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
    prefix_cap: int | None = None,
    suffix_cap: int | None = None,
    family_cap: int | None = None,
    max_overlap: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Motor de swap M-STAT-002 — baseline + trinca dominante 01-02-03/sufixo/família e anti-clone."""
    rows = [dict(game) for game in pool if _game_signature(game)]
    target = min(int(limit), len(rows))
    if not rows or target <= 0:
        return [], {
            "structural_swaps": 0,
            "structural_triple_swaps": 0,
            "prefix_swaps": 0,
            "suffix_swaps": 0,
            "overlap_swaps": 0,
            "iterations": 0,
            "swap_exhausted": False,
        }

    effective_structural_triple_cap = int(
        prefix_cap if prefix_cap is not None else _structural_triple_cap_for_pool(target)
    )
    effective_suffix_cap = int(suffix_cap if suffix_cap is not None else _suffix_cap_for_pool(target))
    effective_family_cap = int(
        family_cap if family_cap is not None else max(2, int(target * MAX_FAMILY_SHARE))
    )
    effective_max_overlap = int(
        max_overlap if max_overlap is not None else _max_overlap_for_game_size(int(game_size))
    )

    distinct_suffixes_in_pool = len({_suffix_key(game) for game in rows if _suffix_key(game)})
    _ = distinct_suffixes_in_pool

    ranked = sorted(rows, key=_profile_score, reverse=True)
    batch = [dict(game) for game in ranked[:target]]
    reserve = [dict(game) for game in ranked[target:]]

    structural_swaps = 0
    structural_triple_swaps = 0
    prefix_swaps = 0
    suffix_swaps = 0
    overlap_swaps = 0
    iteration = 0
    executing_swaps = True

    while executing_swaps and iteration < MAX_SWAP_ITERATIONS:
        executing_swaps = False
        iteration += 1

        prefix_counts = _prefix_count_map(batch)
        suffix_counts = _suffix_count_map(batch)
        family_counts = _family_count_map(batch)
        triple_count = prefix_counts.get(DOMINANT_STRUCTURAL_TRIPLE_LABEL, 0)
        has_non_triple_reserve = any(
            _prefix_key(game) != DOMINANT_STRUCTURAL_TRIPLE_LABEL for game in reserve
        )
        violating_structural_triples = (
            {DOMINANT_STRUCTURAL_TRIPLE_LABEL}
            if triple_count > effective_structural_triple_cap and has_non_triple_reserve
            else set()
        )
        violating_suffixes = set()
        for suffix, count in suffix_counts.items():
            if count <= effective_suffix_cap:
                continue
            if any(_suffix_key(game) != suffix for game in reserve):
                violating_suffixes.add(suffix)
        violating_families = {family for family, count in family_counts.items() if count > effective_family_cap}

        if violating_structural_triples or violating_suffixes or violating_families:
            structural_progress = False
            for batch_index in range(len(batch) - 1, -1, -1):
                game = batch[batch_index]
                prefix = _prefix_key(game)
                suffix = _suffix_key(game)
                family = _family_key(game)
                if (
                    prefix not in violating_structural_triples
                    and suffix not in violating_suffixes
                    and family not in violating_families
                ):
                    continue

                swapped = False
                ranked_reserve = sorted(
                    enumerate(reserve),
                    key=lambda item: (
                        1 if _prefix_key(item[1]) == DOMINANT_STRUCTURAL_TRIPLE_LABEL else 0,
                        prefix_counts.get(_prefix_key(item[1]), 0),
                        suffix_counts.get(_suffix_key(item[1]), 0),
                        family_counts.get(_family_key(item[1]), 0),
                        -_profile_score(item[1]),
                    ),
                )
                for reserve_index, candidate in ranked_reserve:
                    if not _candidate_fits_structural_caps(
                        candidate,
                        prefix_counts=prefix_counts,
                        suffix_counts=suffix_counts,
                        family_counts=family_counts,
                        prefix_cap=effective_structural_triple_cap,
                        suffix_cap=effective_suffix_cap,
                        family_cap=effective_family_cap,
                        removed_prefix=prefix,
                        removed_suffix=suffix,
                        removed_family=family,
                    ):
                        continue
                    removed = batch.pop(batch_index)
                    replacement = dict(candidate)
                    replacement["m_stat_002_structural_swap"] = True
                    if prefix in violating_structural_triples:
                        replacement["m_stat_002_structural_triple_swap"] = True
                        replacement["m_stat_002_prefix_swap"] = True
                        structural_triple_swaps += 1
                        prefix_swaps += 1
                    elif suffix in violating_suffixes:
                        replacement["m_stat_002_suffix_swap"] = True
                        suffix_swaps += 1
                    removed.setdefault("m_stat_002_demoted_to_reserve", True)
                    batch.append(replacement)
                    reserve.pop(reserve_index)
                    reserve.append(removed)
                    reserve.sort(key=_profile_score, reverse=True)
                    structural_swaps += 1
                    structural_progress = True
                    executing_swaps = True
                    swapped = True
                    break
                if swapped:
                    break
            if executing_swaps:
                continue
            _ = structural_progress

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
            prefix_counts = _prefix_count_map(batch)
            suffix_counts = _suffix_count_map(batch)
            family_counts = _family_count_map(batch)
            ejected = batch[violator_index]
            ejected_prefix = _prefix_key(ejected)
            ejected_suffix = _suffix_key(ejected)
            ejected_family = _family_key(ejected)
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
                    prefix_counts.get(_prefix_key(item[1]), 0),
                    suffix_counts.get(_suffix_key(item[1]), 0),
                    family_counts.get(_family_key(item[1]), 0),
                    -_profile_score(item[1]),
                ),
            )
            for reserve_index, candidate in ranked_reserve:
                if not _candidate_fits_structural_caps(
                    candidate,
                    prefix_counts=prefix_counts,
                    suffix_counts=suffix_counts,
                    family_counts=family_counts,
                    prefix_cap=effective_structural_triple_cap,
                    suffix_cap=effective_suffix_cap,
                    family_cap=effective_family_cap,
                    removed_prefix=ejected_prefix,
                    removed_suffix=ejected_suffix,
                    removed_family=ejected_family,
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

    final_triple_count = int(_prefix_count_map(batch).get(DOMINANT_STRUCTURAL_TRIPLE_LABEL, 0))
    reserve_diag = _evaluate_non_triplet_reserve(
        target=target,
        triple_cap=effective_structural_triple_cap,
        pool_rows=rows,
        reserve_rows=reserve,
        final_triple_count=final_triple_count,
    )

    return batch[:target], {
        "structural_swaps": structural_swaps,
        "structural_triple_swaps": structural_triple_swaps,
        "structural_triplet_010203_swaps": structural_triple_swaps,
        "prefix_swaps": prefix_swaps,
        "suffix_swaps": suffix_swaps,
        "overlap_swaps": overlap_swaps,
        "iterations": iteration,
        "swap_exhausted": iteration >= MAX_SWAP_ITERATIONS,
        "structural_triple_cap": effective_structural_triple_cap,
        "structural_triplet_010203_cap": effective_structural_triple_cap,
        "prefix_cap": effective_structural_triple_cap,
        "structural_triplet_010203_count": final_triple_count,
        "structural_triplet_010203_excess": reserve_diag["structural_triplet_010203_excess"],
        "non_triplet_pool_count": reserve_diag["non_triplet_pool_count"],
        "non_triplet_reserve_count": reserve_diag["non_triplet_reserve_count"],
        "non_triplet_required_count": reserve_diag["non_triplet_required_count"],
        "non_triplet_ideal_count": reserve_diag["non_triplet_ideal_count"],
        "pool_insufficient_non_triplet_reserve": reserve_diag["pool_insufficient_non_triplet_reserve"],
        "responsible_agent": reserve_diag["responsible_agent"],
        "next_mission_hint": reserve_diag["next_mission_hint"],
        "suffix_cap": effective_suffix_cap,
        "family_cap": effective_family_cap,
        "max_overlap_permitted": effective_max_overlap,
        "structural_triplet_policy": "allowed_until_cap_penalize_excess_only",
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
        prefix_cap=caps["prefix_cap"],
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
    previous_contest_numbers: Sequence[int] | None = None,
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
    caps = _family_caps(limit)
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
    similarity_before = decompose_pool_similarity(
        before_slice,
        game_size=int(game_size),
        previous_contest_numbers=previous_contest_numbers,
        structural_triple_dominance_cap=caps["prefix_cap"],
    )
    similarity_after = decompose_pool_similarity(
        after_slice,
        game_size=int(game_size),
        previous_contest_numbers=previous_contest_numbers,
        structural_triple_dominance_cap=caps["prefix_cap"],
    )
    criteria = evaluate_top_slice_criteria(
        diversity_before=float(before_metrics.get("diversity_score", 0.0) or 0.0),
        diversity_after=float(after_metrics.get("diversity_score", 0.0) or 0.0),
    )
    dominant_pair = after_metrics.get("dominant_family") or ("", 0)
    if isinstance(dominant_pair, (list, tuple)) and len(dominant_pair) >= 2:
        dominant_label = str(dominant_pair[0] or "")
        dominant_count = int(dominant_pair[1] or 0)
    else:
        dominant_label, dominant_count = "", 0
    suffix_top = after_metrics.get("top_suffix") or ("", 0)
    suffix_label = str(suffix_top[0] or "") if isinstance(suffix_top, (list, tuple)) else ""
    suffix_share = int(suffix_top[1] or 0) if isinstance(suffix_top, (list, tuple)) and len(suffix_top) >= 2 else 0
    prefix_top = after_metrics.get("top_prefix") or ("", 0)
    prefix_label = str(prefix_top[0] or "") if isinstance(prefix_top, (list, tuple)) else ""
    prefix_share = int(prefix_top[1] or 0) if isinstance(prefix_top, (list, tuple)) and len(prefix_top) >= 2 else 0
    triple_share = 0
    if prefix_label == DOMINANT_STRUCTURAL_TRIPLE_LABEL:
        triple_share = prefix_share
    else:
        for game in after_slice:
            if _prefix_key(game) == DOMINANT_STRUCTURAL_TRIPLE_LABEL:
                triple_share += 1
    gp_requirements = _non_triplet_reserve_requirements(
        target=int(requested_count),
        triple_cap=caps["prefix_cap"],
    )
    top_slice_requirements = _non_triplet_reserve_requirements(
        target=limit,
        triple_cap=caps["prefix_cap"],
    )
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
        "dominant_prefix_after": prefix_label,
        "dominant_prefix_share_after": prefix_share,
        "dominant_prefix_within_cap": prefix_share <= caps["prefix_cap"],
        "dominant_structural_triple_label": DOMINANT_STRUCTURAL_TRIPLE_LABEL,
        "dominant_structural_triple_share_after": triple_share,
        "dominant_structural_triple_within_cap": triple_share <= caps["prefix_cap"],
        "similarity_decomposition_before": similarity_before,
        "similarity_decomposition_after": similarity_after,
        "similarity_decomposition_report_before": build_similarity_decomposition_trace(similarity_before),
        "similarity_decomposition_report_after": build_similarity_decomposition_trace(similarity_after),
        "pool_insufficient_non_triplet_reserve": bool(
            swap_stats.get("pool_insufficient_non_triplet_reserve")
        ),
        "responsible_agent": str(swap_stats.get("responsible_agent") or ""),
        "next_mission_hint": str(swap_stats.get("next_mission_hint") or ""),
        "non_triplet_pool_count": int(swap_stats.get("non_triplet_pool_count", 0) or 0),
        "non_triplet_reserve_count": int(swap_stats.get("non_triplet_reserve_count", 0) or 0),
        "non_triplet_required_count_top_slice": int(top_slice_requirements["required"]),
        "non_triplet_ideal_count_top_slice": int(top_slice_requirements["ideal"]),
        "non_triplet_required_count_gp": int(gp_requirements["required"]),
        "non_triplet_ideal_count_gp": int(gp_requirements["ideal"]),
    }
    return reordered_pool, bundle


def build_diverse_top_slice_trace(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    criteria = dict(source.get("criteria") or {})
    swap_stats = dict(source.get("swap_stats") or {})
    triple_count = int(
        swap_stats.get("structural_triplet_010203_count")
        or source.get("dominant_structural_triple_share_after", 0)
        or 0
    )
    triple_cap = int(
        swap_stats.get("structural_triplet_010203_cap")
        or swap_stats.get("structural_triple_cap")
        or swap_stats.get("prefix_cap", 0)
        or 0
    )
    triple_excess = int(
        swap_stats.get("structural_triplet_010203_excess")
        or max(triple_count - triple_cap, 0)
    )
    triple_swaps = int(
        swap_stats.get("structural_triplet_010203_swaps")
        or swap_stats.get("structural_triple_swaps")
        or swap_stats.get("prefix_swaps", 0)
        or 0
    )
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
        "structural_triplet_010203_count": triple_count,
        "structural_triplet_010203_cap": triple_cap,
        "structural_triplet_010203_excess": triple_excess,
        "structural_triplet_010203_swaps": triple_swaps,
        "structural_triplet_policy": str(
            swap_stats.get("structural_triplet_policy") or "allowed_until_cap_penalize_excess_only"
        ),
        "structural_swaps": int(swap_stats.get("structural_swaps", 0) or 0),
        "prefix_swaps": int(swap_stats.get("prefix_swaps", 0) or 0),
        "structural_triple_swaps": triple_swaps,
        "suffix_swaps": int(swap_stats.get("suffix_swaps", 0) or 0),
        "overlap_swaps": int(swap_stats.get("overlap_swaps", 0) or 0),
        "structural_triple_cap": triple_cap,
        "prefix_cap": triple_cap,
        "suffix_cap": int(swap_stats.get("suffix_cap", 0) or 0),
        "max_overlap_permitted": int(swap_stats.get("max_overlap_permitted", 0) or 0),
        "dominant_family_after": str(source.get("dominant_family_after") or ""),
        "dominant_family_share_after": int(source.get("dominant_family_share_after", 0) or 0),
        "dominant_family_within_cap": bool(source.get("dominant_family_within_cap")),
        "dominant_suffix_after": str(source.get("dominant_suffix_after") or ""),
        "dominant_suffix_share_after": int(source.get("dominant_suffix_share_after", 0) or 0),
        "dominant_suffix_within_cap": bool(source.get("dominant_suffix_within_cap")),
        "dominant_prefix_after": str(source.get("dominant_prefix_after") or ""),
        "dominant_prefix_share_after": int(source.get("dominant_prefix_share_after", 0) or 0),
        "dominant_prefix_within_cap": bool(source.get("dominant_prefix_within_cap")),
        "dominant_structural_triple_label": str(
            source.get("dominant_structural_triple_label") or DOMINANT_STRUCTURAL_TRIPLE_LABEL
        ),
        "dominant_structural_triple_share_after": int(
            source.get("dominant_structural_triple_share_after", 0) or 0
        ),
        "dominant_structural_triple_within_cap": bool(
            source.get("dominant_structural_triple_within_cap")
        ),
        "similarity_decomposition_before": dict(source.get("similarity_decomposition_report_before") or {}),
        "similarity_decomposition_after": dict(source.get("similarity_decomposition_report_after") or {}),
        "pool_insufficient_non_triplet_reserve": bool(
            swap_stats.get("pool_insufficient_non_triplet_reserve")
            or source.get("pool_insufficient_non_triplet_reserve")
        ),
        "responsible_agent": str(
            swap_stats.get("responsible_agent") or source.get("responsible_agent") or ""
        ),
        "next_mission_hint": str(
            swap_stats.get("next_mission_hint") or source.get("next_mission_hint") or ""
        ),
        "non_triplet_pool_count": int(
            swap_stats.get("non_triplet_pool_count") or source.get("non_triplet_pool_count", 0) or 0
        ),
        "non_triplet_reserve_count": int(
            swap_stats.get("non_triplet_reserve_count") or source.get("non_triplet_reserve_count", 0) or 0
        ),
        "non_triplet_required_count_top_slice": int(
            source.get("non_triplet_required_count_top_slice", 0) or 0
        ),
        "non_triplet_ideal_count_top_slice": int(
            source.get("non_triplet_ideal_count_top_slice", 0) or 0
        ),
        "non_triplet_required_count_gp": int(source.get("non_triplet_required_count_gp", 0) or 0),
        "non_triplet_ideal_count_gp": int(source.get("non_triplet_ideal_count_gp", 0) or 0),
    }
