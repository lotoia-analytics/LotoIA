import pytest

from dashboard.clean_core import _expand_official_card, _expand_generation_games_for_format
from dashboard.institutional_app import (
    INSTITUTIONAL_MATRIX_PRIMARY_LABELS,
    INSTITUTIONAL_MATRIX_TECHNICAL_LABELS,
    LEI15A_NUCLEO_15D_CONGELADO,
    NUCLEO_LEI15A_15D_CONGELADO,
    RESERVAS_PRIORITARIAS_LEI15A,
    build_institutional_matrix_primary_view,
    build_institutional_matrix_rows,
    build_institutional_matrix_technical_view,
    infer_matrix_cell,
    summarize_institutional_matrix_reading,
)

LEI15A_NUCLEO_FORMATTED = " ".join(f"{number:02d}" for number in LEI15A_NUCLEO_15D_CONGELADO)


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
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    games = [
        {
            "jogo": 1,
            "numbers": final_card,
            "final_card_numbers": final_card,
        }
    ]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=[final_card])

    assert len(rows) == 1
    row = rows[0]
    assert row["jogo"] == 1
    assert row["celula_matriz"] == "15D Top 20"
    assert row["formato_d"] == "15D"
    assert row["escala_top"] == "Top 20"
    assert row["cartao_final_lido"] == LEI15A_NUCLEO_FORMATTED
    assert row["cartao_final_assinatura"] == "01-02-03-04-09-10-11-12-13-18-20-22-23-24-25"
    assert row["nucleo_a_dezenas"] == LEI15A_NUCLEO_FORMATTED
    assert row["referencias_auditadas_j12_j34"] == "01 02 03 09 10 11 13 18 20 22 23 24 25"
    assert row["vigilancia_j71"] == "01 02 03 09 10 13 18 20 22 23 24"
    assert row["lei15_aplicada"] is True
    assert row["sincronizado_com_cartao_final"] is True
    assert row["status_institucional"] == "SINCRONIZADO_COM_CARTAO_FINAL"
    assert row["status_estrutural_anterior"] == "NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA"
    assert "15D" in row["leitura_institucional"]
    assert "núcleo Lei 15A congelado" in row["leitura_institucional"]


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
    assert row["status_institucional"] == "SINCRONIZADO_COM_CARTAO_FINAL"
    assert row["status_estrutural_anterior"] == "NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA"
    assert row["referencias_auditadas_j12_j34"] == "01 02 03 05 07 08 09 10 11 13 14 15 18 22 24 25"
    assert row["vigilancia_j71"] == "01 02 03 05 07 08 09 10 13 15 18 22 24"
    assert row["sincronizado_com_cartao_final"] is True
    assert "cartão_final lido e sincronizado com a saída superior" in row["leitura_institucional"]


def test_build_institutional_matrix_rows_marks_final_card_mismatch() -> None:
    games = [
        {
            "jogo": 1,
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25],
            "final_card_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25],
        }
    ]
    divergent_superior_card = [[1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 21, 22, 24]]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=divergent_superior_card)

    assert rows[0]["sincronizado_com_cartao_final"] is True
    assert rows[0]["status_institucional"] == "SINCRONIZADO_COM_CARTAO_FINAL"
    assert rows[0]["cartao_final_lido"] == LEI15A_NUCLEO_FORMATTED
    assert "núcleo Lei 15A congelado" in rows[0]["leitura_institucional"]


def test_build_institutional_matrix_rows_reads_superior_final_card_not_core_only() -> None:
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    expanded_final = sorted(core + [2, 4])
    games = [{"jogo": 1, "numbers": core, "final_card_numbers": expanded_final}]

    rows = build_institutional_matrix_rows(games, 17, 20, superior_final_cards=[expanded_final])

    assert rows[0]["cartao_final_lido"] == " ".join(f"{number:02d}" for number in expanded_final)
    assert rows[0]["nucleo_a_dezenas"] == LEI15A_NUCLEO_FORMATTED
    assert rows[0]["sincronizado_com_cartao_final"] is True


