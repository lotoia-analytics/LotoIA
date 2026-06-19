"""Política estrutural soberana 15D — memória ML institucional (M-ML-070)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    ScientificInstitutionalMemory,
    create_database,
    get_session,
)
from lotoia.statistics.advanced import calculate_sequence_stats
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-ML-070"
POLICY_VERSION = "M-ML-070-v1"
MEMORY_KIND = "structural_policy_15d"
MEMORY_STATUS_ACTIVE = "active"
MEMORY_ORIGIN = "institutional_sovereign_base_15d"
MEMORY_REASON = "política soberana base 15D"
EXPECTED_IMPACT = (
    "Garantir rastreabilidade e conformidade estrutural dos cartões 15D "
    "(repetição 7–10, paridade 7/8 ou 8/7, sequência ≤ 6)."
)

RULE_REPEAT = "repeticao_7_10"
RULE_PARITY = "paridade_preferencial_7_8"
RULE_SEQUENCE = "sequencia_maxima_6"
APPLIED_RULES: tuple[str, ...] = (RULE_REPEAT, RULE_PARITY, RULE_SEQUENCE)

PREFERRED_PARITY_PAIRS: tuple[tuple[int, int], ...] = ((7, 8), (8, 7))
ALLOWED_PARITY_PAIRS: tuple[tuple[int, int], ...] = (
    (7, 8),
    (8, 7),
    (6, 9),
    (9, 6),
)
CORE_NUMBERS: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS: tuple[int, ...] = (2, 4, 11, 15, 24, 25)


def is_structural_policy_15d_format(game_size: int) -> bool:
    return int(game_size) == 15


def build_structural_policy_15d_memory() -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    return {
        "mission_id": MISSION_ID,
        "formato": "15D",
        "tipo": MEMORY_KIND,
        "policy_version": POLICY_VERSION,
        "status": MEMORY_STATUS_ACTIVE,
        "origem_institucional": MEMORY_ORIGIN,
        "motivo": MEMORY_REASON,
        "impacto_esperado": EXPECTED_IMPACT,
        "regras_aplicadas": list(APPLIED_RULES),
        "repeticao_ultimo_concurso_min": 7,
        "repeticao_ultimo_concurso_max": 10,
        "paridade_preferencial": [list(pair) for pair in PREFERRED_PARITY_PAIRS],
        "paridade_permitida": [list(pair) for pair in ALLOWED_PARITY_PAIRS],
        "sequencia_maxima": 6,
        "core_numbers": list(CORE_NUMBERS),
        "discouraged_numbers": list(DISCOURAGED_NUMBERS),
        "created_at": now,
        "updated_at": now,
    }


def _normalize_numbers(numbers: Sequence[int] | None) -> set[int]:
    normalized: set[int] = set()
    for raw in numbers or []:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 25:
            normalized.add(value)
    return normalized


def _parity_pair(numbers: Sequence[int]) -> tuple[int, int]:
    odd_count = sum(1 for number in numbers if int(number) % 2 != 0)
    return odd_count, len(numbers) - odd_count


def resolve_previous_contest_numbers(history: Sequence[Any] | None) -> list[int]:
    if not history:
        return []
    last_draw = history[-1]
    numbers = getattr(last_draw, "numbers", None)
    if numbers:
        return sorted(int(number) for number in numbers)
    if isinstance(last_draw, Mapping):
        raw = last_draw.get("numbers") or last_draw.get("dezenas") or []
        return sorted(int(number) for number in raw if 1 <= int(number) <= 25)
    return []


def validate_game_structural_policy_15d(
    numbers: Sequence[int],
    *,
    previous_contest_numbers: Sequence[int] | None,
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_policy = dict(policy or build_structural_policy_15d_memory())
    card_numbers = sorted(_normalize_numbers(numbers))
    previous_numbers = _normalize_numbers(previous_contest_numbers)
    violations: list[str] = []

    repeat_count: int | None = None
    if not previous_numbers:
        violations.append("repeticao:concurso_anterior_indisponivel")
    else:
        repeat_count = len(set(card_numbers) & previous_numbers)
        repeat_min = int(resolved_policy.get("repeticao_ultimo_concurso_min", 7) or 7)
        repeat_max = int(resolved_policy.get("repeticao_ultimo_concurso_max", 10) or 10)
        if repeat_count < repeat_min or repeat_count > repeat_max:
            violations.append(f"repeticao:fora_faixa_{repeat_min}_{repeat_max}:{repeat_count}")

    parity = _parity_pair(card_numbers)
    preferred_pairs = {
        tuple(int(part) for part in pair)
        for pair in resolved_policy.get("paridade_preferencial", PREFERRED_PARITY_PAIRS)
        if isinstance(pair, (list, tuple)) and len(pair) >= 2
    }
    if parity not in preferred_pairs:
        violations.append(f"paridade:fora_preferencial_7_8:{parity[0]}_{parity[1]}")

    sequence_stats = calculate_sequence_stats(card_numbers)
    largest_sequence = int(sequence_stats.get("largest_sequence", 0) or 0)
    sequence_max = int(resolved_policy.get("sequencia_maxima", 6) or 6)
    if largest_sequence > sequence_max:
        violations.append(f"sequencia:maxima_excedida:{largest_sequence}>{sequence_max}")

    return {
        "approved": not violations,
        "violations": violations,
        "violated_rules": violations,
        "applied_rules": list(APPLIED_RULES),
        "repeat_count": repeat_count,
        "parity": list(parity),
        "largest_sequence": largest_sequence,
        "policy_version": str(resolved_policy.get("policy_version") or POLICY_VERSION),
    }


def _game_signature(game: Mapping[str, Any]) -> tuple[int, ...]:
    numbers = resolve_cartao_final_from_game(dict(game))
    return tuple(sorted(numbers))


def _validate_game_record(
    game: Mapping[str, Any],
    *,
    previous_contest_numbers: Sequence[int] | None,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    numbers = resolve_cartao_final_from_game(dict(game))
    return validate_game_structural_policy_15d(
        numbers,
        previous_contest_numbers=previous_contest_numbers,
        policy=policy,
    )


def _enrich_with_validation(
    game: Mapping[str, Any],
    *,
    previous_numbers: Sequence[int] | None,
    memory: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    validation = _validate_game_record(
        game,
        previous_contest_numbers=previous_numbers,
        policy=memory,
    )
    enriched = dict(game)
    enriched["structural_policy_15d_validation"] = validation
    enriched["structural_policy_memory_loaded"] = True
    enriched["structural_policy_format"] = "15D"
    enriched["structural_policy_version"] = memory.get("policy_version")
    enriched["policy_compliance_status"] = "compliant" if validation["approved"] else "non_compliant"
    return enriched, validation


def apply_structural_policy_15d_to_sovereign_batch(
    selected_games: Sequence[dict[str, Any]],
    *,
    pool_games: Sequence[dict[str, Any]],
    history: Sequence[Any] | None,
    required_count: int,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Governa o lote final 15D pela conformidade estrutural (M-ML-070-FIX-01).

    A política deixa de ser observacional: o lote final prioriza cartões
    conformes (repetição 7–10, paridade permitida, sequência ≤ 6). Cartões não
    conformes só entram para completar ``required_count`` quando não há conformes
    suficientes, e essa exceção é rastreada em ``non_compliant_kept_reason``.
    """
    memory = ensure_structural_policy_15d_memory(db_path)
    previous_numbers = resolve_previous_contest_numbers(history)
    original_signatures = [_game_signature(game) for game in selected_games]

    # Candidatos únicos: seleção soberana do GP primeiro, depois o pool conforme.
    compliant_candidates: list[dict[str, Any]] = []
    non_compliant_candidates: list[dict[str, Any]] = []
    seen_signatures: set[tuple[int, ...]] = set()
    for game in list(selected_games) + list(pool_games):
        signature = _game_signature(game)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        enriched, validation = _enrich_with_validation(
            game, previous_numbers=previous_numbers, memory=memory
        )
        if validation["approved"]:
            compliant_candidates.append(enriched)
        else:
            non_compliant_candidates.append(enriched)

    # Conformes governam o lote: ordenados por qualidade (profile/final score).
    compliant_candidates.sort(
        key=lambda row: (
            -float(row.get("profile_score", 0) or 0),
            -float((row.get("final_score") or {}).get("final_score", 0) or 0),
        )
    )

    final_games: list[dict[str, Any]] = []
    for game in compliant_candidates:
        if len(final_games) >= required_count:
            break
        final_games.append(game)

    non_compliant_kept = 0
    if len(final_games) < required_count:
        for game in non_compliant_candidates:
            if len(final_games) >= required_count:
                break
            final_games.append(game)
            non_compliant_kept += 1
    final_games = final_games[:required_count]

    violated_rules = sorted(
        {
            violation
            for game in final_games
            for violation in list((game.get("structural_policy_15d_validation") or {}).get("violations") or [])
        }
    )
    compliant_count = sum(
        1
        for game in final_games
        if bool((game.get("structural_policy_15d_validation") or {}).get("approved"))
    )
    non_compliant_count = len(final_games) - compliant_count
    if compliant_count == len(final_games) and final_games:
        compliance_status = "compliant"
    elif compliant_count == 0 and final_games:
        compliance_status = "non_compliant"
    elif final_games:
        compliance_status = "partial"
    else:
        compliance_status = "empty"
    compliance_rate = round(compliant_count / len(final_games), 4) if final_games else 0.0
    lote_alterado = [_game_signature(game) for game in final_games] != original_signatures
    non_compliant_kept_reason = (
        "insufficient_compliant_pool" if non_compliant_kept else None
    )

    bundle = {
        "mission_id": MISSION_ID,
        "structural_policy_memory_loaded": True,
        "structural_policy_format": "15D",
        "structural_policy_version": memory.get("policy_version"),
        "structural_policy_applied": True,
        "structural_policy_application_mode": "governing_by_compliance",
        "structural_policy_15d_memory": memory,
        "applied_rules": list(APPLIED_RULES),
        "violated_rules": violated_rules,
        "policy_violations": violated_rules,
        "policy_compliance_status": compliance_status,
        "previous_contest_numbers": list(previous_numbers),
        "games_validated": len(final_games),
        "games_compliant": compliant_count,
        "games_non_compliant": non_compliant_count,
        "compliance_rate": compliance_rate,
        "lote_alterado": lote_alterado,
        "non_compliant_kept": non_compliant_kept,
        "non_compliant_kept_reason": non_compliant_kept_reason,
        "memory_status": memory.get("status"),
        "memory_origin": memory.get("origem_institucional"),
    }
    return final_games, bundle


