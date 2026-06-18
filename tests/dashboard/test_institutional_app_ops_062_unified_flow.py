from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
import dashboard.institutional_simulation_contests as simulation_contests
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_SIMULATION,
    STATUS_NOT_OFFICIALIZED,
    STATUS_OFFICIALIZED,
)


def test_persist_path_sets_lot_operational_status() -> None:
    source = inspect.getsource(institutional_app._persist_clean_law15_generation_history)
    assert "build_lot_status_context" in source
    assert "lot_operational_status" in source
    assert "structural_validation_completed" in source


def test_simulation_uses_same_generator() -> None:
    source = inspect.getsource(institutional_app._run_simulation_lot_generation)
    assert "_run_clean_law15_generation" in source
    assert "GENERATION_ORIGIN_SIMULATION" in source
    assert "simulation_mode" in source


def test_simulation_multicontest_limit_50() -> None:
    source = inspect.getsource(institutional_app._run_simulation_multicontest_lab)
    assert "SIMULATION_MAX_CONTESTS" in source
    assert simulation_contests.SIMULATION_MAX_CONTESTS == 50


def test_conference_all_official_mode() -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "conference_all_official" in source
    assert "_resolve_latest_official_conference_contest" in source
    assert "is_official_conference_eligible" in source


def test_conference_page_auto_latest_contest() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "_load_official_conference_generation_groups" in source
    assert "conference_all_official=True" in source
    assert "Escolha o Concurso" not in source


def test_structural_coverage_filters_inactive_lots() -> None:
    from lotoia.observability import card_structure_diagnostics as csd

    source = inspect.getsource(csd.load_operational_card_structure_diagnostics_from_db)
    assert "_event_eligible_for_active_structural_reading" in source


def test_supersede_on_calibration() -> None:
    assert "_supersede_prior_lots_for_calibration" in dir(institutional_app)


def test_resolve_status_examples() -> None:
    from lotoia.operations.lot_operational_status import resolve_lot_operational_status
    from lotoia.ml.ml_operational_verdict import VERDICT_APROVADO, VERDICT_BLOQUEADO

    assert resolve_lot_operational_status(
        ml_verdict=VERDICT_APROVADO,
        official_release_allowed=True,
    ) == STATUS_OFFICIALIZED
    assert resolve_lot_operational_status(
        ml_verdict=VERDICT_BLOQUEADO,
        official_release_allowed=False,
        generation_origin=GENERATION_ORIGIN_SIMULATION,
        simulation_mode=True,
    ) == STATUS_NOT_OFFICIALIZED
