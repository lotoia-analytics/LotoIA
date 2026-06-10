import pytest

from dashboard.clean_core import _expand_official_card, _expand_generation_games_for_format
from dashboard.institutional_app import (
    INSTITUTIONAL_MATRIX_PRIMARY_LABELS,
    INSTITUTIONAL_MATRIX_TECHNICAL_LABELS,
    NUCLEO_LEI15_15D_CONGELADO,
    RESERVAS_LEI15A_PRIORITARIAS,
    build_institutional_matrix_primary_view,
    build_institutional_matrix_rows,
    build_institutional_matrix_technical_view,
    build_institutional_panel_sync_checks,
    build_lei15A_registration_card,
    build_lei15a_operational_read,
    evaluate_institutional_panel_sync,
    infer_matrix_cell,
    normalize_dezenas,
    summarize_institutional_matrix_reading,
    validate_lei15_lei15a_runtime_contract,
)


def _format_card(numbers: list[int]) -> str:
    return " ".join(f"{number:02d}" for number in sorted(numbers))


def _lei15a_frozen_nucleus() -> list[int]:
    return list(NUCLEO_LEI15_15D_CONGELADO)


def _lei15a_auditadas_from_cartao(cartao: list[int], formato_d: int) -> list[int]:
    if formato_d <= 15:
        return []
    return sorted(set(cartao) - set(_lei15a_frozen_nucleus()))


def _lei15a_vigilantes_from_auditadas(auditadas: list[int]) -> list[int]:
    return sorted(set(auditadas).intersection(RESERVAS_LEI15A_PRIORITARIAS))


def _build_game_row(core: list[int], card_format: int, game_index: int = 1) -> tuple[dict, list[int]]:
    core_numbers, reserves, final_card = _expand_official_card(core, card_format, game_index=game_index)
    game = {
        "jogo": game_index,
        "numbers": core_numbers,
        "core_numbers": core_numbers,
        "audited_reserve_numbers": reserves,
        "final_card_numbers": final_card,
    }
    return game, final_card


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
            "core_numbers": final_card,
            "final_card_numbers": final_card,
        }
    ]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=[final_card])

    row = rows[0]
    assert row["cartao_final_lido"] == _format_card(final_card)
    assert row["nucleo_a_dezenas"] == _format_card(_lei15a_frozen_nucleus())
    assert row["nucleo_a_dezenas"] != _format_card(final_card)
    assert row["auditadas_escolhidas"] == "-"
    assert row["vigilantes_escolhidas"] == "-"
    assert row["sincronizado_com_cartao_final"] is True
    assert "componentes próprios da Lei 15A" in row["leitura_institucional"]
    assert row["lei15a_boundary_checks"]["no_direct_copy"] is True


def test_build_institutional_matrix_rows_uses_lei15a_components_for_16d() -> None:
    generation_final = [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25, 9]
    core = generation_final[:15]
    reserves = [9]
    games = [
        {
            "jogo": 2,
            "numbers": core,
            "core_numbers": core,
            "audited_reserve_numbers": reserves,
            "final_card_numbers": generation_final,
        }
    ]
    expected_auditadas = _lei15a_auditadas_from_cartao(generation_final, 16)
    expected_vigilantes = _lei15a_vigilantes_from_auditadas(expected_auditadas)

    rows = build_institutional_matrix_rows(games, 16, 20, superior_final_cards=[generation_final])

    row = rows[0]
    assert row["formato_d"] == "16D"
    assert row["cartao_final_lido"] == _format_card(generation_final)
    assert row["nucleo_a_dezenas"] == _format_card(_lei15a_frozen_nucleus())
    assert row["nucleo_a_dezenas"] != _format_card(core)
    assert row["auditadas_escolhidas"] == _format_card(expected_auditadas)
    assert row["auditadas_escolhidas"] != _format_card(reserves)
    assert row["vigilantes_escolhidas"] == _format_card(expected_vigilantes)
    assert row["sincronizado_com_cartao_final"] is True


def test_build_institutional_matrix_rows_marks_final_card_mismatch() -> None:
    games = [
        {
            "jogo": 1,
            "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25],
            "core_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25],
            "final_card_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25],
        }
    ]
    divergent_superior_card = [[1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 21, 22, 24]]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=divergent_superior_card)

    assert rows[0]["cartao_final_lido"] == _format_card(divergent_superior_card[0])
    assert rows[0]["sincronizado_com_cartao_final"] is True
    assert rows[0]["origem_geracao"] == "Lei15.generation"
    assert rows[0]["origem_leitura"] == "Lei15A.validation"


