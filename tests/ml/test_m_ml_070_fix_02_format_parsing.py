"""M-ML-070-FIX-02 — Central ML normaliza formato 15D sem quebrar.

Garante que o parsing de formato vindo de snapshot/context_json/UI nunca usa
``int(formatos[0])`` direto e tolera valores como "15D"/"15d" e inválidos.
"""

from __future__ import annotations

import pytest

from lotoia.ml.structural_policy_15d import is_structural_policy_15d_format
from lotoia.observability.coverage_evidence_interpreter import (
    _normalize_format_size,
    _normalize_format_sizes,
    build_calibration_plan,
    interpret_coverage_evidence,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (15, 15),
        ("15", 15),
        ("15D", 15),
        ("15d", 15),
        (" 15 ", 15),
        ("15 dezenas", 15),
        (16, 16),
        ("23D", 23),
        (15.0, 15),
    ],
)
def test_normalize_format_size_valid(value, expected) -> None:
    assert _normalize_format_size(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "abc", "D15", None, 0, -5, True, False, "Dezenas", [], {}],
)
def test_normalize_format_size_invalid_returns_none(value) -> None:
    assert _normalize_format_size(value) is None


def test_normalize_format_sizes_filters_invalid() -> None:
    assert _normalize_format_sizes(["15D", "abc", None, "16", 17]) == [15, 16, 17]
    assert _normalize_format_sizes("15D") == []  # não-lista → vazio, sem quebrar
    assert _normalize_format_sizes(None) == []


def test_15d_recognized_after_normalization() -> None:
    assert is_structural_policy_15d_format(_normalize_format_size("15D")) is True
    assert is_structural_policy_15d_format(_normalize_format_size("16D")) is False


# --------------------------------------------------------------------------- #
# Central ML não quebra com formato "15D" (caminho que usava int(formatos[0]))
# --------------------------------------------------------------------------- #
def test_build_calibration_plan_handles_15d_string() -> None:
    plan = build_calibration_plan({"formatos_analisados": ["15D"], "total_jogos": 20})
    assert isinstance(plan, dict)


def test_interpret_coverage_evidence_handles_15d_string() -> None:
    result = interpret_coverage_evidence({"formatos_analisados": ["15D"], "total_jogos": 20})
    assert isinstance(result, dict)


def test_interpret_coverage_evidence_handles_invalid_formats() -> None:
    # Formatos inválidos não podem quebrar a tela.
    result = interpret_coverage_evidence({"formatos_analisados": ["abc", None], "total_jogos": 5})
    assert isinstance(result, dict)


def test_build_calibration_plan_handles_15d_lowercase_and_invalid_mix() -> None:
    plan = build_calibration_plan({"formatos_analisados": ["15d"]})
    assert isinstance(plan, dict)
    plan_invalid = build_calibration_plan({"formatos_analisados": ["xx", "15D"]})
    assert isinstance(plan_invalid, dict)
