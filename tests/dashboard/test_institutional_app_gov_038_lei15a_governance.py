from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_governance as institutional_governance
import dashboard.institutional_lei15a_governance as lei15a_governance
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v36"


def test_lei15a_governance_module_imports() -> None:
    assert callable(lei15a_governance.build_lei15a_governance_snapshot)
    assert callable(lei15a_governance.render_lei15a_governance_section)


def test_lei15a_governance_snapshot_has_mandatory_quote_and_status() -> None:
    payload = lei15a_governance.build_lei15a_governance_snapshot(generation_blocked=True)
    text_blob = str(payload)

    assert lei15a_governance.LEI15A_MANDATORY_QUOTE in text_blob
    assert payload["formal_status"] == lei15a_governance.LEI15A_FORMAL_STATUS
    assert "REDEFINIDA" in payload["formal_status"]
    assert "FUTURA" in payload["formal_status"]
    assert "SUBORDINADA AO CORE_002" in payload["formal_status"]
    assert "INOPERANTE" in payload["formal_status"]
    assert payload["core_sovereignty"] == "LEI15_CORE_002 permanece soberano"
    assert payload["generation_status"] == "BLOQUEADA"
    assert payload["mission_id"] == "M-GOV-038"
    assert len(payload["constitutional_points"]) == 12
    assert any("15+1/15+2" in point for point in payload["constitutional_points"])
    assert any("generate_best_games" in item for item in payload["prohibitions"])
    assert any("NÃO REATIVADA" in row["valor"] for row in payload["status_rows"])


def test_lei15a_governance_module_is_read_only_without_generation_or_purge() -> None:
    source = inspect.getsource(lei15a_governance.render_lei15a_governance_section)
    forbidden = (
        "_run_clean_law15_generation",
        "_invoke_sovereign_adm_generate_best_games",
        "generate_best_games",
        "build_lei15a_operational_read",
        "execute_purge",
        "dry_run_history_cleanup",
        "st.button",
        "st.form",
    )
    for token in forbidden:
        assert token not in source


def test_governance_page_integrates_lei15a_section() -> None:
    source = inspect.getsource(institutional_governance.render_governance_read_only_page)
    assert "render_lei15a_governance_section" in source


def test_constitutional_status_lines_lei15a_redefined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    lines = institutional_app._constitutional_status_lines()

    assert "REDEFINIDA" in lines["lei15a_status"]
    assert "FUTURA" in lines["lei15a_status"]
    assert "SUBORDINADA AO CORE_002" in lines["lei15a_status"]
    assert "INOPERANTE" in lines["lei15a_status"]


def test_governance_snapshot_includes_m_gov_038_mission() -> None:
    payload = institutional_governance.build_governance_snapshot(
        app_build=BUILD_MARKER,
        active_commit="test",
        generation_blocked=True,
        inventory_reference="PR #124",
    )
    mission_ids = {row["id"] for row in payload["missions"]}
    assert "M-GOV-038" in mission_ids
    law_names = {row["nome"] for row in payload["laws"]}
    assert "Lei 15A" in law_names
    block_codes = {row["codigo"] for row in payload["blocks"]}
    assert "BLK-LEI15A-001" in block_codes


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True


def test_m_vis_033_regression_core_002_module_exists() -> None:
    from dashboard import institutional_core_002

    payload = institutional_core_002.build_core_002_snapshot(generation_blocked=True)
    assert "INOPERANTE" in payload["lei15a_status"] or "REDEFINIDA" in payload["lei15a_status"]


def test_m_vis_037_regression_conference_audit_exists() -> None:
    from dashboard import institutional_conference_audit

    payload = institutional_conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=False,
    )
    assert "Lei 001" in payload["lei_001_rule"]
