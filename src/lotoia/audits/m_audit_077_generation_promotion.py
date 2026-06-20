"""M-AUDIT-077 — Auditoria de promoção GE 025→040 (read-only)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, get_session
from lotoia.governance.lei15_core_002_sovereign import (
    core_002_batch_label_game_size,
    is_sovereign_core_label,
)
from lotoia.ml.ml_operational_verdict import evaluate_batch_ml_verdict_from_games
from lotoia.ml.overlap_format_thresholds import (
    LEVEL_ATENCAO,
    LEVEL_BOM,
    LEVEL_CRITICO,
    LEVEL_RUIM,
    classify_overlap_for_format,
)
from lotoia.ml.structural_policy_15d import analyze_batch_structural_policy_15d, build_structural_policy_15d_memory
from lotoia.observability.card_structure_diagnostics import (
    build_card_structure_payload,
    extract_operational_structural_metrics,
)
from lotoia.operations.lot_operational_status import (
    extract_lot_operational_status,
    is_analytical_history_eligible,
    is_official_conference_eligible,
)
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-AUDIT-077"

OVERLAP_ACCEPTABLE_LEVELS = frozenset({LEVEL_BOM})
OVERLAP_ATTENTION_LEVELS = frozenset({LEVEL_ATENCAO, LEVEL_RUIM})
OVERLAP_CRITICAL_LEVELS = frozenset({LEVEL_CRITICO})


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_operational_index(events: Sequence[Mapping[str, Any]]) -> dict[int, int]:
    """generation_event_id → índice operacional soberano (001, 002, …)."""
    eligible: list[tuple[int, str]] = []
    for row in events:
        ge_id = _safe_int(row.get("id") or row.get("generation_event_id"))
        if ge_id <= 0:
            continue
        label = str(row.get("analysis_batch_label") or "").strip().upper()
        if not is_sovereign_core_label(label):
            continue
        eligible.append((ge_id, str(row.get("created_at") or "")))
    eligible.sort(key=lambda item: (item[1], item[0]))
    return {ge_id: index + 1 for index, (ge_id, _created_at) in enumerate(eligible)}


def resolve_generation_event_ids_for_operational_range(
    events: Sequence[Mapping[str, Any]],
    *,
    operational_start: int,
    operational_end: int,
) -> list[int]:
    index = build_operational_index(events)
    reverse = {seq: ge_id for ge_id, seq in index.items()}
    targets: list[int] = []
    for seq in range(int(operational_start), int(operational_end) + 1):
        ge_id = reverse.get(seq)
        if ge_id:
            targets.append(int(ge_id))
    return targets


def _game_records_from_rows(rows: Sequence[Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for row in rows:
        numbers = [int(number) for number in (getattr(row, "numbers", None) or [])]
        context_json = dict(getattr(row, "context_json", {}) or {})
        final_card = list(context_json.get("final_card_numbers") or numbers or [])
        games.append(
            {
                "game_index": int(getattr(row, "game_index", 0) or 0),
                "numbers": numbers,
                "final_card_numbers": final_card,
                "context_json": context_json,
                "profile_type": str(getattr(row, "profile_type", "") or ""),
            }
        )
    return games


def _max_pairwise_overlap(cards: Sequence[Sequence[int]], index: int) -> int:
    current = set(int(number) for number in cards[index])
    best = 0
    for other_index, other in enumerate(cards):
        if other_index == index:
            continue
        best = max(best, len(current & set(int(number) for number in other)))
    return best


def classify_games_in_lot(
    games: Sequence[Mapping[str, Any]],
    *,
    card_format: int,
    previous_contest_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Classifica jogos individualmente — aceitável / atenção / crítico."""
    cards = [resolve_cartao_final_from_game(dict(game)) for game in games]
    cards = [card for card in cards if card]
    acceptable = 0
    attention = 0
    critical = 0
    per_game: list[dict[str, Any]] = []
    policy_compliant = 0

    policy_audit: dict[str, Any] = {}
    if int(card_format) == 15 and games:
        policy_audit = analyze_batch_structural_policy_15d(
            [dict(game) for game in games],
            previous_contest_numbers=list(previous_contest_numbers or []),
            policy=build_structural_policy_15d_memory(),
        )
        policy_by_index = {
            int(row.get("game_index", 0) or 0): dict(row.get("validation") or {})
            for row in list(policy_audit.get("per_game") or [])
        }
    else:
        policy_by_index = {}

    for index, game in enumerate(games):
        game_index = int(game.get("game_index", index + 1) or index + 1)
        card = resolve_cartao_final_from_game(dict(game))
        overlap_max = _max_pairwise_overlap(cards, index) if card and len(cards) > 1 else 0
        overlap_class = classify_overlap_for_format(overlap_max, int(card_format or 15))
        level = str(overlap_class.get("level") or LEVEL_BOM)
        policy_row = dict(policy_by_index.get(game_index) or {})
        policy_approved = bool(policy_row.get("approved")) if policy_row else True

        if level in OVERLAP_CRITICAL_LEVELS or (policy_row and not policy_approved):
            bucket = "critico"
            critical += 1
        elif level in OVERLAP_ATTENTION_LEVELS:
            bucket = "atencao"
            attention += 1
        else:
            bucket = "aceitavel"
            acceptable += 1
        if policy_approved:
            policy_compliant += 1

        individually_promotable = bucket == "aceitavel" and policy_approved
        per_game.append(
            {
                "game_index": game_index,
                "overlap_max_in_lot": overlap_max,
                "overlap_level": level,
                "bucket": bucket,
                "policy_approved": policy_approved,
                "individually_structurally_acceptable": bucket in {"aceitavel", "atencao"} and policy_approved,
                "individually_promotable_under_lot_gate": individually_promotable,
            }
        )

    return {
        "total_games": len(games),
        "acceptable": acceptable,
        "attention": attention,
        "critical": critical,
        "policy_compliant": policy_compliant,
        "structural_policy_15d": {
            "games_compliant": int(policy_audit.get("games_compliant", 0) or 0),
            "compliance_label": str(policy_audit.get("compliance_label") or ""),
            "violations": list(policy_audit.get("violations") or []),
        },
        "per_game": per_game,
        "lot_evaluated_as_whole": True,
        "individual_promotion_supported": False,
    }


