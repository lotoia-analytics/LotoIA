"""M-ML-079 — reconciliação validador structural_policy_15d com CORE_002 soberano."""

from __future__ import annotations

from typing import Any

import pytest

from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15a_operational import NUCLEO_LEI15_15D_CONGELADO, build_lei15a_operational_read
from lotoia.ml.structural_policy_15d import (
    COMPLIANCE_LABEL_APROVADO,
    POLICY_VERSION,
    analyze_batch_structural_policy_15d,
    build_structural_policy_15d_memory,
    validate_game_structural_policy_15d,
)
from lotoia.ml.structural_pool_15d_generator import (
    MIN_POOL_COMPLIANCE_RATE,
    _generate_compliant_card,
    build_ml_structural_15d_pool,
)
from lotoia.generator.basic_generator import _attach_scores, _build_game
from dataclasses import dataclass
from random import Random


@dataclass
class _Draw:
    numbers: list[int]


PREVIOUS = list(range(1, 16))

# CORE_002-style: sem dezenas do núcleo antigo (7, 12, 16, 23), repetição/paridade/sequência OK.
NO_CORE_CARD = [1, 2, 3, 5, 6, 9, 10, 11, 13, 14, 17, 18, 19, 20, 22]

# CORE_002-style: 6 discouraged (2, 4, 11, 15, 24, 25), repetição/paridade/sequência OK.
MANY_DISCOURAGED_CARD = [1, 2, 3, 4, 9, 10, 11, 13, 14, 15, 18, 20, 22, 24, 25]


def _game(numbers: list[int]) -> dict[str, Any]:
    return {"numbers": numbers, "final_card_numbers": numbers}


@pytest.fixture(autouse=True)
def _enable_structural_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_STRUCTURAL_15D_POOL_ENABLED", "1")


def test_core002_game_without_core_numbers_is_approved() -> None:
    result = validate_game_structural_policy_15d(
        NO_CORE_CARD,
        previous_contest_numbers=PREVIOUS,
    )
    assert result["approved"] is True
    assert not result["violations"]
    assert result["core_present_count"] == 0
    assert any("core:" in item for item in result["diagnostics"])


def test_core002_game_with_many_discouraged_is_approved() -> None:
    result = validate_game_structural_policy_15d(
        MANY_DISCOURAGED_CARD,
        previous_contest_numbers=PREVIOUS,
    )
    assert result["approved"] is True
    assert not result["violations"]
    assert result["discouraged_present_count"] >= 4
    assert any("discouraged:" in item for item in result["diagnostics"])


def test_traceability_fields_remain_on_validation() -> None:
    result = validate_game_structural_policy_15d(
        MANY_DISCOURAGED_CARD,
        previous_contest_numbers=PREVIOUS,
    )
    for key in (
        "core_present",
        "core_present_count",
        "discouraged_present",
        "discouraged_present_count",
        "diagnostics",
    ):
        assert key in result


def test_batch_compliance_rate_at_least_90_for_ten_core002_style_games() -> None:
    policy = build_structural_policy_15d_memory()
    rng = Random(79)
    games: list[dict[str, Any]] = []
    previous = set(PREVIOUS)
    for _ in range(40):
        card = _generate_compliant_card(rng, previous, policy=policy)
        if not card:
            continue
        game = _build_game(card)
        _attach_scores(game, history=[_Draw(PREVIOUS)], profile_type="recorrente")
        games.append(game)
        if len(games) >= 10:
            break
    assert len(games) >= 10

    analysis = analyze_batch_structural_policy_15d(
        games[:10],
        previous_contest_numbers=PREVIOUS,
        policy=policy,
    )
    assert analysis["compliance_score"] >= MIN_POOL_COMPLIANCE_RATE
    assert analysis["compliance_label"] == COMPLIANCE_LABEL_APROVADO
    assert not any("core:" in item for item in analysis.get("policy_violations") or [])
    assert not any("discouraged:" in item for item in analysis.get("policy_violations") or [])


def test_pool_builder_compliance_rate_restored() -> None:
    policy = build_structural_policy_15d_memory()
    rng = Random(790)
    raw_pool: list[dict[str, Any]] = []
    previous = set(PREVIOUS)
    for _ in range(30):
        card = _generate_compliant_card(rng, previous, policy=policy)
        if not card:
            continue
        game = _build_game(card)
        _attach_scores(game, history=[_Draw(PREVIOUS)], profile_type="recorrente")
        raw_pool.append(game)
    assert len(raw_pool) >= 10

    pool, bundle = build_ml_structural_15d_pool(
        raw_pool,
        history=[_Draw(PREVIOUS)],
        min_compliant=10,
        seed=79,
        policy=policy,
    )
    assert bundle["compliance_rate"] >= MIN_POOL_COMPLIANCE_RATE
    assert len(pool) >= 10


def test_nucleo_congelado_is_informational_not_validation_gate() -> None:
    read = build_lei15a_operational_read(
        cartao_final_lei15=NO_CORE_CARD,
        formato_d=17,
    )
    assert read["nucleo_operacional_gp"] == list(NUCLEO_LEI15_15D_CONGELADO)
    assert read["auditadas"]
    validation = validate_game_structural_policy_15d(
        NO_CORE_CARD,
        previous_contest_numbers=PREVIOUS,
    )
    assert validation["approved"] is True


def test_policy_version_errata_m_ml_079() -> None:
    assert POLICY_VERSION == "M-ML-079-v1"
    assert BUILD_MARKER == "institutional-adm-runtime-v95"
