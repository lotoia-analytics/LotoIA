"""M-UI-ML-001 visual reference — Central ML cockpit styling."""

from __future__ import annotations

import inspect

import dashboard.institutional_ml_calibration_cockpit as cockpit
import dashboard.institutional_ml_cockpit_visual as visual
from dashboard.institutional_build import BUILD_MARKER


def test_build_marker_v77_visual_reference() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v78"


def test_cockpit_uses_visual_reference_layer() -> None:
    render_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    assert "inject_central_ml_visual_styles" in render_source
    assert "render_central_ml_header" in render_source
    assert "begin_section_shell" in render_source
    assert "render_metric_grid" in inspect.getsource(cockpit._render_diagnosis_card)
    assert "render_verdict_banner" in inspect.getsource(cockpit._render_ml_verdict_block)
    assert "render_plan_list" in inspect.getsource(cockpit._render_recommendation_card)


def test_visual_module_exposes_mission_reference_components() -> None:
    source = inspect.getsource(visual)
    assert "Decisão de Calibração" in source
    assert "lotoia-cml-metric-grid" in source
    assert "lotoia-cml-verdict" in source
    assert "lotoia-cml-plan-list" in source
