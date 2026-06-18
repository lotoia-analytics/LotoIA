from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_governance as institutional_governance
import dashboard.institutional_light_mode as institutional_light_mode
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v28"


def test_institutional_light_mode_imports() -> None:
    assert callable(institutional_light_mode.is_light_mode_enabled)


def test_governance_read_only_snapshot_contains_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    payload = institutional_governance.build_governance_snapshot(
        app_build=BUILD_MARKER,
        active_commit="a5a3f2f250b1",
        generation_blocked=True,
        inventory_reference="PR #124 — merge 328d26f",
    )
    text_blob = str(payload)

    assert institutional_governance.GOVERNANCE_READ_ONLY_ALERT in text_blob
    assert "Gestão de Projetos" in text_blob
    assert "M-GOV-030" in text_blob
    assert "M-OPS-INC-001" in text_blob
    assert "M-VIS-031" in text_blob
    assert "M-VIS-032" in text_blob
    assert "M-GOV-038" in text_blob
    assert "Lei 15A" in text_blob
    assert "Lei 001" in text_blob
    assert "Lei 15" in text_blob
    assert "ADR-047" in text_blob
    assert payload["generation_status"] == "BLOQUEADA"
    assert payload["purge_status"] == "PROTEGIDO"
    assert "read-only" in payload["read_only_alert"].lower()


def test_governance_page_source_is_read_only_without_generation_or_purge_calls() -> None:
    source = inspect.getsource(institutional_governance.render_governance_read_only_page)

    forbidden_calls = (
        "_run_clean_law15_generation",
        "output_commander",
        "dry_run_history_cleanup",
        "execute_purge",
        "st.button",
        "st.form",
    )
    for token in forbidden_calls:
        assert token not in source


def test_governance_sidebar_route_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
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

    page = institutional_app._render_sidebar("governance_read_only", {"counts": {}, "latest": {}})

    assert page == "governance_read_only"


def test_governance_module_reads_versioned_docs() -> None:
    payload = institutional_governance.build_governance_snapshot(
        app_build=BUILD_MARKER,
        active_commit="test",
        generation_blocked=True,
        inventory_reference="PR #124 — merge 328d26f",
    )
    assert "QUADRO_PROJETOS_MISSOES" in payload["quadro_excerpt"] or "Quadro" in payload["quadro_excerpt"]
    assert any(row["disponivel"] for row in payload["laws"])
