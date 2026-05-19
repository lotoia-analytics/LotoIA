from lotoia.generator.basic_generator import (
    _attach_scores,
    _hybrid_score_sort_key,
    generate_best_games,
    generate_filtered_game,
    generate_multiple_games,
)
from lotoia.statistics.advanced import calculate_sequence_stats


def test_generate_filtered_game_returns_15_numbers() -> None:
    result = generate_filtered_game()

    assert len(result["numbers"]) == 15
    assert len(set(result["numbers"])) == 15


def test_generate_filtered_game_numbers_are_between_1_and_25() -> None:
    result = generate_filtered_game()

    assert all(1 <= number <= 25 for number in result["numbers"])


def test_generate_filtered_game_sum_is_valid() -> None:
    result = generate_filtered_game()

    assert 170 <= result["sum"] <= 240
    assert result["sum"] == sum(result["numbers"])


def test_generate_filtered_game_odd_even_distribution_is_valid() -> None:
    result = generate_filtered_game()

    assert 6 <= result["odd"] <= 9
    assert result["even"] == 15 - result["odd"]


def test_generate_filtered_game_frame_center_distribution_is_valid() -> None:
    result = generate_filtered_game()

    assert 8 <= result["frame"] <= 12
    assert 3 <= result["center"] <= 7
    assert result["frame"] + result["center"] == 15


def test_generate_filtered_game_numbers_are_sorted() -> None:
    result = generate_filtered_game()

    assert result["numbers"] == sorted(result["numbers"])


def test_generate_filtered_game_respects_sequence_filter() -> None:
    result = generate_filtered_game()
    sequence_stats = calculate_sequence_stats(result["numbers"])

    assert sequence_stats["sequence_count"] <= 3
    assert sequence_stats["largest_sequence"] <= 3


def test_generate_filtered_game_returns_quadra_score() -> None:
    result = generate_filtered_game()

    assert "quadra_score" in result


def test_generate_filtered_game_returns_final_score() -> None:
    result = generate_filtered_game()

    assert "final_score" in result


def test_generate_filtered_game_returns_quadra_score_structure() -> None:
    result = generate_filtered_game()

    assert set(result["quadra_score"]) == {
        "found_quadras",
        "total_frequency",
        "average_frequency",
        "average_rank",
        "top_quadras",
    }


def test_generate_filtered_game_returns_final_score_structure() -> None:
    result = generate_filtered_game()

    assert set(result["final_score"]) == {"final_score", "components"}
    assert set(result["final_score"]["components"]) == {
        "duo_score",
        "terno_score",
        "quadra_score",
        "quina_score",
        "delay_score",
        "frequency_score",
        "sum_score",
        "sequence_score",
    }


def test_generate_filtered_game_returns_empty_quadra_score_without_quadras(monkeypatch) -> None:
    empty_score = {
        "found_quadras": 0,
        "total_frequency": 0,
        "average_frequency": 0,
        "average_rank": 0,
        "top_quadras": [],
    }
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.calculate_quadra_score",
        lambda numbers: empty_score,
    )

    result = generate_filtered_game()

    assert result["quadra_score"] == empty_score


def test_attach_scores_adds_quadra_and_final_scores(monkeypatch) -> None:
    game = {
        "numbers": [1, 2, 3, 4, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24],
        "odd": 6,
        "even": 9,
        "sum": 186,
        "frame": 10,
        "center": 5,
    }
    quadra_score = {
        "found_quadras": 0,
        "total_frequency": 0,
        "average_frequency": 0,
        "average_rank": 0,
        "top_quadras": [],
    }
    final_score = {"final_score": 42, "components": {}}
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.calculate_quadra_score",
        lambda numbers: quadra_score,
    )
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.calculate_final_score",
        lambda numbers: final_score,
    )

    result = _attach_scores(game)

    assert result["quadra_score"] == quadra_score
    assert result["final_score"] == final_score


def test_attach_scores_falls_back_when_final_score_fails(monkeypatch) -> None:
    game = {
        "numbers": [1, 2, 3, 4, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24],
        "odd": 6,
        "even": 9,
        "sum": 186,
        "frame": 10,
        "center": 5,
    }
    quadra_score = {
        "found_quadras": 0,
        "total_frequency": 0,
        "average_frequency": 0,
        "average_rank": 0,
        "top_quadras": [],
    }

    def fail_final_score(numbers: list[int]) -> dict[str, object]:
        raise RuntimeError("missing stats")

    monkeypatch.setattr(
        "lotoia.generator.basic_generator.calculate_quadra_score",
        lambda numbers: quadra_score,
    )
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.calculate_final_score",
        fail_final_score,
    )

    result = _attach_scores(game)

    assert result["quadra_score"] == quadra_score
    assert result["final_score"]["final_score"] == 0
    assert set(result["final_score"]["components"]) == {
        "duo_score",
        "terno_score",
        "quadra_score",
        "quina_score",
        "delay_score",
        "frequency_score",
        "sum_score",
        "sequence_score",
    }


def test_generate_multiple_games_returns_requested_count() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    assert len(result) == 3


