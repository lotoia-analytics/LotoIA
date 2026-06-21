"""M-SANITY-001 — Filtro de Soberania Oficial (tolerância zero)."""

from __future__ import annotations

import logging

import pytest

from lotoia.generation.structural_sovereignty_validator import (
    MISSION_ID,
    apply_structural_sovereignty_to_gp,
    build_official_structural_baseline,
    validate_structural_sovereignty,
)
from lotoia.statistics.card_structure import format_dezena_group, compute_prefix

LOGGER_NAME = "lotoia.generation.structural_sovereignty_validator"


def _official_cards_without_prefix(prefix: str) -> list[list[int]]:
    """Histórico sintético sem o prefixo alvo (freq oficial zero para o padrão)."""
    cards = [
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17],
        [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        [1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    ]
    target = str(prefix)
    return [
        card
        for card in cards
        if format_dezena_group(compute_prefix(card, 3)) != target
    ]


def test_validate_rejects_prefix_with_zero_official_frequency() -> None:
    target_prefix = "01-04-07"
    invalid_game = {
        "numbers": [1, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "final_card_numbers": [1, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    }
    assert format_dezena_group(compute_prefix(invalid_game["numbers"], 3)) == target_prefix

    result = validate_structural_sovereignty(invalid_game, [])
    assert result.get("valid") is False
    assert result.get("mission_id") == MISSION_ID
    assert any(v.get("kind") == "prefix_3" for v in list(result.get("violations") or []))


def test_validate_accepts_prefix_with_known_historical_frequency() -> None:
    """01-04-05 tem freq histórica M-CORE-003 > 0 — não é vazio estatístico."""
    known_prefix_game = {
        "numbers": [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 22, 23, 24, 25],
        "final_card_numbers": [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 22, 23, 24, 25],
    }
    assert format_dezena_group(compute_prefix(known_prefix_game["numbers"], 3)) == "01-04-05"

    result = validate_structural_sovereignty(known_prefix_game, [])
    assert result.get("valid") is True


def test_validate_accepts_historically_compatible_game() -> None:
    official_history = _official_cards_without_prefix("01-04-05")
    baseline = build_official_structural_baseline(official_history)
    valid_game = {
        "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "final_card_numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    }
    result = validate_structural_sovereignty(valid_game, baseline)
    assert result.get("valid") is True


def test_apply_structural_sovereignty_filters_and_replaces(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER_NAME)
    official_history = _official_cards_without_prefix("01-04-05")
    invalid = {
        "numbers": [1, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "profile_score": 10.0,
        "final_score": {"final_score": 1.0},
    }
    replacement = {
        "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "profile_score": 8.0,
        "final_score": {"final_score": 1.0},
    }
    gp, bundle = apply_structural_sovereignty_to_gp(
        [invalid],
        [replacement],
        1,
        official_history,
    )
    assert len(gp) == 1
    assert gp[0]["numbers"] == replacement["numbers"]
    assert int(bundle.get("discarded_count", 0) or 0) == 1
    assert "[LEI15_SANITY]" in caplog.text
    assert "Prefixo: 01-04-07" in caplog.text


def test_compose_sovereign_gp_applies_sanity_filter() -> None:
    from lotoia.generation.lei15_core_002 import compose_sovereign_gp
    from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, get_core_002_config

    official_history = _official_cards_without_prefix("01-04-05")
    invalid = {
        "numbers": [1, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
        "profile_score": 10.0,
        "final_score": {"final_score": 1.0},
        "prefix_signature": "01-04-05",
        "suffix_signature": "23-24-25",
    }
    valid = {
        "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "profile_score": 9.0,
        "final_score": {"final_score": 1.0},
        "prefix_signature": "01-02-03",
        "suffix_signature": "23-24-25",
    }
    cfg = get_core_002_config(BATCH_LABEL)
    gp = compose_sovereign_gp(
        [invalid, valid],
        1,
        cfg,
        game_size=15,
        official_history=official_history,
    )
    assert len(gp) == 1
    assert gp[0]["numbers"] == valid["numbers"]
