from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_structural_coverage as structural_coverage
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v32"


def test_structural_coverage_module_imports() -> None:
    assert callable(structural_coverage.build_structural_coverage_snapshot)
    assert callable(structural_coverage.render_structural_coverage_governance_section)


def test_structural_coverage_snapshot_has_six_bases_and_alerts() -> None:
    payload = structural_coverage.build_structural_coverage_snapshot(generation_blocked=True)
    text_blob = str(payload)

    assert len(payload["six_bases_rows"]) == 6
    assert len(payload["institutional_alerts"]) == 3
    assert "LEI15_CORE_002" in text_blob
    assert BATCH_LABEL in text_blob
    assert payload["generation_status"] == "BLOQUEADA"
    assert structural_coverage.SIX_BASES_QUOTE in text_blob
    assert "Cobertura Estrutural não é promessa de acerto." in payload["institutional_alerts"]
    assert "diagnóstica e governamental" in text_blob
    assert "Nenhuma ação operacional" in text_blob


def test_structural_coverage_separates_sovereign_from_historical() -> None:
    payload = structural_coverage.build_structural_coverage_snapshot(generation_blocked=True)
    historical = {row["variante"]: row for row in payload["historical_evidence"]}

    assert historical["V1 (STRUCT_REALIGN_V1_15D_001)"]["soberano"] == "NÃO"
    assert historical["CAND-D (STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001)"]["soberano"] == "NÃO"
    assert historical["V2 / V3 / V4"]["soberano"] == "NÃO"
    assert historical["Baseline legado (STRUCT_TEST_15D_001)"]["soberano"] == "NÃO"
    assert historical["LEI15_CORE_002"]["soberano"] == "SIM"
    assert "V1" in payload["historical_assessments"]
    assert "CAND-D" in payload["historical_assessments"]


def test_structural_coverage_module_is_read_only_without_generation_or_purge() -> None:
    source = inspect.getsource(structural_coverage.render_structural_coverage_governance_section)
    forbidden = (
        "_run_clean_law15_generation",
        "_invoke_sovereign_adm_generate_best_games",
        "generate_best_games",
        "output_commander",
        "dry_run_history_cleanup",
        "execute_purge",
        "st.button",
        "st.form",
    )
    for token in forbidden:
        assert token not in source


def test_cobertura_page_integrates_governance_and_is_read_only() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "render_structural_coverage_governance_section" in source
    assert "LEI15_CORE_002" in source
    assert "Cobertura Operacional CORE_002" in source or "OPERATIONAL_COVERAGE_TITLE" in source
    assert "OPERATIONAL_SOURCE_CAPTION" in source or "generation_events / generated_games" in source
    forbidden = (
        "_run_clean_law15_generation",
        "generate_best_games",
        "execute_purge",
        "st.button",
    )
    for token in forbidden:
        assert token not in source


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True
    assert result["games"] == []


def test_m_vis_033_regression_core_002_route_exists() -> None:
    assert "core_002_read_only" in institutional_app.PAGE_TARGETS.values()
    assert institutional_app.PAGE_TARGETS["Núcleo Lei 15 — CORE_002"] == "core_002_read_only"


def test_m_lei15_003_regression_sovereign_path_helpers_exist() -> None:
    assert callable(institutional_app._invoke_sovereign_adm_generate_best_games)
    assert callable(institutional_app._resolve_adm_sovereign_batch_label)
