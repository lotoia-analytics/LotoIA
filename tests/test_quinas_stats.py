from pathlib import Path

import pytest

from lotoia.statistics.advanced import calculate_quina_score, load_quinas_stats
from scripts.build_quinas_stats import EXPECTED_QUINA_COUNT, build_quinas_stats


def test_load_quinas_stats_loads_json(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.csv"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text(
        "quina,frequency\n10-11-12-20-25,280\n1-2-3-4-5,300\n",
        encoding="utf-8",
    )

    build_quinas_stats(source_path, output_path)

    result = load_quinas_stats(output_path)

    assert result["10-11-12-20-25"] == {
        "count": 280,
        "rank": 2,
        "relative_strength": round(280 / EXPECTED_QUINA_COUNT, 3),
    }


def test_quinas_stats_json_has_official_shape(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.csv"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text("quina,count\n1-2-3-4-5,300\n", encoding="utf-8")

    result = build_quinas_stats(source_path, output_path)

    assert set(result["1-2-3-4-5"]) == {"count", "rank", "relative_strength"}


def test_quinas_stats_ranking_orders_by_highest_count(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.csv"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text(
        "quina,frequency\n10-11-12-20-25,280\n1-2-3-4-5,300\n5-6-7-8-9,290\n",
        encoding="utf-8",
    )

    result = build_quinas_stats(source_path, output_path)

    assert result["1-2-3-4-5"]["rank"] == 1
    assert result["5-6-7-8-9"]["rank"] == 2
    assert result["10-11-12-20-25"]["rank"] == 3


def test_quinas_stats_calculates_relative_strength(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.txt"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text("10-11-12-20-25 280\n", encoding="utf-8")

    result = build_quinas_stats(source_path, output_path)

    assert result["10-11-12-20-25"]["relative_strength"] == round(
        280 / EXPECTED_QUINA_COUNT,
        3,
    )


def test_quinas_stats_validates_quina_format(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.csv"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text("quina,frequency\n1-2-3-4-4,300\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unicas"):
        build_quinas_stats(source_path, output_path)


def test_quinas_stats_validates_positive_count(tmp_path: Path) -> None:
    source_path = tmp_path / "quinas_frequentes.csv"
    output_path = tmp_path / "quinas_stats.json"
    source_path.write_text("quina,frequency\n1-2-3-4-5,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="maior que zero"):
        build_quinas_stats(source_path, output_path)


def test_load_quinas_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_quinas_stats(tmp_path / "missing_quinas_stats.json")

    assert result == {}


def test_calculate_quina_score_loads_quinas_stats(monkeypatch) -> None:
    loaded = False

    def fake_load_quinas_stats() -> dict[str, dict[str, float | int]]:
        nonlocal loaded
        loaded = True
        return {}

    monkeypatch.setattr("lotoia.statistics.advanced.load_quinas_stats", fake_load_quinas_stats)

    calculate_quina_score([1, 2, 3, 4, 5, 6])

    assert loaded is True


def test_calculate_quina_score_identifies_found_quinas(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quinas_stats",
        lambda: {
            "1-2-3-4-5": {"count": 300, "rank": 1, "relative_strength": 1.44},
            "1-2-3-4-6": {"count": 280, "rank": 51, "relative_strength": 1.34},
        },
    )

    result = calculate_quina_score([1, 2, 3, 4, 5, 6])

    assert result["found_quinas"] == 2


def test_calculate_quina_score_calculates_scores(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quinas_stats",
        lambda: {
            "1-2-3-4-5": {"count": 300, "rank": 10, "relative_strength": 1.44},
            "1-2-3-4-6": {"count": 200, "rank": 30, "relative_strength": 0.96},
        },
    )

    result = calculate_quina_score([1, 2, 3, 4, 5, 6])

    assert result["total_count"] == 500
    assert result["average_count"] == 250
    assert result["average_rank"] == 20
    assert result["average_relative_strength"] == pytest.approx(1.2)


def test_calculate_quina_score_without_found_quinas(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_quinas_stats", lambda: {})

    result = calculate_quina_score([1, 2, 3, 4, 5, 6])

    assert result == {
        "found_quinas": 0,
        "total_count": 0,
        "average_count": 0,
        "average_rank": 0,
        "average_relative_strength": 0,
        "top_quinas": [],
    }


def test_calculate_quina_score_identifies_top_quinas(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quinas_stats",
        lambda: {
            "1-2-3-4-5": {"count": 300, "rank": 1, "relative_strength": 1.44},
            "1-2-3-4-6": {"count": 280, "rank": 50, "relative_strength": 1.34},
            "1-2-3-5-6": {"count": 200, "rank": 51, "relative_strength": 0.96},
        },
    )

    result = calculate_quina_score([1, 2, 3, 4, 5, 6])

    assert result["top_quinas"] == [
        {"quina": "1-2-3-4-5", "count": 300, "rank": 1, "relative_strength": 1.44},
        {"quina": "1-2-3-4-6", "count": 280, "rank": 50, "relative_strength": 1.34},
    ]


def test_calculate_quina_score_validates_numbers() -> None:
    with pytest.raises(ValueError, match="entre 1 e 25"):
        calculate_quina_score([0, 1, 2, 3, 4])