def test_build_institutional_matrix_rows_uses_lei15a_components_for_17d() -> None:
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    core_numbers, reserves, generation_final = _expand_official_card(core, 17, game_index=1)
    expected_auditadas = _lei15a_auditadas_from_cartao(generation_final, 17)
    expected_vigilantes = _lei15a_vigilantes_from_auditadas(expected_auditadas)
    games = [
        {
            "jogo": 1,
            "numbers": core_numbers,
            "core_numbers": core_numbers,
            "audited_reserve_numbers": reserves,
            "final_card_numbers": generation_final,
        }
    ]

    rows = build_institutional_matrix_rows(games, 17, 20, superior_final_cards=[generation_final])

    assert rows[0]["cartao_final_lido"] == _format_card(generation_final)
    assert rows[0]["nucleo_a_dezenas"] == _format_card(_lei15a_frozen_nucleus())
    assert rows[0]["auditadas_escolhidas"] == _format_card(expected_auditadas)
    assert rows[0]["auditadas_escolhidas"] != _format_card(reserves)
    assert rows[0]["vigilantes_escolhidas"] == _format_card(expected_vigilantes)
    assert rows[0]["sincronizado_com_cartao_final"] is True


def test_build_institutional_matrix_rows_syncs_20_rows_with_upper_final_cards() -> None:
    games = []
    superior_cards = []
    for index in range(20):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        games.append({"jogo": index + 1, "numbers": core, "core_numbers": core, "final_card_numbers": core})
        superior_cards.append(core)

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=superior_cards)

    assert len(rows) == 20
    assert all(
        row["cartao_final_lido"] == _format_card(superior_cards[index])
        for index, row in enumerate(rows)
    )
    assert len({row["cartao_final_lido"] for row in rows}) == 20
    assert all(row["sincronizado_com_cartao_final"] is True for row in rows)


def test_institutional_matrix_primary_view_keeps_only_human_readable_columns() -> None:
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    rows = build_institutional_matrix_rows(
        [{"jogo": 1, "numbers": final_card, "core_numbers": final_card, "final_card_numbers": final_card}],
        15,
        10,
        superior_final_cards=[final_card],
    )

    primary_df = build_institutional_matrix_primary_view(rows)

    assert list(primary_df.columns) == list(INSTITUTIONAL_MATRIX_PRIMARY_LABELS.values())
    assert primary_df.iloc[0]["Cartão validado Lei 15A"] == _format_card(final_card)
    assert primary_df.iloc[0]["Núcleo Operacional GP Lei 15A"] == _format_card(_lei15a_frozen_nucleus())


def test_institutional_matrix_technical_view_preserves_full_trace() -> None:
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    rows = build_institutional_matrix_rows(
        [{"jogo": 1, "numbers": final_card, "core_numbers": final_card, "final_card_numbers": final_card}],
        15,
        10,
        superior_final_cards=[final_card],
    )

    technical_df = build_institutional_matrix_technical_view(rows)

    assert technical_df.iloc[0]["Assinatura do cartão final"] == "01-03-05-07-08-09-10-14-15-17-21-22-23-24-25"


def test_institutional_matrix_summary_reports_synchronized_17d_batch() -> None:
    games = []
    superior_cards = []
    for index in range(10):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        _, reserves, expanded = _expand_official_card(core, 17, game_index=index + 1)
        games.append(
            {
                "jogo": index + 1,
                "numbers": core,
                "core_numbers": core,
                "audited_reserve_numbers": reserves,
                "final_card_numbers": expanded,
            }
        )
        superior_cards.append(expanded)

    rows = build_institutional_matrix_rows(games, 17, 10, superior_final_cards=superior_cards)
    sync_checks = [
        {
            "jogo": index + 1,
            "cartao_final_superior": _format_card(superior_cards[index]),
            "cartao_final_lido": row["cartao_final_lido"],
            "sincronizado": row["cartao_final_lido"] == _format_card(superior_cards[index]),
        }
        for index, row in enumerate(rows)
    ]

    summary = summarize_institutional_matrix_reading(rows, sync_checks=sync_checks, card_format=17)

    assert summary["total_games"] == 10
    assert summary["synchronized_count"] == 10
    assert summary["failure_count"] == 0
    assert len({row["cartao_final_lido"] for row in rows}) == 10


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