def test_build_institutional_matrix_rows_syncs_20_rows_with_upper_final_cards() -> None:
    games = []
    superior_cards = []
    for index in range(20):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        games.append({"jogo": index + 1, "numbers": core, "final_card_numbers": core})
        superior_cards.append(core)

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=superior_cards)

    assert len(rows) == 20
    assert all(row["jogo"] == index + 1 for index, row in enumerate(rows))
    assert all(row["cartao_final_lido"] == LEI15A_NUCLEO_FORMATTED for row in rows)
    assert all(row["sincronizado_com_cartao_final"] is True for row in rows)
    assert all(row["status_institucional"] == "SINCRONIZADO_COM_CARTAO_FINAL" for row in rows)


def test_institutional_matrix_primary_view_keeps_only_human_readable_columns() -> None:
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    rows = build_institutional_matrix_rows(
        [{"jogo": 1, "numbers": final_card, "final_card_numbers": final_card}],
        15,
        10,
        superior_final_cards=[final_card],
    )

    primary_df = build_institutional_matrix_primary_view(rows)

    assert list(primary_df.columns) == list(INSTITUTIONAL_MATRIX_PRIMARY_LABELS.values())
    assert INSTITUTIONAL_MATRIX_PRIMARY_LABELS["nucleo_a_dezenas"] == "Núcleo Operacional GP"
    assert "Núcleo Lei 15" not in INSTITUTIONAL_MATRIX_PRIMARY_LABELS.values()
    assert "Célula matriz" not in primary_df.columns
    assert primary_df.iloc[0]["Cartão final"] == LEI15A_NUCLEO_FORMATTED
    assert primary_df.iloc[0]["Núcleo Operacional GP"] == LEI15A_NUCLEO_FORMATTED
    assert bool(primary_df.iloc[0]["Sincronizado"]) is True


def test_institutional_matrix_technical_view_preserves_full_trace() -> None:
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    rows = build_institutional_matrix_rows(
        [{"jogo": 1, "numbers": final_card, "final_card_numbers": final_card}],
        15,
        10,
        superior_final_cards=[final_card],
    )

    technical_df = build_institutional_matrix_technical_view(rows)

    assert list(technical_df.columns) == list(INSTITUTIONAL_MATRIX_TECHNICAL_LABELS.values())
    assert technical_df.iloc[0]["Assinatura do cartão final"] == "01-02-03-04-09-10-11-12-13-18-20-22-23-24-25"
    assert technical_df.iloc[0]["Célula matriz"] == "15D Top 10"


def test_institutional_matrix_summary_reports_synchronized_17d_batch() -> None:
    games = []
    superior_cards = []
    for index in range(10):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        _, _, expanded = _expand_official_card(core, 17, game_index=index + 1)
        games.append({"jogo": index + 1, "numbers": core, "final_card_numbers": expanded})
        superior_cards.append(expanded)

    rows = build_institutional_matrix_rows(games, 17, 10, superior_final_cards=superior_cards)
    sync_checks = [
        {
            "jogo": index + 1,
            "cartao_final_superior": " ".join(f"{number:02d}" for number in superior_cards[index]),
            "cartao_final_lido": row["cartao_final_lido"],
            "sincronizado": row["cartao_final_lido"]
            == " ".join(f"{number:02d}" for number in superior_cards[index]),
        }
        for index, row in enumerate(rows)
    ]

    summary = summarize_institutional_matrix_reading(rows, sync_checks=sync_checks, card_format=17)

    assert summary["total_games"] == 10
    assert summary["synchronized_count"] == 10
    assert summary["failure_count"] == 0
    assert summary["card_format"] == 17
    assert summary["overall_status"] == "LEITURA SINCRONIZADA"
    assert summary["institutional_caption_status"] == (
        "LEITURA_INSTITUCIONAL_PADRONIZADA_E_SINCRONIZADA_COM_CARTAO_FINAL"
    )


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


def test_build_institutional_matrix_rows_15d_auditadas_vigilantes_empty() -> None:
    """Para 15D, auditadas_escolhidas e vigilantes_escolhidas devem ser '-'"""
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    games = [
        {
            "jogo": 1,
            "numbers": final_card,
            "final_card_numbers": final_card,
        }
    ]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=[final_card])

    assert len(rows) == 1
    row = rows[0]
    assert row["formato_d"] == "15D"
    assert row["cartao_final_lido"] == LEI15A_NUCLEO_FORMATTED
    assert row["auditadas_escolhidas"] == "-"
    assert row["vigilantes_escolhidas"] == "-"


