"""agent_operador_ml — Executor Autônomo Local Pré-Entrega do GP (M-AGENT-002).

Camada corretiva ativa antes da entrega do GP ao operador. Não é segundo ML nem
observador passivo: detecta falhas estruturais, corrige a seleção interna e
devolve a quantidade solicitada ou declara falha comprovada de pool insuficiente.
"""

from __future__ import annotations

import os
import uuid
from collections import Counter
from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import DIVERSITY_LOW_THRESHOLD, LEVEL_CRITICO, classify_overlap_for_format
from lotoia.ml.supervised_output_calibration import analyze_pool_structural_issues
from lotoia.operations.partial_game_promotion import (
    GAME_QUALITY_ACCEPTABLE,
    GAME_QUALITY_ATTENTION,
    GAME_QUALITY_CRITICAL,
)
from lotoia.statistics.card_structure import (
    compute_gp_redundancy,
    compute_prefix,
    compute_suffix,
    format_dezena_group,
    resolve_cartao_final_from_game,
)
from lotoia.statistics.diverse_top_slice_selection import (
    reorder_pool_with_diverse_top_slice,
    select_diverse_pre_gp_top_slice,
    slice_limit,
)
from lotoia.statistics.similarity_overlap_decomposition import DOMINANT_STRUCTURAL_TRIPLE_LABEL

MISSION_ID = "M-AGENT-002"
AGENT_NAME = "agent_operador_ml"
AGENT_MODE = "EXECUTOR_AUTONOMO_LOCAL_PRE_ENTREGA"
EXECUTOR_VERSION = "M-AGENT-002-FIX-02-v2"

ENV_AGENT_ENABLED = "LOTOIA_AGENT_OPERADOR_ML_ENABLED"
ENV_AGENT_MAX_ATTEMPTS = "LOTOIA_AGENT_OPERADOR_ML_MAX_ATTEMPTS"
DEFAULT_MAX_ATTEMPTS = 8

GP_ENTREGUE_ACEITAVEL = "GP_ENTREGUE_ACEITAVEL"
GP_ENTREGUE_COM_ALERTA = "GP_ENTREGUE_COM_ALERTA"
GP_FALHA_POOL_INSUFICIENTE = "GP_FALHA_POOL_INSUFICIENTE"

DOMINANCE_SHARE_THRESHOLD = 0.35
SIMILARITY_ATTENTION_THRESHOLD = DIVERSITY_LOW_THRESHOLD
STRUCTURAL_DIVERSITY_MIN = DIVERSITY_LOW_THRESHOLD
ACTION_REDUCE_SIMILARITY_OVERLAP = "reduce_similarity_overlap"
ACTION_RECOMPOSE_OVERLAP_DIVERSITY = "recompose_by_overlap_diversity"
SIMILARITY_ISSUE_TYPES = frozenset(
    {"similaridade_media_gp_elevada", "sobreposicao_maxima_elevada"}
)


