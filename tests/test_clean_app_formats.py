import pytest

from dashboard.clean_core import _expand_official_card, _expand_generation_games_for_format
from dashboard.institutional_app import build_institutional_matrix_rows, infer_matrix_cell


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


def test_infer_matrix_cell_labels_15d_top20() -> None:
    inferred = infer_matrix_cell(15, 20)

    assert inferred["celula_matriz"] == "15D Top 20"
    assert inferred["formato_d"] == "15D"
    assert inferred["escala_top"] == "Top 20"
    assert inferred["dezenas_por_jogo"] == 15
    assert inferred["quantidade_jogos"] == 20


def test_build_institutional_matrix_rows_marks_15d_institutional_reading() -> None:
    games = [
        {
            "jogo": 1,
            "numbers": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25],
            "final_card_numbers": [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25],
        }
    ]

    rows = build_institutional_matrix_rows(games, 15, 20)

    assert len(rows) == 1
    row = rows[0]
    assert row["jogo"] == 1
    assert row["celula_matriz"] == "15D Top 20"
    assert row["formato_d"] == "15D"
    assert row["escala_top"] == "Top 20"
    assert row["nucleo_a_dezenas"] == "01 03 05 07 08 09 10 14 15 17 21 22 23 24 25"
    assert row["referencias_auditadas_j12_j34"] == "01 03 05 07 08 09 10 14 15 22 23 24 25"
    assert row["vigilancia_j71"] == "01 03 05 07 08 09 10 15 22 23 24"
    assert row["status_institucional"] == "NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA"
    assert "15D" in row["leitura_institucional"]
    assert "leitura institucional" in row["leitura_institucional"]


def test_build_institutional_matrix_rows_marks_16d_with_institutional_refs() -> None:
    games = [
        {
            "jogo": 2,
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25, 9],
            "final_card_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25, 9],
        }
    ]

    rows = build_institutional_matrix_rows(games, 16, 20)

    assert len(rows) == 1
    row = rows[0]
    assert row["formato_d"] == "16D"
    assert row["escala_top"] == "Top 20"
    assert row["celula_matriz"] == "16D Top 20"
    assert row["status_institucional"] == "NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA"
    assert row["referencias_auditadas_j12_j34"] == "01 02 03 05 07 08 09 10 11 13 14 15 18 22 24 25"
    assert row["vigilancia_j71"] == "01 02 03 05 07 08 09 10 13 15 18 22 24"
    assert "15 + reservas auditadas" in row["leitura_institucional"]


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
