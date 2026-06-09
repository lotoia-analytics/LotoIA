import pytest

from lotoia.backtesting import BacktestResult

from dashboard.app import (
    _backtest_games_dataframe,
    _distribution_chart,
    _format_numbers,
    _games_dataframe,
    _score_correlation_chart,
)
from dashboard.institutional_app import OFFICIAL_15_GROUPS_REGISTRY, OFFICIAL_15_QUANTITY_TO_GROUP, _official_15_group_games_for_quantity
from dashboard import institutional_app as ia


def test_format_numbers_uses_two_digits() -> None:
    assert _format_numbers([1, 2, 10, 25]) == "01 02 10 25"


def test_games_dataframe_contains_scores_and_rank() -> None:
    dataframe = _games_dataframe(
        [
            {
                "numbers": [1, 2, 3, 4, 5],
                "odd": 3,
                "even": 2,
                "sum": 15,
                "final_score": {"final_score": 87.5, "components": {}},
                "quadra_score": {"found_quadras": 12, "average_rank": 123.4},
            }
        ]
    )

    assert dataframe.loc[0, "rank"] == 1
    assert dataframe.loc[0, "final_score"] == 87.5
    assert dataframe.loc[0, "quadras"] == 12


def test_backtest_dataframe_and_charts_are_created() -> None:
    result = BacktestResult(
        contests_analyzed=1,
        games_per_contest=1,
        pool_size=1,
        history_window=20,
        total_games=1,
        average_hits=11,
        hit_distribution={"11": 1, "12": 0, "13": 0, "14": 0, "15": 0},
        best_game=None,
        worst_game=None,
        average_winner_final_score=70,
        final_score_hit_correlation=0,
        contest_results=[
            {
                "contest": 100,
                "target_numbers": list(range(1, 16)),
                "best_hits": 11,
                "average_hits": 11,
                "games": [
                    {
                        "contest": 100,
                        "numbers": list(range(1, 16)),
                        "hits": 11,
                        "final_score": {"final_score": 70, "components": {}},
                        "quadra_score": {"found_quadras": 20, "average_rank": 300},
                    }
                ],
            }
        ],
    )

    dataframe = _backtest_games_dataframe(result)
    distribution_chart = _distribution_chart(result.hit_distribution)
    correlation_chart = _score_correlation_chart(result)

    assert dataframe.loc[0, "concurso"] == 100
    assert dataframe.loc[0, "acertos"] == 11
    assert distribution_chart.data
    assert correlation_chart.data


def test_official_group_registry_has_expected_sizes() -> None:
    assert {group: len(games) for group, games in OFFICIAL_15_GROUPS_REGISTRY.items()} == {
        "G50": 50,
        "G30": 30,
        "G20": 20,
        "G10": 10,
    }


def test_official_quantity_maps_to_group_and_package_size() -> None:
    for quantity, expected_group in ((10, "G10"), (20, "G20"), (30, "G30"), (50, "G50")):
        assert OFFICIAL_15_QUANTITY_TO_GROUP[quantity] == expected_group
        assert len(_official_15_group_games_for_quantity(quantity)) == quantity


def test_clean_runtime_strategy_display_is_archived_and_direct() -> None:
    strategy = ia._generation_strategy_display(15)

    assert strategy["generation_mode"] == "CLEAN_DIRECT_15_LAW_RUNTIME"
    assert strategy["policy_mode"] == "CLEAN_DIRECT_15_LAW_RUNTIME"
    assert strategy["legacy_generation_flow"] == "ARCHIVED"
    assert strategy["scientific_status"] == "CLEAN_DIRECT_15_LAW_RUNTIME"
    assert "Runtime Limpo ADM 15" in strategy["strategy_label"]


@pytest.mark.parametrize("requested_count", [10, 20, 30, 50])
def test_clean_runtime_generates_requested_quantity(monkeypatch, requested_count: int) -> None:
    candidates = [
        {"numbers": list(range(1, 26))},
        {"numbers": list(range(2, 26)) + [1]},
        {"numbers": list(range(3, 26)) + [1, 2]},
    ]
    monkeypatch.setattr(ia, "generate_ranked_games", lambda **kwargs: candidates * 4)

    games = ia._generate_direct_15_games(
        total_games=requested_count,
        seed=123,
        history_frequency={},
        latest_numbers=set(),
        batch_number_usage={},
        batch_profile_usage={},
        batch_total_games=requested_count,
        core_numbers=[],
        discouraged_numbers=[],
        max_frequency_ratio=1.0,
        min_frequency_ratio=0.0,
        preferred_profile_ratios={},
        odd_min=5,
        odd_max=10,
        even_min=5,
        even_max=10,
        sequence_max=15,
        coverage_min=0.0,
        entropy_min=0.0,
        repeat_min=0,
        repeat_max=15,
        preferred_parity_pairs=[],
        allowed_parity_pairs=[],
    )

    assert len(games) == requested_count
    assert all(len(game["numbers"]) == 15 for game in games)


