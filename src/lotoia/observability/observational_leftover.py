"""Cálculo observacional de dezenas sobrando (sem impacto em geração/conferência)."""

from __future__ import annotations

from typing import Any, Sequence

LEFTOVER_BASIS = "observadas_minus_cartao_final_conferido"


def normalize_dezenas(values: Sequence[int | str] | None) -> list[int]:
    if not values:
        return []
    normalized: list[int] = []
    for value in values:
        if isinstance(value, int):
            if 1 <= value <= 25:
                normalized.append(int(value))
            continue
        text = str(value or "").strip()
        if not text or text == "-":
            continue
        for token in text.replace(",", " ").split():
            cleaned = token.strip().lstrip("+")
            if cleaned.isdigit():
                number = int(cleaned)
                if 1 <= number <= 25:
                    normalized.append(number)
    return sorted(set(normalized))


def compute_dezenas_sobrando(
    observadas: Sequence[int | str],
    cartao_referencia: Sequence[int | str],
) -> list[int]:
    """dezenas_sobrando = sort(set(observadas) - set(cartao_referencia))."""
    observed = set(normalize_dezenas(observadas))
    reference = set(normalize_dezenas(cartao_referencia))
    return sorted(observed - reference)


def format_dezenas(numbers: Sequence[int]) -> str:
    return " ".join(f"{int(number):02d}" for number in numbers) or "-"


def build_observational_leftover_payload(
    *,
    observadas: Sequence[int | str],
    cartao_referencia: Sequence[int | str],
) -> dict[str, Any]:
    observadas_norm = normalize_dezenas(observadas)
    cartao_norm = normalize_dezenas(cartao_referencia)
    leftovers = compute_dezenas_sobrando(observadas_norm, cartao_norm)
    return {
        "dezenas_observadas": observadas_norm,
        "cartao_referencia": cartao_norm,
        "dezenas_sobrando": leftovers,
        "dezenas_sobrando_count": len(leftovers),
        "leftover_basis": LEFTOVER_BASIS,
    }
