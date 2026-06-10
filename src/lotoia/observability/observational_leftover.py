"""Cálculo observacional pós-conferência de dezenas sobrando (sem impacto em geração/conferência)."""

from __future__ import annotations

from typing import Any, Sequence

REAL_LEFTOVER_BASIS = "cartao_final_minus_resultado_oficial"
OBSERVATIONAL_SOURCE_CARTAO_FINAL = "cartao_final"
ML_ROLE_DIAGNOSTIC_ONLY = "diagnostic_only"
FORBIDDEN_OBSERVATIONAL_SOURCES = frozenset(
    {
        "nucleo_lei_15",
        "nucleo_lei_15a_congelado",
        "núcleo_lei_15",
        "nucleo",
        "nucleo_operacional_gp",
        "base_core",
    }
)


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


def compute_dezenas_acertadas(
    cartao_final: Sequence[int | str],
    resultado_oficial: Sequence[int | str],
) -> list[int]:
    card = set(normalize_dezenas(cartao_final))
    official = set(normalize_dezenas(resultado_oficial))
    return sorted(card & official)


def compute_dezenas_sobrando(
    cartao_final: Sequence[int | str],
    resultado_oficial: Sequence[int | str],
) -> list[int]:
    """dezenas_sobrando = sort(set(cartao_final) - set(resultado_oficial))."""
    card = set(normalize_dezenas(cartao_final))
    official = set(normalize_dezenas(resultado_oficial))
    return sorted(card - official)


def compute_dezenas_faltando(
    cartao_final: Sequence[int | str],
    resultado_oficial: Sequence[int | str],
) -> list[int]:
    card = set(normalize_dezenas(cartao_final))
    official = set(normalize_dezenas(resultado_oficial))
    return sorted(official - card)


def format_dezenas(numbers: Sequence[int]) -> str:
    return " ".join(f"{int(number):02d}" for number in numbers) or "-"


def validate_observational_source(origem_observacional: str | None) -> list[str]:
    errors: list[str] = []
    normalized = str(origem_observacional or "").strip().lower()
    if normalized in {item.lower() for item in FORBIDDEN_OBSERVATIONAL_SOURCES}:
        errors.append(f"origem_observacional_forbidden:{normalized}")
    return errors


def validate_real_leftover_guards(
    *,
    cartao_final: Sequence[int | str],
    resultado_oficial: Sequence[int | str],
    concurso_analisado: int | None,
    generation_event_id: int | None,
    origem_observacional: str | None = OBSERVATIONAL_SOURCE_CARTAO_FINAL,
) -> list[str]:
    errors: list[str] = []
    if not normalize_dezenas(cartao_final):
        errors.append("cartao_final_missing")
    if not normalize_dezenas(resultado_oficial):
        errors.append("resultado_oficial_missing")
    if concurso_analisado is None or int(concurso_analisado) <= 0:
        errors.append("concurso_analisado_missing")
    if generation_event_id is None or int(generation_event_id) <= 0:
        errors.append("generation_event_id_missing")
    if str(origem_observacional or "").strip() != OBSERVATIONAL_SOURCE_CARTAO_FINAL:
        errors.append("origem_observacional_invalid")
    errors.extend(validate_observational_source(origem_observacional))
    return errors


def build_real_post_conference_leftover_payload(
    *,
    cartao_final: Sequence[int | str],
    resultado_oficial: Sequence[int | str],
) -> dict[str, Any]:
    cartao_norm = normalize_dezenas(cartao_final)
    resultado_norm = normalize_dezenas(resultado_oficial)
    acertadas = compute_dezenas_acertadas(cartao_norm, resultado_norm)
    sobrando = compute_dezenas_sobrando(cartao_norm, resultado_norm)
    faltando = compute_dezenas_faltando(cartao_norm, resultado_norm)
    return {
        "origem_observacional": OBSERVATIONAL_SOURCE_CARTAO_FINAL,
        "dezenas_observadas": cartao_norm,
        "cartao_final": cartao_norm,
        "cartao_referencia": resultado_norm,
        "resultado_oficial": resultado_norm,
        "dezenas_acertadas": acertadas,
        "dezenas_sobrando": sobrando,
        "dezenas_faltando": faltando,
        "dezenas_sobrando_count": len(sobrando),
        "leftover_basis": REAL_LEFTOVER_BASIS,
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
    }
