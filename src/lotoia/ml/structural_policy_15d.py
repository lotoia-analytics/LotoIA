"""Política estrutural soberana 15D — memória ML institucional (M-ML-070)."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any, Mapping, Sequence

from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    GeneratedGame,
    ScientificInstitutionalMemory,
    create_database,
    get_session,
)
from lotoia.statistics.advanced import calculate_sequence_stats
from lotoia.statistics.card_structure import resolve_cartao_final_from_game

MISSION_ID = "M-ML-070"
POLICY_VERSION = "M-ML-070-v1"
MEMORY_KIND = "structural_policy_15d"
MEMORY_KIND_BATCH = "structural_policy_15d_batch"
MEMORY_STATUS_ACTIVE = "active"
COMPLIANCE_LABEL_APROVADO = "APROVADO"
COMPLIANCE_LABEL_ATENCAO = "ATENÇÃO"
COMPLIANCE_LABEL_REPROVADO = "REPROVADO"
CORE_MIN_PRESENT = 2
DISCOURAGED_MAX_PRESENT = 3
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
ALLOWED_PARITY_PAIRS: tuple[tuple[int, int], ...] = PREFERRED_PARITY_PAIRS
NON_COMPLIANT_PARITY_PAIRS: tuple[tuple[int, int], ...] = ((6, 9), (9, 6))
CORE_NUMBERS: tuple[int, ...] = (7, 12, 16, 23)
DISCOURAGED_NUMBERS: tuple[int, ...] = (2, 4, 11, 15, 24, 25)


def is_structural_policy_15d_format(game_size: int) -> bool:
    return int(game_size) == 15


def _parity_pairs_as_lists(
    pairs: Sequence[tuple[int, int]] | None = None,
) -> list[list[int]]:
    return [list(pair) for pair in (pairs or PREFERRED_PARITY_PAIRS)]


def normalize_structural_policy_15d_memory(memory: Mapping[str, Any]) -> dict[str, Any]:
    """Alinha paridade da memória à política soberana (somente 7/8 e 8/7)."""
    normalized = dict(memory)
    canonical = _parity_pairs_as_lists(PREFERRED_PARITY_PAIRS)
    normalized["paridade_preferencial"] = canonical
    normalized["paridade_permitida"] = canonical
    return normalized


def _stored_parity_pairs(memory: Mapping[str, Any], field: str) -> set[tuple[int, int]]:
    stored: set[tuple[int, int]] = set()
    for pair in memory.get(field) or []:
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            stored.add((int(pair[0]), int(pair[1])))
    return stored


def memory_needs_parity_alignment(memory: Mapping[str, Any]) -> bool:
    canonical = set(PREFERRED_PARITY_PAIRS)
    for field in ("paridade_preferencial", "paridade_permitida"):
        stored = _stored_parity_pairs(memory, field)
        if stored and stored != canonical:
            return True
        if stored & set(NON_COMPLIANT_PARITY_PAIRS):
            return True
    return False


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
        "paridade_preferencial": _parity_pairs_as_lists(PREFERRED_PARITY_PAIRS),
        "paridade_permitida": _parity_pairs_as_lists(ALLOWED_PARITY_PAIRS),
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

    core_numbers = _normalize_numbers(resolved_policy.get("core_numbers") or CORE_NUMBERS)
    discouraged_numbers = _normalize_numbers(
        resolved_policy.get("discouraged_numbers") or DISCOURAGED_NUMBERS
    )
    card_set = set(card_numbers)
    core_present = sorted(card_set & core_numbers)
    discouraged_present = sorted(card_set & discouraged_numbers)
    diagnostics: list[str] = []
    if len(core_present) < CORE_MIN_PRESENT:
        diagnostics.append(f"core:abaixo_minimo_{CORE_MIN_PRESENT}:{len(core_present)}")
    if len(discouraged_present) > DISCOURAGED_MAX_PRESENT:
        diagnostics.append(
            f"discouraged:acima_limite_{DISCOURAGED_MAX_PRESENT + 1}:{len(discouraged_present)}"
        )

    return {
        "approved": not violations,
        "violations": violations,
        "violated_rules": violations,
        "diagnostics": diagnostics,
        "applied_rules": list(APPLIED_RULES),
        "repeat_count": repeat_count,
        "parity": list(parity),
        "largest_sequence": largest_sequence,
        "core_present": core_present,
        "core_present_count": len(core_present),
        "discouraged_present": discouraged_present,
        "discouraged_present_count": len(discouraged_present),
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
    conformes (repetição 7–10, paridade 7/8 ou 8/7, sequência ≤ 6). Cartões não
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
    payload = normalize_structural_policy_15d_memory(dict(memory or build_structural_policy_15d_memory()))
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
        raw_stored = dict(getattr(row, "policy_applied", {}) or {})
        if raw_stored:
            stored = normalize_structural_policy_15d_memory(raw_stored)
            stored.setdefault("memory_row_id", int(getattr(row, "id", 0) or 0))
            stored.setdefault(
                "status",
                str(getattr(row, "structural_status", MEMORY_STATUS_ACTIVE) or MEMORY_STATUS_ACTIVE),
            )
            stored.setdefault("updated_at", getattr(row, "created_at", datetime.now(UTC)).isoformat())
            if memory_needs_parity_alignment(raw_stored):
                persist_structural_policy_15d_memory(db_path, stored)
            return stored
    if persist_if_missing:
        return persist_structural_policy_15d_memory(db_path)
    return build_structural_policy_15d_memory()


def ensure_structural_policy_15d_memory(db_path: Any = DEFAULT_DATABASE_PATH) -> dict[str, Any]:
    canonical = build_structural_policy_15d_memory()
    active = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)
    if active and str(active.get("policy_version") or "") == canonical["policy_version"]:
        return normalize_structural_policy_15d_memory(active)
    return persist_structural_policy_15d_memory(db_path, canonical)


def resolve_policy_compliance_label(
    compliant_count: int,
    total: int,
    violations: Sequence[str] | None,
) -> str:
    total_games = max(int(total), 0)
    compliant = max(int(compliant_count), 0)
    violation_items = [str(item).strip() for item in (violations or []) if str(item).strip()]
    if total_games == 0:
        return COMPLIANCE_LABEL_REPROVADO
    if compliant == total_games and not violation_items:
        return COMPLIANCE_LABEL_APROVADO
    if compliant == 0 or len(violation_items) >= total_games:
        return COMPLIANCE_LABEL_REPROVADO
    return COMPLIANCE_LABEL_ATENCAO


def _resolve_policy_compliance_status(compliance_label: str) -> str:
    label = str(compliance_label or "").strip().upper()
    if label == COMPLIANCE_LABEL_APROVADO:
        return "compliant"
    if label == COMPLIANCE_LABEL_REPROVADO:
        return "non_compliant"
    return "partial"


def _load_games_from_generation_event_ids(
    db_path: Any,
    generation_event_ids: Sequence[int],
) -> list[dict[str, Any]]:
    ids = sorted({int(value) for value in generation_event_ids if int(value) > 0})
    if not ids:
        return []
    games: list[dict[str, Any]] = []
    create_database(db_path)
    with get_session(db_path) as session:
        rows = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id.in_(ids))
            .order_by(GeneratedGame.generation_event_id.asc(), GeneratedGame.game_index.asc())
            .all()
        )
        for row in rows:
            context = dict(getattr(row, "context_json", {}) or {})
            numbers = list(getattr(row, "numbers", []) or context.get("final_card_numbers") or [])
            games.append(
                {
                    "numbers": numbers,
                    "final_card_numbers": list(context.get("final_card_numbers") or numbers),
                    "context_json": context,
                    "generation_event_id": int(getattr(row, "generation_event_id", 0) or 0),
                    "game_index": int(getattr(row, "game_index", 0) or 0),
                }
            )
    return games


def _resolve_previous_numbers_from_context(
    context: Mapping[str, Any] | None,
    *,
    previous_numbers: Sequence[int] | None = None,
) -> list[int]:
    if previous_numbers:
        return sorted(_normalize_numbers(previous_numbers))
    payload = dict(context or {})
    bundle = dict(payload.get("structural_policy_15d_bundle") or {})
    from_bundle = list(bundle.get("previous_contest_numbers") or [])
    if from_bundle:
        return sorted(int(number) for number in from_bundle)
    raw = payload.get("previous_contest_numbers") or payload.get("ultimo_concurso_numeros")
    if isinstance(raw, (list, tuple, set)):
        return sorted(int(number) for number in raw if 1 <= int(number) <= 25)
    history = payload.get("history") or payload.get("draw_history")
    if history:
        return resolve_previous_contest_numbers(history)
    return []


def analyze_batch_structural_policy_15d(
    games: Sequence[dict[str, Any]],
    *,
    previous_contest_numbers: Sequence[int] | None,
    policy: Mapping[str, Any] | None = None,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    resolved_policy = dict(policy or ensure_structural_policy_15d_memory(db_path))
    previous_numbers = _resolve_previous_numbers_from_context(
        {"previous_contest_numbers": list(previous_contest_numbers or [])},
        previous_numbers=previous_contest_numbers,
    )
    per_game: list[dict[str, Any]] = []
    all_violations: list[str] = []
    all_diagnostics: list[str] = []
    compliant_count = 0
    core_hits: Counter[int] = Counter()
    discouraged_hits: Counter[int] = Counter()

    for index, game in enumerate(games):
        validation = _validate_game_record(
            game,
            previous_contest_numbers=previous_numbers,
            policy=resolved_policy,
        )
        per_game.append(
            {
                "game_index": int(game.get("game_index", index) or index),
                "generation_event_id": int(game.get("generation_event_id", 0) or 0),
                "validation": validation,
            }
        )
        if validation.get("approved"):
            compliant_count += 1
        for violation in list(validation.get("violations") or []):
            all_violations.append(str(violation))
        for diagnostic in list(validation.get("diagnostics") or []):
            all_diagnostics.append(str(diagnostic))
        for number in list(validation.get("core_present") or []):
            core_hits[int(number)] += 1
        for number in list(validation.get("discouraged_present") or []):
            discouraged_hits[int(number)] += 1

    total_games = len(per_game)
    unique_violations = sorted(set(all_violations))
    unique_diagnostics = sorted(set(all_diagnostics))
    compliance_label = resolve_policy_compliance_label(
        compliant_count,
        total_games,
        unique_violations,
    )
    if unique_diagnostics and compliance_label == COMPLIANCE_LABEL_APROVADO:
        compliance_label = COMPLIANCE_LABEL_ATENCAO
    compliance_score = round(compliant_count / total_games, 4) if total_games else 0.0
    policy_compliance_status = _resolve_policy_compliance_status(compliance_label)

    return {
        "mission_id": MISSION_ID,
        "policy_version": str(resolved_policy.get("policy_version") or POLICY_VERSION),
        "structural_policy_memory_loaded": True,
        "structural_policy_version": str(resolved_policy.get("policy_version") or POLICY_VERSION),
        "structural_policy_applied": bool(previous_numbers),
        "games_total": total_games,
        "games_compliant": compliant_count,
        "games_validated": total_games,
        "compliance_score": compliance_score,
        "compliance_label": compliance_label,
        "policy_compliance_status": policy_compliance_status,
        "violations": unique_violations,
        "violated_rules": unique_violations,
        "diagnostics": unique_diagnostics,
        "policy_violations": unique_violations + unique_diagnostics,
        "core_coverage_stats": {
            "core_numbers": list(resolved_policy.get("core_numbers") or CORE_NUMBERS),
            "hits_by_number": dict(core_hits),
            "games_below_core_minimum": sum(
                1
                for row in per_game
                if int((row.get("validation") or {}).get("core_present_count", 0) or 0) < CORE_MIN_PRESENT
            ),
        },
        "discouraged_coverage_stats": {
            "discouraged_numbers": list(resolved_policy.get("discouraged_numbers") or DISCOURAGED_NUMBERS),
            "hits_by_number": dict(discouraged_hits),
            "games_above_discouraged_limit": sum(
                1
                for row in per_game
                if int((row.get("validation") or {}).get("discouraged_present_count", 0) or 0)
                > DISCOURAGED_MAX_PRESENT
            ),
        },
        "previous_contest_numbers": list(previous_numbers),
        "per_game": per_game,
        "applied_rules": list(APPLIED_RULES),
    }


def analyze_games_from_context_or_records(
    games: Sequence[dict[str, Any]] | None,
    context: Mapping[str, Any] | None,
    policy: Mapping[str, Any] | None,
    previous_numbers: Sequence[int] | None,
    *,
    db_path: Any = DEFAULT_DATABASE_PATH,
) -> dict[str, Any]:
    resolved_games = [dict(row) for row in list(games or [])]
    payload = dict(context or {})
    if not resolved_games:
        context_games = payload.get("games") or payload.get("generated_games")
        if isinstance(context_games, list):
            resolved_games = [dict(row) for row in context_games if isinstance(row, Mapping)]
    if not resolved_games:
        ge_ids = [
            int(value)
            for value in list(payload.get("generation_event_ids") or [])
            if int(value) > 0
        ]
        selected_ge = int(payload.get("selected_generation_event_id") or payload.get("generation_event_id") or 0)
        if selected_ge > 0:
            ge_ids.append(selected_ge)
        resolved_games = _load_games_from_generation_event_ids(db_path, ge_ids)
    resolved_policy = dict(policy or ensure_structural_policy_15d_memory(db_path))
    previous_contest_numbers = _resolve_previous_numbers_from_context(
        payload,
        previous_numbers=previous_numbers,
    )
    return analyze_batch_structural_policy_15d(
        resolved_games,
        previous_contest_numbers=previous_contest_numbers,
        policy=resolved_policy,
        db_path=db_path,
    )


def build_structural_policy_15d_diagnosis(analysis: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    violations = [str(item) for item in list(analysis.get("violations") or []) if str(item).strip()]
    diagnostics = [str(item) for item in list(analysis.get("diagnostics") or []) if str(item).strip()]
    compliance_label = str(analysis.get("compliance_label") or "")
    games_total = int(analysis.get("games_total", 0) or 0)
    games_compliant = int(analysis.get("games_compliant", 0) or 0)

    if violations:
        issues.append(
            {
                "issue_type": "structural_policy_15d_violation",
                "problema_detectado": "Cartões 15D fora da política estrutural soberana.",
                "evidencia": f"{len(violations)} violação(ões); conformes {games_compliant}/{games_total}.",
                "causa_provavel": "Repetição, paridade ou sequência fora dos limites institucionais.",
                "acao_recomendada": "Aplicar calibração supervisionada com penalidades de política 15D.",
                "impacto_esperado": "Elevar conformidade estrutural sem alterar Lei 15.",
                "severidade": "alta" if compliance_label == COMPLIANCE_LABEL_REPROVADO else "media",
                "violations": violations,
            }
        )
    if diagnostics:
        issues.append(
            {
                "issue_type": "structural_policy_15d_diagnostic",
                "problema_detectado": "Alertas core/discouraged na política 15D.",
                "evidencia": "; ".join(diagnostics[:6]),
                "causa_provavel": "Cobertura insuficiente de core ou excesso de dezenas desencorajadas.",
                "acao_recomendada": "Reforçar core_numbers e penalizar discouraged_numbers no rerank.",
                "impacto_esperado": "Melhorar aderência estrutural sem bloqueio soberano.",
                "severidade": "media",
                "diagnostics": diagnostics,
            }
        )
    if not issues and games_total > 0:
        issues.append(
            {
                "issue_type": "structural_policy_15d_compliant",
                "problema_detectado": "Política estrutural 15D em conformidade.",
                "evidencia": f"Conformes {games_compliant}/{games_total}.",
                "causa_provavel": "Lote alinhado à política institucional M-ML-070.",
                "acao_recomendada": "Manter monitoramento estrutural na próxima geração.",
                "impacto_esperado": "Preservar rastreabilidade e conformidade 15D.",
                "severidade": "baixa",
            }
        )
    return issues


def build_structural_policy_15d_calibration_plan(
    analysis: Mapping[str, Any],
    policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_policy = dict(policy or {})
    violations = [str(item) for item in list(analysis.get("violations") or [])]
    diagnostics = [str(item) for item in list(analysis.get("diagnostics") or [])]
    plan_items: list[str] = []
    impact_items: list[str] = []
    parametros_sugeridos: dict[str, Any] = {
        "game_size": 15,
        "formato_alvo": "15D",
        "structural_policy_15d": True,
    }

    if any("repeticao" in item for item in violations):
        plan_items.append("Ajustar repetição com último concurso para faixa 7–10 (política 15D).")
        impact_items.append("Normalizar repetição estrutural sem violar Lei 15.")
        parametros_sugeridos["repeat_penalty_boost"] = 1.15
        parametros_sugeridos["repeat_target_min"] = int(
            resolved_policy.get("repeticao_ultimo_concurso_min", 7) or 7
        )
        parametros_sugeridos["repeat_target_max"] = int(
            resolved_policy.get("repeticao_ultimo_concurso_max", 10) or 10
        )

    if any("paridade" in item for item in violations):
        plan_items.append("Penalizar paridade fora de 7/8 ou 8/7 (política 15D).")
        impact_items.append("Aproximar cartões da paridade preferencial institucional.")
        parametros_sugeridos["parity_penalty_boost"] = 1.12

    if any("sequencia" in item for item in violations):
        plan_items.append("Penalizar sequências acima do máximo 6 (política 15D).")
        impact_items.append("Reduzir sequências longas nos cartões 15D.")
        parametros_sugeridos["sequence_penalty_boost"] = 1.18
        parametros_sugeridos["sequence_max_allowed"] = int(resolved_policy.get("sequencia_maxima", 6) or 6)

    if any("core:" in item for item in diagnostics):
        plan_items.append("Reforçar core_numbers institucionais (7, 12, 16, 23).")
        impact_items.append("Elevar presença mínima de dezenas core nos cartões 15D.")
        parametros_sugeridos["core_numbers_boost"] = 1.2
        parametros_sugeridos["core_numbers"] = list(resolved_policy.get("core_numbers") or CORE_NUMBERS)

    if any("discouraged:" in item for item in diagnostics):
        plan_items.append("Penalizar discouraged_numbers acima do limite (política 15D).")
        impact_items.append("Reduzir concentração de dezenas desencorajadas.")
        parametros_sugeridos["discourage_penalty_boost"] = 1.15
        parametros_sugeridos["discouraged_numbers"] = list(
            resolved_policy.get("discouraged_numbers") or DISCOURAGED_NUMBERS
        )

    return {
        "mission_id": MISSION_ID,
        "structural_policy_15d_calibration": True,
        "plan_items": plan_items,
        "impact_items": impact_items,
        "parametros_sugeridos": parametros_sugeridos,
        "has_plan": bool(plan_items),
        "compliance_label": str(analysis.get("compliance_label") or ""),
        "policy_compliance_status": str(analysis.get("policy_compliance_status") or ""),
    }


def record_structural_policy_batch_memory(
    db_path: Any = DEFAULT_DATABASE_PATH,
    *,
    generation_event_id: int,
    batch_id: str,
    analysis: Mapping[str, Any],
    bundle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload_bundle = dict(bundle or {})
    calibration_plan = build_structural_policy_15d_calibration_plan(analysis)
    policy_payload = {
        "mission_id": MISSION_ID,
        "memory_kind": MEMORY_KIND_BATCH,
        "generation_event_id": int(generation_event_id),
        "batch_id": str(batch_id or ""),
        "policy_version": str(analysis.get("policy_version") or POLICY_VERSION),
        "compliance_label": str(analysis.get("compliance_label") or ""),
        "policy_compliance_status": str(analysis.get("policy_compliance_status") or ""),
        "compliance_score": float(analysis.get("compliance_score", 0) or 0),
        "games_total": int(analysis.get("games_total", 0) or 0),
        "games_compliant": int(analysis.get("games_compliant", 0) or 0),
        "violations": list(analysis.get("violations") or []),
        "diagnostics": list(analysis.get("diagnostics") or []),
        "suggested_actions": list(calibration_plan.get("plan_items") or []),
        "applied_actions": list(payload_bundle.get("actions_applied") or []),
        "structural_policy_applied": bool(analysis.get("structural_policy_applied")),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    merged_policy = {
        **dict(load_active_structural_policy_15d_memory(db_path, persist_if_missing=False) or {}),
        **policy_payload,
    }
    create_database(db_path)
    with get_session(db_path) as session:
        session.add(
            ScientificInstitutionalMemory(
                memory_kind=MEMORY_KIND_BATCH,
                strategy_name="15 dezenas",
                game_size=15,
                batch_id=str(batch_id or f"GE-{int(generation_event_id)}"),
                generation_range={
                    "generation_event_id": int(generation_event_id),
                    "mission_id": MISSION_ID,
                },
                total_games=int(analysis.get("games_total", 0) or 0),
                unique_games=int(analysis.get("games_compliant", 0) or 0),
                duplicate_games=max(
                    0,
                    int(analysis.get("games_total", 0) or 0) - int(analysis.get("games_compliant", 0) or 0),
                ),
                structural_status=str(analysis.get("compliance_label") or MEMORY_STATUS_ACTIVE),
                scientific_status=str(analysis.get("policy_compliance_status") or MEMORY_STATUS_ACTIVE),
                scientific_classification="STRUCTURAL_POLICY_15D_BATCH",
                main_reason=MEMORY_REASON,
                recommended_action="structural_policy_15d_batch_trace",
                policy_applied=merged_policy,
                policy_before={},
                policy_after=merged_policy,
                decision_mode="INSTITUCIONAL",
                approved_for_use=1,
                notes=str(analysis.get("compliance_label") or EXPECTED_IMPACT),
                source=MISSION_ID,
            )
        )
        session.commit()
    return policy_payload


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
            "compliance_label": str(bundle.get("compliance_label") or ""),
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
            "structural_policy_applied": bool(payload.get("structural_policy_applied")),
            "applied_rules": list(payload.get("applied_rules") or []),
            "violated_rules": list(payload.get("violated_rules") or []),
            "policy_violations": list(payload.get("policy_violations") or payload.get("violated_rules") or []),
            "policy_compliance_status": str(payload.get("policy_compliance_status") or ""),
            "compliance_label": str(payload.get("compliance_label") or ""),
            "games_validated": int(payload.get("games_validated", 0) or 0),
            "games_compliant": int(payload.get("games_compliant", 0) or 0),
        }
    return {"available": False}