def persist_structural_policy_15d_memory(
    db_path: Any = DEFAULT_DATABASE_PATH,
    memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(memory or build_structural_policy_15d_memory())
    payload["updated_at"] = datetime.now(UTC).isoformat()
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind=MEMORY_KIND,
                strategy_name="15 dezenas",
                game_size=15,
                batch_id=f"{MISSION_ID}-{payload.get('policy_version', POLICY_VERSION)}",
                generation_range={"mission_id": MISSION_ID, "formato": "15D"},
                total_games=0,
                unique_games=0,
                duplicate_games=0,
                structural_status=MEMORY_STATUS_ACTIVE,
                scientific_status=MEMORY_STATUS_ACTIVE,
                scientific_classification="STRUCTURAL_POLICY_15D",
                main_reason=MEMORY_REASON,
                recommended_action="apply_structural_policy_15d_validation",
                policy_applied=dict(payload),
                policy_before={},
                policy_after=dict(payload),
                decision_mode="INSTITUCIONAL",
                approved_for_use=1,
                notes=EXPECTED_IMPACT,
                source=MISSION_ID,
            )
        )
        session.commit()
    return payload


def load_active_structural_policy_15d_memory(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    persist_if_missing: bool = True,
) -> dict[str, Any]:
    create_database(db_path)
    with get_session(db_path) as session:
        row = (
            session.query(ScientificInstitutionalMemory)
            .filter(
                ScientificInstitutionalMemory.memory_kind == MEMORY_KIND,
                ScientificInstitutionalMemory.game_size == 15,
                ScientificInstitutionalMemory.approved_for_use == 1,
            )
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .first()
        )
    if row is not None:
        stored = dict(getattr(row, "policy_applied", {}) or {})
        if stored:
            stored.setdefault("memory_row_id", int(getattr(row, "id", 0) or 0))
            stored.setdefault(
                "status",
                str(getattr(row, "structural_status", MEMORY_STATUS_ACTIVE) or MEMORY_STATUS_ACTIVE),
            )
            stored.setdefault("updated_at", getattr(row, "created_at", datetime.now(UTC)).isoformat())
            return stored
    if persist_if_missing:
        return persist_structural_policy_15d_memory(db_path)
    return build_structural_policy_15d_memory()


