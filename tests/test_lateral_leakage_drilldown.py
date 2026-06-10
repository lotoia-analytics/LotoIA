from __future__ import annotations

import pytest

from lotoia.observability.ml_diagnostic_panels import (
    ADM_ACEITO,
    ALERT_001,
    ALERT_SIDE_LEAK,
    build_alert_001_cards,
    build_lateral_leakage_evidence,
    build_side_leak_panel_payload,
    register_ml_diagnostic_decision,
)
from lotoia.observability.observational_leftover import ML_ROLE_DIAGNOSTIC_ONLY

OFFICIAL_15 = [1, 3, 5, 7, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
NUCLEO = {1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25}


def _context_with_leak(*, games: list[dict], run_id: int = 786) -> dict:
    return {
        "available": True,
        "source": "postgresql",
        "tables": "reconciliation_runs / reconciliation_games",
        "reconciliation_run_id": run_id,
        "contest_id": 3700,
        "generation_event_id": 501,
        "resultado_oficial": OFFICIAL_15,
        "games": games,
        "ml_role": ML_ROLE_DIAGNOSTIC_ONLY,
        "generation_command": False,
        "recalibration_command": False,
    }


def test_leakage_table_has_sample_size_and_run_id() -> None:
    games = [
        {
            "game_index": 1,
            "generation_event_id": 501,
            "numbers": sorted(NUCLEO | {6}),
            "hits": 10,
        },
        {
            "game_index": 2,
            "generation_event_id": 501,
            "numbers": sorted(NUCLEO | {6}),
            "hits": 10,
        },
    ]
    evidence = build_lateral_leakage_evidence(_context_with_leak(games=games))
    assert evidence["leakage_table"]
    row = evidence["leakage_table"][0]
    assert row["sample_size"] == 2
    assert row["reconciliation_run_id"] == 786
    assert "frequencia_vazamento" in row
    assert "percentual_vazamento" in row


def test_drilldown_per_dezena_has_required_columns() -> None:
    games = [
        {
            "game_index": 7,
            "generation_event_id": 909,
            "numbers": sorted(NUCLEO | {6, 8}),
            "hits": 11,
            "matched_numbers": [1, 3, 5, 7, 9, 11, 12, 13, 18, 20, 22],
        }
    ]
    evidence = build_lateral_leakage_evidence(_context_with_leak(games=games))
    drilldown = evidence["drilldown_per_dezena"]["06"][0]
    assert drilldown["dezena"] == "06"
    assert drilldown["jogo_id"] == 7
    assert drilldown["generation_event_id"] == 909
    assert drilldown["reconciliation_run_id"] == 786
    assert drilldown["concurso_analisado"] == 3700
    assert drilldown["cartao_final"] != "-"
    assert drilldown["resultado_oficial"] != "-"
    assert drilldown["hits"] == 11
    assert drilldown["sobra_real"]
    assert drilldown["vazou"] is True


def test_side_leak_panel_exposes_aggregate_and_drilldown() -> None:
    games = [
        {"game_index": 1, "generation_event_id": 1, "numbers": sorted(NUCLEO | {6}), "hits": 9}
        for _ in range(4)
    ] + [
        {"game_index": 5, "generation_event_id": 1, "numbers": sorted(NUCLEO), "hits": 12}
    ]
    payload = build_side_leak_panel_payload(_context_with_leak(games=games))
    assert payload["generation_command"] is False
    assert payload["recalibration_command"] is False
    assert payload["ml_role"] == ML_ROLE_DIAGNOSTIC_ONLY
    assert payload["leakage_table"][0]["sample_size"] == 5
    assert payload["drilldown_per_dezena"]
    assert payload["alert"] == ALERT_SIDE_LEAK


def test_alert_001_card_includes_leakage_evidence() -> None:
    games = [
        {"game_index": i, "generation_event_id": 1, "numbers": sorted(NUCLEO | {6}), "hits": 9}
        for i in range(1, 4)
    ]
    contexts = [
        _context_with_leak(games=games, run_id=10),
        _context_with_leak(games=games, run_id=9),
    ]
    cards = build_alert_001_cards(contexts)
    assert cards
    card = cards[0]
    assert card["tipo_alerta"] == ALERT_001
    evidence = card["leakage_evidence"]
    assert evidence["leakage_table"]
    assert evidence["drilldown_per_dezena"]


def test_register_alert_001_requires_drilldown_for_adr(tmp_path) -> None:
    db_path = tmp_path / "drill.db"
    with pytest.raises(ValueError, match="drilldown"):
        register_ml_diagnostic_decision(
            alert_type=ALERT_001,
            dezena=6,
            ml_proposal={"action": "propor_promocao_reserva_via_ADR", "target_dezena": "06"},
            adm_decision=ADM_ACEITO,
            reconciliation_run_id=1,
            db_path=db_path,
        )
