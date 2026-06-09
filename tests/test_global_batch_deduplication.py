from __future__ import annotations

from itertools import combinations, islice

from lotoia.governance.output_commander import output_commander_validate_games


def _game(numbers: tuple[int, ...]) -> dict[str, object]:
    return {"numbers": list(numbers)}


def test_global_batch_deduplication_across_four_groups_of_fifty() -> None:
    all_games = [_game(combo) for combo in islice(combinations(range(1, 26), 15), 200)]
    groups = [all_games[index : index + 50] for index in range(0, 200, 50)]
    seen_signatures: set[str] = set()
    total_persisted = 0

    for group_index, group in enumerate(groups, start=1):
        report = output_commander_validate_games(
            group,
            batch_id="batch-global-dedup",
            target_size=15,
            required_total=50,
            candidate_total=50,
            persisted_signatures=seen_signatures,
            historical_deduplication_mode="BLOCK",
        )

        assert report["status_comandante_saida"] == "APROVADO", group_index
        assert report["approved_total"] == 50, group_index
        assert report["quantidade_jogos_duplicados"] == 0, group_index
        assert report["quantidade_jogos_rejeitados"] == 0, group_index
        assert len(report["accepted_signatures"]) == 50, group_index
        assert len(report["accepted_games"]) == 50, group_index

        seen_signatures.update(report["accepted_signatures"])
        total_persisted += len(report["accepted_games"])

    assert total_persisted == 200
    assert len(seen_signatures) == 200


def test_global_batch_deduplication_rejects_duplicate_between_groups() -> None:
    first_group = [_game(combo) for combo in islice(combinations(range(1, 26), 15), 50)]
    duplicate_game = dict(first_group[0])
    new_game_source = islice(combinations(range(1, 26), 15), 50, 51)
    second_group = [duplicate_game, _game(next(new_game_source))]

    seen_signatures: set[str] = set()
    first_report = output_commander_validate_games(
        first_group,
        batch_id="batch-global-dedup-dup",
        target_size=15,
        required_total=50,
        candidate_total=50,
        persisted_signatures=seen_signatures,
        historical_deduplication_mode="BLOCK",
    )
    seen_signatures.update(first_report["accepted_signatures"])

    second_report = output_commander_validate_games(
        second_group,
        batch_id="batch-global-dedup-dup",
        target_size=15,
        required_total=50,
        candidate_total=50,
        persisted_signatures=seen_signatures,
        historical_deduplication_mode="BLOCK",
    )

    assert second_report["status_comandante_saida"] == "BLOQUEADO"
    assert second_report["quantidade_jogos_aprovados"] == 1
    assert second_report["quantidade_jogos_duplicados"] == 1
    assert second_report["quantidade_jogos_rejeitados"] == 49
    assert second_report["historical_duplicates_found"] == 1
    assert any("duplicado_na_bateria" in error for item in second_report["invalid_games"] for error in item["errors"])
