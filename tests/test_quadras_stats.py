from pathlib import Path

from lotoia.statistics.advanced import calculate_quadra_score, load_quadras_stats
from scripts.build_quadras_stats import build_quadras_stats


def test_load_quadras_stats_loads_json(tmp_path: Path) -> None:
    source_path = tmp_path / "quadras_frequentes.csv"
    output_path = tmp_path / "quadras_stats.json"
    source_path.write_text(
        "quadra,frequencia\n10-11-20-25,487\n1-2-3-4,500\n",
        encoding="utf-8",
    )

    build_quadras_stats(source_path, output_path)

    result = load_quadras_stats(output_path)

    assert result["10-11-20-25"] == {"frequency": 487, "rank": 2}


def test_quadras_stats_ranking_orders_by_highest_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "quadras_frequentes.csv"
    output_path = tmp_path / "quadras_stats.json"
    source_path.write_text(
        "quadra,frequencia\n10-11-20-25,487\n1-2-3-4,500\n5-6-7-8,499\n",
        encoding="utf-8",
    )

    result = build_quadras_stats(source_path, output_path)

    assert result["1-2-3-4"]["rank"] == 1
    assert result["5-6-7-8"]["rank"] == 2
    assert result["10-11-20-25"]["rank"] == 3


def test_quadras_stats_keeps_frequency(tmp_path: Path) -> None:
    source_path = tmp_path / "quadras_frequentes.txt"
    output_path = tmp_path / "quadras_stats.json"
    source_path.write_text("10-11-20-25 487\n", encoding="utf-8")

    result = build_quadras_stats(source_path, output_path)

    assert result["10-11-20-25"]["frequency"] == 487


def test_load_quadras_stats_returns_empty_dict_when_file_is_missing(tmp_path: Path) -> None:
    result = load_quadras_stats(tmp_path / "missing_quadras_stats.json")

    assert result == {}


def test_calculate_quadra_score_loads_quadras_stats(monkeypatch) -> None:
    loaded = False

    def fake_load_quadras_stats() -> dict[str, dict[str, int]]:
        nonlocal loaded
        loaded = True
        return {}

    monkeypatch.setattr("lotoia.statistics.advanced.load_quadras_stats", fake_load_quadras_stats)

    calculate_quadra_score([1, 2, 3, 4, 5])

    assert loaded is True


def test_calculate_quadra_score_identifies_found_quadras(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quadras_stats",
        lambda: {
            "1-2-3-4": {"frequency": 500, "rank": 1},
            "1-2-3-5": {"frequency": 400, "rank": 51},
        },
    )

    result = calculate_quadra_score([1, 2, 3, 4, 5])

    assert result["found_quadras"] == 2


def test_calculate_quadra_score_calculates_scores(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quadras_stats",
        lambda: {
            "1-2-3-4": {"frequency": 500, "rank": 10},
            "1-2-3-5": {"frequency": 300, "rank": 30},
        },
    )

    result = calculate_quadra_score([1, 2, 3, 4, 5])

    assert result["total_frequency"] == 800
    assert result["average_frequency"] == 400
    assert result["average_rank"] == 20


def test_calculate_quadra_score_without_found_quadras(monkeypatch) -> None:
    monkeypatch.setattr("lotoia.statistics.advanced.load_quadras_stats", lambda: {})

    result = calculate_quadra_score([1, 2, 3, 4, 5])

    assert result == {
        "found_quadras": 0,
        "total_frequency": 0,
        "average_frequency": 0,
        "average_rank": 0,
        "top_quadras": [],
    }


def test_calculate_quadra_score_identifies_top_quadras(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.statistics.advanced.load_quadras_stats",
        lambda: {
            "1-2-3-4": {"frequency": 500, "rank": 1},
            "1-2-3-5": {"frequency": 400, "rank": 50},
            "1-2-4-5": {"frequency": 300, "rank": 51},
        },
    )

    result = calculate_quadra_score([1, 2, 3, 4, 5])

    assert result["top_quadras"] == [
        {"quadra": "1-2-3-4", "frequency": 500, "rank": 1},
        {"quadra": "1-2-3-5", "frequency": 400, "rank": 50},
    ]