def ensure_structural_policy_15d_memory(db_path: Any = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    canonical = build_structural_policy_15d_memory()
    active = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)
    if active and str(active.get("policy_version") or "") == canonical["policy_version"]:
        return active
    return persist_structural_policy_15d_memory(db_path, canonical)


def extract_structural_policy_application_from_context(
    context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(context or {})
    bundle = dict(payload.get("structural_policy_15d_bundle") or {})
    if bundle:
        return {
            "available": True,
            "structural_policy_memory_loaded": bool(bundle.get("structural_policy_memory_loaded")),
            "structural_policy_format": str(bundle.get("structural_policy_format") or "15D"),
            "structural_policy_version": str(bundle.get("structural_policy_version") or ""),
            "structural_policy_applied": bool(bundle.get("structural_policy_applied")),
            "structural_policy_application_mode": str(bundle.get("structural_policy_application_mode") or ""),
            "applied_rules": list(bundle.get("applied_rules") or []),
            "violated_rules": list(bundle.get("violated_rules") or []),
            "policy_violations": list(bundle.get("policy_violations") or bundle.get("violated_rules") or []),
            "policy_compliance_status": str(bundle.get("policy_compliance_status") or ""),
            "games_validated": int(bundle.get("games_validated", 0) or 0),
            "games_compliant": int(bundle.get("games_compliant", 0) or 0),
            "games_non_compliant": int(bundle.get("games_non_compliant", 0) or 0),
            "compliance_rate": float(bundle.get("compliance_rate", 0.0) or 0.0),
            "lote_alterado": bool(bundle.get("lote_alterado")),
            "non_compliant_kept_reason": bundle.get("non_compliant_kept_reason"),
        }
    if payload.get("structural_policy_memory_loaded"):
        return {
            "available": True,
            "structural_policy_memory_loaded": True,
            "structural_policy_format": str(payload.get("structural_policy_format") or "15D"),
            "structural_policy_version": str(payload.get("structural_policy_version") or ""),
            "applied_rules": list(payload.get("applied_rules") or []),
            "violated_rules": list(payload.get("violated_rules") or []),
            "policy_compliance_status": str(payload.get("policy_compliance_status") or ""),
            "games_validated": int(payload.get("games_validated", 0) or 0),
            "games_compliant": int(payload.get("games_compliant", 0) or 0),
        }
    return {"available": False}
