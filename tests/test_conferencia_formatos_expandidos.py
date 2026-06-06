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
    assert info["origem_dezenas_conferencia"] == ("núcleo_lei_15" if card_format == 15 else "cartao_final")
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
