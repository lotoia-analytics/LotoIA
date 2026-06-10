from __future__ import annotations

from lotoia.observability.ml_diagnostic_panels import (
    ALERT_SIDE_LEAK,
    CANDIDATE_FLAG_13_14,
    CANDIDATE_FLAG_14_15,
    build_evolution_13_14_panel_payload,
    build_evolution_14_15_panel_payload,
    build_side_leak_panel_payload,
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
                "numbers": sorted(NUCLEO | {5, 7}),
                "hits": 13,
            },
            {
                "game_index": 2,
                "numbers": sorted(NUCLEO | {6, 8}),
                "hits": 13,
            },
            {
                "game_index": 3,
                "numbers": sorted(NUCLEO | {5}),
                "hits": 14,
            },
            {
                "game_index": 4,
                "numbers": sorted(NUCLEO | {7, 15}),
                "hits": 14,
            },
        ],
    }


def test_side_leak_panel_flags_outside_nucleo() -> None:
    payload = build_side_leak_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["generation_command"] is False
    assert payload["rows"]
    dezenas = {row["dezena"] for row in payload["rows"]}
    assert "05" in dezenas
    assert "06" in dezenas
    assert payload["rows"][0]["frequencia_vazamento"] >= 1


def test_evolution_13_14_ranks_missing_dezenas() -> None:
    payload = build_evolution_13_14_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["games_analyzed"] == 2
    assert payload["candidate_flag"] == CANDIDATE_FLAG_13_14
    assert payload["rows"]
    assert payload["candidata_conversao"] == payload["rows"][0]["dezena_faltante"]


def test_evolution_14_15_ranks_missing_dezenas() -> None:
    payload = build_evolution_14_15_panel_payload(_sample_context())
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["games_analyzed"] == 2
    assert payload["candidate_flag"] == CANDIDATE_FLAG_14_15
    assert payload["rows"]


def test_side_leak_alert_when_threshold_exceeded() -> None:
    context = _sample_context()
    outside = sorted(set(range(1, 26)) - NUCLEO)[:3]
    context["games"] = [
        {"game_index": index, "numbers": sorted(NUCLEO | {outside[0]}), "hits": 12}
        for index in range(1, 5)
    ] + [
        {"game_index": 5, "numbers": sorted(NUCLEO | {outside[0]}), "hits": 12},
    ]
    payload = build_side_leak_panel_payload(context)
    assert payload["alert"] == ALERT_SIDE_LEAK
    assert payload["alert_dezenas"]