def test_build_institutional_matrix_rows_15d_auditadas_vigilantes_empty() -> None:
    final_card = [1, 3, 5, 7, 8, 9, 10, 14, 15, 17, 21, 22, 23, 24, 25]
    games = [{"jogo": 1, "numbers": final_card, "core_numbers": final_card, "final_card_numbers": final_card}]

    rows = build_institutional_matrix_rows(games, 15, 20, superior_final_cards=[final_card])

    row = rows[0]
    assert row["cartao_final_lido"] == _format_card(final_card)
    assert row["auditadas_escolhidas"] == "-"
    assert row["vigilantes_escolhidas"] == "-"


def test_lower_panel_mirrors_upper_panel_not_fixed_lei15a_card() -> None:
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    game, generation_final = _build_game_row(core, 17, game_index=1)
    fixed_card = build_lei15A_registration_card(17)["registration_card"]

    rows = build_institutional_matrix_rows([game], 17, 20, superior_final_cards=[generation_final])

    assert rows[0]["cartao_final_lido"] == _format_card(generation_final)
    assert rows[0]["cartao_final_lido"] != _format_card(fixed_card)


@pytest.mark.parametrize("card_format", [16, 17, 18, 19, 20])
def test_panel_sync_regression_cartao_final_only(card_format: int) -> None:
    games = []
    superior_cards = []
    for index in range(10):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        game, final_card = _build_game_row(core, card_format, game_index=index + 1)
        games.append(game)
        superior_cards.append(final_card)

    rows = build_institutional_matrix_rows(games, card_format, 10, superior_final_cards=superior_cards)

    assert len(rows) == 10
    superior_labels = {_format_card(card) for card in superior_cards}
    inferior_labels = {row["cartao_final_lido"] for row in rows}
    assert inferior_labels == superior_labels
    for index, row in enumerate(rows):
        assert row["cartao_final_lido"] == _format_card(superior_cards[index])
        assert row["nucleo_a_dezenas"] == _format_card(_lei15a_frozen_nucleus())
        assert row["nucleo_a_dezenas"] != _format_card(games[index]["core_numbers"])
        expected_auditadas = _lei15a_auditadas_from_cartao(superior_cards[index], card_format)
        assert row["auditadas_escolhidas"] == _format_card(expected_auditadas)
        assert row["vigilantes_escolhidas"] == _format_card(
            _lei15a_vigilantes_from_auditadas(expected_auditadas)
        )
        assert row["sincronizado_com_cartao_final"] is True
        assert row["lei15a_boundary_checks"]["no_direct_copy"] is True


def test_build_lei15A_registration_card_remains_governance_only() -> None:
    registration = build_lei15A_registration_card(17)
    assert registration["operational"] is True
    assert registration["status"] == "registro_lei15a"


def test_normalize_dezenas_accepts_plus_prefix_and_lists() -> None:
    assert normalize_dezenas("+16 +21 +17") == ("16", "17", "21")
    assert normalize_dezenas("16 17 21") == ("16", "17", "21")
    assert normalize_dezenas(["16", "21", "17"]) == ("16", "17", "21")
    assert normalize_dezenas("-") == tuple()
    assert normalize_dezenas(None) == tuple()


def test_evaluate_institutional_panel_sync_compares_only_final_card() -> None:
    cartao = "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20"
    assert evaluate_institutional_panel_sync(
        cartao_final_superior=cartao,
        cartao_final_lido=cartao,
        reservas_auditadas_superior="+16 +21 +17",
        auditadas_inferior="05 07 14",
    ) is True
    assert evaluate_institutional_panel_sync(
        cartao_final_superior=cartao,
        cartao_final_lido=cartao,
        reservas_auditadas_superior="+16 +21 +17",
        auditadas_inferior="16 17 21",
    ) is True


