from __future__ import annotations

from lotoia.clients.game_expansion import expand_generation_games_for_format
from lotoia.governance.lei15a_operational import apply_lei15a_validated_card, build_lei15a_operational_read


def test_build_lei15a_operational_read_marks_synchronized_card() -> None:
    final_card = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7, 4, 11]
    read = build_lei15a_operational_read(cartao_final_lei15=final_card, formato_d=17)

    assert read["cartao_validado"] == sorted(final_card)
    assert read["lei15a_synchronized"] is True
    assert read["auditadas"] == sorted(set(final_card) - set(read["nucleo_operacional_gp"]))


def test_apply_lei15a_validated_card_sets_delivery_numbers() -> None:
    final_card = [1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25]
    tagged = apply_lei15a_validated_card(
        {"final_card_numbers": final_card, "numbers": [99]},
        formato_d=15,
    )

    assert tagged["numbers"] == final_card
    assert tagged["cartao_validado_lei15a"] == final_card
    assert tagged["lei15a_synchronized"] is True


def test_expand_generation_games_for_format_tags_lei15a_card() -> None:
    core = [1, 3, 5, 6, 9, 10, 13, 14, 17, 18, 20, 23, 24, 25, 7]
    expanded = expand_generation_games_for_format([{"numbers": core}], 17)

    game = expanded[0]
    assert game["cartao_validado_lei15a"] == game["final_card_numbers"]
    assert game["numbers"] == game["cartao_validado_lei15a"]
    assert game["lei15a_synchronized"] is True
    assert len(game["cartao_validado_lei15a"]) == 17
