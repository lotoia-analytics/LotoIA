import pytest

from lotoia.models.draw import Draw
from lotoia.statistics.temporal import FeatureContext, build_features


def make_draw(contest: int) -> Draw:
    numbers = sorted(((contest + offset - 1) % 25) + 1 for offset in range(15))
    return Draw(contest=contest, date=None, numbers=numbers)


def test_build_features_uses_only_history_before_cutoff() -> None:
    draws = [make_draw(contest) for contest in range(1, 6)]

    features = build_features(draws, cutoff_contest=4)

    assert isinstance(features, FeatureContext)
    history = features.history
    assert [draw.contest for draw in history] == [1, 2, 3]
    assert features.cutoff_contest == 4
    assert features.last_contest == 3
    assert all(draw.contest < 4 for draw in history)


def test_build_features_returns_temporal_models() -> None:
    draws = [make_draw(contest) for contest in range(1, 4)]

    features = build_features(draws, cutoff_contest=3)

    assert features.history_size == 2
    assert set(features.history_model) == {"duos", "ternos", "quadras", "quinas"}
    assert len(features.delays) == 25
    assert set(features.hot_cold_numbers) == {"window", "hot", "cold"}
    assert set(features.repeated_numbers) == {"count", "numbers"}


def test_build_features_keeps_mapping_compatibility() -> None:
    features = build_features([make_draw(1), make_draw(2)], cutoff_contest=2)

    assert features["cutoff_contest"] == 2
    assert features["history_size"] == 1
    assert set(features) >= {"cutoff_contest", "history", "history_model"}


def test_build_features_rejects_invalid_cutoff() -> None:
    with pytest.raises(ValueError, match="maior que zero"):
        build_features([], cutoff_contest=0)
