from __future__ import annotations

from lotoia.governance.structural_rfe import validate_rfe_final_card


def test_rfe_01_accepts_7_repeated_numbers() -> None:
    final_card = [1, 2, 3, 4, 5, 6, 11, 16, 17, 18, 19, 20, 21, 22, 23]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is True
    assert result.repeated_from_previous == 7


def test_rfe_01_accepts_10_repeated_numbers() -> None:
    final_card = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 16, 17, 18, 21, 22]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is True
    assert result.repeated_from_previous == 10


def test_rfe_01_blocks_less_than_7_repeated_numbers() -> None:
    final_card = [1, 2, 3, 4, 5, 6, 16, 17, 18, 19, 20, 21, 22, 23, 24]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is False
    assert result.repeated_from_previous == 6
    assert any("RFE-01" in reason for reason in result.blocked_reasons)


def test_rfe_01_blocks_more_than_10_repeated_numbers() -> None:
    final_card = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 21, 22]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is False
    assert result.repeated_from_previous == 11
    assert any("RFE-01" in reason for reason in result.blocked_reasons)


def test_rfe_02_blocks_empty_row() -> None:
    final_card = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 21, 22]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is False
    assert 3 in result.empty_rows
    assert any("RFE-02" in reason for reason in result.blocked_reasons)


def test_rfe_02_blocks_empty_column() -> None:
    final_card = [1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 13, 15, 16, 17, 18]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card, previous)

    assert result.approved is False
    assert 4 in result.empty_columns
    assert any("RFE-02" in reason for reason in result.blocked_reasons)


def test_rfe_validates_final_card_with_reserves() -> None:
    final_card_17d = [1, 2, 3, 4, 5, 6, 7, 11, 16, 17, 18, 19, 20, 21, 22, 23, 24]
    previous = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    result = validate_rfe_final_card(final_card_17d, previous)

    assert result.approved is True
    assert result.repeated_from_previous == 8
