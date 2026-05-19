from pathlib import Path

import pytest

from lotoia.statistics.advanced import calculate_sena_score, load_senas_stats
from scripts.build_senas_stats import build_senas_stats


def test_build_senas_stats_generates_json(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text(
        "0001) 03 04 15 19 20 21 44\n"
        "0002) 01 04 09 10 11 23 42\n",
        encoding="utf-8",
    )

    result = build_senas_stats(source_path, output_path)
    loaded = load_senas_stats(output_path)

    assert output_path.exists()
    assert result == loaded
    assert result["03-04-15-19-20-21"]["count"] == 44


def test_senas_stats_json_has_official_shape(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text("0001) 03 04 15 19 20 21 44\n", encoding="utf-8")

    result = build_senas_stats(source_path, output_path)

    assert result["03-04-15-19-20-21"] == {
        "count": 44,
        "rank": 1,
        "relative_strength": 1.0,
    }


def test_senas_stats_ranking_orders_by_highest_count(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text(
        "0001) 01 02 03 04 05 06 10\n"
        "0002) 03 04 15 19 20 21 44\n"
        "0003) 01 04 09 10 11 23 42\n",
        encoding="utf-8",
    )

    result = build_senas_stats(source_path, output_path)

    assert result["03-04-15-19-20-21"]["rank"] == 1
    assert result["01-04-09-10-11-23"]["rank"] == 2
    assert result["01-02-03-04-05-06"]["rank"] == 3


def test_senas_stats_calculates_relative_strength(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text(
        "0001) 03 04 15 19 20 21 44\n"
        "0002) 01 04 09 10 11 23 22\n",
        encoding="utf-8",
    )

    result = build_senas_stats(source_path, output_path)

    assert result["03-04-15-19-20-21"]["relative_strength"] == 1.0
    assert result["01-04-09-10-11-23"]["relative_strength"] == 0.5


def test_senas_stats_validates_sena_format(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text("0001) 03 04 15 19 20 20 44\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Nenhuma sena valida"):
        build_senas_stats(source_path, output_path)


def test_senas_stats_validates_number_range(tmp_path: Path) -> None:
    source_path = tmp_path / "senas.txt"
    output_path = tmp_path / "senas_stats.json"
    source_path.write_text("0001) 03 04 15 19 20 26 44\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Nenhuma sena valida"):
        build_senas_stats(source_path, output_path)


def test_load_senas_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_senas_stats(tmp_path / "missing_senas_stats.json")

    assert result == {}


def test_calculate_sena_score_loads_senas_stats(monkeypatch) -> None:
    loaded = False

    def fake_load_senas_stats() -> dict[str, dict[str, float | int]]:
        nonlocal loaded
        loaded = True
        return {}

    monkeypatch.setattr("lotoia.statistics.advanced.load_senas_stats", fake_load_senas_stats)

    calculate_sena_score([1, 2, 3, 4, 5, 6])

    assert loaded is True


def test_calculate_sena_score_calculates_scores(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_senas_stats",
        lambda: {
            "01-02-03-04-05-06": {"count": 44, "rank": 1, "relative_strength": 1.0},
            "01-02-03-04-05-07": {"count": 22, "rank": 2, "relative_strength": 0.5},
        },
    )

    result = calculate_sena_score([1, 2, 3, 4, 5, 6, 7])

    assert result["found_senas"] == 2
    assert result["total_count"] == 66
    assert result["average_count"] == 33
    assert result["average_rank"] == 1.5
    assert result["average_relative_strength"] == 0.75
    assert result["score"] == 75


def test_calculate_sena_score_is_normalized(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_senas_stats",
        lambda: {
            "01-02-03-04-05-06": {"count": 44, "rank": 1, "relative_strength": 1.5},
        },
    )

    result = calculate_sena_score([1, 2, 3, 4, 5, 6])

    assert 0 <= result["score"] <= 100
    assert result["score"] == 100


def test_calculate_sena_score_without_found_senas(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_senas_stats", lambda: {})

    result = calculate_sena_score([1, 2, 3, 4, 5, 6])

    assert result == {
        "found_senas": 0,
        "total_count": 0,
        "average_count": 0,
        "average_rank": 0,
        "average_relative_strength": 0,
        "score": 0,
        "top_senas": [],
    }


def test_calculate_sena_score_validates_numbers() -> None:
    with pytest.raises(ValueError, match="entre 1 e 25"):
        calculate_sena_score([0, 1, 2, 3, 4, 5])
