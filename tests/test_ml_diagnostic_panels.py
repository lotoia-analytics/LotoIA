from __future__ import annotations

from lotoia.observability.ml_diagnostic_panels import (
    ALERT_SIDE_LEAK,
    CANDIDATE_FLAG_13_14,
    CANDIDATE_FLAG_14_15,
    _build_hits_distribution,
    build_evolution_13_14_panel_payload,
    build_evolution_14_15_panel_payload,
    build_side_leak_panel_payload,
    get_evolution_target_hits,
)
from lotoia.observability.observational_leftover import ML_ROLE_DIAGNOSTIC_ONLY

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
NUCLEO = {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25}


def _sample_context() -> dict:
    return {
        "available": True,
        "source": "postgresql",
        "tables": "reconciliation_runs / reconciliation_games",
        "reconciliation_run_id": 42,
        "contest_id": 3700,
        "resultado_oficial": OFFICIAL_15,
        "games": [
            {
                "game_index": 1,
                "numbers": sorted(NUCLEO),
                "hits": 13,
            },
            {
                "game_index": 2,
                "numbers": sorted(NUCLEO),
                "hits": 13,
            },
            {
                "game_index": 3,
                "numbers": sorted(NUCLEO),
                "hits": 14,
            },
            {
                "game_index": 4,
                "numbers": sorted(NUCLEO),
                "hits": 14,
            },
        ],
    }


def test_side_leak_panel_flags_sobra_real_dezenas() -> None:
    payload = build_side_leak_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["generation_command"] is False
    assert payload["leakage_table"]
    dezenas = {row["dezena"] for row in payload["leakage_table"]}
    assert "02" in dezenas
    assert payload["leakage_table"][0]["sample_size"] == 4
    assert payload["drilldown_per_dezena"]


def test_evolution_13_14_ranks_missing_dezenas() -> None:
    payload = build_evolution_13_14_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["games_analyzed"] == 2
    assert payload["count_hits_target"] == 2
    assert payload["hits_distribution"][13] == 2
    assert payload["hits_distribution"][14] == 2
    assert payload["candidate_flag"] == CANDIDATE_FLAG_13_14
    assert payload["rows"]
    assert payload["candidata_conversao"] == payload["rows"][0]["dezena_faltante"]


def test_evolution_14_15_ranks_missing_dezenas() -> None:
    payload = build_evolution_14_15_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["games_analyzed"] == 2
    assert payload["count_hits_target"] == 2
    assert payload["candidate_flag"] == CANDIDATE_FLAG_14_15
    assert payload["rows"]


def test_evolution_uses_normalized_hits_from_matched_numbers() -> None:
    context = _sample_context()
    context["hits_distribution"] = {13: 1, 14: 0, 15: 1}
    context["games"] = [
        {
            "game_index": 1,
            "numbers": sorted(NUCLEO),
            "hits": 0,
            "matched_numbers": sorted(OFFICIAL_15)[:13],
        }
    ]
    payload = build_evolution_13_14_panel_payload(context)
    assert payload["available"] is True
    assert payload["games_analyzed"] == 1
    assert payload["count_hits_target"] == 1


def test_evolution_empty_only_when_count_hits_target_zero() -> None:
    context = _sample_context()
    context["hits_distribution"] = {12: 2, 14: 1, 15: 1}
    context["games"] = [game for game in context["games"] if int(game.get("hits", 0) or 0) != 13]
    payload = build_evolution_13_14_panel_payload(context)
    assert payload["available"] is False
    assert payload["count_hits_target"] == 0
    assert payload["perfect_hits_count"] == 1


def test_build_hits_distribution_normalizes_int_hits() -> None:
    games = [
        {"hits": 13, "numbers": [], "matched_numbers": []},
        {"hits": "14", "numbers": [], "matched_numbers": []},
    ]
    distribution = _build_hits_distribution(games, OFFICIAL_15)
    assert distribution[13] == 1
    assert distribution[14] == 1


def test_get_evolution_target_hits_15d() -> None:
    assert get_evolution_target_hits(15) == [13, 14]


def test_get_evolution_target_hits_17d() -> None:
    assert get_evolution_target_hits(17) == [15, 16]


def test_get_evolution_target_hits_18d() -> None:
    assert get_evolution_target_hits(18) == [16, 17]


def test_side_leak_alert_when_threshold_exceeded() -> None:
    context = _sample_context()
    context["games"] = [
        {"game_index": index, "numbers": sorted(NUCLEO | {6}), "hits": 10}
        for index in range(1, 5)
    ] + [
        {"game_index": 5, "numbers": sorted(NUCLEO | {6}), "hits": 10},
    ]
    payload = build_side_leak_panel_payload(context)
    assert payload["alert"] == ALERT_SIDE_LEAK
    assert payload["alert_dezenas"]
    assert payload["drilldown_per_dezena"]["06"]
