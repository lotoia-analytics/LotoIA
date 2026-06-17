from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_core_002 as institutional_core_002
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v24"


def test_core_002_module_imports() -> None:
    assert callable(institutional_core_002.build_core_002_snapshot)
    assert callable(institutional_core_002.render_core_002_read_only_page)


def test_core_002_snapshot_contains_required_concepts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    payload = institutional_core_002.build_core_002_snapshot(generation_blocked=True)
    text_blob = str(payload)

    assert "LEI15_CORE_002" in text_blob
    assert BATCH_LABEL in text_blob
    assert "01–25" in payload["eligible_universe"]
    assert payload["reinforce_digits"] == [7, 12, 16, 23]
    assert payload["blind_spot_digits"] == [6, 16, 17]
    assert set(payload["contextual_penalty_digits"]) == {2, 4, 11, 15, 24, 25}
    assert set(payload["never_hard_block_digits"]) == {15, 24, 25}
    assert payload["controlled_prefix_digits"] == [1, 2, 3]
    assert set(payload["controlled_suffix_digits"]) == {22, 23, 24, 25}
    assert payload["generation_status"] == "BLOQUEADA"
    assert "INOPERANTE" in payload["lei15a_status"] or "REDEFINIDA" in payload["lei15a_status"]
    assert "ASSISTIVO" in payload["ml_status"]
    assert len(payload["six_bases_definitions"]) == 6
    assert "V1" in payload["six_bases_historical"]
    assert "CAND-D" in payload["six_bases_historical"]
    assert institutional_core_002.SIX_BASES_QUOTE in text_blob
    assert institutional_core_002.INSTITUTIONAL_MATRIX_QUOTE in text_blob


def test_core_002_matrix_has_25_eligible_digits() -> None:
    rows = institutional_core_002.build_sovereign_matrix_rows()
    assert len(rows) == 25
    assert all(row["papeis"].startswith("elegível") for row in rows)


def test_core_002_page_source_is_read_only_without_generation_or_purge() -> None:
    source = inspect.getsource(institutional_core_002.render_core_002_read_only_page)
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


def test_core_002_sidebar_route_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
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

    page = institutional_app._render_sidebar("core_002_read_only", {"counts": {}, "latest": {}})

    assert page == "core_002_read_only"


def test_cobertura_page_integrates_governance_section() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "render_structural_coverage_governance_section" in source
    assert "LEI15_CORE_002" in source
    assert "histórico não é núcleo" in source


def test_m_vis_031_and_lei15_regression_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True
    assert result["games"] == []


def test_historical_evidence_classifies_v1_and_cand_d_as_non_sovereign() -> None:
    payload = institutional_core_002.build_core_002_snapshot(generation_blocked=True)
    historical = {row["variante"]: row for row in payload["historical_evidence"]}
    assert historical["V1 (STRUCT_REALIGN_V1_15D_001)"]["soberano"] == "NÃO"
    assert historical["CAND-D (STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001)"]["soberano"] == "NÃO"
    assert historical["LEI15_CORE_002"]["soberano"] == "SIM"