def is_agent_operador_ml_enabled() -> bool:
    raw = os.getenv(ENV_AGENT_ENABLED, "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_max_agent_attempts() -> int:
    raw = os.getenv(ENV_AGENT_MAX_ATTEMPTS, str(DEFAULT_MAX_ATTEMPTS)).strip()
    try:
        value = int(raw)
    except ValueError:
        value = DEFAULT_MAX_ATTEMPTS
    return max(1, min(value, 12))


def _game_signature(game: Mapping[str, Any]) -> tuple[int, ...]:
    card = resolve_cartao_final_from_game(dict(game))
    return tuple(sorted(int(number) for number in card)) if card else tuple()


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


def _dominant_key(counter: Counter[str], *, threshold: float) -> str:
    if not counter:
        return ""
    total = sum(counter.values())
    if total <= 0:
        return ""
    key, count = counter.most_common(1)[0]
    if not key:
        return ""
    if count / total >= threshold:
        return key
    return ""


def _duplicate_signatures(games: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    signatures = [_game_signature(game) for game in games]
    counter = Counter(
        ",".join(f"{number:02d}" for number in signature)
        for signature in signatures
        if signature
    )
    return dict(counter)


def _cards_from_games(games: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    rows: list[list[int]] = []
    for game in games:
        card = resolve_cartao_final_from_game(dict(game))
        if card:
            rows.append(list(card))
    return rows


def _is_valid_card(game: Mapping[str, Any], *, card_format: int) -> bool:
    card = resolve_cartao_final_from_game(dict(game))
    if len(card) != int(card_format):
        return False
    normalized = {int(number) for number in card}
    return len(normalized) == int(card_format) and all(1 <= number <= 25 for number in normalized)


def _classify_batch(
    games: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    parent_lot_context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    _ = parent_lot_context
    cards = _cards_from_games(games)
    duplicate_map = _duplicate_signatures(games)
    classifications: list[dict[str, Any]] = []
    for index, game in enumerate(games):
        signature = ",".join(f"{n:02d}" for n in _game_signature(game))
        overlap_max = 0
        if int(duplicate_map.get(signature, 0) or 0) > 1:
            status = GAME_QUALITY_CRITICAL
            reason = "exact_duplicate_in_lot"
        else:
            overlap_max = 0
            if len(cards) > 1:
                current = set(cards[index])
                for other_index, other in enumerate(cards):
                    if other_index == index:
                        continue
                    overlap_max = max(overlap_max, len(current & set(other)))
            overlap_class = classify_overlap_for_format(overlap_max, int(card_format))
            if str(overlap_class.get("level") or "") == LEVEL_CRITICO:
                status = GAME_QUALITY_CRITICAL
                reason = f"overlap_critico:{overlap_max}"
            elif overlap_max >= int(card_format) - 1:
                status = GAME_QUALITY_ATTENTION
                reason = f"overlap_atencao:{overlap_max}"
            else:
                status = GAME_QUALITY_ACCEPTABLE
                reason = "structural_ok"
        classifications.append(
            {
                "game_quality_status": status,
                "game_quality_reason": reason,
                "overlap_max_in_lot": overlap_max if len(cards) > 1 else 0,
            }
        )
    return classifications


def _has_critical_games(classifications: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        str(row.get("game_quality_status") or "") == GAME_QUALITY_CRITICAL
        for row in classifications
    )


def _attention_count(classifications: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        1
        for row in classifications
        if str(row.get("game_quality_status") or "") == GAME_QUALITY_ATTENTION
    )


def compute_gp_batch_metrics(
    games: Sequence[Mapping[str, Any]],
    *,
    requested_quantity: int,
    card_format: int,
    batch_label: str | None = None,
    parent_lot_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Métricas estruturais do lote GP para trace antes/depois."""
    game_list = [dict(game) for game in games]
    cards = _cards_from_games(game_list)
    signatures = [_game_signature(game) for game in game_list]
    unique_signatures = {signature for signature in signatures if signature}
    duplicate_count = len(signatures) - len(unique_signatures)
    duplicate_rate = round(duplicate_count / max(len(signatures), 1), 4)

    redundancy = compute_gp_redundancy(cards, game_size=int(card_format)) if len(cards) >= 2 else {}
    diagnostics = analyze_pool_structural_issues(
        game_list,
        game_size=int(card_format),
        batch_label=batch_label,
        requested_count=int(requested_quantity),
    )
    redundancy_diag = dict(diagnostics.get("redundancy") or {})

    prefix_counter = Counter(_prefix_key(game) for game in game_list if _prefix_key(game))
    suffix_counter = Counter(_suffix_key(game) for game in game_list if _suffix_key(game))
    triple_counter = Counter(
        _prefix_key(game)
        for game in game_list
        if _prefix_key(game) == DOMINANT_STRUCTURAL_TRIPLE_LABEL
    )
    family_counter = Counter(_family_key(game) for game in game_list if _family_key(game))

    classifications = _classify_batch(
        game_list,
        card_format=int(card_format),
        parent_lot_context=parent_lot_context,
    )
    critical = _has_critical_games(classifications)

    diversity_score = round(
        1.0 - float(redundancy_diag.get("similaridade_media_entre_jogos", 0.0) or 0.0),
        4,
    )

    return {
        "gp_requested_quantity": int(requested_quantity),
        "gp_delivered_quantity": len(game_list),
        "unique_games": len(unique_signatures),
        "duplicates": int(duplicate_count),
        "duplicate_rate": duplicate_rate,
        "mean_similarity": float(
            redundancy_diag.get("similaridade_media_entre_jogos", 0.0)
            or redundancy.get("similaridade_media_entre_jogos", 0.0)
            or 0.0
        ),
        "max_overlap": int(
            redundancy_diag.get("sobreposicao_maxima", 0)
            or redundancy.get("sobreposicao_maxima", 0)
            or 0
        ),
        "structural_diversity": diversity_score,
        "dominant_prefix": _dominant_key(prefix_counter, threshold=DOMINANCE_SHARE_THRESHOLD),
        "dominant_suffix": _dominant_key(suffix_counter, threshold=DOMINANCE_SHARE_THRESHOLD),
        "dominant_triple": (
            DOMINANT_STRUCTURAL_TRIPLE_LABEL
            if triple_counter
            and triple_counter.get(DOMINANT_STRUCTURAL_TRIPLE_LABEL, 0) / max(len(game_list), 1)
            >= DOMINANCE_SHARE_THRESHOLD
            else ""
        ),
        "dominant_family": _dominant_key(family_counter, threshold=DOMINANCE_SHARE_THRESHOLD),
        "critical_status": critical,
        "attention_games": _attention_count(classifications),
        "acceptable_games": sum(
            1
            for row in classifications
            if str(row.get("game_quality_status") or "") == GAME_QUALITY_ACCEPTABLE
        ),
        "issue_count": int(diagnostics.get("issue_count", 0) or 0),
        "issues": list(diagnostics.get("issues") or [])[:8],
        "operational_status": "critical" if critical else ("attention" if _attention_count(classifications) else "acceptable"),
    }


def _max_overlap_attention_threshold(card_format: int) -> int:
    return max(int(card_format) - 2, 12)


def _has_similarity_overlap_issues(metrics: Mapping[str, Any], *, card_format: int) -> bool:
    mean_similarity = float(metrics.get("mean_similarity", 0.0) or 0.0)
    max_overlap = int(metrics.get("max_overlap", 0) or 0)
    structural_diversity = float(metrics.get("structural_diversity", 0.0) or 0.0)
    issue_count = int(metrics.get("issue_count", 0) or 0)
    if mean_similarity >= SIMILARITY_ATTENTION_THRESHOLD:
        return True
    if structural_diversity < STRUCTURAL_DIVERSITY_MIN:
        return True
    if max_overlap >= _max_overlap_attention_threshold(card_format):
        return True
    for issue in list(metrics.get("issues") or []):
        if str(issue.get("tipo") or "") in SIMILARITY_ISSUE_TYPES:
            return True
    return issue_count > 0 and (
        mean_similarity >= SIMILARITY_ATTENTION_THRESHOLD * 0.9
        or max_overlap >= _max_overlap_attention_threshold(card_format) - 1
    )


def _metrics_similarity_improved(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> bool:
    mean_before = float(before.get("mean_similarity", 0.0) or 0.0)
    mean_after = float(after.get("mean_similarity", 0.0) or 0.0)
    overlap_before = int(before.get("max_overlap", 0) or 0)
    overlap_after = int(after.get("max_overlap", 0) or 0)
    diversity_before = float(before.get("structural_diversity", 0.0) or 0.0)
    diversity_after = float(after.get("structural_diversity", 0.0) or 0.0)
    issues_before = int(before.get("issue_count", 0) or 0)
    issues_after = int(after.get("issue_count", 0) or 0)
    return (
        mean_after < mean_before
        or overlap_after < overlap_before
        or diversity_after > diversity_before
        or issues_after < issues_before
    )


def _overlap_contribution_ranking(
    games: Sequence[Mapping[str, Any]],
) -> list[tuple[int, int]]:
    cards = _cards_from_games(games)
    ranking: list[tuple[int, int]] = []
    for index, card in enumerate(cards):
        current = set(card)
        contribution = 0
        for other_index, other in enumerate(cards):
            if other_index == index:
                continue
            contribution += len(current & set(other))
        ranking.append((index, contribution))
    ranking.sort(key=lambda row: row[1], reverse=True)
    return ranking


def _score_attempt(
    metrics: Mapping[str, Any],
    *,
    requested_quantity: int,
) -> float:
    delivered = int(metrics.get("gp_delivered_quantity", 0) or 0)
    if delivered < requested_quantity:
        return -10_000.0 + delivered
    score = float(metrics.get("structural_diversity", 0.0) or 0.0) * 200.0
    score -= float(metrics.get("mean_similarity", 0.0) or 0.0) * 180.0
    score -= int(metrics.get("duplicates", 0) or 0) * 500.0
    score -= int(metrics.get("max_overlap", 0) or 0) * 12.0
    score -= int(metrics.get("attention_games", 0) or 0) * 25.0
    if bool(metrics.get("critical_status")):
        score -= 5_000.0
    if metrics.get("dominant_prefix"):
        score -= 80.0
    if metrics.get("dominant_suffix"):
        score -= 80.0
    if metrics.get("dominant_triple"):
        score -= 100.0
    if metrics.get("dominant_family"):
        score -= 60.0
    score -= int(metrics.get("issue_count", 0) or 0) * 12.0
    return round(score, 4)


def _pool_unique_conformant_candidates(
    pool: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    exclude_signatures: set[tuple[int, ...]] | None = None,
) -> list[dict[str, Any]]:
    excluded = set(exclude_signatures or set())
    seen: set[tuple[int, ...]] = set()
    conformant: list[dict[str, Any]] = []
    for game in pool:
        if not _is_valid_card(game, card_format=card_format):
            continue
        signature = _game_signature(game)
        if not signature or signature in excluded or signature in seen:
            continue
        seen.add(signature)
        conformant.append(dict(game))
    return conformant


def _deduplicate_selection(
    selected: list[dict[str, Any]],
    pool: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
) -> tuple[list[dict[str, Any]], int, str]:
    signatures_seen: set[tuple[int, ...]] = set()
    output: list[dict[str, Any]] = []
    replacements = 0
    pool_rows = _pool_unique_conformant_candidates(pool, card_format=card_format)

    for game in selected:
        signature = _game_signature(game)
        if signature and signature not in signatures_seen:
            signatures_seen.add(signature)
            output.append(dict(game))
            continue
        replacement = None
        for candidate in pool_rows:
            candidate_sig = _game_signature(candidate)
            if candidate_sig and candidate_sig not in signatures_seen:
                replacement = dict(candidate)
                signatures_seen.add(candidate_sig)
                replacement["agent_operador_ml_substituted"] = True
                replacement["agent_operador_ml_replaced_signature"] = (
                    ",".join(f"{n:02d}" for n in signature) if signature else ""
                )
                replacements += 1
                break
        if replacement is not None:
            output.append(replacement)
    if replacements == 0 and len(output) < len(selected):
        return output, 0, "deduplicate_no_material"
    return output, replacements, "deduplicate_redundant_games"


def _swap_dominant_games(
    selected: list[dict[str, Any]],
    pool: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    batch_label: str | None,
    requested_quantity: int,
    dominance_kind: str,
) -> tuple[list[dict[str, Any]], int, str]:
    if not selected:
        return selected, 0, f"swap_{dominance_kind}_skipped"

    metrics = compute_gp_batch_metrics(
        selected,
        requested_quantity=requested_quantity,
        card_format=card_format,
        batch_label=batch_label,
    )
    dominant = str(metrics.get(f"dominant_{dominance_kind}") or "")
    if not dominant:
        return selected, 0, f"swap_{dominance_kind}_not_needed"

    selected_signatures = {_game_signature(game) for game in selected}
    replacements = 0
    output = [dict(game) for game in selected]
    pool_candidates = _pool_unique_conformant_candidates(
        pool,
        card_format=card_format,
        exclude_signatures=selected_signatures,
    )

    for index, game in enumerate(output):
        key_fn = {
            "prefix": _prefix_key,
            "suffix": _suffix_key,
            "family": _family_key,
            "triple": lambda row: _prefix_key(row) if _prefix_key(row) == DOMINANT_STRUCTURAL_TRIPLE_LABEL else "",
        }.get(dominance_kind, _prefix_key)
        if key_fn(game) != dominant:
            continue
        for candidate in pool_candidates:
            candidate_sig = _game_signature(candidate)
            if not candidate_sig or candidate_sig in selected_signatures:
                continue
            if key_fn(candidate) == dominant:
                continue
            replacement = dict(candidate)
            replacement["agent_operador_ml_dominance_swap"] = dominance_kind
            output[index] = replacement
            selected_signatures.add(candidate_sig)
            replacements += 1
            break

    action = f"swap_dominant_{dominance_kind}"
    return output, replacements, action


def _recompose_gp(
    pool: Sequence[Mapping[str, Any]],
    *,
    requested_quantity: int,
    card_format: int,
    batch_label: str | None,
    attempt_index: int,
) -> tuple[list[dict[str, Any]], str]:
    pool_rows = [dict(game) for game in pool]
    if len(pool_rows) < requested_quantity:
        return [], "recompose_insufficient_pool"

    limit = slice_limit(requested_count=requested_quantity)
    diverse_slice = select_diverse_pre_gp_top_slice(
        pool_rows,
        limit=limit,
        game_size=int(card_format),
        batch_label=batch_label,
        requested_count=int(requested_quantity),
        relax_level=int(attempt_index),
    )
    reordered = reorder_pool_with_diverse_top_slice(pool_rows, diverse_slice)

    try:
        from lotoia.generation.lei15_core_002 import compose_sovereign_gp
        from lotoia.governance.lei15_core_002_sovereign import get_core_002_config

        config = get_core_002_config(batch_label)
        recomposed = compose_sovereign_gp(
            reordered,
            int(requested_quantity),
            config,
            game_size=int(card_format),
        )
    except Exception:
        return [], "recompose_compose_failed"

    if len(recomposed) < requested_quantity:
        return recomposed, "recompose_partial"
    for game in recomposed:
        game["agent_operador_ml_recomposed"] = True
    return recomposed[:requested_quantity], "recompose_diverse_gp"


def _reduce_similarity_overlap(
    selected: list[dict[str, Any]],
    pool: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    batch_label: str | None,
    requested_quantity: int,
    attempt_index: int,
) -> tuple[list[dict[str, Any]], int, str, dict[str, Any]]:
    """Substitui jogos de maior contribuição a overlap por candidatos mais diversos."""
    diagnostics: dict[str, Any] = {
        "overlap_reduction_candidates_evaluated": 0,
        "pool_alternatives_available": 0,
        "substitutions_applied": 0,
    }
    metrics_before = compute_gp_batch_metrics(
        selected,
        requested_quantity=requested_quantity,
        card_format=card_format,
        batch_label=batch_label,
    )
    if not _has_similarity_overlap_issues(metrics_before, card_format=card_format):
        return selected, 0, "reduce_similarity_overlap_not_needed", diagnostics

    output = [dict(game) for game in selected]
    selected_signatures = {_game_signature(game) for game in output if _game_signature(game)}
    pool_candidates = _pool_unique_conformant_candidates(
        pool,
        card_format=card_format,
        exclude_signatures=selected_signatures,
    )
    diagnostics["pool_alternatives_available"] = len(pool_candidates)
    if not pool_candidates:
        return selected, 0, "reduce_similarity_overlap_no_pool_alternatives", diagnostics

    cards = _cards_from_games(output)
    replace_count = max(3, min(len(output) // 4, 8 + attempt_index))
    ranking = _overlap_contribution_ranking(output)

    for game_index, _contribution in ranking[:replace_count]:
        if game_index >= len(output):
            continue
        best_candidate: dict[str, Any] | None = None
        best_score = -1.0
        for candidate in pool_candidates:
            diagnostics["overlap_reduction_candidates_evaluated"] += 1
            candidate_signature = _game_signature(candidate)
            if not candidate_signature or candidate_signature in selected_signatures:
                continue
            candidate_card = resolve_cartao_final_from_game(dict(candidate))
            if not candidate_card:
                continue
            overlaps = [
                len(set(candidate_card) & set(cards[other_index]))
                for other_index in range(len(cards))
                if other_index != game_index
            ]
            max_overlap = max(overlaps, default=0)
            candidate_score = (int(card_format) - max_overlap) / max(int(card_format), 1)
            candidate_score += float(candidate.get("profile_score", 0.0) or 0.0) * 0.01
            if candidate_score > best_score:
                best_score = candidate_score
                best_candidate = dict(candidate)
        if best_candidate is None:
            continue
        old_signature = _game_signature(output[game_index])
        replacement = dict(best_candidate)
        replacement["agent_operador_ml_overlap_swap"] = True
        output[game_index] = replacement
        new_signature = _game_signature(replacement)
        if old_signature:
            selected_signatures.discard(old_signature)
        if new_signature:
            selected_signatures.add(new_signature)
            cards[game_index] = list(resolve_cartao_final_from_game(replacement) or [])
        diagnostics["substitutions_applied"] += 1

    metrics_after = compute_gp_batch_metrics(
        output,
        requested_quantity=requested_quantity,
        card_format=card_format,
        batch_label=batch_label,
    )
    if _metrics_similarity_improved(metrics_before, metrics_after):
        return output, int(diagnostics["substitutions_applied"]), ACTION_REDUCE_SIMILARITY_OVERLAP, diagnostics
    if diagnostics["substitutions_applied"] > 0:
        return output, int(diagnostics["substitutions_applied"]), "reduce_similarity_overlap_partial", diagnostics
    return selected, 0, "reduce_similarity_overlap_no_gain", diagnostics


def _recompose_by_overlap_diversity(
    pool: Sequence[Mapping[str, Any]],
    *,
    requested_quantity: int,
    card_format: int,
    batch_label: str | None,
    attempt_index: int,
) -> tuple[list[dict[str, Any]], int, str, dict[str, Any]]:
    diagnostics = {
        "overlap_reduction_candidates_evaluated": 0,
        "pool_alternatives_available": len(
            _pool_unique_conformant_candidates(pool, card_format=card_format)
        ),
        "substitutions_applied": 0,
    }
    recomposed, action = _recompose_gp(
        pool,
        requested_quantity=requested_quantity,
        card_format=card_format,
        batch_label=batch_label,
        attempt_index=attempt_index,
    )
    if recomposed and len(recomposed) >= requested_quantity:
        for game in recomposed:
            game["agent_operador_ml_recomposed_overlap"] = True
        return (
            recomposed[:requested_quantity],
            len(recomposed),
            ACTION_RECOMPOSE_OVERLAP_DIVERSITY,
            diagnostics,
        )
    return recomposed, len(recomposed), action or "recompose_by_overlap_diversity_failed", diagnostics


def _resolve_delivery_status(
    games: Sequence[Mapping[str, Any]],
    *,
    requested_quantity: int,
    card_format: int,
    batch_label: str | None,
) -> str:
    metrics = compute_gp_batch_metrics(
        games,
        requested_quantity=requested_quantity,
        card_format=card_format,
        batch_label=batch_label,
    )
    if int(metrics.get("gp_delivered_quantity", 0) or 0) < requested_quantity:
        return GP_FALHA_POOL_INSUFICIENTE
    if bool(metrics.get("critical_status")):
        return GP_FALHA_POOL_INSUFICIENTE
    if int(metrics.get("duplicates", 0) or 0) > 0:
        return GP_FALHA_POOL_INSUFICIENTE
    if int(metrics.get("attention_games", 0) or 0) > 0 or int(metrics.get("issue_count", 0) or 0) > 0:
        return GP_ENTREGUE_COM_ALERTA
    if metrics.get("dominant_prefix") or metrics.get("dominant_suffix") or metrics.get("dominant_triple"):
        return GP_ENTREGUE_COM_ALERTA
    return GP_ENTREGUE_ACEITAVEL


def _build_failure_evidence(
    *,
    requested_quantity: int,
    delivered_quantity: int,
    pool_size: int,
    unique_pool: int,
    conformant_pool: int,
    cause: str,
) -> dict[str, Any]:
    possible = min(int(unique_pool), int(conformant_pool), int(pool_size))
    return {
        "primary_cause": cause,
        "requested_quantity": int(requested_quantity),
        "delivered_quantity": int(delivered_quantity),
        "possible_quantity": int(possible),
        "pool_size": int(pool_size),
        "unique_pool_candidates": int(unique_pool),
        "conformant_pool_candidates": int(conformant_pool),
        "numeric_evidence": {
            "gap": max(int(requested_quantity) - int(delivered_quantity), 0),
            "conformant_shortfall": max(int(requested_quantity) - int(conformant_pool), 0),
        },
        "technical_recommendation": (
            "Aumentar pool_size na geração soberana ou reduzir quantidade solicitada; "
            "verificar conformidade Lei 15 / política 15D e colisões estruturais no pool."
        ),
    }


def execute_agent_operador_ml_pre_delivery(
    *,
    requested_quantity: int,
    card_format: int,
    selected_games: Sequence[Mapping[str, Any]],
    candidate_pool: Sequence[Mapping[str, Any]],
    batch_label: str | None = None,
    ml_metrics: Mapping[str, Any] | None = None,
    structural_policy_bundle: Mapping[str, Any] | None = None,
    core_002_status: str = "sovereign",
    law_15_status: str = "active",
    lot_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Executor autônomo local pré-entrega do GP."""
    trace_id = f"agent-operador-ml-{uuid.uuid4().hex[:16]}"
    requested = max(int(requested_quantity), 1)
    card_size = int(card_format or 15)
    pool = [dict(game) for game in candidate_pool] if candidate_pool else []
    if not pool:
        pool = [dict(game) for game in selected_games]

    before_metrics = compute_gp_batch_metrics(
        selected_games,
        requested_quantity=requested,
        card_format=card_size,
        batch_label=batch_label,
        parent_lot_context=lot_context,
    )

    unique_pool = len({_game_signature(game) for game in pool if _game_signature(game)})
    conformant_pool = len(
        _pool_unique_conformant_candidates(pool, card_format=card_size)
    )

    attempts: list[dict[str, Any]] = []
    actions_applied: list[str] = []
    best_games = [dict(game) for game in selected_games]
    best_metrics = dict(before_metrics)
    best_score = _score_attempt(best_metrics, requested_quantity=requested)
    best_index = 0

    if conformant_pool < requested:
        failure = _build_failure_evidence(
            requested_quantity=requested,
            delivered_quantity=len(best_games),
            pool_size=len(pool),
            unique_pool=unique_pool,
            conformant_pool=conformant_pool,
            cause="conformant_candidates_insufficient",
        )
        trace = _build_trace(
            trace_id=trace_id,
            requested_quantity=requested,
            delivered_quantity=len(best_games),
            delivery_status=GP_FALHA_POOL_INSUFICIENTE,
            failure_reason=str(failure.get("primary_cause") or ""),
            failure_evidence=failure,
            attempts_count=0,
            actions_applied=[],
            before_metrics=before_metrics,
            after_metrics=before_metrics,
            best_attempt_index=0,
            improvement_summary="Sem material conforme suficiente no pool — correção não iniciada.",
            reasoning_summary=(
                f"Pool com {conformant_pool} candidatos conformes únicos para {requested} solicitados."
            ),
            expected_effect="Declarar falha comprovada sem mascarar métricas.",
            observed_effect="Entrega impossível antes da primeira tentativa corretiva.",
            ml_metrics=ml_metrics,
            structural_policy_bundle=structural_policy_bundle,
            core_002_status=core_002_status,
            law_15_status=law_15_status,
            attempt_results=[],
        )
        return {
            "games": best_games,
            "trace": trace,
            "delivery_status": GP_FALHA_POOL_INSUFICIENTE,
            "agent_applied": True,
        }

    working = [dict(game) for game in selected_games]
    max_attempts = get_max_agent_attempts()
    similarity_overlap_trace: dict[str, Any] = {
        "agent_similarity_overlap_correction_attempted": False,
        "agent_similarity_overlap_correction_action": "",
        "agent_similarity_overlap_correction_applied": False,
        "agent_noop_prevented": False,
        "similarity_before": float(before_metrics.get("mean_similarity", 0.0) or 0.0),
        "similarity_after": float(before_metrics.get("mean_similarity", 0.0) or 0.0),
        "max_overlap_before": int(before_metrics.get("max_overlap", 0) or 0),
        "max_overlap_after": int(before_metrics.get("max_overlap", 0) or 0),
        "structural_diversity_before": float(before_metrics.get("structural_diversity", 0.0) or 0.0),
        "structural_diversity_after": float(before_metrics.get("structural_diversity", 0.0) or 0.0),
        "issue_count_before": int(before_metrics.get("issue_count", 0) or 0),
        "issue_count_after": int(before_metrics.get("issue_count", 0) or 0),
        "overlap_reduction_candidates_evaluated": 0,
        "pool_alternatives_available": 0,
        "similarity_overlap_best_attempt_metrics": dict(before_metrics),
        "agent_similarity_overlap_correction_failed": False,
        "similarity_overlap_failure_reason": "",
        "similarity_overlap_failure_evidence": {},
    }
    similarity_needed_initial = _has_similarity_overlap_issues(before_metrics, card_format=card_size)

    def _run_similarity_overlap_correction(
        games: list[dict[str, Any]],
        attempt: int,
    ) -> tuple[list[dict[str, Any]], int, str, dict[str, Any]]:
        reduced, changed, action, diagnostics = _reduce_similarity_overlap(
            games,
            pool,
            card_format=card_size,
            batch_label=batch_label,
            requested_quantity=requested,
            attempt_index=attempt,
        )
        if action == ACTION_REDUCE_SIMILARITY_OVERLAP:
            return reduced, changed, action, diagnostics
        recomposed, recompose_changed, recompose_action, recompose_diag = _recompose_by_overlap_diversity(
            pool,
            requested_quantity=requested,
            card_format=card_size,
            batch_label=batch_label,
            attempt_index=attempt,
        )
        merged_diag = {
            **diagnostics,
            **recompose_diag,
            "reduce_action": action,
            "recompose_action": recompose_action,
        }
        if recomposed and len(recomposed) >= requested:
            return recomposed[:requested], recompose_changed, ACTION_RECOMPOSE_OVERLAP_DIVERSITY, merged_diag
        if changed > 0:
            return reduced, changed, action, merged_diag
        return games, 0, recompose_action or action, merged_diag

    def _record_overlap_diag(overlap_diag: Mapping[str, Any], action: str) -> None:
        if not overlap_diag:
            return
        similarity_overlap_trace["overlap_reduction_candidates_evaluated"] = max(
            int(similarity_overlap_trace.get("overlap_reduction_candidates_evaluated", 0) or 0),
            int(overlap_diag.get("overlap_reduction_candidates_evaluated", 0) or 0),
        )
        similarity_overlap_trace["pool_alternatives_available"] = max(
            int(similarity_overlap_trace.get("pool_alternatives_available", 0) or 0),
            int(overlap_diag.get("pool_alternatives_available", 0) or 0),
        )
        if action in {ACTION_REDUCE_SIMILARITY_OVERLAP, ACTION_RECOMPOSE_OVERLAP_DIVERSITY}:
            similarity_overlap_trace["agent_similarity_overlap_correction_action"] = action

    for attempt_index in range(max_attempts):
        overlap_diag: dict[str, Any] = {}
        if attempt_index == 0:
            working, changed, action = _deduplicate_selection(working, pool, card_format=card_size)
        elif attempt_index == 1:
            working, changed, action = _swap_dominant_games(
                working, pool, card_format=card_size, batch_label=batch_label,
                requested_quantity=requested, dominance_kind="prefix",
            )
        elif attempt_index == 2:
            working, changed, action = _swap_dominant_games(
                working, pool, card_format=card_size, batch_label=batch_label,
                requested_quantity=requested, dominance_kind="suffix",
            )
        elif attempt_index == 3:
            working, changed, action = _swap_dominant_games(
                working, pool, card_format=card_size, batch_label=batch_label,
                requested_quantity=requested, dominance_kind="triple",
            )
        elif attempt_index == 4:
            working, changed, action = _swap_dominant_games(
                working, pool, card_format=card_size, batch_label=batch_label,
                requested_quantity=requested, dominance_kind="family",
            )
        elif attempt_index == 5:
            working, changed, action, overlap_diag = _run_similarity_overlap_correction(
                working,
                attempt_index,
            )
            similarity_overlap_trace["agent_similarity_overlap_correction_attempted"] = True
            similarity_overlap_trace["agent_noop_prevented"] = similarity_needed_initial
        else:
            working, changed, action, overlap_diag = _recompose_by_overlap_diversity(
                pool,
                requested_quantity=requested,
                card_format=card_size,
                batch_label=batch_label,
                attempt_index=attempt_index,
            )
            similarity_overlap_trace["agent_similarity_overlap_correction_attempted"] = True

        _record_overlap_diag(overlap_diag, action)

        if action and action not in actions_applied and not action.endswith("_not_needed"):
            actions_applied.append(action)

        attempt_metrics = compute_gp_batch_metrics(
            working,
            requested_quantity=requested,
            card_format=card_size,
            batch_label=batch_label,
            parent_lot_context=lot_context,
        )
        attempt_score = _score_attempt(attempt_metrics, requested_quantity=requested)
        attempts.append(
            {
                "attempt_index": attempt_index,
                "action": action,
                "changes": int(changed) if isinstance(changed, int) else 0,
                "score": attempt_score,
                "metrics": attempt_metrics,
                "delivered_quantity": len(working),
                "overlap_diagnostics": dict(overlap_diag),
            }
        )
        if attempt_score > best_score:
            best_score = attempt_score
            best_games = [dict(game) for game in working]
            best_metrics = dict(attempt_metrics)
            best_index = attempt_index
            similarity_overlap_trace["similarity_overlap_best_attempt_metrics"] = dict(attempt_metrics)

        if (
            int(attempt_metrics.get("gp_delivered_quantity", 0) or 0) >= requested
            and not bool(attempt_metrics.get("critical_status"))
            and int(attempt_metrics.get("duplicates", 0) or 0) == 0
            and int(attempt_metrics.get("issue_count", 0) or 0) == 0
            and not attempt_metrics.get("dominant_prefix")
            and not attempt_metrics.get("dominant_suffix")
            and not attempt_metrics.get("dominant_triple")
            and int(attempt_metrics.get("attention_games", 0) or 0) == 0
            and not _has_similarity_overlap_issues(attempt_metrics, card_format=card_size)
        ):
            break

    if similarity_needed_initial and not similarity_overlap_trace.get(
        "agent_similarity_overlap_correction_attempted"
    ):
        working, changed, action, overlap_diag = _run_similarity_overlap_correction(working, max_attempts)
        similarity_overlap_trace["agent_similarity_overlap_correction_attempted"] = True
        similarity_overlap_trace["agent_noop_prevented"] = True
        _record_overlap_diag(overlap_diag, action)
        if action and action not in actions_applied and not action.endswith("_not_needed"):
            actions_applied.append(action)
        attempt_metrics = compute_gp_batch_metrics(
            working,
            requested_quantity=requested,
            card_format=card_size,
            batch_label=batch_label,
            parent_lot_context=lot_context,
        )
        attempt_score = _score_attempt(attempt_metrics, requested_quantity=requested)
        attempts.append(
            {
                "attempt_index": len(attempts),
                "action": action,
                "changes": int(changed),
                "score": attempt_score,
                "metrics": attempt_metrics,
                "delivered_quantity": len(working),
                "overlap_diagnostics": dict(overlap_diag),
                "forced_similarity_pass": True,
            }
        )
        if attempt_score > best_score:
            best_score = attempt_score
            best_games = [dict(game) for game in working]
            best_metrics = dict(attempt_metrics)
            best_index = len(attempts) - 1
            similarity_overlap_trace["similarity_overlap_best_attempt_metrics"] = dict(attempt_metrics)

    similarity_overlap_trace["similarity_after"] = float(best_metrics.get("mean_similarity", 0.0) or 0.0)
    similarity_overlap_trace["max_overlap_after"] = int(best_metrics.get("max_overlap", 0) or 0)
    similarity_overlap_trace["structural_diversity_after"] = float(
        best_metrics.get("structural_diversity", 0.0) or 0.0
    )
    similarity_overlap_trace["issue_count_after"] = int(best_metrics.get("issue_count", 0) or 0)
    similarity_overlap_trace["agent_similarity_overlap_correction_applied"] = _metrics_similarity_improved(
        before_metrics,
        best_metrics,
    )
    if similarity_needed_initial and not similarity_overlap_trace["agent_similarity_overlap_correction_applied"]:
        similarity_overlap_trace["agent_similarity_overlap_correction_failed"] = True
        similarity_overlap_trace["similarity_overlap_failure_reason"] = (
            "pool_without_diverse_alternatives_sufficient"
            if int(similarity_overlap_trace.get("pool_alternatives_available", 0) or 0) <= 0
            else "no_measurable_similarity_overlap_gain_after_correction"
        )
        similarity_overlap_trace["similarity_overlap_failure_evidence"] = {
            "requested_quantity": requested,
            "pool_alternatives_available": int(
                similarity_overlap_trace.get("pool_alternatives_available", 0) or 0
            ),
            "overlap_reduction_candidates_evaluated": int(
                similarity_overlap_trace.get("overlap_reduction_candidates_evaluated", 0) or 0
            ),
            "similarity_before": float(before_metrics.get("mean_similarity", 0.0) or 0.0),
            "similarity_after": float(best_metrics.get("mean_similarity", 0.0) or 0.0),
            "max_overlap_before": int(before_metrics.get("max_overlap", 0) or 0),
            "max_overlap_after": int(best_metrics.get("max_overlap", 0) or 0),
            "issue_count_before": int(before_metrics.get("issue_count", 0) or 0),
            "issue_count_after": int(best_metrics.get("issue_count", 0) or 0),
        }

    delivery_status = _resolve_delivery_status(
        best_games,
        requested_quantity=requested,
        card_format=card_size,
        batch_label=batch_label,
    )

    failure_reason = ""
    failure_evidence: dict[str, Any] = {}
    if delivery_status == GP_FALHA_POOL_INSUFICIENTE:
        cause = "pool_insufficient"
        if conformant_pool < requested:
            cause = "conformant_candidates_insufficient"
        elif unique_pool < requested:
            cause = "unique_candidates_insufficient"
        elif int(best_metrics.get("duplicates", 0) or 0) > 0:
            cause = "duplicate_collisions_unresolved"
        elif bool(best_metrics.get("critical_status")):
            cause = "critical_games_remain_after_correction"
        failure_reason = cause
        failure_evidence = _build_failure_evidence(
            requested_quantity=requested,
            delivered_quantity=len(best_games),
            pool_size=len(pool),
            unique_pool=unique_pool,
            conformant_pool=conformant_pool,
            cause=cause,
        )

    diversity_gain = round(
        float(best_metrics.get("structural_diversity", 0.0) or 0.0)
        - float(before_metrics.get("structural_diversity", 0.0) or 0.0),
        4,
    )
    overlap_delta = int(before_metrics.get("max_overlap", 0) or 0) - int(
        best_metrics.get("max_overlap", 0) or 0
    )
    improvement_summary = (
        f"diversidade {before_metrics.get('structural_diversity')}→{best_metrics.get('structural_diversity')} "
        f"(Δ{diversity_gain}); overlap_max {before_metrics.get('max_overlap')}→{best_metrics.get('max_overlap')} "
        f"(Δ{overlap_delta}); duplicados {before_metrics.get('duplicates')}→{best_metrics.get('duplicates')}."
    )

    primary_action = actions_applied[0] if actions_applied else "no_correction_needed"

    trace = _build_trace(
        trace_id=trace_id,
        requested_quantity=requested,
        delivered_quantity=len(best_games),
        delivery_status=delivery_status,
        failure_reason=failure_reason,
        failure_evidence=failure_evidence,
        attempts_count=len(attempts),
        actions_applied=actions_applied,
        before_metrics=before_metrics,
        after_metrics=best_metrics,
        best_attempt_index=best_index,
        improvement_summary=improvement_summary,
        reasoning_summary=(
            f"Melhor tentativa #{best_index} com ação principal '{primary_action}' "
            f"— status {delivery_status}."
        ),
        expected_effect="Reduzir redundância estrutural e garantir unicidade pré-entrega.",
        observed_effect=improvement_summary,
        ml_metrics=ml_metrics,
        structural_policy_bundle=structural_policy_bundle,
        core_002_status=core_002_status,
        law_15_status=law_15_status,
        attempt_results=attempts,
        primary_corrective_action=primary_action,
        similarity_overlap_trace=similarity_overlap_trace,
    )

    return {
        "games": best_games,
        "trace": trace,
        "delivery_status": delivery_status,
        "agent_applied": True,
    }


def _build_trace(
    *,
    trace_id: str,
    requested_quantity: int,
    delivered_quantity: int,
    delivery_status: str,
    failure_reason: str,
    failure_evidence: Mapping[str, Any],
    attempts_count: int,
    actions_applied: Sequence[str],
    before_metrics: Mapping[str, Any],
    after_metrics: Mapping[str, Any],
    best_attempt_index: int,
    improvement_summary: str,
    reasoning_summary: str,
    expected_effect: str,
    observed_effect: str,
    ml_metrics: Mapping[str, Any] | None,
    structural_policy_bundle: Mapping[str, Any] | None,
    core_002_status: str,
    law_15_status: str,
    attempt_results: Sequence[Mapping[str, Any]],
    primary_corrective_action: str = "",
    similarity_overlap_trace: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "agent_operador_ml_applied": True,
        "agent_name": AGENT_NAME,
        "agent_mode": AGENT_MODE,
        "agent_mission_id": MISSION_ID,
        "agent_executor_version": EXECUTOR_VERSION,
        "agent_trace_id": trace_id,
        "gp_requested_quantity": int(requested_quantity),
        "gp_delivered_quantity": int(delivered_quantity),
        "gp_delivery_status": delivery_status,
        "gp_failure_reason": failure_reason,
        "gp_failure_evidence": dict(failure_evidence),
        "agent_attempts_count": int(attempts_count),
        "agent_actions_applied": list(actions_applied),
        "agent_before_metrics": dict(before_metrics),
        "agent_after_metrics": dict(after_metrics),
        "agent_best_attempt_index": int(best_attempt_index),
        "agent_improvement_summary": improvement_summary,
        "agent_reasoning_summary": reasoning_summary,
        "agent_expected_effect": expected_effect,
        "agent_observed_effect": observed_effect,
        "agent_action_executed": bool(actions_applied) or bool(attempt_results),
        "agent_respected_core_002": True,
        "agent_respected_law_15": True,
        "agent_primary_corrective_action": primary_corrective_action or (
            actions_applied[0] if actions_applied else "none"
        ),
        "agent_attempt_results": list(attempt_results),
        "ml_metrics_snapshot": dict(ml_metrics or {}),
        "structural_policy_bundle_snapshot": dict(structural_policy_bundle or {}),
        "core_002_status": str(core_002_status),
        "law_15_status": str(law_15_status),
    }
    payload.update(dict(similarity_overlap_trace or {}))
    return payload


def build_agent_operador_ml_ui_summary(trace: Mapping[str, Any] | None) -> dict[str, Any]:
    """Resumo discreto para painel institucional."""
    payload = dict(trace or {})
    if not payload.get("agent_operador_ml_applied"):
        return {"visible": False}
    return {
        "visible": True,
        "status": str(payload.get("gp_delivery_status") or "-"),
        "requested": int(payload.get("gp_requested_quantity", 0) or 0),
        "delivered": int(payload.get("gp_delivered_quantity", 0) or 0),
        "primary_action": str(payload.get("agent_primary_corrective_action") or "-"),
        "improvement": str(payload.get("agent_improvement_summary") or ""),
        "trace_id": str(payload.get("agent_trace_id") or ""),
        "trace": payload,
    }
