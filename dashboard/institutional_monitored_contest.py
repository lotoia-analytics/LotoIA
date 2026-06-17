"""Card operacional — último concurso monitorado (M-DADOS-048)."""

from __future__ import annotations

import os
from typing import Any, Callable

MISSION_ID = "M-DADOS-048"

SOVEREIGN_SOURCE_LABEL = "PostgreSQL / imported_contests"

ENV_OPERATOR_EXPECTED_CONTEST = "LOTOIA_OPERATOR_EXPECTED_CONTEST"

PLAUSIBILITY_GAP_ABOVE_EXPECTED = 50

OUTLIER_ARTIFACT_TEMPLATE = (
    "Concursos ignorados como artefato/outlier em imported_contests: {excluded}."
)

SYNC_DIVERGENCE_TEMPLATE = (
    "Base oficial PostgreSQL desatualizada — último concurso persistido: {persisted}, "
    "esperado pelo operador: {expected}."
)

NUMBERS_MISMATCH_TEMPLATE = (
    "Divergência de dezenas no concurso {contest}: persistido difere do resultado "
    "oficial informado pelo operador."
)

VALID_LOTOFACIL_DEZENAS_COUNT = 15

HISTORY_SOURCE_DIVERGENCE_TEMPLATE = (
    "lotofacil_official_history diverge de imported_contests — "
    "history_max={history_max}, imported_max={imported_max}. UI usa imported_contests."
)

INVALID_CONTEST_SESSION_RESET_TEMPLATE = (
    "Concurso {invalid} ignorado — inválido ou ausente em imported_contests. "
    "Selecionado: {selected}."
)


def resolve_operator_expected_contest() -> int | None:
    raw = str(os.getenv(ENV_OPERATOR_EXPECTED_CONTEST, "") or "").strip()
    if not raw.isdigit():
        return None
    value = int(raw)
    return value if value > 0 else None


def normalize_contest_numbers(numbers: Any) -> list[int]:
    if not isinstance(numbers, (list, tuple)):
        return []
    normalized: list[int] = []
    for value in numbers:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25:
            normalized.append(number)
    return sorted(normalized)


def contest_numbers_match(record: dict[str, Any] | None, expected_numbers: list[int] | tuple[int, ...]) -> bool:
    if not record:
        return False
    persisted = normalize_contest_numbers(record.get("dezenas") or [])
    expected = normalize_contest_numbers(list(expected_numbers))
    return bool(persisted) and persisted == expected


def is_valid_lotofacil_contest_record(record: dict[str, Any] | None) -> bool:
    numbers = normalize_contest_numbers((record or {}).get("dezenas") or [])
    return len(numbers) == VALID_LOTOFACIL_DEZENAS_COUNT and len(set(numbers)) == VALID_LOTOFACIL_DEZENAS_COUNT


def filter_plausible_contest_records(
    records: list[dict[str, Any]],
    *,
    operator_expected_contest: int | None = None,
) -> tuple[list[dict[str, Any]], list[int], str | None]:
    """Remove artefatos de teste/outlier sem hardcode — acima do cluster operacional real."""
    valid_records = [record for record in records if is_valid_lotofacil_contest_record(record)]
    contest_numbers = sorted(int(record["contest_number"]) for record in valid_records)
    if not contest_numbers:
        return [], [], None

    expected = operator_expected_contest if operator_expected_contest is not None else resolve_operator_expected_contest()
    excluded: list[int] = []
    plausible_numbers = list(contest_numbers)

    if expected:
        plausible_numbers = [number for number in contest_numbers if number <= expected + PLAUSIBILITY_GAP_ABOVE_EXPECTED]
        excluded = [number for number in contest_numbers if number not in plausible_numbers]
    elif len(contest_numbers) >= 2:
        anchor = contest_numbers[-2]
        threshold = anchor + max(100, int(anchor * 0.05))
        plausible_numbers = [number for number in contest_numbers if number <= threshold]
        excluded = [number for number in contest_numbers if number not in plausible_numbers]

    plausible_records = [
        record for record in valid_records if int(record["contest_number"]) in plausible_numbers
    ]
    outlier_message = (
        OUTLIER_ARTIFACT_TEMPLATE.format(excluded=", ".join(str(number) for number in excluded))
        if excluded
        else None
    )
    return plausible_records, sorted(plausible_numbers), outlier_message