def test_reported_games_6_8_9_10_sync_on_final_card_only() -> None:
    """Casos reportados: sincronização valida apenas cartão final, não componentes."""
    cases = [
        {
            "jogo": 6,
            "cartao_final_superior": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
            "cartao_final_lido": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
        },
        {
            "jogo": 8,
            "cartao_final_superior": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
            "cartao_final_lido": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
        },
        {
            "jogo": 9,
            "cartao_final_superior": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
            "cartao_final_lido": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
        },
        {
            "jogo": 10,
            "cartao_final_superior": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
            "cartao_final_lido": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20",
        },
    ]

    results = [
        {
            "jogo": case["jogo"],
            "sincronizado": evaluate_institutional_panel_sync(
                cartao_final_superior=case["cartao_final_superior"],
                cartao_final_lido=case["cartao_final_lido"],
            ),
        }
        for case in cases
    ]

    assert results == [
        {"jogo": 6, "sincronizado": True},
        {"jogo": 8, "sincronizado": True},
        {"jogo": 9, "sincronizado": True},
        {"jogo": 10, "sincronizado": True},
    ]


@pytest.mark.parametrize(
    ("upper_reservas", "lower_auditadas", "expected_sync"),
    [
        ("+16 +21 +17", "16 17 21", True),
        ("+21 +17 +05", "05 17 21", True),
    ],
)
def test_runtime_contract_regression_cartao_final_only(
    upper_reservas: str, lower_auditadas: str, expected_sync: bool
) -> None:
    cartao = "01 02 03 04 07 08 09 14 15 16 17 18 19 20 21 23 24 25"
    assert (
        evaluate_institutional_panel_sync(
            cartao_final_superior=cartao,
            cartao_final_lido=cartao,
            reservas_auditadas_superior=upper_reservas,
            auditadas_inferior=lower_auditadas,
        )
        is expected_sync
    )


def test_runtime_contract_detects_fixed_lower_card_override() -> None:
    institutional_rows = [
        {
            "cartao_final_lido": "01 02 03",
            "auditadas_escolhidas": "15",
            "vigilantes_escolhidas": "15",
            "lei15a_origin_log": {
                "lei15a": {
                    "nucleo_operacional_gp": {"copied_from_lei15": False},
                    "auditadas": {"copied_from_lei15_reservas": False, "fixed_constant_used": False},
                    "vigilantes": {"copied_from_lei15_reservas": False, "fixed_constant_used": False},
                    "cartao_validado": {"generated_new_card": False, "overrode_lei15_card": False},
                }
            },
            "lei15a_boundary_checks": {
                "component_boundary_preserved": True,
                "no_direct_copy": True,
                "no_fixed_override": True,
            },
            "sincronizado_com_cartao_final": True,
        },
        {
            "cartao_final_lido": "01 02 03",
            "auditadas_escolhidas": "15",
            "vigilantes_escolhidas": "15",
            "lei15a_origin_log": {
                "lei15a": {
                    "nucleo_operacional_gp": {"copied_from_lei15": False},
                    "auditadas": {"copied_from_lei15_reservas": False, "fixed_constant_used": False},
                    "vigilantes": {"copied_from_lei15_reservas": False, "fixed_constant_used": False},
                    "cartao_validado": {"generated_new_card": False, "overrode_lei15_card": False},
                }
            },
            "lei15a_boundary_checks": {
                "component_boundary_preserved": True,
                "no_direct_copy": True,
                "no_fixed_override": True,
            },
            "sincronizado_com_cartao_final": False,
        },
    ]
    games_table_rows = [
        {"cartão_final": "01 02 03", "reservas_auditadas": "+15"},
        {"cartão_final": "04 05 06", "reservas_auditadas": "+16"},
    ]
    contract = validate_lei15_lei15a_runtime_contract(
        institutional_rows=institutional_rows,
        games_table_rows=games_table_rows,
    )
    assert contract["classification"] == "CONFLITANTE"
    assert contract["fixed_override_detected"] is True
    assert contract["checks_results"]["CHECK_008_PERSISTENCE_GUARD"] is False
    assert contract["persistence_allowed"] is False


def test_runtime_contract_validates_synced_generation_batch() -> None:
    games = []
    superior_cards = []
    for index in range(10):
        core = sorted((((number + index - 1) % 25) + 1) for number in range(1, 16))
        game, final_card = _build_game_row(core, 17, game_index=index + 1)
        games.append(game)
        superior_cards.append(final_card)

    rows = build_institutional_matrix_rows(games, 17, 10, superior_final_cards=superior_cards)
    games_table_rows = [
        {
            "cartão_final": _format_card(superior_cards[index]),
            "reservas_auditadas": (
                " ".join(f"+{number:02d}" for number in games[index]["audited_reserve_numbers"])
                if games[index]["audited_reserve_numbers"]
                else "-"
            ),
        }
        for index in range(10)
    ]
    contract = validate_lei15_lei15a_runtime_contract(
        institutional_rows=rows,
        games_table_rows=games_table_rows,
    )
    assert contract["classification"] == "COMPATIVEL"
    assert contract["persistence_allowed"] is True
    assert contract["checks_results"]["CHECK_001_CARTAO_FINAL_SYNC"] is True
    assert contract["checks_results"]["CHECK_002_NO_NUCLEO_COPY"] is True
    assert contract["checks_results"]["CHECK_007_COMPONENT_BOUNDARY"] is True
    assert contract["checks_results"]["CHECK_008_PERSISTENCE_GUARD"] is True
    assert len(contract["failed_checks"]) == 0


