from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RFEValidationResult:
    approved: bool
    blocked_reasons: list[str]
    repeated_from_previous: int | None
    empty_rows: list[int]
    empty_columns: list[int]


LOTOFACIL_ROWS: dict[int, set[int]] = {
    1: {1, 2, 3, 4, 5},
    2: {6, 7, 8, 9, 10},
    3: {11, 12, 13, 14, 15},
    4: {16, 17, 18, 19, 20},
    5: {21, 22, 23, 24, 25},
}

LOTOFACIL_COLUMNS: dict[int, set[int]] = {
    1: {1, 6, 11, 16, 21},
    2: {2, 7, 12, 17, 22},
    3: {3, 8, 13, 18, 23},
    4: {4, 9, 14, 19, 24},
    5: {5, 10, 15, 20, 25},
}


def normalize_numbers(numbers: Iterable[int]) -> set[int]:
    normalized: set[int] = set()
    for number in numbers or []:
        try:
            value = int(number)
        except (TypeError, ValueError):
            continue
        if 1 <= value <= 25:
            normalized.add(value)
    return normalized


def validate_rfe_final_card(
    final_card_numbers: Iterable[int],
    previous_contest_numbers: Iterable[int] | None,
) -> RFEValidationResult:
    """
    Valida o cartão final conforme RFE-01 e RFE-02.

    Esta função não gera dezenas, não altera Lei 15, não altera reservas
    e não altera Lei 16. Ela apenas aprova ou reprova estruturalmente
    um cartão final já composto.
    """
    final_numbers = normalize_numbers(final_card_numbers)
    previous_numbers = normalize_numbers(previous_contest_numbers or [])

    blocked_reasons: list[str] = []
    repeated_from_previous: int | None = None

    if previous_numbers:
        repeated_from_previous = len(final_numbers.intersection(previous_numbers))
        if repeated_from_previous < 7 or repeated_from_previous > 10:
            blocked_reasons.append(
                f"RFE-01: repetição com concurso anterior fora da faixa 7-10 ({repeated_from_previous})."
            )
    else:
        blocked_reasons.append("RFE-01: concurso anterior indisponível para validação estrutural.")

    empty_rows = [
        row_index
        for row_index, row_numbers in LOTOFACIL_ROWS.items()
        if not final_numbers.intersection(row_numbers)
    ]

    empty_columns = [
        column_index
        for column_index, column_numbers in LOTOFACIL_COLUMNS.items()
        if not final_numbers.intersection(column_numbers)
    ]

    if empty_rows:
        blocked_reasons.append(f"RFE-02: linha(s) zerada(s): {', '.join(map(str, empty_rows))}.")

    if empty_columns:
        blocked_reasons.append(f"RFE-02: coluna(s) zerada(s): {', '.join(map(str, empty_columns))}.")

    return RFEValidationResult(
        approved=not blocked_reasons,
        blocked_reasons=blocked_reasons,
        repeated_from_previous=repeated_from_previous,
        empty_rows=empty_rows,
        empty_columns=empty_columns,
    )
