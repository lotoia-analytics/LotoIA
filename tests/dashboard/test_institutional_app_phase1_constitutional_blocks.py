from __future__ import annotations

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_light_mode as institutional_light_mode
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v24"
    assert institutional_app.SOVEREIGN_BATCH_LABEL == BATCH_LABEL


def test_institutional_light_mode_imports() -> None:
    assert callable(institutional_light_mode.is_light_mode_enabled)


def test_sovereign_generation_blocked_when_env_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    assert institutional_app._is_sovereign_generation_blocked() is True


def test_sovereign_generation_active_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    assert institutional_app._is_sovereign_generation_blocked() is False


def test_run_clean_law15_generation_returns_blocked_payload_when_env_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    result = institutional_app._run_clean_law15_generation(requested_count=10)

    assert result["blocked"] is True
    assert result["games"] == []
    assert result["analysis_batch_label"] == BATCH_LABEL
    assert "SOVEREIGN_GENERATION_BLOCKED" in str(result["commander_report"]["motivo_bloqueio"])


def test_orphan_generation_page_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    sidebar_calls: list[str] = []
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
        lambda label, **kwargs: sidebar_calls.append(str(label)),
    )
    monkeypatch.setattr(institutional_app, "_resolve_active_commit", lambda: "test")
    monkeypatch.setattr(institutional_app, "_render_constitutional_status_panel", lambda **kwargs: None)

    page = institutional_app._render_sidebar("generation", {"counts": {}, "latest": {}})

    assert page == "clean_law15_generation"


def test_constitutional_status_lines_blocked_when_env_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    lines = institutional_app._constitutional_status_lines()

    assert lines["core_id"] == "LEI15_CORE_002"
    assert lines["batch_label"] == BATCH_LABEL
    assert lines["generation_status"] == "BLOQUEADA"
    assert "REDEFINIDA" in lines["lei15a_status"]
    assert "INOPERANTE" in lines["lei15a_status"]
    assert "ASSISTIVO" in lines["ml_status"]
    assert lines["history_status"] == "PROTEGIDO"
    assert "M-GOV-030" in lines["gestao_projetos"]
    assert "PR #124" in lines["inventario_painel"]


def test_delete_history_page_source_has_no_active_purge_button() -> None:
    import inspect

    from dashboard import institutional_controlled_cleanup

    source = inspect.getsource(institutional_app._render_delete_history_page)
    assert "Apagar historico persistido" not in source
    assert "_purge_institutional_history_tables" not in source

    module_source = inspect.getsource(
        institutional_controlled_cleanup.render_restricted_controlled_cleanup_page
    )
    assert "CONTROLLED_CLEANUP_MANDATORY_QUOTE" in module_source
    assert "Purge Real — BLOQUEADO" in module_source
