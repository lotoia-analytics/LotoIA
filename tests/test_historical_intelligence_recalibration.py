from lotoia.generator.basic_generator import _compose_profiled_games
from lotoia.models.draw import Draw
from lotoia.statistics.historical_intelligence import (
    PROFILE_CHAOTIC,
    PROFILE_HYBRID,
    PROFILE_RECURRENT,
    DrawLike,
    classify_profile,
    partial_recurrence_metrics,
    profile_quota,
    structural_rarity_score,
)


def test_partial_recurrence_counts_matches_from_9_to_12_plus() -> None:
    candidate = list(range(1, 16))
    history = [
        Draw(contest=1, date=None, numbers=list(range(1, 10)) + list(range(16, 22))),
        Draw(contest=2, date=None, numbers=list(range(1, 11)) + list(range(16, 21))),
        Draw(contest=3, date=None, numbers=list(range(1, 12)) + list(range(16, 20))),
        Draw(contest=4, date=None, numbers=list(range(1, 13)) + list(range(16, 19))),
    ]

    metrics = partial_recurrence_metrics(candidate, history)

    assert metrics["partial_match_counts"] == {"9": 1, "10": 1, "11": 1, "12_plus": 1}
    assert metrics["partial_match_max"] == 12
    assert metrics["jaccard_similarity"] > 0


def test_structural_rarity_varies_by_structure() -> None:
    history = [Draw(contest=1, date=None, numbers=list(range(1, 16)))]
    balanced = [1, 2, 4, 6, 7, 9, 11, 13, 14, 16, 18, 20, 22, 24, 25]
    extreme = list(range(1, 15)) + [25]

    assert structural_rarity_score(balanced, history) != structural_rarity_score(extreme, history)


def test_profile_quota_composes_40_40_20_for_20_games() -> None:
    assert profile_quota(20) == {
        PROFILE_RECURRENT: 8,
        PROFILE_HYBRID: 8,
        PROFILE_CHAOTIC: 4,
    }


def test_compose_profiled_games_respects_profile_quotas() -> None:
    games = []
    for profile_index, profile in enumerate((PROFILE_RECURRENT, PROFILE_HYBRID, PROFILE_CHAOTIC)):
        for index in range(10):
            start = ((profile_index * 8 + index) % 25) + 1
            numbers = sorted((((start + offset - 1) % 25) + 1) for offset in range(15))
            games.append(
                {
                    "numbers": numbers,
                    "profile_type": profile,
                    "profile_score": 100 - index,
                    "final_score": {"final_score": 50},
                    "quadra_score": {"found_quadras": 0},
                }
            )

    selected = _compose_profiled_games(games, 20)

    assert sum(1 for game in selected if game["profile_type"] == PROFILE_RECURRENT) == 8
    assert sum(1 for game in selected if game["profile_type"] == PROFILE_HYBRID) == 8
    assert sum(1 for game in selected if game["profile_type"] == PROFILE_CHAOTIC) == 4


def test_classify_profile_keeps_all_three_classes_reachable_on_representative_samples() -> None:
    history = [
        DrawLike(contest=1, numbers=list(range(1, 16))),
        DrawLike(contest=2, numbers=list(range(2, 17))),
        DrawLike(contest=3, numbers=list(range(3, 18))),
    ]

    recurrent_like = [4, 6, 8, 10, 12, 14, 16, 18, 20, 21, 22, 23, 24, 25, 3]
    hybrid_like = [1, 2, 4, 6, 7, 9, 11, 13, 14, 16, 18, 20, 22, 24, 25]
    chaotic_like = [1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]

    assert classify_profile(recurrent_like, history) == PROFILE_RECURRENT
    assert classify_profile(hybrid_like, history) == PROFILE_HYBRID
    assert classify_profile(chaotic_like, history) == PROFILE_CHAOTIC


def test_classify_profile_on_historical_dataset_keeps_nonzero_distribution() -> None:
    from lotoia.data.loader import load_draws_csv

    draws = load_draws_csv()
    history = [DrawLike(contest=d.contest, numbers=list(d.numbers)) for d in draws]
    counts = {PROFILE_RECURRENT: 0, PROFILE_HYBRID: 0, PROFILE_CHAOTIC: 0}

    for draw in draws:
        counts[classify_profile(list(draw.numbers), history)] += 1

    assert counts[PROFILE_RECURRENT] > 0
    assert counts[PROFILE_HYBRID] > 0
    assert counts[PROFILE_CHAOTIC] > 0
