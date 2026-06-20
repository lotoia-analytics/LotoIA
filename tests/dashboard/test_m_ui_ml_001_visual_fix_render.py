"""M-UI-ML-001-FIX — Central ML renderização nativa (sem HTML cru)."""

from __future__ import annotations

import inspect

import dashboard.institutional_ml_cockpit_visual as visual
from dashboard.institutional_build import BUILD_MARKER


def test_build_marker_v79_native_render() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v82"


def test_metric_grid_uses_native_streamlit_components() -> None:
    source = inspect.getsource(visual.render_metric_grid)
    assert "st.metric" in source
    assert "st.container(border=True)" in source
    assert "lotoia-cml-metric-grid" not in source


def test_section_shell_uses_native_container() -> None:
    source = inspect.getsource(visual.section_shell)
    assert "st.container(border=True)" in source


def test_display_reason_strips_hit_phrases() -> None:
    reason = (
        "ausência de captura 13/14/15 com redundância alta, "
        "política estrutural 15D não conforme [REPROVADO]"
    )
    cleaned = visual.sanitize_structural_display_reason(reason)
    assert "captura 13/14" not in cleaned.lower()
    assert "política estrutural 15d" in cleaned.lower()


def test_plan_filter_removes_capture_items() -> None:
    items = [
        "Aumentar penalidade de similaridade/overlap.",
        "Combinar elevação de diversidade para captura 13/14.",
        "Penalizar clones estruturais.",
    ]
    filtered = visual.filter_operational_plan_items(items)
    assert len(filtered) == 2
    assert all("captura" not in item.lower() for item in filtered)
