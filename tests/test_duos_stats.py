from pathlib import Path

import pytest

from lotoia.statistics.advanced import load_duos_stats
from scripts.build_duos_stats import build_duos_stats


def test_load_duos_stats_loads_json(tmp_path: Path) -> None:
    source_path = tmp_path / "duos_frequentes.csv"
    output_path = tmp_path / "duos_stats.json"
    source_path.write_text(
        "duo,frequency\n11-20,1408\n10-25,1404\n",
        encoding="utf-8",
    )

    build_duos_stats(source_path, output_path)

    result = load_duos_stats(output_path)

    assert result["11-20"] == {"frequency": 1408, "rank": 1}


def test_duos_stats_ranking_orders_by_highest_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "duos_frequentes.csv"
    output_path = tmp_path / "duos_stats.json"
    source_path.write_text(
        "duo,frequency\n10-25,1404\n11-20,1408\n1-2,1200\n",
        encoding="utf-8",
    )

    result = build_duos_stats(source_path, output_path)

    assert result["11-20"]["rank"] == 1
    assert result["10-25"]["rank"] == 2
    assert result["1-2"]["rank"] == 3


def test_duos_stats_keeps_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "duos_frequentes.txt"
    output_path = tmp_path / "duos_stats.json"
    source_path.write_text("11-20 1408\n", encoding="utf-8")

    result = build_duos_stats(source_path, output_path)

    assert result["11-20"]["frequency"] == 1408


def test_duos_stats_validates_duo_format(tmp_path: Path) -> None:
    source_path = tmp_path / "duos_frequentes.csv"
    output_path = tmp_path / "duos_stats.json"
    source_path.write_text("duo,frequency\n11-11,1408\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unicas"):
        build_duos_stats(source_path, output_path)


def test_duos_stats_validates_positive_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "duos_frequentes.csv"
    output_path = tmp_path / "duos_stats.json"
    source_path.write_text("duo,frequency\n11-20,0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="maior que zero"):
        build_duos_stats(source_path, output_path)


def test_load_duos_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_duos_stats(tmp_path / "missing_duos_stats.json")

    assert result == {}
