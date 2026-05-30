from __future__ import annotations

from lotoia.governance.output_commander import game_signature, output_commander_validate_games


def test_game_signature_normalizes_numbers_and_order() -> None:
    assert game_signature([25, 1, 2, 15, 3]) == "01-02-03-15-25"
    assert game_signature([3, 15, 2, 1, 25]) == "01-02-03-15-25"


def test_output_commander_blocks_duplicate_games_and_duplicate_numbers() -> None:
    report = output_commander_validate_games(
        [
            {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]},
            {"numbers": [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]},
        ],
        batch_id="batch-a",
        target_size=15,
        persisted_signatures=set(),
    )
    assert report["status_comandante_saida"] == "ERRO_CRITICO"
    assert report["quantidade_jogos_unicos"] == 1
    assert report["quantidade_jogos_duplicados"] == 1
    assert report["duplicate_hashes"] == ["01-02-03-04-05-06-07-08-09-10-11-12-13-14-15"]


def test_output_commander_rejects_internal_duplicate_numbers() -> None:
    report = output_commander_validate_games(
        [
            {"numbers": [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]},
        ],
        batch_id="batch-b",
        target_size=15,
        persisted_signatures=set(),
    )
    assert report["status_comandante_saida"] == "ERRO_CRITICO"
    assert report["invalid_games"][0]["errors"] == ["dezenas_duplicadas"]
