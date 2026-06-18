from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_controlled_cleanup as controlled_cleanup
import dashboard.institutional_governance as institutional_governance
import dashboard.institutional_route_inventory as route_inventory
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_controlled_cleanup_module_imports() -> None:
    assert callable(controlled_cleanup.build_controlled_cleanup_snapshot)
    assert callable(controlled_cleanup.render_restricted_controlled_cleanup_page)


def test_controlled_cleanup_snapshot_has_mandatory_quote_and_lei_001() -> None:
    payload = controlled_cleanup.build_controlled_cleanup_snapshot(
        table_counts={"generation_events": 3, "generated_games": 30, "imported_contests": 100},
        session_institutional_keys=["institutional_page_id"],
    )
    text_blob = str(payload)

    assert controlled_cleanup.CONTROLLED_CLEANUP_MANDATORY_QUOTE in text_blob
    assert "Lei 001" in payload["lei_001_guard"]
    assert payload["purge_real_status"] == "BLOQUEADO"
    assert payload["dry_run_status"] == "OBRIGATÓRIO PARA LIMPEZA FUTURA"
    assert payload["history_status"] == "PROTEGIDO"
    assert payload["mission_id"] == "M-DADOS-039"
    assert "generation_events" in payload["protected_tables"]
    assert "generated_games" in payload["protected_tables"]
    assert "imported_contests" in payload["protected_tables"]
    assert any(row["artefato"] == "scientific_institutional_memory" for row in payload["protected_evidence"])
    assert any(row["artefato"] == "scientific_calibration_decisions" for row in payload["protected_evidence"])
    assert any(row["artefato"] == "institutional_output_signatures" for row in payload["protected_evidence"])
    assert any("dry-run" in req.lower() for req in payload["dry_run_requirements"])
    assert any("Limpeza de sessão" in row["tipo"] for row in payload["cleanup_separation"])
    assert any(row["purge"] == "BLOQUEADO" for row in payload["cleanup_separation"])


def test_controlled_cleanup_module_has_no_real_purge_execution() -> None:
    source = inspect.getsource(controlled_cleanup.render_restricted_controlled_cleanup_page)
    forbidden = (
        "_purge_institutional_history_tables",
        "execute_purge",
        "dry_run_history_cleanup",
        "DELETE FROM",
        "generate_best_games",
        "_run_clean_law15_generation",
    )
    for token in forbidden:
        assert token not in source


def test_controlled_cleanup_purge_tab_has_no_destructive_button() -> None:
    source = inspect.getsource(controlled_cleanup.render_restricted_controlled_cleanup_page)
    assert "Apagar historico persistido" not in source
    assert "Purge Real — BLOQUEADO" in source


def test_restricted_cleanup_page_integrated_in_institutional_app() -> None:
    source = inspect.getsource(institutional_app._render_restricted_controlled_cleanup_page)
    assert "render_restricted_controlled_cleanup_page" in source
    assert "_purge_institutional_history_tables" not in source


def test_sidebar_uses_restricted_controlled_cleanup_label() -> None:
    source = inspect.getsource(institutional_app._render_sidebar)
    assert "OFFICIAL_SIDEBAR_MENU" in source
    page_ids = [page_id for _group, entries in route_inventory.OFFICIAL_SIDEBAR_MENU for _label, page_id in entries]
    labels = [label for _group, entries in route_inventory.OFFICIAL_SIDEBAR_MENU for label, _pid in entries]
    assert "restricted_controlled_cleanup" in page_ids
    assert "Área Restrita — Limpeza Controlada" in labels


def test_delete_history_alias_routes_to_restricted_area() -> None:
    source = inspect.getsource(institutional_app.main)
    assert "restricted_controlled_cleanup" in source
    assert "_render_restricted_controlled_cleanup_page" in source


def test_governance_snapshot_includes_m_dados_039() -> None:
    payload = institutional_governance.build_governance_snapshot(
        app_build=BUILD_MARKER,
        active_commit="test",
        generation_blocked=True,
        inventory_reference="PR #124",
    )
    mission_ids = {row["id"] for row in payload["missions"]}
    block_codes = {row["codigo"] for row in payload["blocks"]}
    assert "M-DADOS-039" in mission_ids
    assert "BLK-LEI001-001" in block_codes
    assert "BLK-HISTORICO-001" in block_codes


def test_m_vis_031_regression_delete_history_has_no_active_purge_button() -> None:
    source = inspect.getsource(institutional_app._render_delete_history_page)
    assert "Apagar historico persistido" not in source
    assert "_purge_institutional_history_tables" not in source


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True


def test_m_gov_038_regression_lei15a_inoperante() -> None:
    from dashboard import institutional_lei15a_governance as lei15a

    payload = lei15a.build_lei15a_governance_snapshot(generation_blocked=True)
    assert "INOPERANTE" in payload["formal_status"]


def test_m_vis_037_regression_conference_audit_exists() -> None:
    from dashboard import institutional_conference_audit

    payload = institutional_conference_audit.build_conference_audit_snapshot(
        generation_blocked=True,
        has_persisted_batches=False,
    )
    assert "Lei 001" in payload["lei_001_rule"]