def extract_lot_metrics_from_games(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = build_card_structure_payload(
        games=[dict(row) for row in games],
        official_cards=[],
        official_contests=[],
        generation_event_ids=[],
        reconciliation_run_ids=[],
        contest_ids=[],
    )
    if not payload.get("available"):
        return {}
    return extract_operational_structural_metrics(payload)


def audit_generation_event_record(
    *,
    event: Mapping[str, Any],
    game_rows: Sequence[Any],
    operational_sequence: int | None = None,
) -> dict[str, Any]:
    context = dict(event.get("context_json") or {})
    batch_label = str(event.get("analysis_batch_label") or context.get("analysis_batch_label") or "")
    card_format = int(
        context.get("selected_card_format")
        or context.get("card_format")
        or core_002_batch_label_game_size(batch_label)
        or 15
    )
    games = _game_records_from_rows(game_rows)
    metrics = extract_lot_metrics_from_games(games)
    hierarchy = dict(context.get("ml_hierarchy_bundle") or context.get("ml_operational_hierarchy") or {})
    game_classification = classify_games_in_lot(
        games,
        card_format=card_format,
        previous_contest_numbers=list(context.get("previous_contest_numbers") or []),
    )
    recomputed_verdict = evaluate_batch_ml_verdict_from_games(
        games,
        calibration_applied=bool(context.get("calibration_applied")),
        calibration_authorized=bool(context.get("calibration_authorized")),
    )
    lot_status = extract_lot_operational_status(context)
    unique_cards = {tuple(resolve_cartao_final_from_game(dict(game))) for game in games}
    unique_cards.discard(tuple())

    row = {
        "mission_id": MISSION_ID,
        "operational_sequence": operational_sequence,
        "generation_event_id": int(event.get("id") or event.get("generation_event_id") or 0),
        "batch_label": batch_label,
        "created_at": str(event.get("created_at") or ""),
        "total_jogos_gerados": len(games),
        "total_jogos_unicos": len(unique_cards),
        "similaridade_media": _safe_float(metrics.get("similaridade_media")),
        "sobreposicao_maxima": _safe_int(metrics.get("sobreposicao_maxima")),
        "score_diversidade": _safe_float(metrics.get("diversity_score")),
        "pares_em_atencao": _safe_int(metrics.get("pares_em_atencao")),
        "dezenas_subcobertas": _safe_int(metrics.get("dezenas_subcobertas")),
        "ml_verdict": str(context.get("ml_verdict") or recomputed_verdict.get("ml_verdict") or ""),
        "gp_quality_tier": str(
            context.get("gp_quality_tier")
            or hierarchy.get("gp_quality_tier")
            or ""
        ),
        "lot_operational_status": lot_status,
        "promotion_block_reason": str(context.get("promotion_block_reason") or ""),
        "official_release_allowed": bool(context.get("official_release_allowed")),
        "is_analytical_history_eligible": is_analytical_history_eligible(context),
        "is_official_conference_eligible": is_official_conference_eligible(context),
        "promoted_to_analytical_history": bool(context.get("promoted_to_analytical_history")),
        "promoted_to_official_conference": bool(context.get("promoted_to_official_conference")),
        "post_calibration_promotion_status": str(context.get("post_calibration_promotion_status") or ""),
        "game_classification": game_classification,
        "persisted_context_snapshot": {
            "ml_verdict_reason": str(context.get("ml_verdict_reason") or context.get("motivo_principal") or ""),
            "calibration_plan_applied_to_generation": bool(context.get("calibration_plan_applied_to_generation")),
            "structural_coverage_review_completed": bool(context.get("structural_coverage_review_completed")),
        },
        "recomputed_ml_verdict": str(recomputed_verdict.get("ml_verdict") or ""),
        "recomputed_official_release_allowed": bool(recomputed_verdict.get("official_release_allowed")),
    }
    row["lot_discarded_entirely"] = not row["is_analytical_history_eligible"] and not row["is_official_conference_eligible"]
    row["games_that_could_have_been_promoted_individually"] = int(game_classification.get("acceptable", 0) or 0)
    return row


def audit_operational_generation_range(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    operational_start: int = 25,
    operational_end: int = 40,
) -> dict[str, Any]:
    """Auditoria read-only — PostgreSQL soberano."""
    audited_at = datetime.now(UTC).isoformat()
    with get_session(db_path) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.asc(), GenerationEvent.id.asc())
            .all()
        )
        event_payloads = [
            {
                "id": int(event.id or 0),
                "generation_event_id": int(event.id or 0),
                "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                "context_json": dict(getattr(event, "context_json", {}) or {}),
            }
            for event in events
        ]
        operational_index = build_operational_index(event_payloads)
        target_ge_ids = resolve_generation_event_ids_for_operational_range(
            event_payloads,
            operational_start=operational_start,
            operational_end=operational_end,
        )
        lots: list[dict[str, Any]] = []
        for ge_id in target_ge_ids:
            event = session.query(GenerationEvent).filter(GenerationEvent.id == int(ge_id)).first()
            if event is None:
                continue
            rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == int(ge_id))
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            lots.append(
                audit_generation_event_record(
                    event={
                        "id": int(event.id or 0),
                        "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                        "context_json": dict(getattr(event, "context_json", {}) or {}),
                    },
                    game_rows=rows,
                    operational_sequence=int(operational_index.get(int(ge_id), 0) or 0) or None,
                )
            )

    eligible_lots = sum(1 for lot in lots if lot.get("is_analytical_history_eligible"))
    eligible_games = sum(int((lot.get("game_classification") or {}).get("acceptable", 0) or 0) for lot in lots)
    total_games = sum(int(lot.get("total_jogos_gerados", 0) or 0) for lot in lots)

    verdict = _build_audit_verdict(lots)
    return {
        "mission_id": MISSION_ID,
        "audited_at": audited_at,
        "operational_range": {"start": int(operational_start), "end": int(operational_end)},
        "operational_index_size": len(operational_index),
        "target_generation_event_ids": target_ge_ids,
        "lots_audited": len(lots),
        "lots_missing_from_db": (int(operational_end) - int(operational_start) + 1) - len(lots),
        "summary": {
            "total_games_in_range": total_games,
            "lots_eligible_analytical_or_conference": eligible_lots,
            "games_structurally_acceptable_in_range": eligible_games,
            "all_lots_blocked": len(lots) > 0 and eligible_lots == 0,
        },
        "central_questions": verdict,
        "lots": lots,
        "functional_changes": False,
        "purge_executed": False,
    }


