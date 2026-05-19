from pathlib import Path

import pytest

from lotoia.statistics.advanced import (
    FINAL_SCORE_WEIGHTS,
    calculate_duo_score,
    calculate_final_score,
    load_frequency_stats,
)
from lotoia.statistics.scoring import ScoreConfig, validate_score_weights


def test_calculate_duo_score_identifies_found_duos(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_duos_stats",
        lambda: {
            "1-2": {"frequency": 1400, "rank": 1},
            "1-3": {"frequency": 1300, "rank": 51},
        },
    )

    result = calculate_duo_score([1, 2, 3])

    assert result["found_duos"] == 2
    assert result["top_duos"] == [{"duo": "1-2", "frequency": 1400, "rank": 1}]


def test_calculate_final_score_returns_all_components(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.calculate_duo_score",
        lambda numbers: {"average_rank": 1},
    )
    monkeypatch.setattr(
        "lotoia.statistics.advanced.calculate_terno_score",
        lambda numbers: {"average_rank": 1},
    )
    monkeypatch.setattr(
        "lotoia.statistics.advanced.calculate_quadra_score",
        lambda numbers: {"average_rank": 1},
    )
    monkeypatch.setattr(
        "lotoia.statistics.advanced.calculate_quina_score",
        lambda numbers: {"average_rank": 1},
    )
    monkeypatch.setattr(
        "lotoia.statistics.advanced.calculate_delay_score",
        lambda numbers: {"score": 50},
    )
    monkeypatch.setattr("lotoia.statistics.advanced._calculate_frequency_component", lambda numbers: 40)
    monkeypatch.setattr("lotoia.statistics.advanced._calculate_sum_component", lambda numbers: 80)
    monkeypatch.setattr(
        "lotoia.statistics.advanced._calculate_sequence_component",
        lambda numbers: 90,
    )

    result = calculate_final_score([1, 2, 3, 4, 5])

    assert result == {
        "final_score": 91.2,
        "components": {
            "duo_score": 100,
            "terno_score": 100,
            "quadra_score": 100,
            "quina_score": 100,
            "delay_score": 50.0,
            "frequency_score": 40,
            "sum_score": 80,
            "sequence_score": 90,
        },
    }


def test_calculate_final_score_calls_component_functions(monkeypatch) -> None:
    called = {
        "duo": False,
        "terno": False,
        "quadra": False,
        "quina": False,
        "delay": False,
    }

    def combo_score(name: str):
        def score(numbers: list[int]) -> dict[str, int]:
            called[name] = True
            return {"average_rank": 1}

        return score

    def delay_score(numbers: list[int]) -> dict[str, int]:
        called["delay"] = True
        return {"score": 100}

    monkeypatch.setattr("lotoia.statistics.advanced.calculate_duo_score", combo_score("duo"))
    monkeypatch.setattr("lotoia.statistics.advanced.calculate_terno_score", combo_score("terno"))
    monkeypatch.setattr("lotoia.statistics.advanced.calculate_quadra_score", combo_score("quadra"))
    monkeypatch.setattr("lotoia.statistics.advanced.calculate_quina_score", combo_score("quina"))
    monkeypatch.setattr("lotoia.statistics.advanced.calculate_delay_score", delay_score)
    monkeypatch.setattr("lotoia.statistics.advanced._calculate_frequency_component", lambda numbers: 100)
    monkeypatch.setattr("lotoia.statistics.advanced._calculate_sum_component", lambda numbers: 100)
    monkeypatch.setattr(
        "lotoia.statistics.advanced._calculate_sequence_component",
        lambda numbers: 100,
    )

    calculate_final_score([1, 2, 3, 4, 5])

    assert called == {
        "duo": True,
        "terno": True,
        "quadra": True,
        "quina": True,
        "delay": True,
    }


def test_calculate_final_score_is_normalized_with_missing_stats(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_duos_stats", lambda: {})
    monkeypatch.setattr("lotoia.statistics.advanced.load_ternos_stats", lambda: {})
    monkeypatch.setattr("lotoia.statistics.advanced.load_quadras_stats", lambda: {})
    monkeypatch.setattr("lotoia.statistics.advanced.load_quinas_stats", lambda: {})
    monkeypatch.setattr("lotoia.statistics.advanced.load_delay_stats", lambda: {})
    monkeypatch.setattr("lotoia.statistics.advanced.load_frequency_stats", lambda: {})

    result = calculate_final_score([1, 2, 3, 4, 5])

    assert 0 <= result["final_score"] <= 100
    assert set(result["components"]) == {
        "duo_score",
        "terno_score",
        "quadra_score",
        "quina_score",
        "delay_score",
        "frequency_score",
        "sum_score",
        "sequence_score",
    }


def test_calculate_final_score_validates_number_range() -> None:
    with pytest.raises(ValueError, match="entre 1 e 25"):
        calculate_final_score([0, 1, 2])


def test_final_score_weights_are_immutable() -> None:
    with pytest.raises(TypeError):
        FINAL_SCORE_WEIGHTS["duo_score"] = 1


def test_validate_score_weights_rejects_missing_component() -> None:
    invalid_weights = FINAL_SCORE_WEIGHTS.copy()
    invalid_weights.pop("duo_score")

    with pytest.raises(ValueError, match="ausentes: duo_score"):
        validate_score_weights(invalid_weights)


def test_validate_score_weights_rejects_zero_total() -> None:
    zero_weights = {name: 0 for name in FINAL_SCORE_WEIGHTS}

    with pytest.raises(ValueError, match="maior que zero"):
        validate_score_weights(zero_weights)


def test_score_config_normalizes_and_freezes_weights() -> None:
    config = ScoreConfig(weights=FINAL_SCORE_WEIGHTS, name="test")

    assert config.name == "test"
    assert config.total_weight == 100
    with pytest.raises(TypeError):
        config.weights["duo_score"] = 1


def test_stats_loaders_are_cached(tmp_path: Path) -> None:
    path = tmp_path / "frequency_stats.json"
    path.write_text(
        '{"1": {"count": 2234, "delta": 23, "relative_strength": 1.01}}\n',
        encoding="utf-8",
    )
    load_frequency_stats.cache_clear()

    first_result = load_frequency_stats(path)
    path.write_text(
        '{"1": {"count": 1, "delta": -2210, "relative_strength": 0.001}}\n',
        encoding="utf-8",
    )
    second_result = load_frequency_stats(path)

    assert first_result == second_result
    assert load_frequency_stats.cache_info().hits == 1
