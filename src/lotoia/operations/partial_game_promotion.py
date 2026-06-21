"""Promoção parcial por jogo em lotes GP — M-OPS-078."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from lotoia.ml.overlap_format_thresholds import (
    LEVEL_ATENCAO,
    LEVEL_BOM,
    LEVEL_CRITICO,
    LEVEL_RUIM,
    classify_overlap_for_format,
)
from lotoia.ml.structural_policy_15d import (
    analyze_batch_structural_policy_15d,
    build_structural_policy_15d_memory,
    validate_game_structural_policy_15d,
)
from lotoia.operations.lot_operational_status import (
    STATUS_APPROVED_WITH_WARNING,
    is_analytical_history_eligible,
    is_official_conference_eligible,
)
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-OPS-078"

GAME_QUALITY_ACCEPTABLE = "acceptable"
GAME_QUALITY_ATTENTION = "attention"
GAME_QUALITY_CRITICAL = "critical"

OVERLAP_ACCEPTABLE = frozenset({LEVEL_BOM})
OVERLAP_ATTENTION = frozenset({LEVEL_ATENCAO, LEVEL_RUIM})
OVERLAP_CRITICAL = frozenset({LEVEL_CRITICO})


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _card_tuple(game: Mapping[str, Any]) -> tuple[int, ...]:
    card = resolve_cartao_final_from_game(dict(game))
    return tuple(sorted(int(number) for number in card))


def _card_signature(card: Sequence[int]) -> str:
    return ",".join(f"{int(number):02d}" for number in sorted(card))


def _max_pairwise_overlap(cards: Sequence[Sequence[int]], index: int) -> int:
    current = set(int(number) for number in cards[index])
    best = 0
    for other_index, other in enumerate(cards):
        if other_index == index:
            continue
        best = max(best, len(current & set(int(number) for number in other)))
    return best


def _attention_conference_allowed(parent_lot_context: Mapping[str, Any]) -> bool:
    lot_status = str(parent_lot_context.get("lot_operational_status") or "").strip().lower()
    if lot_status == STATUS_APPROVED_WITH_WARNING:
        return True
    if bool(parent_lot_context.get("partial_promotion_enabled")):
        return True
    if bool(parent_lot_context.get("promoted_to_official_conference")):
        return True
    if bool(parent_lot_context.get("official_release_allowed")):
        return True
    return False


def classify_individual_game_quality(
    game: Mapping[str, Any],
    *,
    card_format: int,
    cards: Sequence[Sequence[int]],
    card_index: int,
    duplicate_signatures: Mapping[str, int],
    policy_validation: Mapping[str, Any] | None = None,
    parent_lot_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classifica um jogo — estrutura apenas, sem hits 13/14/15."""
    parent = dict(parent_lot_context or {})
    game_index = _safe_int(game.get("game_index"), default=card_index + 1)
    card = list(cards[card_index]) if card_index < len(cards) else resolve_cartao_final_from_game(dict(game))
    signature = _card_signature(card)
    reasons: list[str] = []

    if int(duplicate_signatures.get(signature, 0) or 0) > 1:
        status = GAME_QUALITY_CRITICAL
        reasons.append("exact_duplicate_in_lot")
    else:
        policy_row = dict(policy_validation or {})
        overlap_max = _max_pairwise_overlap(cards, card_index) if len(cards) > 1 else 0
        overlap_class = classify_overlap_for_format(overlap_max, int(card_format or 15))
        overlap_level = str(overlap_class.get("level") or LEVEL_BOM)

        if policy_row and not bool(policy_row.get("approved", True)):
            violations = list(policy_row.get("violations") or [])
            if any("crit" in str(item).lower() for item in violations):
                status = GAME_QUALITY_CRITICAL
            else:
                status = GAME_QUALITY_ATTENTION
            if violations:
                reasons.extend(str(item) for item in violations[:3])
        elif overlap_level in OVERLAP_CRITICAL:
            status = GAME_QUALITY_CRITICAL
            reasons.append(f"overlap_critico:{overlap_max}")
        elif overlap_level in OVERLAP_ATTENTION:
            status = GAME_QUALITY_ATTENTION
            reasons.append(f"overlap_atencao:{overlap_max}")
        else:
            status = GAME_QUALITY_ACCEPTABLE

        if not policy_row and int(card_format) == 15:
            quick = validate_game_structural_policy_15d(
                resolve_cartao_final_from_game(dict(game)),
                previous_contest_numbers=list(parent.get("previous_contest_numbers") or []),
                policy=build_structural_policy_15d_memory(),
            )
            if not bool(quick.get("approved", True)):
                violations = list(quick.get("violations") or [])
                status = GAME_QUALITY_CRITICAL if violations else GAME_QUALITY_ATTENTION
                reasons.extend(str(item) for item in violations[:3])

    analytical_eligible = status in {GAME_QUALITY_ACCEPTABLE, GAME_QUALITY_ATTENTION}
    conference_eligible = status == GAME_QUALITY_ACCEPTABLE or (
        status == GAME_QUALITY_ATTENTION and _attention_conference_allowed(parent)
    )

    return {
        "game_quality_status": status,
        "game_quality_reason": "; ".join(reasons) if reasons else "structural_ok",
        "game_analytical_eligible": analytical_eligible,
        "game_conference_eligible": conference_eligible,
        "source_generation_event_id": _safe_int(
            parent.get("generation_event_id") or game.get("source_generation_event_id")
        ),
        "parent_lot_verdict": str(parent.get("ml_verdict") or ""),
        "parent_lot_status": str(parent.get("lot_operational_status") or ""),
        "overlap_max_in_lot": _max_pairwise_overlap(cards, card_index) if len(cards) > 1 else 0,
        "game_signature": signature,
        "partial_promotion_mission_id": MISSION_ID,
    }