def test_build_institutional_matrix_rows_17d_auditadas_equals_final_minus_lei15a_nucleo() -> None:
    """Para 17D, auditadas_escolhidas = cartao_final - núcleo Lei 15A congelado."""
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    _, reserves, final_card = _expand_official_card(core, 17, game_index=1)

    games = [
        {
            "jogo": 1,
            "numbers": core,
            "final_card_numbers": final_card,
        }
    ]

    rows = build_institutional_matrix_rows(games, 17, 20, superior_final_cards=[final_card])

    assert len(rows) == 1
    row = rows[0]
    assert row["formato_d"] == "17D"
    assert row["nucleo_a_dezenas"] == LEI15A_NUCLEO_FORMATTED

    auditadas_str = row["auditadas_escolhidas"]
    auditadas_numbers = [int(x) for x in auditadas_str.split()] if auditadas_str != "-" else []
    expected_auditadas = sorted(set(final_card) - set(LEI15A_NUCLEO_15D_CONGELADO))

    assert auditadas_numbers == expected_auditadas


def test_build_institutional_matrix_rows_auditadas_equals_final_minus_nucleo() -> None:
    """Verifica que auditadas_escolhidas = cartao_final - nucleo_lei_15"""
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    _, reserves, final_card = _expand_official_card(core, 17, game_index=1)
    
    games = [
        {
            "jogo": 1,
            "numbers": core,
            "final_card_numbers": final_card,
            "core_numbers": sorted(core),
        }
    ]

    rows = build_institutional_matrix_rows(games, 17, 20, superior_final_cards=[final_card])

    assert len(rows) == 1
    row = rows[0]
    
    # Converte strings para conjuntos de números
    nucleo_str = row["nucleo_a_dezenas"]
    nucleo = set(int(x) for x in nucleo_str.split()) if nucleo_str != "-" else set()
    
    cartao_str = row["cartao_final_lido"]
    cartao = set(int(x) for x in cartao_str.split()) if cartao_str != "-" else set()
    
    auditadas_str = row["auditadas_escolhidas"]
    auditadas = set(int(x) for x in auditadas_str.split()) if auditadas_str != "-" else set()
    
    # Verifica que auditadas = cartao - nucleo
    expected_auditadas = cartao - nucleo
    assert auditadas == expected_auditadas, f"Expected {expected_auditadas}, got {auditadas}"


def test_build_institutional_matrix_rows_vigilantes_escolhidas_intersection() -> None:
    """Verifica que vigilantes_escolhidas = auditadas_escolhidas ∩ reservas_prioritarias Lei 15A."""
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    _, reserves, final_card = _expand_official_card(core, 17, game_index=1)

    games = [
        {
            "jogo": 1,
            "numbers": core,
            "final_card_numbers": final_card,
            "core_numbers": sorted(core),
        }
    ]

    rows = build_institutional_matrix_rows(games, 17, 20, superior_final_cards=[final_card])

    assert len(rows) == 1
    row = rows[0]

    auditadas_str = row["auditadas_escolhidas"]
    auditadas = set(int(x) for x in auditadas_str.split()) if auditadas_str != "-" else set()

    vigilantes_str = row["vigilantes_escolhidas"]
    vigilantes = set(int(x) for x in vigilantes_str.split()) if vigilantes_str != "-" else set()

    reservas_set = set(RESERVAS_PRIORITARIAS_LEI15A)

    expected_vigilantes = auditadas.intersection(reservas_set)
    assert vigilantes == expected_vigilantes, f"Expected {expected_vigilantes}, got {vigilantes}"


def test_lower_band_does_not_mirror_generation_core_numbers() -> None:
    """Faixa inferior não deve espelhar core_numbers da geração quando divergem do núcleo Lei 15A."""
    generation_core = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    generation_formatted = " ".join(f"{number:02d}" for number in generation_core)
    games = [
        {
            "jogo": 1,
            "numbers": generation_core,
            "final_card_numbers": generation_core,
            "core_numbers": generation_core,
        }
    ]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=[generation_core])

    assert rows[0]["nucleo_a_dezenas"] == LEI15A_NUCLEO_FORMATTED
    assert rows[0]["nucleo_a_dezenas"] != generation_formatted
    assert rows[0]["cartao_final_lido"] == LEI15A_NUCLEO_FORMATTED
    assert set(NUCLEO_LEI15A_15D_CONGELADO) == set(LEI15A_NUCLEO_15D_CONGELADO)