def test_generate_multiple_games_returns_unique_games() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)
    game_keys = [tuple(game["numbers"]) for game in result]

    assert len(set(game_keys)) == len(game_keys)


def test_generate_multiple_games_respects_max_repeated() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    for index, game in enumerate(result):
        for previous_game in result[:index]:
            repeated = len(set(game["numbers"]) & set(previous_game["numbers"]))
            assert repeated <= 9


def test_generate_multiple_games_returns_15_numbers_per_game() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    assert all(len(game["numbers"]) == 15 for game in result)
    assert all(len(set(game["numbers"])) == 15 for game in result)


def test_generate_multiple_games_numbers_are_between_1_and_25() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    for game in result:
        assert all(1 <= number <= 25 for number in game["numbers"])


def test_generate_multiple_games_returns_quadra_score_for_all_games() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    assert all("quadra_score" in game for game in result)


def test_generate_multiple_games_returns_final_score_for_all_games() -> None:
    result = generate_multiple_games(count=3, max_repeated=9)

    assert all("final_score" in game for game in result)


def make_scored_game(
    numbers: list[int],
    found_quadras: int,
    average_frequency: float,
    average_rank: float,
    final_score: float = 0,
) -> dict[str, object]:
    return {
        "numbers": numbers,
        "odd": 7,
        "even": 8,
        "sum": sum(numbers),
        "frame": 10,
        "center": 5,
        "quadra_score": {
            "found_quadras": found_quadras,
            "total_frequency": int(found_quadras * average_frequency),
            "average_frequency": average_frequency,
            "average_rank": average_rank,
            "top_quadras": [],
        },
        "final_score": {"final_score": final_score, "components": {}},
    }


def test_generate_best_games_returns_requested_count(monkeypatch) -> None:
    pool = [
        make_scored_game([1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 1, 100, 10, 10),
        make_scored_game([1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 2, 100, 10, 20),
        make_scored_game([1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25], 3, 100, 10, 30),
    ]
    monkeypatch.setattr("lotoia.generator.basic_generator.generate_filtered_game", pool.pop)

    result = generate_best_games(count=2, pool_size=3)

    assert result["count"] == 2
    assert len(result["games"]) == 2


def test_hybrid_score_sort_key_orders_by_final_score() -> None:
    weaker_quadra_game = make_scored_game(
        [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        1,
        500,
        1,
        90,
    )
    stronger_quadra_game = make_scored_game(
        [1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        5,
        500,
        1,
        70,
    )

    result = sorted([stronger_quadra_game, weaker_quadra_game], key=_hybrid_score_sort_key)

    assert result[0] == weaker_quadra_game


def test_hybrid_score_sort_key_breaks_ties_by_found_quadras() -> None:
    fewer_quadras = make_scored_game(
        [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        1,
        500,
        1,
        90,
    )
    more_quadras = make_scored_game(
        [1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        3,
        500,
        10,
        90,
    )

    result = sorted([fewer_quadras, more_quadras], key=_hybrid_score_sort_key)

    assert result[0] == more_quadras


def test_hybrid_score_sort_key_breaks_ties_by_average_rank() -> None:
    worse_rank = make_scored_game(
        [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        2,
        500,
        40,
        90,
    )
    better_rank = make_scored_game(
        [1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        2,
        300,
        10,
        90,
    )

    result = sorted([worse_rank, better_rank], key=_hybrid_score_sort_key)

    assert result[0] == better_rank


def test_generate_best_games_orders_by_hybrid_score(monkeypatch) -> None:
    pool = [
        make_scored_game([1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 5, 500, 1, 70),
        make_scored_game([1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 2, 300, 40, 90),
        make_scored_game([1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25], 2, 400, 60, 90),
        make_scored_game([1, 3, 4, 5, 7, 9, 11, 12, 14, 16, 18, 20, 22, 24, 25], 2, 400, 30, 90),
    ]
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.generate_filtered_game",
        lambda: pool.pop(0),
    )

    result = generate_best_games(count=3, pool_size=4)

    assert [game["numbers"] for game in result["games"]] == [
        [1, 3, 4, 5, 7, 9, 11, 12, 14, 16, 18, 20, 22, 24, 25],
        [1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        [1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25],
    ]


def test_generate_best_games_returns_quadra_score_for_all_games() -> None:
    result = generate_best_games(count=3, pool_size=5)

    assert all("quadra_score" in game for game in result["games"])


def test_generate_best_games_returns_final_score_for_all_games() -> None:
    result = generate_best_games(count=3, pool_size=5)

    assert all("final_score" in game for game in result["games"])


def test_generate_best_games_avoids_duplicate_games(monkeypatch) -> None:
    duplicate = make_scored_game(
        [1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25],
        1,
        100,
        10,
    )
    pool = [
        duplicate,
        duplicate,
        make_scored_game([1, 2, 3, 5, 7, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25], 2, 100, 10),
        make_scored_game([1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 22, 24, 25], 3, 100, 10),
    ]
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.generate_filtered_game",
        lambda: pool.pop(0),
    )

    result = generate_best_games(count=2, pool_size=3)
    game_keys = [tuple(game["numbers"]) for game in result["games"]]

    assert len(set(game_keys)) == len(game_keys)
