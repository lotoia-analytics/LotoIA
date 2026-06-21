"""M-UI-MENU-001 — Menu operacional limpo; governança oculta do sidebar."""

from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_route_inventory as route_inventory
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED

HIDDEN_MENU_LABELS = (
    "Governança Institucional — read-only",
    "Área Restrita — Limpeza Controlada",
    "Status Constitucional",
    "Central ML — Calibração Supervisionada",
)

OPERATIONAL_MENU_LABELS = (
    "Gerar Jogos",
    "Conferir Resultados",
    "Histórico Analítico",
    "Cobertura Estrutural",
    "Simular Resultados",
)


def test_build_marker_v88() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v96"


def test_official_sidebar_menu_has_eight_operational_items() -> None:
    page_ids = route_inventory.official_sidebar_page_ids()
    assert len(page_ids) == 8
    assert "governance_read_only" not in page_ids
    assert "restricted_controlled_cleanup" not in page_ids
    assert "central_ml_diagnostics" in page_ids
    assert page_ids <= route_inventory.INSTITUTIONAL_ALLOWED_PAGES


def test_hidden_sidebar_pages_remain_allowed() -> None:
    assert route_inventory.HIDDEN_SIDEBAR_PAGE_IDS == frozenset(
        {
            "governance_read_only",
            "restricted_controlled_cleanup",
        }
    )
    for page_id in route_inventory.HIDDEN_SIDEBAR_PAGE_IDS:
        assert page_id in route_inventory.INSTITUTIONAL_ALLOWED_PAGES


def test_sidebar_source_hides_governance_and_constitutional_status() -> None:
    source = inspect.getsource(institutional_app._render_sidebar)
    assert "OFFICIAL_SIDEBAR_MENU" in source
    assert "_render_constitutional_status_panel(compact=True)" not in source
    for label in HIDDEN_MENU_LABELS:
        assert label not in source


def test_official_menu_prioritizes_operational_flow() -> None:
    menu_labels = [
        label for _group, entries in route_inventory.OFFICIAL_SIDEBAR_MENU for label, _pid in entries
    ]
    assert menu_labels[: len(OPERATIONAL_MENU_LABELS)] == list(OPERATIONAL_MENU_LABELS)


def test_quick_access_excludes_governance() -> None:
    labels = [item["label"] for item in institutional_app.INSTITUTIONAL_QUICK_ACCESS]
    page_ids = [item["page_id"] for item in institutional_app.INSTITUTIONAL_QUICK_ACCESS]
    assert "Governança Institucional — read-only" not in labels
    assert "governance_read_only" not in page_ids
    assert "Central ML — Calibração Supervisionada" not in labels
    assert "central_ml_diagnostics" in page_ids
    assert labels[:3] == [
        "Gerar Jogos",
        "Conferir Resultados",
        "Histórico Analítico",
    ]


def test_governance_route_still_resolves_when_hidden(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    monkeypatch.setattr(institutional_app.st, "session_state", {"institutional_page_id": "governance_read_only"})
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

    page = institutional_app._render_sidebar("governance_read_only", {"counts": {}, "latest": {}})

    assert page == "governance_read_only"


def test_route_inventory_snapshot_marks_hidden_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = route_inventory.build_route_inventory_snapshot(app_build=BUILD_MARKER)
    active_ids = {row["page_id"] for row in payload["active_routes"]}
    removed_ids = {row["page_id"] for row in payload["removed_routes"]}

    assert payload["menu_ui_mission"] == "M-UI-MENU-001"
    assert "governance_read_only" not in active_ids
    assert "restricted_controlled_cleanup" not in active_ids
    assert "central_ml_diagnostics" in active_ids
    assert "governance_read_only" in removed_ids
    assert "restricted_controlled_cleanup" in removed_ids
    assert "central_ml_diagnostics" not in removed_ids
    assert set(payload["hidden_sidebar_page_ids"]) == set(route_inventory.HIDDEN_SIDEBAR_PAGE_IDS)
