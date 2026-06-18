from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_route_inventory as route_inventory
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED

REMOVED_SIDEBAR_LABELS = (
    "Benchmark resumido",
    "Métricas HB",
    "Comparativos histórico",
    "Conferência por concurso",
    "Dezenas faltantes",
    "Dezenas sobrando",
    "Simulação Institucional / Backtesting",
    "Central ML Assistiva",
    "Vazamento Lateral Constitucional",
    "Evolução 13 -> 14",
    "Evolução 14 -> 15",
    "Núcleo Lei 15 — CORE_002",
    "Auditoria Runtime",
    "Auditoria Observacional",
    "Analítico observacional",
)

OFFICIAL_SIDEBAR_LABELS = (
    "Painel Inicial Institucional",
    "Gerador ADM CORE_002 — Geração Soberana Controlada",
    "Conferir Resultados — Auditoria de Lotes Persistidos",
    "Simular Resultados",
    "Histórico Analítico",
    "Histórico Institucional",
    "Cobertura Estrutural",
    "Central ML — Calibração Supervisionada",
    "Governança Institucional — read-only",
    "Área Restrita — Limpeza Controlada",
)


def test_build_marker_v38() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v47"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_official_sidebar_menu_has_ten_items() -> None:
    page_ids = route_inventory.official_sidebar_page_ids()
    assert len(page_ids) == 10
    assert page_ids == frozenset(route_inventory.INSTITUTIONAL_ALLOWED_PAGES) - {"fallback"}


def test_sidebar_source_uses_official_menu_constant() -> None:
    source = inspect.getsource(institutional_app._render_sidebar)
    assert "OFFICIAL_SIDEBAR_MENU" in source
    for label in REMOVED_SIDEBAR_LABELS:
        assert label not in source
    menu_labels = [label for _group, entries in route_inventory.OFFICIAL_SIDEBAR_MENU for label, _pid in entries]
    for label in menu_labels:
        assert label in str(route_inventory.OFFICIAL_SIDEBAR_MENU)


def test_legacy_routes_redirect_safely() -> None:
    assert route_inventory.resolve_institutional_page_id("institutional_simulation_backtesting") == "simulation"
    assert route_inventory.resolve_institutional_page_id("summary_benchmark") == "structural_coverage"
    assert route_inventory.resolve_institutional_page_id("hb_metrics") == "structural_coverage"
    assert route_inventory.resolve_institutional_page_id("comparative_history") == "structural_coverage"
    assert route_inventory.resolve_institutional_page_id("audit_monitoring_conference") == "conference"
    assert route_inventory.resolve_institutional_page_id("audit_monitoring_missing_numbers") == "structural_coverage"
    assert route_inventory.resolve_institutional_page_id("audit_monitoring_side_leak") == "central_ml_diagnostics"
    assert route_inventory.resolve_institutional_page_id("Central ML Assistiva") == "central_ml_diagnostics"
    assert route_inventory.resolve_institutional_page_id("core_002_read_only") == "governance_read_only"


def test_canonical_page_id_applies_m_vis_057_fallbacks() -> None:
    assert institutional_app._canonical_page_id("Benchmark resumido") == "structural_coverage"
    assert institutional_app._canonical_page_id("Simulação Institucional / Backtesting") == "simulation"
    assert institutional_app._canonical_page_id("Núcleo Lei 15 — CORE_002") == "governance_read_only"
    assert institutional_app._canonical_page_id("Conferência por concurso") == "conference"


@pytest.mark.parametrize(
    ("legacy_page_id", "expected_page"),
    [
        ("summary_benchmark", "structural_coverage"),
        ("institutional_simulation_backtesting", "simulation"),
        ("core_002_read_only", "governance_read_only"),
        ("audit_monitoring_conference", "conference"),
    ],
)
def test_sidebar_resolves_legacy_session_page_ids(
    monkeypatch: pytest.MonkeyPatch,
    legacy_page_id: str,
    expected_page: str,
) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    monkeypatch.setattr(institutional_app.st, "session_state", {"institutional_page_id": legacy_page_id})
    monkeypatch.setattr(institutional_app, "_apply_institutional_styles", lambda: None)
    monkeypatch.setattr(institutional_app, "_render_sidebar_logo", lambda: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "divider", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "expander", lambda *args, **kwargs: institutional_app.st.sidebar)
    monkeypatch.setattr(
        institutional_app.st.sidebar,
        "button",
        lambda label, **kwargs: False,
    )
    monkeypatch.setattr(institutional_app, "_resolve_active_commit", lambda: "test")
    monkeypatch.setattr(institutional_app, "_render_constitutional_status_panel", lambda **kwargs: None)

    page = institutional_app._render_sidebar(legacy_page_id, {"counts": {}, "latest": {}})

    assert page == expected_page


def test_route_inventory_active_routes_match_official_menu() -> None:
    payload = route_inventory.build_route_inventory_snapshot(app_build=BUILD_MARKER)
    active_ids = {row["page_id"] for row in payload["active_routes"]}
    assert active_ids == route_inventory.official_sidebar_page_ids()
    assert "core_002_read_only" not in active_ids
    assert payload["menu_cleanup_mission"] == "M-VIS-057"


def test_main_dispatch_keeps_core_pages() -> None:
    source = inspect.getsource(institutional_app.main)
    assert 'elif page == "structural_coverage"' in source
    assert 'elif page == "central_ml_diagnostics"' in source
    assert 'elif page == "conference"' in source
    assert 'elif page == "simulation"' in source
