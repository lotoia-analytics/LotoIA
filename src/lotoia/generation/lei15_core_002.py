"""Lei 15 — Núcleo Soberano LEI15_CORE_002 (5 camadas).

L1 generation_cand_d   — pool CAND-D N-C1..N-C6
L2 v1_selection_compose — compose_diverse_gp (Realinhamento V1)
L3 v1_strong_shield     — lei15_core_structural_payload
L4 anti_clone_gp        — overlap e arquitetura no GP final
L5 critical_digit_layer — reforço 07/12/23; penalização contextual 15/25
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence

from lotoia.generation.lei15_core_structural_payload import (
    apply_core_traceability_payload,
    is_v1_strong_pattern,
)
from lotoia.governance.lei15_core_candidate_001 import (
    BATCH_LABEL_D,
    resolve_candidate_config,
)
from lotoia.governance.lei15_core_002_sovereign import (
    CANDIDATE_ORIGIN_LABEL,
    Core002SovereignConfig,
    SOVEREIGN_STATUS,
)

logger = logging.getLogger(__name__)

# DEZENAS REFORÇADAS (L5 critical_digit_layer):
# - 07, 12, 23: dezenas com frequência oficial estável (~60%)
# - 16 REMOVIDA: super-representada (80% vs 55% oficial = +25pp)
# Ver: análise de frequência 300 concursos oficiais vs LotoIA (jun/2026)
_REINFORCE_DIGITS: frozenset[int] = frozenset({7, 12, 23})
_CONTEXTUAL_DISCOURAGE: frozenset[int] = frozenset({11, 15, 24, 25})
_NEVER_HARD_BLOCK: frozenset[int] = frozenset({15, 24, 25})
_GP_MAX_OVERLAP: int = 10
_GP_MAX_ARCH_PCT: float = 0.12


def _relaxed_overlap_limits(count: int) -> tuple[int, ...]:
    target = max(int(count or 0), 1)
    limits = [_GP_MAX_OVERLAP + 1, _GP_MAX_OVERLAP + 2]
    if target >= 20:
        limits.append(_GP_MAX_OVERLAP + 3)
    if target >= 35:
        limits.append(min(14, _GP_MAX_OVERLAP + 4))
    if target >= 50:
        limits.append(15)
    return tuple(sorted(set(limits)))


def _arch_share_limit(*, gp_target: int, relaxed: bool) -> float:
    if relaxed and int(gp_target) >= 25:
        return min(0.28, _GP_MAX_ARCH_PCT * 2.5)
    return _GP_MAX_ARCH_PCT


def _generation_cand_d_config():
    return resolve_candidate_config(BATCH_LABEL_D)


def _pairwise_overlap(a: list[int], b: list[int]) -> int:
    return len(set(a) & set(b))


def _architecture_key(game: dict) -> tuple[str, str]:
    return (
        str(game.get("prefix_signature") or ""),
        str(game.get("suffix_signature") or ""),
    )


def apply_critical_digit_layer(pool: list[dict]) -> list[dict]:
    """L5 — reforço suave de dezenas críticas; penalização contextual, sem veto."""
    for game in pool:
        nums = set(int(n) for n in (game.get("numbers") or []))
        boost = sum(2.5 for d in _REINFORCE_DIGITS if d in nums)
        penalty = 0.0
        discourage_present = nums & _CONTEXTUAL_DISCOURAGE
        if len(discourage_present) >= 4:
            penalty = (len(discourage_present) - 3) * 1.5
        # 15/24/25: penalização contextual apenas — nunca hard-block (_NEVER_HARD_BLOCK)
        current = float(game.get("profile_score", 0) or 0)
        game["profile_score"] = round(max(0.0, current + boost - penalty), 2)
        game["critical_digit_layer_applied"] = True
        meta = dict(game.get("lei15_core_002_metadata") or {})
        meta["critical_digit_boost"] = round(boost, 2)
        meta["critical_digit_penalty"] = round(penalty, 2)
        game["lei15_core_002_metadata"] = meta
    return pool


def build_sovereign_pool(
    pool_size: int,
    *,
    seed: int,
    history: list[object],
    config: Core002SovereignConfig,
) -> list[dict]:
    """L1 — pool diverso via motor CAND-D (N-C1..N-C6)."""
    from lotoia.generation.lei15_core_candidate_001 import build_candidate_pool

    cand_cfg = _generation_cand_d_config()
    pool = build_candidate_pool(pool_size, seed=seed, history=history, config=cand_cfg)
    pool = apply_critical_digit_layer(pool)
    for game in pool:
        game["generation_cand_d_applied"] = True
        game["v1_strong_shield_applied"] = bool(game.get("v1_strong_pattern_shield"))
        game["lei15_core_002_applied"] = True
        game["sovereign_core_status"] = config.sovereign_core_status
        game["candidate_origin_label"] = config.candidate_origin_label
    logger.info(
        "[LEI15_CORE_002] sovereign pool=%d cand_d_variant=D epoch=%s",
        len(pool),
        config.evidence_epoch,
    )
    return pool


def _passes_anti_clone(
    candidate: dict,
    selected: list[dict],
    *,
    arch_counts: Counter,
    gp_target: int,
    max_overlap: int | None = None,
    relax_arch: bool = False,
) -> bool:
    nums = list(candidate.get("numbers") or [])
    overlap_limit = int(max_overlap if max_overlap is not None else _GP_MAX_OVERLAP)
    if is_v1_strong_pattern(nums):
        return True
    for other in selected:
        if _pairwise_overlap(nums, list(other.get("numbers") or [])) > overlap_limit:
            return False
    arch = _architecture_key(candidate)
    arch_limit = _arch_share_limit(gp_target=gp_target, relaxed=relax_arch)
    if selected and arch_counts[arch] / max(len(selected), 1) > arch_limit:
        return False
    return True


def _append_anti_clone_candidates(
    selected: list[dict],
    candidates: list[dict],
    *,
    arch_counts: Counter,
    seen_keys: set[tuple[int, ...]],
    gp_target: int,
    max_overlap: int,
    completion: bool,
    relaxed: bool,
) -> None:
    for game in candidates:
        if len(selected) >= gp_target:
            break
        key = tuple(game.get("numbers") or [])
        if not key or key in seen_keys:
            continue
        if not _passes_anti_clone(
            game,
            selected,
            arch_counts=arch_counts,
            gp_target=gp_target,
            max_overlap=max_overlap,
            relax_arch=relaxed,
        ):
            continue
        enriched = dict(game)
        if completion:
            enriched["anti_clone_completion"] = True
        if relaxed:
            enriched["anti_clone_relaxed_overlap"] = max_overlap
        selected.append(enriched)
        seen_keys.add(key)
        arch_counts[_architecture_key(enriched)] += 1


def apply_anti_clone_gp(
    games: list[dict],
    pool: list[dict],
    count: int,
    *,
    game_size: int = 15,
    fallback_pool: list[dict] | None = None,
) -> list[dict]:
    """L4 — limita redundância no GP; exceção para padrões V1-strong."""
    selected: list[dict] = []
    arch_counts: Counter = Counter()
    seen_keys: set[tuple[int, ...]] = set()

    ordered = sorted(
        games,
        key=lambda g: (
            -float(g.get("profile_score", 0) or 0),
            -float(g.get("final_score", {}).get("final_score", 0) or 0),
        ),
    )
    _append_anti_clone_candidates(
        selected,
        ordered,
        arch_counts=arch_counts,
        seen_keys=seen_keys,
        gp_target=count,
        max_overlap=_GP_MAX_OVERLAP,
        completion=False,
        relaxed=False,
    )

    if len(selected) < count:
        pool_sources: list[list[dict]] = []
        for source in (pool, list(fallback_pool or [])):
            if not source:
                continue
            pool_sources.append(
                sorted(source, key=lambda g: -float(g.get("profile_score", 0) or 0))
            )
        for source in pool_sources:
            _append_anti_clone_candidates(
                selected,
                source,
                arch_counts=arch_counts,
                seen_keys=seen_keys,
                gp_target=count,
                max_overlap=_GP_MAX_OVERLAP,
                completion=True,
                relaxed=False,
            )
            if len(selected) >= count:
                break

    if len(selected) < count:
        relaxed_limits = _relaxed_overlap_limits(count)
        completion_sources = [
            ordered,
            *[
                sorted(source, key=lambda g: -float(g.get("profile_score", 0) or 0))
                for source in (pool, list(fallback_pool or []))
                if source
            ],
        ]
        for overlap_limit in relaxed_limits:
            if len(selected) >= count:
                break
            for source in completion_sources:
                _append_anti_clone_candidates(
                    selected,
                    source,
                    arch_counts=arch_counts,
                    seen_keys=seen_keys,
                    gp_target=count,
                    max_overlap=overlap_limit,
                    completion=True,
                    relaxed=True,
                )
                if len(selected) >= count:
                    break

    for game in selected:
        game["anti_clone_gp_applied"] = True
    logger.info(
        "[LEI15_CORE_002] anti_clone_gp selected=%d target=%d game_size=%d",
        len(selected),
        count,
        game_size,
    )
    return selected[:count]


def compose_sovereign_gp(
    pool: list[dict],
    count: int,
    config: Core002SovereignConfig,
    *,
    game_size: int = 15,
    official_history: Sequence[object] | None = None,
) -> list[dict]:
    """L2 compose V1 + M-CORE-003 diversity caps + L4 anti-clone + payload soberano."""
    from lotoia.generation.m_core_003_prefix_suffix_policy import (
        enforce_gp_diversity_cap,
        pre_filter_pool_diversity,
    )
    from lotoia.generation.structural_realignment_v1 import compose_diverse_gp
    from lotoia.governance.law15_structural_realignment_v1 import get_realignment_config

    filtered_pool = pre_filter_pool_diversity(pool, gp_size=count)
    realign_cfg = get_realignment_config()
    composed = compose_diverse_gp(
        filtered_pool, count, realign_cfg, game_size=game_size
    )
    for game in composed:
        game["v1_selection_compose_applied"] = True
        game["m_core_003_pre_filter_applied"] = True

    capped = enforce_gp_diversity_cap(
        composed,
        filtered_pool,
        count,
        fallback_pool=pool,
    )
    gp = apply_anti_clone_gp(
        capped,
        filtered_pool,
        count,
        game_size=game_size,
        fallback_pool=pool,
    )
    gp = enforce_gp_diversity_cap(gp, filtered_pool, count, fallback_pool=pool)
    sanity_bundle: dict[str, object] = {}
    if official_history:
        from lotoia.generation.structural_sovereignty_validator import (
            apply_structural_sovereignty_to_gp,
        )

        gp, sanity_bundle = apply_structural_sovereignty_to_gp(
            gp,
            filtered_pool,
            count,
            official_history,
            fallback_pool=pool,
        )
    tag_sovereign_gp_metadata(gp, config=config)
    if sanity_bundle:
        for game in gp:
            game.setdefault("structural_sovereignty_sanity", dict(sanity_bundle))
    return gp


def tag_sovereign_gp_metadata(
    games: list[dict],
    *,
    config: Core002SovereignConfig,
) -> None:
    """Anexa payload institucional obrigatório a cada cartão do GP."""
    for game in games:
        origin = str(game.get("perfil_origem_real") or game.get("profile_type") or "")
        apply_core_traceability_payload(
            game,
            profile_origin=origin,
            relabeling_applied=bool(game.get("relabeling_applied")),
            relabeling_reason=game.get("relabeling_reason"),
        )
        game["lei15_core_002_applied"] = True
        game["sovereign_core_status"] = config.sovereign_core_status or SOVEREIGN_STATUS
        game["candidate_origin_label"] = (
            config.candidate_origin_label or CANDIDATE_ORIGIN_LABEL
        )
        game.setdefault("generation_cand_d_applied", True)
        game.setdefault("v1_selection_compose_applied", True)
        game.setdefault(
            "v1_strong_shield_applied", bool(game.get("v1_strong_pattern_shield"))
        )
        game.setdefault("anti_clone_gp_applied", True)
        game.setdefault("critical_digit_layer_applied", True)
        meta = dict(game.get("lei15_core_002_metadata") or {})
        meta.update(
            {
                "core_id": "LEI15_CORE_002",
                "adr": config.adr,
                "layers": [
                    "generation_cand_d",
                    "v1_selection_compose",
                    "m_core_003_prefix_suffix_policy",
                    "v1_strong_shield",
                    "anti_clone_gp",
                    "critical_digit_layer",
                ],
            }
        )
        game["lei15_core_002_metadata"] = meta