def _build_audit_verdict(lots: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not lots:
        return {
            "generation_produced_games": "indeterminado — sem lotes no intervalo",
            "ml_classification_blocked": "indeterminado",
            "promotion_pipeline_blocked": "indeterminado",
            "conference_blocked": "indeterminado",
            "at_least_one_structurally_valid_game_per_lot": "indeterminado",
            "system_evaluates_whole_lot_not_individual_games": True,
            "primary_root_cause": "dados_indisponiveis_no_runtime",
        }

    block_reasons: dict[str, int] = {}
    verdicts: dict[str, int] = {}
    statuses: dict[str, int] = {}
    lots_with_acceptable_games = 0
    for lot in lots:
        reason = str(lot.get("promotion_block_reason") or "no_block_reason_recorded")
        block_reasons[reason] = block_reasons.get(reason, 0) + 1
        verdict = str(lot.get("ml_verdict") or "—")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        status = str(lot.get("lot_operational_status") or "—")
        statuses[status] = statuses.get(status, 0) + 1
        acceptable = int((lot.get("game_classification") or {}).get("acceptable", 0) or 0)
        if acceptable > 0:
            lots_with_acceptable_games += 1

    dominant_reason = max(block_reasons, key=block_reasons.get) if block_reasons else ""
    dominant_verdict = max(verdicts, key=verdicts.get) if verdicts else ""
    any_games = all(int(lot.get("total_jogos_gerados", 0) or 0) > 0 for lot in lots)
    any_eligible = any(
        bool(lot.get("is_analytical_history_eligible")) or bool(lot.get("is_official_conference_eligible"))
        for lot in lots
    )

    return {
        "1_generation_produced_games": any_games,
        "2_ml_classification_blocked_promotion": not any_eligible and dominant_verdict in {
            "REPROVADO",
            "PRECISA CALIBRAR",
            "BLOQUEADO PARA OFICIALIZAÇÃO",
        },
        "3_promotion_pipeline_blocked": not any_eligible,
        "4_conference_blocked": not any(
            bool(lot.get("is_official_conference_eligible")) for lot in lots
        ),
        "5_at_least_one_structurally_valid_game_in_each_lot": lots_with_acceptable_games == len(lots),
        "6_system_evaluates_whole_lot_not_individual_games": True,
        "dominant_ml_verdict": dominant_verdict,
        "dominant_lot_operational_status": max(statuses, key=statuses.get) if statuses else "",
        "dominant_promotion_block_reason": dominant_reason,
        "lots_with_acceptable_games": lots_with_acceptable_games,
        "lots_with_zero_eligible_promotion": sum(
            1
            for lot in lots
            if not bool(lot.get("is_analytical_history_eligible"))
            and not bool(lot.get("is_official_conference_eligible"))
        ),
        "primary_root_cause_hypothesis": (
            "classificacao_ml_e_promocao_por_lote"
            if not any_eligible and lots_with_acceptable_games > 0
            else (
                "geracao_sem_jogos_ou_colapso_estrutural_total"
                if lots_with_acceptable_games == 0
                else "promocao_parcial_esperada"
            )
        ),
    }
