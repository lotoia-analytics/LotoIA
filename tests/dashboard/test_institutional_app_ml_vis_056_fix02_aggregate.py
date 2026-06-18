from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import (
    AGGREGATE_DIAGNOSIS_HEADLINE,
    AGGREGATE_SCOPE_LABEL,
    VIS_COCKPIT_FIX02_MISSION_ID,
    build_cockpit_persist_bundle,
    build_ml_calibration_aggregate_context,
    build_ml_calibration_cockpit_snapshot,
)


def test_build_marker_v37() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v50"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_cockpit_main_render_has_no_lot_selector() -> None:
    render_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    assert "Lote analisado" not in render_source
    assert "selectbox" not in render_source
    assert "AGGREGATE_SCOPE_LABEL" in render_source
    expander_source = inspect.getsource(cockpit._render_technical_expanders)
    assert "Detalhes por lote" in expander_source
    assert "expanded=False" in expander_source


def test_cockpit_snapshot_aggregate_mode() -> None:
    event_details = [
        {
            "generation_event_id": 250,
            "batch_label": "CORE_002",
            "card_format": 15,
            "persisted_games": 5,
            "calibration_applied": True,
            "diversity_score": 0.42,
            "issues_detected": ["Quase repetidos elevado"],
            "calibration_diagnostics": {
                "issues": [{"tipo": "quase_repetidos_alto", "descricao": "Quase repetidos elevado"}],
                "redundancy": {"cartoes_quase_repetidos": 12, "sobreposicao_media": 9.5},
            },
            "created_at": "2026-06-17T12:00:00+00:00",
        },
        {
            "generation_event_id": 249,
            "batch_label": "CORE_002",
            "card_format": 16,
            "persisted_games": 3,
            "calibration_applied": False,
            "diversity_score": 0.61,
            "issues_detected": [],
            "calibration_diagnostics": {"issues": [], "redundancy": {}},
            "created_at": "2026-06-17T11:00:00+00:00",
        },
    ]
    aggregate = build_ml_calibration_aggregate_context(event_details)
    assert aggregate["available"] is True
    assert aggregate["scope_label"] == AGGREGATE_SCOPE_LABEL
    assert aggregate["headline"] == AGGREGATE_DIAGNOSIS_HEADLINE
    assert aggregate["total_events"] == 2
    assert aggregate["total_games"] == 8
    assert len(aggregate["lot_rows"]) == 2
    assert any(row["formato"] == "16D" for row in aggregate["format_breakdown"])


def test_persist_bundle_uses_aggregate_scope() -> None:
    bundle = build_cockpit_persist_bundle(
        workflow_status="pendente",
        decision_at="2026-06-17T12:00:00+00:00",
        apply_next_generation=False,
        recommendations=["Manter calibração"],
    )
    assert bundle["fix_mission_id"] == VIS_COCKPIT_FIX02_MISSION_ID
    assert bundle["cockpit_scope"] == "aggregate"
    assert "authorized_event_id" not in bundle


def test_cockpit_snapshot_signature_has_no_generation_event_id() -> None:
    signature = inspect.signature(build_ml_calibration_cockpit_snapshot)
    assert "generation_event_id" not in signature.parameters
