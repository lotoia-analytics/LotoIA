"""M-UI-ML-001 — Central ML redesenhada como central de decisão operacional."""

from __future__ import annotations

import inspect

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS


MAIN_SECTIONS = (
    "Diagnóstico geral da saída",
    "Evidências e decisão",
    "Plano de calibração recomendado",
    "Comando supervisionado",
)

MOVED_TO_AUDIT_MARKERS = (
    "_render_ml_operational_hierarchy_card",
    "_render_structural_15d_pool_card",
    "_render_pre_final_pool_ml_card",
    "_render_authorized_plan_semantics_card",
    "_render_structural_policy_15d_card",
    "_render_agent_responsible_card",
    "_render_overlap_format_verdict",
    "_render_historical_hit_analytics_card",
    "_render_impact_card",
    "_render_result_card",
    "_render_technical_expanders",
)


def test_build_marker_v76() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v80"
    assert BUILD_MARKER not in DEPRECATED_BUILD_MARKERS


def test_main_layout_is_single_column_decision_flow() -> None:
    render_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    module_source = inspect.getsource(cockpit)
    assert "row1_col1" not in render_source
    assert "row2_col1" not in render_source
    assert "### Detalhes técnicos" not in render_source
    assert "_render_diagnosis_card" in render_source
    assert "_render_decision_evidence_card" in render_source
    assert "_render_recommendation_card" in render_source
    assert "_render_command_card" in render_source
    assert "_render_technical_audit_section" in render_source
    for section in MAIN_SECTIONS:
        assert section in module_source


def test_technical_content_moved_to_collapsed_audit() -> None:
    audit_source = inspect.getsource(cockpit._render_technical_audit_section)
    assert 'st.expander("🛡️ Auditoria Técnica", expanded=False)' in audit_source
    for marker in MOVED_TO_AUDIT_MARKERS:
        assert marker in audit_source


def test_diagnosis_main_view_is_operational_only() -> None:
    diagnosis_source = inspect.getsource(cockpit._render_diagnosis_card)
    assert "generation_event_ids" not in diagnosis_source
    assert "checksum" not in diagnosis_source
    assert "Similaridade média" in diagnosis_source
    assert "Formato" in diagnosis_source
    technical_source = inspect.getsource(cockpit._render_diagnosis_technical_details)
    assert "generation_event_ids" in technical_source
    assert "checksum" in technical_source


def test_decision_section_shows_verdict_without_duplicate_plan() -> None:
    decision_source = inspect.getsource(cockpit._render_decision_evidence_card)
    assert "Veredito ML" in decision_source or "_render_ml_verdict_block" in decision_source
    assert "Plano recomendado" not in decision_source
    assert "render_verdict_banner" in inspect.getsource(cockpit._render_ml_verdict_block)


def test_mission_ui_id_declared() -> None:
    assert cockpit.MISSION_UI_ID == "M-UI-ML-001"
