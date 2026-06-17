from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_assistive as ml_assistive
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v24"


def test_ml_assistive_module_imports() -> None:
    assert callable(ml_assistive.build_ml_assistive_snapshot)
    assert callable(ml_assistive.render_ml_assistive_governance_section)
    assert callable(ml_assistive.render_constitutional_side_leak_section)


def test_ml_assistive_snapshot_has_required_security_fields() -> None:
    payload = ml_assistive.build_ml_assistive_snapshot()
    text_blob = str(payload)

    assert payload["generation_cmd"] is False
    assert payload["recalibration_cmd"] is False
    assert payload["ml_operacional"] is True
    assert payload["decision_trace_enabled"] is True
    assert payload["feature_attribution_enabled"] is True
    assert "Guardião Analítico Assistivo" in text_blob or "operacional supervisionado" in text_blob
    assert "geracao_por_ml" in payload["ml_security_status"]
    assert payload["ml_security_status"]["promocao_automatica"] == "proibida"
    assert len(payload["ml_six_bases_relation"]) == 6
    assert len(payload["separation_matrix"]) == 5
    assert "M-VIS-036" in text_blob


def test_ml_assistive_snapshot_read_only_when_ml_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "0")
    payload = ml_assistive.build_ml_assistive_snapshot()
    assert payload["ml_operacional"] is False
    assert "efeito operacional automático" in payload["guardian_quote"]


def test_side_leak_snapshot_has_constitutional_risks() -> None:
    payload = ml_assistive.build_constitutional_side_leak_snapshot()
    text_blob = str(payload)
    risks = {row["risco"] for row in payload["risk_rows"]}

    assert payload["generation_cmd"] is False
    assert payload["recalibration_cmd"] is False
    assert "Diagnóstico constitucional read-only" in payload["status"]
    assert "Bypass de caminho soberano" in risks
    assert "Relabeling indevido" in risks
    assert "Hit isolado como veredicto" in risks
    assert "Histórico confundido com Núcleo" in risks
    assert "diagnóstico read-only" in text_blob.lower() or "read-only" in text_blob


def test_ml_assistive_modules_are_read_only_without_operational_buttons() -> None:
    for func_name in (
        "render_ml_assistive_governance_section",
        "render_constitutional_side_leak_section",
    ):
        source = inspect.getsource(getattr(ml_assistive, func_name))
        forbidden = (
            "_run_clean_law15_generation",
            "generate_best_games",
            "execute_purge",
            "dry_run_history_cleanup",
            "st.button",
            "st.form",
        )
        for token in forbidden:
            assert token not in source, f"{func_name} must not contain {token}"


def test_central_ml_page_integrates_governance_section() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "render_ml_assistive_governance_section" in source
    assert "Guardião Analítico Assistivo" not in source  # lives in module
    assert "generation_cmd: `False`" in source
    assert "recalibration_cmd: `False`" in source
    assert "Diagnóstico ML observacional" in source


def test_side_leak_page_integrates_constitutional_section() -> None:
    source = inspect.getsource(institutional_app._render_audit_monitoring_page)
    assert "render_constitutional_side_leak_section" in source
    assert "Vazamento Lateral Constitucional" in source


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True
    assert result["games"] == []


def test_m_vis_034_regression_structural_coverage_module_exists() -> None:
    from dashboard import institutional_structural_coverage

    payload = institutional_structural_coverage.build_structural_coverage_snapshot(
        generation_blocked=True,
    )
    assert len(payload["six_bases_rows"]) == 6


def test_m_vis_033_regression_core_002_route_exists() -> None:
    assert "core_002_read_only" in institutional_app.PAGE_TARGETS.values()


def test_m_lei15_003_regression_sovereign_helpers_exist() -> None:
    assert callable(institutional_app._invoke_sovereign_adm_generate_best_games)