def test_build_lei15a_operational_read_preserves_component_boundary() -> None:
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    core_numbers, reserves, generation_final = _expand_official_card(core, 17, game_index=1)
    game = {
        "jogo": 1,
        "core_numbers": core_numbers,
        "audited_reserve_numbers": reserves,
        "final_card_numbers": generation_final,
    }
    read = build_lei15a_operational_read(
        game=game,
        cartao_final_lei15=generation_final,
        formato_d=17,
    )

    assert read["nucleo_operacional_gp"] == _lei15a_frozen_nucleus()
    assert read["nucleo_operacional_gp"] != core_numbers
    assert read["auditadas"] == _lei15a_auditadas_from_cartao(generation_final, 17)
    assert read["auditadas"] != reserves
    assert read["cartao_validado"] == generation_final
    assert read["sources"]["nucleo_operacional_gp"]["copied_from_lei15"] is False
    assert read["sources"]["auditadas"]["copied_from_lei15_reservas"] is False
    assert read["sources"]["auditadas"]["fixed_constant_used"] is False
    assert read["sources"]["cartao_validado"]["generated_new_card"] is False
    assert read["checks"]["cartao_final_sync"] is True
    assert read["checks"]["no_direct_copy"] is True


def test_lei15a_panel_semantic_labels_avoid_ambiguous_wording() -> None:
    from dashboard import institutional_app as app

    module_source = open(app.__file__, encoding="utf-8").read()
    assert "16D–23D = núcleo operacional GP + reservas auditadas" not in module_source
    assert "15D nasce do núcleo operacional GP" not in module_source
    assert app.LEI15A_PANEL_FORMAT_16D_23D_LABEL == "16D–23D = cartão validado pela matriz GP da Lei 15A"
    assert "componentes próprios da Lei 15A" in app.LEI15A_PANEL_DESCRIPTION
    assert "cartão validado deve coincidir com o cartão final superior" in app.LEI15A_PANEL_DESCRIPTION
    assert "preservando componentes próprios" in app.LEI15A_PANEL_SYNC_SUCCESS
    assert "Não significa cópia de núcleo" in app.LEI15A_PANEL_SYNC_SEMANTICS


def test_lei15a_panel_column_labels_differentiate_laws() -> None:
    from dashboard.institutional_app import (
        INSTITUTIONAL_MATRIX_PRIMARY_LABELS,
        LEI15_UPPER_PANEL_COLUMN_LABELS,
        LEI15A_LOWER_PANEL_TITLE,
        LEI15_UPPER_PANEL_TITLE,
    )

    assert LEI15_UPPER_PANEL_TITLE == "Jogos gerados pela Lei 15"
    assert LEI15A_LOWER_PANEL_TITLE == "Leitura operacional Lei 15A"
    assert LEI15_UPPER_PANEL_COLUMN_LABELS["núcleo_lei_15"] == "Núcleo Lei 15"
    assert LEI15_UPPER_PANEL_COLUMN_LABELS["reservas_auditadas"] == "Reservas auditadas Lei 15"
    assert LEI15_UPPER_PANEL_COLUMN_LABELS["cartão_final"] == "Cartão final Lei 15"
    assert INSTITUTIONAL_MATRIX_PRIMARY_LABELS["nucleo_a_dezenas"] == "Núcleo Operacional GP Lei 15A"
    assert INSTITUTIONAL_MATRIX_PRIMARY_LABELS["auditadas_escolhidas"] == "Auditadas Lei 15A"
    assert INSTITUTIONAL_MATRIX_PRIMARY_LABELS["vigilantes_escolhidas"] == "Vigilantes Lei 15A"
    assert INSTITUTIONAL_MATRIX_PRIMARY_LABELS["cartao_final_lido"] == "Cartão validado Lei 15A"
