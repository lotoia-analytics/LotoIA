from pathlib import Path

import pytest

from lotoia.statistics.advanced import _calculate_frequency_component, load_frequency_stats
from scripts.build_frequency_stats import (
    EXPECTED_FREQUENCY,
    _build_stats_from_counts,
    build_frequency_stats,
)


def _history_header() -> str:
    columns = ["concurso", "data", *[f"d{number}" for number in range(1, 16)]]
    return ",".join(columns)


def _history_row(contest: int, numbers: list[int]) -> str:
    values = [str(contest), "01/01/2026", *[str(number) for number in numbers]]
    return ",".join(values)


def test_build_frequency_stats_generates_json(tmp_path: Path) -> None:
    source_path = tmp_path / "historico_lotofacil.csv"
    output_path = tmp_path / "frequency_stats.json"
    source_path.write_text(
        "\n".join(
            [
                _history_header(),
                _history_row(1, list(range(1, 16))),
                _history_row(2, list(range(11, 26))),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = build_frequency_stats(source_path, output_path)
    loaded = load_frequency_stats(output_path)

    assert output_path.exists()
    assert result["1"]["count"] == 1
    assert result["11"]["count"] == 2
    assert loaded == result


def test_frequency_stats_calculates_delta() -> None:
    counts = {number: 0 for number in range(1, 26)}
    counts[1] = 2234

    result = _build_stats_from_counts(counts)

    assert EXPECTED_FREQUENCY == 2211
    assert result["1"]["delta"] == 23


def test_frequency_stats_calculates_relative_strength() -> None:
    counts = {number: 0 for number in range(1, 26)}
    counts[1] = 2234

    result = _build_stats_from_counts(counts)

    assert result["1"]["relative_strength"] == 1.01


def test_frequency_stats_validates_number_range(tmp_path: Path) -> None:
    source_path = tmp_path / "historico_lotofacil.csv"
    output_path = tmp_path / "frequency_stats.json"
    source_path.write_text(
        _history_header() + "\n" + _history_row(1, [*range(1, 15), 26]) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="entre 1 e 25"):
        build_frequency_stats(source_path, output_path)


def test_frequency_stats_validates_repeated_numbers(tmp_path: Path) -> None:
    source_path = tmp_path / "historico_lotofacil.csv"
    output_path = tmp_path / "frequency_stats.json"
    source_path.write_text(
        _history_header() + "\n" + _history_row(1, [1, *range(1, 15)]) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="repetidas"):
        build_frequency_stats(source_path, output_path)


def test_load_frequency_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_frequency_stats(tmp_path / "missing_frequency_stats.json")

    assert result == {}


def test_frequency_score_uses_frequency_stats_loader(monkeypatch) -> None:
    loaded = False

    def fake_load_frequency_stats() -> dict[str, dict[str, float | int]]:
        nonlocal loaded
        loaded = True
        return {
            "1": {"count": 2234, "delta": 23, "relative_strength": 1.01},
            "2": {"count": 2210, "delta": -1, "relative_strength": 1.0},
        }

    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_frequency_stats",
        fake_load_frequency_stats,
    )

    _calculate_frequency_component([1, 2])

    assert loaded is True


def test_frequency_score_calculates_from_relative_strength(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_frequency_stats",
        lambda: {
            "1": {"count": 2234, "delta": 23, "relative_strength": 1.01},
            "2": {"count": 2234, "delta": 23, "relative_strength": 1.01},
            "3": {"count": 2234, "delta": 23, "relative_strength": 1.01},
        },
    )

    result = _calculate_frequency_component([1, 2, 3])

    assert result == 60


def test_frequency_score_penalizes_extreme_imbalance(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_frequency_stats",
        lambda: {
            "1": {"count": 4422, "delta": 2211, "relative_strength": 2.0},
            "2": {"count": 1105, "delta": -1106, "relative_strength": 0.5},
        },
    )

    result = _calculate_frequency_component([1, 2])

    assert result == 0


def test_frequency_score_is_normalized_to_0_100(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_frequency_stats",
        lambda: {
            "1": {"count": 5000, "delta": 2789, "relative_strength": 3.0},
            "2": {"count": 5000, "delta": 2789, "relative_strength": 3.0},
            "3": {"count": 5000, "delta": 2789, "relative_strength": 3.0},
        },
    )

    result = _calculate_frequency_component([1, 2, 3])

    assert 0 <= result <= 100
    assert result == 100


def test_frequency_score_validates_number_range() -> None:
    with pytest.raises(ValueError, match="entre 1 e 25"):
        _calculate_frequency_component([0, 1, 2])
