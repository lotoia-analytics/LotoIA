from __future__ import annotations

import inspect
from typing import Any

import dashboard.institutional_app as institutional_app
import dashboard.institutional_simulation_contests as simulation_contests
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_SIMULATION,
    STATUS_NOT_OFFICIALIZED,
)


def _sample_records(start: int, count: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for offset in range(count):
        contest_number = start + offset
        dezenas = list(range(1, 16))
        records.append(
            {
                "contest_number": contest_number,
                "data": "2026-01-01",
                "dezenas": dezenas,
            }
        )
    return records


def _sample_games(count: int = 3) -> list[dict[str, Any]]:
    return [
        {"numbers": list(range(1, 16))},
        {"numbers": list(range(2, 17))},
        {"numbers": list(range(3, 18))},
    ][:count]


def test_simulation_page_shows_contest_selection_block() -> None:
    source = inspect.getsource(institutional_app._render_simulation_page)
    assert "Concursos para comparação" in source
    assert "Comparar lote conferido contra concursos selecionados" in source
    assert "Lotes conferidos" in source
    assert "SELECTION_MODE_LABELS" in source
    assert "sim_contest_selection_mode" in source
    assert "Gerar lote laboratório" not in source


def test_resolve_last_10_contests() -> None:
    context = {
        "valid_contest_numbers": list(range(3600, 3660)),
        "max_contest": 3659,
    }
    selection = simulation_contests.resolve_simulation_contest_selection(
        context=context,
        selection_mode=simulation_contests.SELECTION_MODE_LAST_10,
    )
    assert selection["blocked"] is False
    assert selection["total_selected"] == 10
    assert selection["contest_initial"] == 3650
    assert selection["contest_final"] == 3659


def test_resolve_last_50_contests() -> None:
    context = {"valid_contest_numbers": list(range(3600, 3700))}
    selection = simulation_contests.resolve_simulation_contest_selection(
        context=context,
        selection_mode=simulation_contests.SELECTION_MODE_LAST_50,
    )
    assert selection["total_selected"] == 50
    assert selection["contest_final"] == 3699


def test_manual_range_blocks_more_than_50() -> None:
    context = {"valid_contest_numbers": list(range(3600, 3660))}
    selection = simulation_contests.resolve_simulation_contest_selection(
        context=context,
        selection_mode=simulation_contests.SELECTION_MODE_MANUAL_RANGE,
        manual_start=3600,
        manual_end=3659,
    )
    assert selection["blocked"] is True
    assert selection["contest_numbers"] == []
    assert "50" in selection["block_reason"]


def test_manual_range_allows_up_to_50() -> None:
    context = {"valid_contest_numbers": list(range(3600, 3660))}
    selection = simulation_contests.resolve_simulation_contest_selection(
        context=context,
        selection_mode=simulation_contests.SELECTION_MODE_MANUAL_RANGE,
        manual_start=3610,
        manual_end=3659,
    )
    assert selection["blocked"] is False
    assert selection["total_selected"] == 50


def test_compare_lab_games_hit_bands_11_to_15() -> None:
    games = [{"numbers": list(range(1, 16))}]
    records = _sample_records(1000, 3)
    payload = simulation_contests.compare_lab_games_against_contests(
        games=games,
        contest_records=records,
    )
    aggregate = payload["aggregate_summary"]
    assert aggregate["count_15_exact"] == 3
    assert aggregate["count_11_exact"] == 0
    assert payload["best_overall"]["best_hits"] == 15
    assert payload["contests_compared"] == 3


def test_central_ml_evidence_not_officialized() -> None:
    multicontest = simulation_contests.compare_lab_games_against_contests(
        games=_sample_games(),
        contest_records=_sample_records(2000, 5),
    )
    lab_result = {
        "lot_operational_status": STATUS_NOT_OFFICIALIZED,
        "selected_card_format": 15,
        "generation_event_id": 42,
        "ml_verdict": "APROVADO",
    }
    selection = simulation_contests.resolve_simulation_contest_selection(
        context={"valid_contest_numbers": list(range(2000, 2005))},
        selection_mode=simulation_contests.SELECTION_MODE_LAST_10,
    )
    evidence = simulation_contests.build_simulation_central_ml_evidence(
        multicontest_payload=multicontest,
        lab_result=lab_result,
        selection=selection,
    )
    assert evidence["lot_operational_status"] == STATUS_NOT_OFFICIALIZED
    assert evidence["officialization_blocked"] is True
    assert evidence["generation_origin"] == GENERATION_ORIGIN_SIMULATION
    assert evidence["calibration_evidence"]["does_not_officialize"] is True
    assert evidence["calibration_evidence"]["does_not_enter_analytical_history"] is True
    assert evidence["calibration_evidence"]["does_not_enter_conference"] is True
    assert "11" in evidence["hit_distribution"]


def test_multicontest_lab_uses_postgresql_selection(monkeypatch) -> None:
    records = _sample_records(3000, 30)

    monkeypatch.setattr(
        institutional_app,
        "_list_all_imported_contest_records",
        lambda: records,
    )
    monkeypatch.setattr(
        institutional_app,
        "_load_imported_contest",
        lambda contest_number: next(
            (record for record in records if record["contest_number"] == contest_number),
            None,
        ),
    )
    monkeypatch.setattr(
        institutional_app,
        "_persist_simulation_central_ml_evidence",
        lambda **kwargs: True,
    )

    payload = institutional_app._run_simulation_multicontest_lab(
        games=_sample_games(2),
        selection_mode=simulation_contests.SELECTION_MODE_LAST_20,
        lab_result={"lot_operational_status": STATUS_NOT_OFFICIALIZED, "selected_card_format": 15},
    )
    assert payload["contests_compared"] == 20
    assert payload["source"] == simulation_contests.SOVEREIGN_SOURCE_LABEL
    assert payload["aggregate_summary"]["count_15_exact"] >= 0
    assert payload["central_ml_evidence"]["contests_compared"] == 20


def test_simulation_multicontest_limit_constant_50() -> None:
    source = inspect.getsource(institutional_app._run_simulation_multicontest_lab)
    assert "SIMULATION_MAX_CONTESTS" in source
    assert simulation_contests.SIMULATION_MAX_CONTESTS == 50