def classify_lot_partial_promotion(
    games: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    parent_lot_context: Mapping[str, Any],
    previous_contest_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Classifica todos os jogos do lote e resume promoção parcial."""
    parent = dict(parent_lot_context or {})
    game_list = [dict(game) for game in games]
    cards = [list(_card_tuple(game)) for game in game_list]
    signatures: dict[str, int] = {}
    for card in cards:
        if not card:
            continue
        signature = _card_signature(card)
        signatures[signature] = signatures.get(signature, 0) + 1

    policy_by_index: dict[int, dict[str, Any]] = {}
    if int(card_format) == 15 and game_list:
        policy_audit = analyze_batch_structural_policy_15d(
            game_list,
            previous_contest_numbers=list(previous_contest_numbers or parent.get("previous_contest_numbers") or []),
            policy=build_structural_policy_15d_memory(),
        )
        policy_by_index = {
            _safe_int(row.get("game_index")): dict(row.get("validation") or {})
            for row in list(policy_audit.get("per_game") or [])
        }

    per_game: list[dict[str, Any]] = []
    counts = {GAME_QUALITY_ACCEPTABLE: 0, GAME_QUALITY_ATTENTION: 0, GAME_QUALITY_CRITICAL: 0}
    for index, game in enumerate(game_list):
        game_index = _safe_int(game.get("game_index"), default=index + 1)
        classification = classify_individual_game_quality(
            game,
            card_format=int(card_format),
            cards=cards,
            card_index=index,
            duplicate_signatures=signatures,
            policy_validation=policy_by_index.get(game_index),
            parent_lot_context=parent,
        )
        counts[str(classification.get("game_quality_status"))] = (
            counts.get(str(classification.get("game_quality_status")), 0) + 1
        )
        per_game.append({"game_index": game_index, **classification})

    lot_analytical_eligible = is_analytical_history_eligible(parent)
    lot_conference_eligible = is_official_conference_eligible(parent)
    games_promoted_analytical = sum(1 for row in per_game if bool(row.get("game_analytical_eligible")))
    games_promoted_conference = sum(1 for row in per_game if bool(row.get("game_conference_eligible")))

    return {
        "mission_id": MISSION_ID,
        "partial_promotion_enabled": True,
        "partial_promotion_mission_id": MISSION_ID,
        "games_total": len(game_list),
        "games_acceptable": int(counts.get(GAME_QUALITY_ACCEPTABLE, 0)),
        "games_attention": int(counts.get(GAME_QUALITY_ATTENTION, 0)),
        "games_critical": int(counts.get(GAME_QUALITY_CRITICAL, 0)),
        "games_promoted_to_analytical": games_promoted_analytical,
        "games_promoted_to_conference": games_promoted_conference,
        "lot_rejected_but_games_promoted": bool(
            not lot_analytical_eligible and games_promoted_analytical > 0
        ),
        "lot_conference_eligible_whole": lot_conference_eligible,
        "per_game": per_game,
    }


def merge_partial_promotion_into_game(game: Mapping[str, Any], classification: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(game)
    merged.update(
        {
            "game_quality_status": str(classification.get("game_quality_status") or ""),
            "game_quality_reason": str(classification.get("game_quality_reason") or ""),
            "game_analytical_eligible": bool(classification.get("game_analytical_eligible")),
            "game_conference_eligible": bool(classification.get("game_conference_eligible")),
            "source_generation_event_id": _safe_int(classification.get("source_generation_event_id")),
            "parent_lot_verdict": str(classification.get("parent_lot_verdict") or ""),
            "parent_lot_status": str(classification.get("parent_lot_status") or ""),
            "partial_promotion_mission_id": MISSION_ID,
        }
    )
    return merged


def apply_partial_promotion_to_payload_games(
    games: list[dict[str, Any]],
    *,
    generation_context: dict[str, Any],
    card_format: int,
    previous_contest_numbers: Sequence[int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Anexa classificação individual aos jogos e resumo ao context_json do lote."""
    parent_context = {
        **dict(generation_context or {}),
        "generation_event_id": _safe_int(generation_context.get("generation_event_id")),
    }
    summary = classify_lot_partial_promotion(
        games,
        card_format=int(card_format),
        parent_lot_context=parent_context,
        previous_contest_numbers=previous_contest_numbers,
    )
    by_index = {
        _safe_int(row.get("game_index")): row for row in list(summary.get("per_game") or [])
    }
    enriched_games: list[dict[str, Any]] = []
    for index, game in enumerate(games):
        game_index = _safe_int(game.get("game_index"), default=index + 1)
        classification = dict(by_index.get(game_index) or {})
        enriched = merge_partial_promotion_into_game(game, classification)
        enriched_games.append(enriched)
    context_patch = {
        "partial_promotion_enabled": True,
        "partial_promotion_mission_id": MISSION_ID,
        "games_total": int(summary.get("games_total", 0) or 0),
        "games_acceptable": int(summary.get("games_acceptable", 0) or 0),
        "games_attention": int(summary.get("games_attention", 0) or 0),
        "games_critical": int(summary.get("games_critical", 0) or 0),
        "games_promoted_to_analytical": int(summary.get("games_promoted_to_analytical", 0) or 0),
        "games_promoted_to_conference": int(summary.get("games_promoted_to_conference", 0) or 0),
        "lot_rejected_but_games_promoted": bool(summary.get("lot_rejected_but_games_promoted")),
    }
    return enriched_games, context_patch


def resolve_game_quality_fields(
    game_context: Mapping[str, Any],
    *,
    game: Mapping[str, Any] | None = None,
    parent_lot_context: Mapping[str, Any] | None = None,
    sibling_games: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deriva classificação quando ausente no PostgreSQL (backfill leitura)."""
    context = dict(game_context or {})
    if context.get("game_quality_status"):
        return {
            "game_quality_status": str(context.get("game_quality_status") or ""),
            "game_quality_reason": str(context.get("game_quality_reason") or ""),
            "game_analytical_eligible": bool(context.get("game_analytical_eligible")),
            "game_conference_eligible": bool(context.get("game_conference_eligible")),
            "parent_lot_verdict": str(context.get("parent_lot_verdict") or ""),
            "parent_lot_status": str(context.get("parent_lot_status") or ""),
            "partial_promotion_mission_id": str(context.get("partial_promotion_mission_id") or MISSION_ID),
        }
    parent = dict(parent_lot_context or {})
    siblings = list(sibling_games or [])
    if game is None:
        return {
            "game_quality_status": "",
            "game_quality_reason": "",
            "game_analytical_eligible": is_analytical_history_eligible(parent),
            "game_conference_eligible": is_official_conference_eligible(parent),
            "parent_lot_verdict": str(parent.get("ml_verdict") or ""),
            "parent_lot_status": str(parent.get("lot_operational_status") or ""),
            "partial_promotion_mission_id": MISSION_ID,
        }
    card_format = _safe_int(
        context.get("selected_card_format") or context.get("card_format") or parent.get("selected_card_format"),
        15,
    )
    if not siblings:
        siblings = [dict(game)]
    summary = classify_lot_partial_promotion(
        siblings,
        card_format=card_format,
        parent_lot_context=parent,
    )
    game_index = _safe_int(game.get("game_index") or context.get("game_index"))
    for row in list(summary.get("per_game") or []):
        if _safe_int(row.get("game_index")) == game_index:
            return dict(row)
    return {
        "game_quality_status": GAME_QUALITY_ACCEPTABLE,
        "game_quality_reason": "legacy_lot_fully_eligible",
        "game_analytical_eligible": is_analytical_history_eligible(parent),
        "game_conference_eligible": is_official_conference_eligible(parent),
        "parent_lot_verdict": str(parent.get("ml_verdict") or ""),
        "parent_lot_status": str(parent.get("lot_operational_status") or ""),
        "partial_promotion_mission_id": MISSION_ID,
    }


def is_game_analytical_eligible(
    game_context: Mapping[str, Any],
    *,
    parent_lot_context: Mapping[str, Any] | None = None,
    sibling_games: Sequence[Mapping[str, Any]] | None = None,
    game: Mapping[str, Any] | None = None,
) -> bool:
    parent = dict(parent_lot_context or {})
    context = dict(game_context or {})
    if context.get("game_quality_status"):
        return bool(context.get("game_analytical_eligible"))
    if bool(parent.get("partial_promotion_enabled")):
        fields = resolve_game_quality_fields(
            context,
            game=game,
            parent_lot_context=parent,
            sibling_games=sibling_games,
        )
        if fields.get("game_quality_status"):
            return bool(fields.get("game_analytical_eligible"))
    return is_analytical_history_eligible(parent)


def is_game_conference_eligible(
    game_context: Mapping[str, Any],
    *,
    parent_lot_context: Mapping[str, Any] | None = None,
    sibling_games: Sequence[Mapping[str, Any]] | None = None,
    game: Mapping[str, Any] | None = None,
) -> bool:
    parent = dict(parent_lot_context or {})
    context = dict(game_context or {})
    if context.get("game_quality_status"):
        if bool(context.get("game_conference_eligible")):
            return True
        status = str(context.get("game_quality_status") or "")
        if status == GAME_QUALITY_CRITICAL:
            return False
        # Read-time: lote promovido após persistência (ex. approved_with_warning na Central ML).
        if is_official_conference_eligible(parent):
            if status == GAME_QUALITY_ACCEPTABLE:
                return True
            if status == GAME_QUALITY_ATTENTION and _attention_conference_allowed(parent):
                return True
    if bool(parent.get("partial_promotion_enabled")):
        fields = resolve_game_quality_fields(
            context,
            game=game,
            parent_lot_context=parent,
            sibling_games=sibling_games,
        )
        if fields.get("game_quality_status"):
            return bool(fields.get("game_conference_eligible"))
    if context.get("game_quality_status"):
        return bool(context.get("game_conference_eligible"))
    return is_official_conference_eligible(parent)


def filter_analytical_games(
    generation: Mapping[str, Any],
    games: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Filtra jogos elegíveis para Histórico Analítico (promoção parcial M-OPS-078)."""
    parent_context = dict(generation.get("context_json") or generation)
    lot_eligible = is_analytical_history_eligible(parent_context)
    partial_enabled = bool(parent_context.get("partial_promotion_enabled"))
    game_list = [dict(game) for game in games]
    if not partial_enabled:
        return list(game_list) if lot_eligible else []
    selected: list[dict[str, Any]] = []
    for game in game_list:
        ctx = dict(game.get("generation_context") or game.get("context_json") or {})
        if is_game_analytical_eligible(
            ctx,
            parent_lot_context=parent_context,
            sibling_games=game_list,
            game=game,
        ):
            selected.append(game)
    return selected


def filter_conference_games(
    generation: Mapping[str, Any],
    games: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Filtra jogos elegíveis para Conferir Resultados."""
    parent_context = dict(generation.get("context_json") or generation)
    lot_eligible = is_official_conference_eligible(parent_context)
    partial_enabled = bool(parent_context.get("partial_promotion_enabled"))
    game_list = [dict(game) for game in games]
    if not partial_enabled:
        return list(game_list) if lot_eligible else []
    selected: list[dict[str, Any]] = []
    for game in game_list:
        ctx = dict(game.get("generation_context") or game.get("context_json") or {})
        if is_game_conference_eligible(
            ctx,
            parent_lot_context=parent_context,
            sibling_games=game_list,
            game=game,
        ):
            selected.append(game)
    return selected
