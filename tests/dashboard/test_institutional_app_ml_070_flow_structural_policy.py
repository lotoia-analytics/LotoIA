from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_structural_policy_coverage import (
    build_structural_policy_coverage_context,
    render_structural_policy_15d_operational_block,
)


def test_build_marker_v59() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v69"


def test_cobertura_page_renders_policy_block_before_diagnostics() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    policy_idx = source.index("render_structural_policy_15d_operational_block")
    diagnostics_idx = source.index("_render_structural_coverage_diagnostics_body")
    assert policy_idx < diagnostics_idx
    assert "build_structural_policy_coverage_context" in source


def test_policy_coverage_helpers_exist() -> None:
    assert callable(render_structural_policy_15d_operational_block)
    assert callable(build_structural_policy_coverage_context)
