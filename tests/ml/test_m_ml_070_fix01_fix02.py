"""M-ML-070-FIX-01 / FIX-02 — gate por formato e paridade soberana 15D."""

from __future__ import annotations

import inspect
from itertools import combinations
from pathlib import Path

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.structural_policy_15d import (
    ALLOWED_PARITY_PAIRS,
    NON_CONFORMING_PARITY_PAIRS,
    PREFERRED_PARITY_PAIRS,
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_memory,
    is_structural_policy_15d_format,
    persist_structural_policy_15d_memory,
    resolve_sovereign_game_size,
    validate_game_structural_policy_15d,
)
from lotoia.generator.basic_generator import generate_best_games


def _previous_numbers() -> list[int]:
    return list(range(1, 16))


def _compliant_numbers() -> list[int]:
    """Cartão 15D conforme: repetição 7, paridade 8/7, sequência máx. 5."""
    return [1, 3, 4, 7, 10, 12, 13, 16, 17, 18, 19, 20, 22, 23, 25]


def _non_compliant_numbers() -> list[int]:
    """Cartão 15D com paridade 6/9 e repetição fora da faixa."""
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 18, 20, 22]


def _parity_96_numbers() -> list[int]:
    """15 dezenas com paridade 9/6."""
    return [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17]


def _distinct_compliant_games(count: int) -> list[list[int]]:
    """Gera `count` cartões 15D distintos e conformes vs. concurso anterior 1–15."""
    previous = _previous_numbers()
    prev_pick = (1, 3, 4, 7, 10, 12, 13)
    new_pool = list(range(16, 26))
    games: list[list[int]] = []
    for combo in combinations(new_pool, 8):
        numbers = sorted(list(prev_pick) + list(combo))
        result = validate_game_structural_policy_15d(
            numbers,
            previous_contest_numbers=previous,
        )
        if result["approved"]:
            games.append(numbers)
        if len(games) >= count:
            break
    if len(games) < count:
        raise RuntimeError(f"expected {count} distinct compliant games, got {len(games)}")
    return games


def test_build_marker_v60() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v60"


def test_memory_parity_without_69_permitida(tmp_path: Path) -> None:
    memory = build_structural_policy_15d_memory()
    assert memory["paridade_permitida"] == [[7, 8], [8, 7]]
    assert (6, 9) not in {tuple(pair) for pair in memory["paridade_permitida"]}
    assert memory["paridade_nao_conforme"] == [[6, 9], [9, 6]]
    db_path = tmp_path / "policy.db"
    persisted = persist_structural_policy_15d_memory(db_path)
    assert persisted["paridade_permitida"] == [[7, 8], [8, 7]]


def test_parity_69_and_96_are_violations() -> None:
    previous = _previous_numbers()
    for numbers in (_non_compliant_numbers(), _parity_96_numbers()):
        result = validate_game_structural_policy_15d(
            numbers,
            previous_contest_numbers=previous,
        )
        assert result["approved"] is False
        assert any("paridade" in violation for violation in result["violations"])


def test_resolve_sovereign_game_size_gp20_not_game_count() -> None:
    games = [{"numbers": _compliant_numbers(), "final_card_numbers": _compliant_numbers()} for _ in range(20)]
    assert resolve_sovereign_game_size(games, requested_count=20) == 15
    assert is_structural_policy_15d_format(resolve_sovereign_game_size(games, requested_count=20))


def test_gate_by_format_not_quantity_in_basic_generator() -> None:
    source = inspect.getsource(generate_best_games)
    assert "count == 15" not in source
    assert "resolve_sovereign_game_size" in source
    assert "is_structural_policy_15d_format" in source


def test_gp20_governs_compliant_first(tmp_path: Path) -> None:
    db_path = tmp_path / "gov.db"
    previous = _previous_numbers()
    compliant = {
        "numbers": _compliant_numbers(),
        "final_card_numbers": _compliant_numbers(),
        "profile_score": 5.0,
        "final_score": {"final_score": 99.0},
    }
    non_compliant = {
        "numbers": _non_compliant_numbers(),
        "final_card_numbers": _non_compliant_numbers(),
        "profile_score": 10.0,
        "final_score": {"final_score": 100.0},
    }
    pool = [non_compliant, compliant]
    games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        [non_compliant],
        pool_games=pool,
        history=[{"numbers": previous}],
        required_count=1,
        game_size=15,
        db_path=db_path,
    )
    assert bundle["structural_policy_applied"] is True
    assert bundle["required_count"] == 1
    assert bundle["game_size"] == 15
    assert games[0]["structural_policy_15d_validation"]["approved"] is True
    assert bundle["lote_alterado"] is True
    assert bundle["compliance_rate"] == 1.0


def test_gp20_bundle_structural_policy_applied_true(tmp_path: Path) -> None:
    db_path = tmp_path / "gp20.db"
    previous = _previous_numbers()
    distinct_cards = _distinct_compliant_games(25)
    selected = [
        {
            "numbers": distinct_cards[index],
            "final_card_numbers": distinct_cards[index],
            "profile_score": float(index),
        }
        for index in range(3)
    ]
    pool = [
        {
            "numbers": numbers,
            "final_card_numbers": numbers,
            "profile_score": float(index),
        }
        for index, numbers in enumerate(distinct_cards)
    ]
    games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=pool,
        history=[{"numbers": previous}],
        required_count=20,
        game_size=15,
        db_path=db_path,
    )
    assert len(games) == 20
    assert bundle["structural_policy_applied"] is True
    assert bundle["structural_policy_memory_loaded"] is True
    assert bundle["structural_policy_version"] == "M-ML-070-v1"
    assert bundle["games_compliant"] == 20
    assert bundle["games_non_compliant"] == 0
    assert bundle["structural_policy_application_mode"] == "compliant_pool_governance"


def test_coverage_ui_shows_conforme_not_permitida_69() -> None:
    import dashboard.institutional_structural_policy_coverage as coverage

    source = inspect.getsource(coverage.render_structural_policy_15d_operational_block)
    assert "Paridade conforme" in source
    assert "Paridade não conforme" in source
    assert "Paridade permitida" not in source


def test_central_ml_ui_parity_alignment() -> None:
    import dashboard.institutional_ml_calibration_cockpit as cockpit

    source = inspect.getsource(cockpit._render_structural_policy_15d_card)
    assert "Paridade conforme" in source
    assert "Paridade não conforme" in source
    assert "Paridade permitida" not in source


def test_verdict_uses_policy_compliance() -> None:
    from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict

    payload = evaluate_ml_operational_verdict(
        {
            "policy_compliance_status": "non_compliant",
            "policy_compliance_label": "REPROVADO",
            "policy_violations": ["paridade:fora_preferencial_7_8:6_9"],
            "formatos_analisados": [15],
        }
    )
    assert "structural_policy" in str(payload.get("trace", {}).get("rule_triggers", payload))


def test_allowed_parity_constants_fix02() -> None:
    assert ALLOWED_PARITY_PAIRS == PREFERRED_PARITY_PAIRS
    assert NON_CONFORMING_PARITY_PAIRS == ((6, 9), (9, 6))
