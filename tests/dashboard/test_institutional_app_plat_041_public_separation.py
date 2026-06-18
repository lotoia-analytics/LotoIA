from __future__ import annotations

import inspect

import pytest

import dashboard.entrypoint_inventory as entrypoint_inventory
import dashboard.institutional_app as institutional_app
import dashboard.public_app as public_app
import dashboard.public_surface as public_surface
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v36"


def test_public_app_imports_without_eager_institutional_main() -> None:
    source = inspect.getsource(public_app.main)
    assert "render_public_app" in source
    assert "resolve_dashboard_mode" in source
    assert "institutional_main()" not in source.replace("render_institutional_adm()", "")


def test_public_app_default_mode_is_public(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(entrypoint_inventory.ENV_DASHBOARD_MODE, raising=False)
    assert entrypoint_inventory.resolve_dashboard_mode() == "public"


def test_public_app_institutional_mode_requires_explicit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(entrypoint_inventory.ENV_DASHBOARD_MODE, "institutional")
    assert entrypoint_inventory.resolve_dashboard_mode() == "institutional"


def test_public_surface_snapshot_has_required_disclaimers() -> None:
    payload = public_surface.build_public_surface_snapshot(
        public_build=public_app.PUBLIC_APP_BUILD
    )
    text_blob = str(payload)

    assert "Canal público em preparação" in text_blob
    assert "Sem geração ativa" in text_blob
    assert "Sem apostas automáticas" in text_blob
    assert "Sem promessa de acerto" in text_blob
    assert "Sem acesso ao Painel ADM" in text_blob
    assert payload["mission_id"] == "M-PLAT-041"


def test_public_surface_does_not_expose_adm_routes_or_generation() -> None:
    source = inspect.getsource(public_surface.render_public_app)
    forbidden = (
        "institutional_app.main",
        "generate_best_games",
        "_generate_direct_15_games",
        "_purge_institutional_history_tables",
        "execute_purge",
        "delete_history",
        "Governança Institucional — read-only",
        "st.button",
    )
    for token in forbidden:
        assert token not in source

    not_offered = {item for item in public_surface.PUBLIC_NOT_OFFERED}
    assert "Governança Institucional — read-only" in not_offered
    assert any("Área Restrita" in item for item in not_offered)
    assert any("Simulação Institucional" in item for item in not_offered)
    assert any("Central ML Assistiva" in item for item in not_offered)


def test_public_app_main_does_not_call_adm_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(entrypoint_inventory.ENV_DASHBOARD_MODE, raising=False)
    calls: list[str] = []

    monkeypatch.setattr(public_app, "_configure_public_page", lambda: None)
    monkeypatch.setattr(public_app, "_render_public_boot_marker", lambda: None)
    monkeypatch.setattr(
        public_app,
        "render_public_app",
        lambda **kwargs: calls.append("public"),
    )
    monkeypatch.setattr(
        public_app,
        "render_institutional_adm",
        lambda: calls.append("adm"),
    )

    public_app.main()

    assert calls == ["public"]


def test_entrypoint_inventory_documents_railway_institutional() -> None:
    payload = entrypoint_inventory.build_entrypoint_inventory_snapshot(
        app_build=BUILD_MARKER,
        public_build=public_app.PUBLIC_APP_BUILD,
    )
    assert payload["railway_entrypoint"] == "dashboard/institutional_app.py"
    assert "Opção A aplicada" in payload["decision"]
    assert payload["default_mode"] == "public"
    entrypoints = {row["entrypoint"] for row in payload["entrypoints"]}
    assert "dashboard/institutional_app.py" in entrypoints
    assert "dashboard/public_app.py" in entrypoints


def test_railway_toml_uses_institutional_entrypoint() -> None:
    from pathlib import Path

    railway_toml = Path("railway.toml").read_text(encoding="utf-8")
    procfile = Path("Procfile").read_text(encoding="utf-8")
    assert "dashboard/institutional_app.py" in railway_toml
    assert "dashboard/institutional_app.py" in procfile
    assert "public_app.py" not in railway_toml


def test_governance_integrates_public_adm_separation() -> None:
    from dashboard import institutional_governance

    source = inspect.getsource(institutional_governance.render_governance_read_only_page)
    assert "render_public_adm_separation_section" in source


def test_m_lei15_003_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True


def test_m_plat_040_regression_legacy_alias_generation() -> None:
    assert institutional_app._canonical_page_id("generation") == "clean_law15_generation"


def test_m_dados_039_regression_delete_history_alias() -> None:
    assert (
        institutional_app._canonical_page_id("delete_history")
        == "restricted_controlled_cleanup"
    )