def test_clean_runtime_reports_insufficient_candidates_when_fill_fails(monkeypatch) -> None:
    monkeypatch.setattr(ia, "generate_ranked_games", lambda **kwargs: [])
    monkeypatch.setattr(ia, "_select_subset_from_candidate", lambda *args, **kwargs: None)
    monkeypatch.setattr(ia, "_force_subset_from_universe", lambda *args, **kwargs: [])

    games = ia._generate_direct_15_games(
        total_games=10,
        seed=123,
        history_frequency={},
        latest_numbers=set(),
        batch_number_usage={},
        batch_profile_usage={},
        batch_total_games=10,
        core_numbers=[],
        discouraged_numbers=[],
        max_frequency_ratio=1.0,
        min_frequency_ratio=0.0,
        preferred_profile_ratios={},
        odd_min=5,
        odd_max=10,
        even_min=5,
        even_max=10,
        sequence_max=15,
        coverage_min=0.0,
        entropy_min=0.0,
        repeat_min=0,
        repeat_max=15,
        preferred_parity_pairs=[],
        allowed_parity_pairs=[],
    )

    assert games == []


def test_clean_runtime_strategy_avoids_legacy_group_materialization() -> None:
    strategy = ia._generation_strategy_display(15)

    assert strategy["generation_mode"] != "OFFICIAL_GROUP_MATERIALIZATION"
    assert strategy["policy_mode"] != "OFFICIAL_GROUP_MATERIALIZATION"


def test_clean_law15_generation_payload_is_isolated(monkeypatch) -> None:
    monkeypatch.setattr(ia, "_history_number_frequency", lambda: {})
    monkeypatch.setattr(ia, "_load_latest_contest_summary", lambda: {"dezenas": []})
    monkeypatch.setattr(ia, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        ia,
        "_generate_direct_15_games",
        lambda **kwargs: [
            {"numbers": list(range(1, 16))},
            {"numbers": list(range(2, 17))},
        ],
    )
    monkeypatch.setattr(
        ia,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
            "historical_deduplication_mode": "AUDIT_ONLY",
            "historical_duplicates_removed": 0,
        },
    )

    result = ia._run_clean_law15_generation(requested_count=10)

    assert result["generation_mode"] == "CLEAN_LAW15_ISOLATED_PAGE"
    assert result["policy_mode"] == "CLEAN_LAW15_ISOLATED_PAGE"
    assert result["selected_quantity"] == 10
    assert result["dezenas_por_jogo"] == 15
    assert result["batch_fill_strategy"] == "FILL_UNTIL_REQUESTED_QUANTITY"
    assert result["scientific_law_role"] == "COMMANDER"
    assert result["clean_adm_runtime_role"] == "EXECUTOR"
    assert result["output_commander_role"] == "AUDITOR"
    assert result["historical_deduplication_mode"] == "AUDIT_ONLY"
    assert result["historical_duplicates_removed"] == 0
    assert result["legacy_generation_flow"] == "ARCHIVED"
    assert result["legacy_dashboard_generation"] == "BYPASSED"
    assert result["legacy_calibrator_role"] == "REMOVED_FROM_RUNTIME"
    assert result["calibration_engine_role"] == "DISABLED"


@pytest.mark.parametrize("requested_count", [10, 20, 30, 50])
def test_clean_law15_generation_page_requests_operational_sizes(monkeypatch, requested_count: int) -> None:
    monkeypatch.setattr(ia, "_history_number_frequency", lambda: {})
    monkeypatch.setattr(ia, "_load_latest_contest_summary", lambda: {"dezenas": []})
    monkeypatch.setattr(ia, "load_all_output_signatures", lambda: [])

    def fake_generate_direct_15_games(**kwargs):
        total_games = int(kwargs.get("total_games", 0) or 0)
        return [{"numbers": list(range(1, 16))} for _ in range(total_games)]

    monkeypatch.setattr(ia, "_generate_direct_15_games", fake_generate_direct_15_games)
    monkeypatch.setattr(
        ia,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
            "historical_deduplication_mode": "AUDIT_ONLY",
            "historical_duplicates_removed": 0,
        },
    )

    result = ia._run_clean_law15_generation(requested_count=requested_count)

    assert len(result["games"]) == requested_count
    assert result["fill_diagnostics"]["fill_completed"] is True
    assert result["fill_diagnostics"]["insufficient_reason"] == "none"
