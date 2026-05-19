from pathlib import Path

import pytest

from lotoia.statistics.advanced import calculate_delay_score, load_delay_stats
from scripts.build_delay_stats import build_delay_stats


def test_load_delay_stats_loads_json(tmp_path: Path) -> None:
    source_path = tmp_path / "atrasos_dezenas.csv"
    output_path = tmp_path / "delay_stats.json"
    source_path.write_text("dezena,delay\n22,3\n7,2\n", encoding="utf-8")

    build_delay_stats(source_path, output_path)

    result = load_delay_stats(output_path)

    assert result["22"] == {"delay": 3}


def test_delay_stats_orders_by_highest_delay(tmp_path: Path) -> None:
    source_path = tmp_path / "atrasos_dezenas.csv"
    output_path = tmp_path / "delay_stats.json"
    source_path.write_text("dezena,delay\n7,2\n22,3\n16,2\n", encoding="utf-8")

    result = build_delay_stats(source_path, output_path)

    assert list(result) == ["22", "7", "16"]


def test_delay_stats_validates_dezena_range(tmp_path: Path) -> None:
    source_path = tmp_path / "atrasos_dezenas.csv"
    output_path = tmp_path / "delay_stats.json"
    source_path.write_text("dezena,delay\n26,3\n", encoding="utf-8")

    with pytest.raises(ValueError, match="entre 1 e 25"):
        build_delay_stats(source_path, output_path)


def test_delay_stats_validates_delay(tmp_path: Path) -> None:
    source_path = tmp_path / "atrasos_dezenas.csv"
    output_path = tmp_path / "delay_stats.json"
    source_path.write_text("dezena,delay\n22,-1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="maior ou igual a zero"):
        build_delay_stats(source_path, output_path)


def test_load_delay_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_delay_stats(tmp_path / "missing_delay_stats.json")

    assert result == {}


def test_calculate_delay_score_loads_delay_stats(monkeypatch) -> None:
    loaded = False

    def fake_load_delay_stats() -> dict[str, dict[str, int]]:
        nonlocal loaded
        loaded = True
        return {}

    monkeypatch.setattr("lotoia.statistics.advanced.load_delay_stats", fake_load_delay_stats)

    calculate_delay_score([1, 2, 3])

    assert loaded is True


def test_calculate_delay_score_rewards_moderate_delays(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_delay_stats",
        lambda: {
            "1": {"delay": 0},
            "2": {"delay": 3},
            "3": {"delay": 9},
        },
    )

    result = calculate_delay_score([1, 2, 3])

    assert result["delays"] == [
        {"number": 1, "delay": 0, "score": 0},
        {"number": 2, "delay": 3, "score": 100},
        {"number": 3, "delay": 9, "score": 0},
    ]
    assert result["score"] == pytest.approx(33.33)


def test_calculate_delay_score_normalizes_to_0_100(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_delay_stats",
        lambda: {
            "1": {"delay": 2},
            "2": {"delay": 3},
            "3": {"delay": 4},
        },
    )

    result = calculate_delay_score([1, 2, 3])

    assert 0 <= result["score"] <= 100


def test_calculate_delay_score_without_found_delays(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_delay_stats", lambda: {})

    result = calculate_delay_score([1, 2, 3])

    assert result == {
        "found_delays": 0,
        "score": 0,
        "average_delay": 0,
        "delays": [],
    }


def test_calculate_delay_score_validates_numbers() -> None:
    with pytest.raises(ValueError, match="entre 1 e 25"):
        calculate_delay_score([0, 1, 2])
