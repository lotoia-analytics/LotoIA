from pathlib import Path

import pytest

from lotoia.statistics.advanced import calculate_terno_score, load_ternos_stats
from scripts.build_ternos_stats import build_ternos_stats


def test_load_ternos_stats_loads_json(tmp_path: Path) -> None:
    source_path = tmp_path / "ternos_frequentes.csv"
    output_path = tmp_path / "ternos_stats.json"
    source_path.write_text(
        "terno,frequency\n10-20-25,842\n10-11-20,835\n",
        encoding="utf-8",
    )

    build_ternos_stats(source_path, output_path)

    result = load_ternos_stats(output_path)

    assert result["10-20-25"] == {"frequency": 842, "rank": 1}


def test_ternos_stats_ranking_orders_by_highest_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "ternos_frequentes.csv"
    output_path = tmp_path / "ternos_stats.json"
    source_path.write_text(
        "terno,frequency\n10-11-20,835\n10-20-25,842\n1-2-3,700\n",
        encoding="utf-8",
    )

    result = build_ternos_stats(source_path, output_path)

    assert result["10-20-25"]["rank"] == 1
    assert result["10-11-20"]["rank"] == 2
    assert result["1-2-3"]["rank"] == 3


def test_ternos_stats_keeps_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "ternos_frequentes.txt"
    output_path = tmp_path / "ternos_stats.json"
    source_path.write_text("10-20-25 842\n", encoding="utf-8")

    result = build_ternos_stats(source_path, output_path)

    assert result["10-20-25"]["frequency"] == 842


def test_ternos_stats_validates_terno_format(tmp_path: Path) -> None:
    source_path = tmp_path / "ternos_frequentes.csv"
    output_path = tmp_path / "ternos_stats.json"
    source_path.write_text("terno,frequency\n10-10-20,842\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unicas"):
        build_ternos_stats(source_path, output_path)


def test_ternos_stats_validates_positive_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "ternos_frequentes.csv"
    output_path = tmp_path / "ternos_stats.json"
    source_path.write_text("terno,frequency\n10-20-25,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="maior que zero"):
        build_ternos_stats(source_path, output_path)


def test_load_ternos_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_ternos_stats(tmp_path / "missing_ternos_stats.json")

    assert result == {}


def test_calculate_terno_score_loads_ternos_stats(monkeypatch) -> None:
    loaded = False

    def fake_load_ternos_stats() -> dict[str, dict[str, int]]:
        nonlocal loaded
        loaded = True
        return {}

    monkeypatch.setattr("lotoia.statistics.advanced.load_ternos_stats", fake_load_ternos_stats)

    calculate_terno_score([1, 2, 3, 4])

    assert loaded is True


def test_calculate_terno_score_identifies_found_ternos(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_ternos_stats",
        lambda: {
            "1-2-3": {"frequency": 800, "rank": 1},
            "1-2-4": {"frequency": 700, "rank": 51},
        },
    )

    result = calculate_terno_score([1, 2, 3, 4])

    assert result["found_ternos"] == 2


def test_calculate_terno_score_calculates_scores(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_ternos_stats",
        lambda: {
            "1-2-3": {"frequency": 800, "rank": 10},
            "1-2-4": {"frequency": 600, "rank": 30},
        },
    )

    result = calculate_terno_score([1, 2, 3, 4])

    assert result["total_frequency"] == 1400
    assert result["average_frequency"] == 700
    assert result["average_rank"] == 20


def test_calculate_terno_score_without_found_ternos(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_ternos_stats", lambda: {})

    result = calculate_terno_score([1, 2, 3, 4])

    assert result == {
        "found_ternos": 0,
        "total_frequency": 0,
        "average_frequency": 0,
        "average_rank": 0,
        "top_ternos": [],
    }


def test_calculate_terno_score_identifies_top_ternos(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_ternos_stats",
        lambda: {
            "1-2-3": {"frequency": 800, "rank": 1},
            "1-2-4": {"frequency": 700, "rank": 50},
            "1-3-4": {"frequency": 600, "rank": 51},
        },
    )

    result = calculate_terno_score([1, 2, 3, 4])

    assert result["top_ternos"] == [
        {"terno": "1-2-3", "frequency": 800, "rank": 1},
        {"terno": "1-2-4", "frequency": 700, "rank": 50},
    ]
