from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_governance as institutional_governance
import dashboard.institutional_route_inventory as route_inventory
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v16"


def test_route_inventory_module_imports() -> None:
    assert callable(route_inventory.build_route_inventory_snapshot)
    assert callable(route_inventory.resolve_institutional_page_id)


def test_legacy_aliases_redirect_safely() -> None:
    assert route_inventory.resolve_institutional_page_id("generation") == "clean_law15_generation"
    assert route_inventory.resolve_institutional_page_id("clear_histories") == "restricted_controlled_cleanup"
    assert route_inventory.resolve_institutional_page_id("delete_history") == "restricted_controlled_cleanup"
    assert route_inventory.resolve_institutional_page_id("conference") == "conference"


def test_canonical_page_id_applies_legacy_aliases() -> None:
    assert institutional_app._canonical_page_id("generation") == "clean_law15_generation"
    assert institutional_app._canonical_page_id("delete_history") == "restricted_controlled_cleanup"
    assert institutional_app._canonical_page_id("Gerar Jogos") == "clean_law15_generation"


def test_route_inventory_snapshot_lists_constitutional_pages() -> None:
    payload = route_inventory.build_route_inventory_snapshot(app_build=BUILD_MARKER)
    text_blob = str(payload)

    assert payload["mission_id"] == "M-PLAT-040"
    active_ids = {row["page_id"] for row in payload["active_routes"]}
    assert "governance_read_only" in active_ids
    assert "core_002_read_only" in active_ids
    assert "structural_coverage" in active_ids
    assert "central_ml_diagnostics" in active_ids
    assert "restricted_controlled_cleanup" in active_ids
    assert "Conferir Resultados — Auditoria de Lotes Persistidos" in text_blob
    assert "Cobertura Estrutural" in payload["constitutional_labels"]
    assert any("Lei 15A" in label and "inoperante" in label for label in payload["constitutional_labels"])
    alias_sources = {row["alias"] for row in payload["alias_routes"]}
    assert "generation" in alias_sources
    assert "delete_history" in alias_sources


def test_route_inventory_module_has_no_generation_or_purge() -> None:
    source = inspect.getsource(route_inventory.render_route_inventory_section)
    forbidden = (
        "generate_best_games",
        "_generate_direct_15_games",
        "_purge_institutional_history_tables",
        "execute_purge",
        "st.button",
    )
    for token in forbidden:
        assert token not in source


def test_orphan_generation_redirects_to_blocked_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    monkeypatch.setattr(institutional_app.st, "session_state", {})
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

    page = institutional_app._render_sidebar("generation", {"counts": {}, "latest": {}})

    assert page == "clean_law15_generation"


def test_main_dispatch_has_no_orphan_generation_handler() -> None:
    source = inspect.getsource(institutional_app.main)
    assert 'elif page == "generation"' not in source
    assert "restricted_controlled_cleanup" in source


def test_governance_integrates_route_inventory() -> None:
    source = inspect.getsource(institutional_governance.render_governance_read_only_page)
    assert "render_route_inventory_section" in source


def test_governance_snapshot_includes_m_plat_040() -> None:
    payload = institutional_governance.build_governance_snapshot(
        app_build=BUILD_MARKER,
        active_commit="test",
        generation_blocked=True,
        inventory_reference="PR #124",
    )
    mission_ids = {row["id"] for row in payload["missions"]}
    block_codes = {row["codigo"] for row in payload["blocks"]}
    law_names = {row["nome"] for row in payload["laws"]}
    assert "M-PLAT-040" in mission_ids
    assert "BLK-LEGACY-ROUTES-001" in block_codes
    assert "Inventário Rotas ADM" in law_names


def test_public_app_not_modified() -> None:
    import dashboard.public_app

    source = inspect.getsource(dashboard.public_app)
    assert "institutional_route_inventory" not in source


def test_m_lei15_003_regression_batch_label_none_rejected() -> None:
    with pytest.raises(RuntimeError, match="batch_label=None"):
        institutional_app._resolve_adm_sovereign_batch_label(None)


def test_m_dados_039_regression_delete_history_alias() -> None:
    assert institutional_app._canonical_page_id("delete_history") == "restricted_controlled_cleanup"


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True
