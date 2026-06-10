from __future__ import annotations

import pytest

from dashboard import institutional_app as admin_app


def _build_game(card_format: int) -> dict[str, object]:
    core = [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25]
    reserves = [4, 6, 9, 12, 15, 16, 17, 19]
    final_card = sorted(core + reserves[: max(0, card_format - 15)])
    return {
        "generation_event_id": 999,
        "formato_cartao": card_format,
        "nucleo_lei_15": " ".join(f"{n:02d}" for n in core),
        "reservas_auditadas": " ".join(f"+{n:02d}" for n in reserves[: max(0, card_format - 15)]),
        "cartao_final": " ".join(f"{n:02d}" for n in final_card),
        "numbers": list(core),
        "core_numbers": list(core),
        "audited_reserve_numbers": list(reserves[: max(0, card_format - 15)]),
        "final_card_numbers": list(final_card),
        "quantidade_nucleo": 15,
        "quantidade_reservas": max(0, card_format - 15),
        "quantidade_final": card_format,
        "game_signature": f"sig-{card_format}",
    }


@pytest.mark.parametrize(
    "card_format,reservas",
    [
        (15, 0),
        (16, 1),
        (17, 2),
        (18, 3),
        (19, 4),
        (20, 5),
        (21, 6),
        (22, 7),
        (23, 8),
    ],
)
def test_select_conference_numbers_uses_final_card(card_format: int, reservas: int) -> None:
    game = _build_game(card_format)
    info = admin_app._select_conference_numbers(game)

    assert info["formato_cartao"] == card_format
    assert info["dezenas_conferidas_count"] == card_format
    assert info["actual_card_size"] == card_format
    assert info["expected_card_size"] == card_format
    assert info["origem_dezenas_conferencia"] == "cartao_final"
    expected_final = sorted(
        list(game["core_numbers"]) + list(game["audited_reserve_numbers"][: max(0, card_format - 15)])
    )
    assert info["conference_numbers"] == expected_final
    assert len(info["conference_numbers"]) == card_format
    assert len(game["audited_reserve_numbers"]) == reservas


def test_conference_compare_uses_cartao_final_for_19d() -> None:
    game = {
        "generation_event_id": 999,
        "formato_cartao": 19,
        "nucleo_lei_15": "01 02 03 05 07 08 10 11 13 14 18 20 22 23 25",
        "reservas_auditadas": "+04 +12 +15 +16",
        "cartao_final": "01 02 03 04 05 07 08 10 11 12 13 14 15 16 18 20 22 23 25",
        "numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "core_numbers": [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        "audited_reserve_numbers": [4, 12, 15, 16],
        "final_card_numbers": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 23, 25],
        "quantidade_nucleo": 15,
        "quantidade_reservas": 4,
        "quantidade_final": 19,
        "game_signature": "sig-19",
    }
    contest = {
        "concurso": 3702,
        "data": "03/06/2026",
        "dezenas": [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18],
    }

    comparison = admin_app._compare_games_against_contest(
        generation_event_id=999,
        games=[game],
        contest=contest,
    )

    diagnostics = dict(comparison.get("diagnostics") or {})
    result = dict(comparison.get("results", [{}])[0] or {})

    assert comparison.get("generation_event_id") == 999
    assert diagnostics.get("generation_event_id") == 999
    assert diagnostics.get("formato_cartao") == 19
    assert diagnostics.get("dezenas_conferidas_count") == 19
    assert diagnostics.get("origem_dezenas_conferencia") == "cartao_final"
    assert result.get("formato_cartao") == 19
    assert result.get("dezenas_conferidas_count") == 19
    assert result.get("origem_dezenas_conferencia") == "cartao_final"
    assert result.get("actual_card_size") == 19
    assert result.get("hits") == 15
    assert result.get("matched_numbers") == [1, 2, 3, 4, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18]


def _build_15d_game(index: int, core: list[int]) -> dict[str, object]:
    final_card = sorted(core)
    return {
        "generation_event_id": 1000 + index,
        "game_index": index,
        "formato_cartao": 15,
        "nucleo_lei_15": " ".join(f"{n:02d}" for n in core),
        "cartao_final": " ".join(f"{n:02d}" for n in final_card),
        "numbers": list(core),
        "core_numbers": list(core),
        "final_card_numbers": list(final_card),
        "quantidade_nucleo": 15,
        "quantidade_reservas": 0,
        "quantidade_final": 15,
        "game_signature": f"sig-15d-{index}",
    }


def test_conferencia_15d_usa_cartao_final_por_jogo() -> None:
    cores = [
        [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
        [1, 3, 4, 5, 6, 9, 10, 12, 14, 15, 17, 19, 21, 23, 24],
        [2, 4, 6, 7, 8, 9, 11, 12, 13, 16, 17, 18, 20, 21, 25],
    ]
    games = [_build_15d_game(index, core) for index, core in enumerate(cores, start=1)]
    contest = {"concurso": 3700, "data": "01/06/2026", "dezenas": cores[0]}

    comparison = admin_app._compare_games_against_contest(
        generation_event_id=1000,
        games=games,
        contest=contest,
    )

    results = list(comparison.get("results") or [])
    assert len(results) == 3
    for game, result in zip(games, results):
        expected = sorted(game["final_card_numbers"])
        assert result["numbers"] == expected
        assert result["cartao_final"] == expected
        assert result["origem_dezenas_conferencia"] == "cartao_final"
    assert len({tuple(row["numbers"]) for row in results}) == 3


def test_conferencia_15d_nao_repete_nucleo_fixo() -> None:
    games = [_build_15d_game(index, core) for index, core in enumerate(
        [
            [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            [1, 3, 4, 5, 6, 9, 10, 12, 14, 15, 17, 19, 21, 23, 24],
        ],
        start=1,
    )]
    guard = admin_app.validate_conference_15d_source(
        games=games,
        conference_results=[
            {"numbers": sorted(g["final_card_numbers"]), "origem_dezenas_conferencia": "cartao_final"}
            for g in games
        ],
    )
    assert guard["valid"] is True
    assert guard["classification"] == "COMPATIVEL"
    assert guard["conferencia_15d_all_rows_identical"] is False


def test_conferencia_15d_bloqueia_nucleo_fixo_repetido() -> None:
    games = [_build_15d_game(index, core) for index, core in enumerate(
        [
            [1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 18, 20, 22, 23, 25],
            [1, 3, 4, 5, 6, 9, 10, 12, 14, 15, 17, 19, 21, 23, 24],
        ],
        start=1,
    )]
    frozen = sorted(admin_app.LEI15A_NUCLEO_15D_CONGELADO)
    guard = admin_app.validate_conference_15d_source(
        games=games,
        conference_results=[
            {"numbers": frozen, "origem_dezenas_conferencia": "nucleo_lei_15a_congelado"},
            {"numbers": frozen, "origem_dezenas_conferencia": "nucleo_lei_15a_congelado"},
        ],
    )
    assert guard["valid"] is False
    assert guard["classification"] == "CONFLITANTE"
    assert guard["persistence_guard_status"] == "BLOQUEADO_NUCLEO_FIXO_15D"
    assert guard["conferencia_15d_all_rows_identical"] is True
    assert guard["jogos_gerados_15d_rows_variable"] is True


def test_conferencia_16d_regressao_preservada() -> None:
    game = _build_game(16)
    info = admin_app._select_conference_numbers(game)
    assert info["origem_dezenas_conferencia"] == "cartao_final"
    assert info["conference_numbers"] == sorted(game["final_card_numbers"])
    assert len(info["conference_numbers"]) == 16