def to_conference_contest_payload(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not is_valid_lotofacil_contest_record(record):
        return None
    contest_number = int((record or {}).get("contest_number", 0) or 0)
    if contest_number <= 0:
        return None
    numbers = normalize_contest_numbers(record.get("dezenas") or [])
    return {
        "contest_number": contest_number,
        "concurso": contest_number,
        "data": str(record.get("data") or ""),
        "dezenas": numbers,
        "source": SOVEREIGN_SOURCE_LABEL,
        "official_contest_source": SOVEREIGN_SOURCE_LABEL,
    }


def build_imported_contests_selection_context(
    *,
    list_imported_contest_records: Callable[[], list[dict[str, Any]]],
    load_imported_contest: Callable[[int], dict[str, Any] | None],
    operator_expected_contest: int | None = None,
    official_history_max: int | None = None,
) -> dict[str, Any]:
    """Seleção operacional de concurso — apenas imported_contests válidos (15D)."""
    expected = operator_expected_contest if operator_expected_contest is not None else resolve_operator_expected_contest()
    all_records = list_imported_contest_records()
    valid_records, valid_numbers, outlier_message = filter_plausible_contest_records(
        all_records,
        operator_expected_contest=expected,
    )
    raw_valid_numbers = sorted(
        int(record["contest_number"])
        for record in all_records
        if is_valid_lotofacil_contest_record(record)
    )
    monitored = build_monitored_contest_card(
        load_latest_imported_contest=lambda: valid_records[-1] if valid_records else None,
        load_imported_contest=load_imported_contest,
        operator_expected_contest=expected,
    )
    default_contest = int(monitored.get("contest_number") or (valid_numbers[-1] if valid_numbers else 0) or 0)
    imported_max = valid_numbers[-1] if valid_numbers else 0
    raw_imported_max = raw_valid_numbers[-1] if raw_valid_numbers else 0
    history_divergence_message = ""
    if official_history_max is not None and int(official_history_max) > 0:
        if not imported_max or int(official_history_max) != int(imported_max):
            history_divergence_message = HISTORY_SOURCE_DIVERGENCE_TEMPLATE.format(
                history_max=int(official_history_max),
                imported_max=int(imported_max or 0),
            )
    return {
        **monitored,
        "valid_contest_numbers": valid_numbers,
        "valid_records": valid_records,
        "min_contest": valid_numbers[0] if valid_numbers else 0,
        "max_contest": imported_max,
        "default_contest": default_contest,
        "official_history_max": official_history_max,
        "raw_imported_max": raw_imported_max,
        "history_divergence_message": history_divergence_message,
        "outlier_message": outlier_message,
    }


def sanitize_conference_session_contest(
    *,
    session_contest: int | None,
    valid_contest_numbers: list[int],
    default_contest: int,
) -> tuple[int, str | None]:
    if not valid_contest_numbers:
        return 0, None
    if session_contest in valid_contest_numbers:
        return int(session_contest), None
    selected = default_contest if default_contest in valid_contest_numbers else valid_contest_numbers[-1]
    if session_contest and int(session_contest) > 0:
        return selected, INVALID_CONTEST_SESSION_RESET_TEMPLATE.format(
            invalid=int(session_contest),
            selected=selected,
        )
    return selected, None


def build_monitored_contest_card(
    *,
    load_latest_imported_contest: Callable[[], dict[str, Any] | None],
    load_imported_contest: Callable[[int], dict[str, Any] | None],
    operator_expected_contest: int | None = None,
) -> dict[str, Any]:
    """Monta payload do card a partir exclusivamente de imported_contests (PostgreSQL)."""
    latest_record = load_latest_imported_contest()
    persisted_number = int(latest_record.get("contest_number", 0) or 0) if latest_record else 0
    expected = operator_expected_contest if operator_expected_contest is not None else resolve_operator_expected_contest()

    if persisted_number <= 0:
        payload: dict[str, Any] = {
            "mission_id": MISSION_ID,
            "contest_number": None,
            "display_contest_number": "—",
            "source": SOVEREIGN_SOURCE_LABEL,
            "sync_status": "EMPTY",
            "sync_message": "Nenhum concurso persistido em imported_contests.",
            "draw_date": "",
            "numbers": [],
            "operator_expected_contest": expected,
            "numbers_match_expected": False,
        }
        if expected:
            payload["sync_status"] = "SYNC_DIVERGENCE"
            payload["sync_message"] = SYNC_DIVERGENCE_TEMPLATE.format(persisted="-", expected=expected)
        return payload

    sync_status = "OK"
    sync_message = ""
    if expected and persisted_number != expected:
        sync_status = "SYNC_DIVERGENCE"
        sync_message = SYNC_DIVERGENCE_TEMPLATE.format(persisted=persisted_number, expected=expected)

    expected_record = load_imported_contest(expected) if expected else None
    numbers_match_expected = bool(expected_record) and persisted_number == expected

    return {
        "mission_id": MISSION_ID,
        "contest_number": persisted_number,
        "display_contest_number": str(persisted_number),
        "source": SOVEREIGN_SOURCE_LABEL,
        "sync_status": sync_status,
        "sync_message": sync_message,
        "draw_date": str(latest_record.get("data") or ""),
        "numbers": normalize_contest_numbers(latest_record.get("dezenas") or []),
        "operator_expected_contest": expected,
        "operator_expected_record": expected_record,
        "numbers_match_expected": numbers_match_expected,
        "latest_record": latest_record,
    }


def validate_expected_contest_numbers(
    card: dict[str, Any],
    *,
    expected_numbers: list[int] | tuple[int, ...],
) -> dict[str, Any]:
    """Validação auxiliar — expected_numbers pertence aos testes/operador, não ao runtime."""
    expected_contest = card.get("operator_expected_contest")
    record = card.get("operator_expected_record")
    if not expected_contest or not record:
        return {
            **card,
            "numbers_validation_status": "SKIPPED",
            "numbers_validation_message": "",
        }
    if contest_numbers_match(record, expected_numbers):
        return {
            **card,
            "numbers_validation_status": "OK",
            "numbers_validation_message": "",
        }
    return {
        **card,
        "numbers_validation_status": "MISMATCH",
        "numbers_validation_message": NUMBERS_MISMATCH_TEMPLATE.format(contest=expected_contest),
    }
