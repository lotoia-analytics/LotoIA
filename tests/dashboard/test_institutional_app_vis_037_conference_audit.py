from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_conference_audit as conference_audit
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v22"


def test_conference_audit_module_imports() -> None:
    assert callable(conference_audit.build_conference_audit_snapshot)
    assert callable(conference_audit.render_conference_governance_section)


def test_conference_audit_snapshot_has_lei_001_and_mandatory_quote() -> None:
    payload = conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=True,
        persisted_generation_events=3,
        persisted_games=30,
        reconciliation_runs=2,
    )
    text_blob = str(payload)

    assert conference_audit.CONFERENCE_MANDATORY_QUOTE in text_blob
    assert payload["sovereign_db"] == "PostgreSQL"
    assert "Lei 001" in payload["lei_001_rule"]
    assert "generation_events" in text_blob
    assert "generated_games" in text_blob
    assert "batch_label" in text_blob
    assert any("Conferência não gera jogos" in alert for alert in payload["institutional_alerts"])
    assert any("Conferência não simula resultado" in alert for alert in payload["institutional_alerts"])
    assert "session_state/cache/tela não são verdade operacional" in text_blob
    assert payload["batch_label_note"] == conference_audit.BATCH_LABEL_NOTE
    assert payload["generation_status"] == "BLOQUEADA"


def test_conference_audit_empty_state_messages() -> None:
    payload = conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=False,
    )
    messages = payload["empty_state_messages"]
    assert any("Sem lote persistido para conferir" in message for message in messages)
    assert any("Ação bloqueada por Lei 001" in message for message in messages)
    assert any("Simulação Institucional" in message for message in messages)


def test_conference_audit_rejects_non_sovereign_sources() -> None:
    payload = conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=True,
    )
    rejected = {row["fonte"] for row in payload["rejected_sources"]}
    assert "session_state" in rejected
    assert "CSV local" in rejected
    assert "cache" in rejected


def test_conference_audit_module_is_read_only_without_generation_or_purge() -> None:
    source = inspect.getsource(conference_audit.render_conference_governance_section)
    forbidden = (
        "_run_clean_law15_generation",
        "_run_institutional_simulation",
        "generate_best_games",
        "_generate_direct_15_games",
        "execute_purge",
        "dry_run_history_cleanup",
        "st.button",
        "st.form",
    )
    for token in forbidden:
        assert token not in source


def test_conference_page_integrates_governance_section() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "render_conference_governance_section" in source
    assert "Auditoria de lote persistido" in source
    assert "generate_best_games" not in source
    assert "_generate_direct_15_games" not in source


def test_run_institutional_conference_empty_batch_lei_001_message() -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "Sem lote persistido para conferir" in source
    assert "Lei 001" in source
    assert "Gere jogos em uma geração ativa" not in source


def test_conference_flow_separation_includes_simulation_and_backtesting() -> None:
    payload = conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=True,
    )
    flows = {row["fluxo"] for row in payload["flow_separation"]}
    assert "Conferir Resultados" in flows
    assert "Simular Resultados" in flows
    assert "Simulação Institucional / Backtesting" in flows
    assert "Geração operacional" in flows


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True


def test_m_vis_036_regression_simulation_backtesting_exists() -> None:
    from dashboard import institutional_simulation_backtesting

    payload = institutional_simulation_backtesting.build_simulation_backtesting_snapshot(
        generation_blocked=True,
    )
    assert "X-1" in payload["temporal_cut_rule"]


def test_m_lei15_003_regression_sovereign_helpers_exist() -> None:
    assert callable(institutional_app._invoke_sovereign_adm_generate_best_games)
