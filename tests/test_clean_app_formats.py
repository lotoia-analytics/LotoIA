import pytest

from dashboard.clean_core import _expand_official_card, _expand_generation_games_for_format


def test_expand_official_card_15_keeps_core() -> None:
    core, reserves, final_card = _expand_official_card([1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7], 15)
    assert len(core) == 15
    assert reserves == []
    assert final_card == sorted(core)


def test_expand_official_card_17_adds_two_reserves() -> None:
    core, reserves, final_card = _expand_official_card([1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7], 17)
    assert len(core) == 15
    assert len(reserves) == 2
    assert len(final_card) == 17
    assert set(core).issubset(final_card)


def test_expand_official_card_18_adds_three_reserves() -> None:
    core, reserves, final_card = _expand_official_card([1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7], 18)
    assert len(core) == 15
    assert len(reserves) == 3
    assert len(final_card) == 18
    assert set(core).issubset(final_card)


def test_expand_generation_games_for_format_adds_display_fields() -> None:
    games = [{"numbers": [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]}]
    expanded = _expand_generation_games_for_format(games, 17)
    assert expanded[0]["card_format"] == 17
    assert len(expanded[0]["core_numbers"]) == 15
    assert len(expanded[0]["audited_reserve_numbers"]) == 2
    assert len(expanded[0]["final_card_numbers"]) == 17


@pytest.mark.parametrize(
    ("card_format", "expected_reserves"),
    [(16, 1), (17, 2), (18, 3), (19, 4), (20, 5), (21, 6), (22, 7), (23, 8)],
)
def test_expand_official_card_supports_16_to_23(card_format: int, expected_reserves: int) -> None:
    core, reserves, final_card = _expand_official_card(
        [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7],
        card_format,
    )

    assert len(core) == 15
    assert len(reserves) == expected_reserves
    assert len(final_card) == card_format
    assert set(core).issubset(final_card)
    assert not set(core).intersection(reserves)
