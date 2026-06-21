"""M-AUTO-CALIB-001 — API LotoIA calibração autônoma."""

from __future__ import annotations

import pytest

from lotoia.api.lotoia_calibration_api import (
    API_VERSION,
    BIAS_RATIO_THRESHOLD,
    FIDELITY_THRESHOLD,
    MISSION_ID,
    build_correction_commands,
    build_external_agent_payload,
    is_lotoia_auto_calib_api_enabled,
    process_sovereign_payload_with_lotoia_api,
)
from lotoia.observability.structural_fidelity_analytics import export_structural_diagnosis_for_lotoia_api


def _sample_games() -> list[dict]:
    return [
        {
            "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            "final_card_numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
            "card_format": 15,
        }
    ]


def test_mission_constants() -> None:
    assert MISSION_ID == "M-AUTO-CALIB-001"
    assert API_VERSION == "v1"
    assert FIDELITY_THRESHOLD == 90.0
    assert BIAS_RATIO_THRESHOLD == 2.0


def test_auto_calib_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOTOIA_AUTO_CALIB_API_ENABLED", raising=False)
    assert is_lotoia_auto_calib_api_enabled() is True
    monkeypatch.setenv("LOTOIA_AUTO_CALIB_API_ENABLED", "0")
    assert is_lotoia_auto_calib_api_enabled() is False


def test_export_structural_diagnosis_for_lotoia_api() -> None:
    bundle = {
        "available": True,
        "fidelity": {
            "structural_fidelity_score": 85.0,
            "official_contests_used": 50,
            "generated_profile": {number: 1 / 15 for number in range(1, 16)},
            "official_profile": {number: 1 / 15 for number in range(1, 16)},
        },
        "bias_report": {
            "verdict": "moderado",
            "compliance": False,
            "ratio_rows": [{"kind": "prefix", "pattern": "01-02-03", "ratio": 2.5, "severity": "moderado"}],
        },
        "quadrant_generated": {"Q1 (01–06)": 0.5, "Q2 (07–12)": 0.2, "Q3 (13–18)": 0.2, "Q4 (19–25)": 0.1},
        "quadrant_official": {"Q1 (01–06)": 0.25, "Q2 (07–12)": 0.25, "Q3 (13–18)": 0.25, "Q4 (19–25)": 0.25},
    }
    diagnosis = export_structural_diagnosis_for_lotoia_api(bundle)
    assert diagnosis["structural_fidelity_score"] == 85.0
    assert diagnosis["max_bias_ratio"] == 2.5
    assert diagnosis["consumer_mission_id"] == "M-AUTO-CALIB-001"


def test_build_correction_commands_for_quadrant_gap() -> None:
    diagnosis = {
        "structural_fidelity_score": 80.0,
        "quadrant_gaps": [{"quadrant": "Q1 (01–06)", "official_share": 0.3, "generated_share": 0.1}],
        "bias_patterns": [],
    }
    commands = build_correction_commands(diagnosis, game_size=15)
    assert any(command.get("kind") == "column_dispersion" for command in commands)


def test_external_agent_payload_schema() -> None:
    evaluation = {
        "evaluated_at": "2026-06-21T00:00:00+00:00",
        "sovereignty_passed": False,
        "requires_recalibration": True,
        "structural_fidelity_score": 72.0,
        "max_bias_ratio": 2.4,
        "correction_commands": [{"kind": "fidelity_recovery"}],
        "diagnosis": {"fidelity_status": {"level": "warning"}},
        "insights": [],
    }
    payload = build_external_agent_payload(evaluation, governance={"auto_recalibrated": True})
    assert payload["schema"] == "lotoia.calibration.v1"
    assert payload["integration_hints"]["next_action"] == "regenerate_with_calibration_plan"


def test_process_sovereign_payload_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_AUTO_CALIB_API_ENABLED", "0")
    result = process_sovereign_payload_with_lotoia_api(
        {},
        games=_sample_games(),
        batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        auto_calib_attempt=0,
    )
    assert result["should_regenerate"] is False


def test_fastapi_lotoia_routes_registered() -> None:
    from backend.main import app

    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/api/lotoia/v1/status" in paths
    assert "/api/lotoia/v1/structural/diagnose" in paths
    assert "/api/lotoia/v1/structural/calibrate" in paths


def test_central_ml_cockpit_supports_audit_only_mode() -> None:
    import inspect

    from dashboard.institutional_ml_calibration_cockpit import render_ml_calibration_cockpit

    source = inspect.getsource(render_ml_calibration_cockpit)
    assert "audit_only" in source
    assert "M-AUTO-CALIB-001" in source


def test_build_marker_v98() -> None:
    from dashboard.institutional_build import BUILD_MARKER

    assert BUILD_MARKER == "institutional-adm-runtime-v98"
