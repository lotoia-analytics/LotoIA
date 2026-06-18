from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_route_inventory as route_inventory
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_build_marker_v33() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v34"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_canonical_page_id_accepts_active_page_ids() -> None:
    assert institutional_app._canonical_page_id("central_ml_diagnostics") == "central_ml_diagnostics"
    assert institutional_app._canonical_page_id("structural_coverage") == "structural_coverage"
    assert institutional_app._canonical_page_id("audit_monitoring_side_leak") == "audit_monitoring_side_leak"


def test_canonical_page_id_resolves_legacy_central_ml_labels() -> None:
    assert (
        institutional_app._canonical_page_id("Central de Diagnósticos ML")
        == "central_ml_diagnostics"
    )
    assert institutional_app._canonical_page_id("Central ML Assistiva") == "central_ml_diagnostics"
    assert (
        institutional_app._canonical_page_id("Central ML — Operacional Supervisionada")
        == "central_ml_diagnostics"
    )


def test_legacy_aliases_redirect_central_ml_routes() -> None:
    assert route_inventory.resolve_institutional_page_id("ml_diagnostics") == "central_ml_diagnostics"
    assert (
        route_inventory.resolve_institutional_page_id("institutional_supervised_ml")
        == "central_ml_diagnostics"
    )
    assert (
        route_inventory.resolve_institutional_page_id("Central de Diagnósticos ML")
        == "central_ml_diagnostics"
    )


def test_central_ml_in_allowed_pages_and_active_routes() -> None:
    assert "central_ml_diagnostics" in route_inventory.INSTITUTIONAL_ALLOWED_PAGES
    active_ids = {row["page_id"] for row in route_inventory.ACTIVE_ROUTE_ROWS}
    assert "central_ml_diagnostics" in active_ids


def test_sidebar_keeps_central_ml_route_without_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setattr(institutional_app.st, "session_state", {"institutional_page_id": "central_ml_diagnostics"})
    monkeypatch.setattr(institutional_app, "_apply_institutional_styles", lambda: None)
    monkeypatch.setattr(institutional_app, "_render_sidebar_logo", lambda: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "divider", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        institutional_app.st.sidebar,
        "button",
        lambda label, **kwargs: False,
    )
    monkeypatch.setattr(institutional_app, "_resolve_active_commit", lambda: "test")
    monkeypatch.setattr(institutional_app, "_render_constitutional_status_panel", lambda **kwargs: None)

    page = institutional_app._render_sidebar("central_ml_diagnostics", {"counts": {}, "latest": {}})

    assert page == "central_ml_diagnostics"
    assert page != "fallback"


def test_main_dispatch_includes_central_ml_diagnostics() -> None:
    source = inspect.getsource(institutional_app.main)
    assert 'elif page == "central_ml_diagnostics"' in source
    assert "_render_central_ml_diagnostics_page" in source


def test_page_targets_maps_central_ml_labels() -> None:
    assert institutional_app.PAGE_TARGETS["Central ML Assistiva"] == "central_ml_diagnostics"
    assert institutional_app.PAGE_TARGETS["Central de Diagnósticos ML"] == "central_ml_diagnostics"
