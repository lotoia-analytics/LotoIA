"""M-ML-073-FIX-01 — bloqueio hierárquico ML como estado operacional no Painel ADM."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_ml_hierarchy_block import (
    CENTRAL_ML_PRE_GP_BLOCK_MESSAGE,
    SESSION_HIERARCHY_BLOCK_KEY,
    build_central_ml_pre_gp_block_notice,
    build_hierarchy_blocked_generation_result,
    render_ml_hierarchy_block_panel,
)
from lotoia.ml.ml_operational_hierarchy import (
    QUALITY_TIER_REPROVADO,
    MlOperationalHierarchyBlockedError,
    STAGE_DIVERSITY,
    build_gp_quality_operational_payload,
    build_ml_hierarchy_block_operational_payload,
    is_ml_operational_hierarchy_block_error,
)


def _sample_hierarchy_bundle() -> dict[str, Any]:
    return {
        "mission_id": "M-ML-073",
        "ml_hierarchy_version": "M-ML-073-v2",
        "hierarchy_compliance": False,
        "gp_closure_allowed": False,
        "gp_delivery_blocked": True,
        "gp_delivery_block_reasons": ["pool_vazio"],
        "current_stage": STAGE_DIVERSITY,
        "blocking_reason": "pool_vazio",
        "blocking_responsible_agent": "agent_estatistico",
        "corrective_action_applied": ["rerank_diversidade", "expansao_pool_diversidade"],
        "stage_results": {
            STAGE_DIVERSITY: {
                "stage_id": STAGE_DIVERSITY,
                "stage_label": "Etapa 2: Diversidade",
                "status": "rejected",
                "passed": False,
                "failures": ["diversidade_baixa"],
                "corrective_actions": ["rerank_diversidade"],
                "responsible_agent": "agent_estatistico",
                "support_agents": ["agent_ml"],
            }
        },
        "stage_failures": ["diversidade_baixa"],
    }


def test_ml_operational_hierarchy_blocked_error_message_prefix() -> None:
    bundle = _sample_hierarchy_bundle()
    exc = MlOperationalHierarchyBlockedError.from_bundle(bundle)
    assert str(exc).startswith("[M-ML-073]")
    assert exc.hierarchy_bundle["blocking_reason"] == bundle["blocking_reason"]
    assert is_ml_operational_hierarchy_block_error(exc) is True


def test_common_runtime_error_not_masked() -> None:
    assert is_ml_operational_hierarchy_block_error(RuntimeError("[LEI15_CORE_002] falha")) is False


def test_build_hierarchy_blocked_generation_result_fields() -> None:
    bundle = _sample_hierarchy_bundle()
    exc = MlOperationalHierarchyBlockedError.from_bundle(bundle)
    result = build_hierarchy_blocked_generation_result(
        hierarchy_bundle=bundle,
        exception_message=str(exc),
        requested_count=5,
        seed=42,
        analysis_batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        ml_enabled=True,
    )
    block = dict(result.get("hierarchy_block") or {})
    assert result["hierarchy_blocked"] is True
    assert result["games"] == []
    assert block["status"] == "GP BLOQUEADO PELA HIERARQUIA ML"
    assert block["responsible_agent"] == "agent_estatistico"
    assert block["supporting_agents"] == ["agent_ml"]
    assert block["failed_stage"] == STAGE_DIVERSITY
    assert block["corrective_action_applied"]
    assert result["persistence_block_reason"] == CENTRAL_ML_PRE_GP_BLOCK_MESSAGE


def test_build_ml_hierarchy_block_operational_payload_trace() -> None:
    payload = build_ml_hierarchy_block_operational_payload(
        _sample_hierarchy_bundle(),
        exception_message="[M-ML-073] teste",
    )
    assert payload["primary_responsible_agent"] == "agent_estatistico"
    assert payload["stage_results"]
    assert payload["ml_operational_hierarchy_trace"]["gp_closure_allowed"] is False


def test_invoke_sovereign_catches_hierarchy_block(monkeypatch: pytest.MonkeyPatch) -> None:
    import dashboard.institutional_app as institutional_app

    bundle = _sample_hierarchy_bundle()

    def _raise_block(**kwargs: Any) -> dict[str, Any]:
        raise MlOperationalHierarchyBlockedError.from_bundle(bundle)

    monkeypatch.setattr(
        "lotoia.generator.basic_generator.generate_best_games",
        _raise_block,
    )
    monkeypatch.setattr(
        institutional_app,
        "resolve_authorized_calibration_plan",
        lambda cockpit_bundle: None,
    )
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    payload = institutional_app._invoke_sovereign_adm_generate_best_games(requested_count=5)

    assert payload.get("hierarchy_blocked") is True
    assert payload.get("games") == []
    assert str(payload.get("hierarchy_block_message", "")).startswith("[M-ML-073]")


def test_run_clean_law15_generation_returns_controlled_block(monkeypatch: pytest.MonkeyPatch) -> None:
    import dashboard.institutional_app as institutional_app

    bundle = _sample_hierarchy_bundle()
    monkeypatch.setattr(institutional_app, "_is_sovereign_generation_blocked", lambda: False)
    monkeypatch.setattr(institutional_app, "get_latest_official_contest", lambda: {"contest_number": 3500, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "hierarchy_blocked": True,
            "hierarchy_block_bundle": bundle,
            "hierarchy_block_message": MlOperationalHierarchyBlockedError.from_bundle(bundle),
            "games": [],
            "ml_enabled": True,
            "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        },
    )
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    result = institutional_app._run_clean_law15_generation(requested_count=5)

    assert result.get("hierarchy_blocked") is True
    assert result.get("games") == []
    assert result["commander_report"]["motivo_bloqueio"] == "ML_OPERATIONAL_HIERARCHY_GP_BLOCKED"
    assert result["hierarchy_block"]["responsible_agent"] == "agent_estatistico"


def test_render_ml_hierarchy_block_panel_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    import streamlit as st

    calls: list[str] = []
    monkeypatch.setattr(st, "markdown", lambda *args, **kwargs: calls.append("markdown"))
    monkeypatch.setattr(st, "error", lambda *args, **kwargs: calls.append("error"))
    monkeypatch.setattr(st, "warning", lambda *args, **kwargs: calls.append("warning"))
    monkeypatch.setattr(st, "info", lambda *args, **kwargs: calls.append("info"))
    monkeypatch.setattr(st, "columns", lambda n: [MagicMock() for _ in range(n)])
    monkeypatch.setattr(st, "expander", lambda *args, **kwargs: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None))
    monkeypatch.setattr(st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "caption", lambda *args, **kwargs: None)

    result = build_hierarchy_blocked_generation_result(
        hierarchy_bundle=_sample_hierarchy_bundle(),
        exception_message="[M-ML-073] bloqueio",
        requested_count=5,
        seed=1,
        analysis_batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        ml_enabled=True,
    )
    render_ml_hierarchy_block_panel(result)
    assert "error" in calls


def test_common_runtime_error_still_propagates_from_invoke(monkeypatch: pytest.MonkeyPatch) -> None:
    import dashboard.institutional_app as institutional_app

    def _raise_other(**kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("[LEI15_CORE_002] compose falhou")

    monkeypatch.setattr(
        "lotoia.generator.basic_generator.generate_best_games",
        _raise_other,
    )
    monkeypatch.setattr(
        institutional_app,
        "resolve_authorized_calibration_plan",
        lambda cockpit_bundle: None,
    )
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    with pytest.raises(RuntimeError, match="LEI15_CORE_002"):
        institutional_app._invoke_sovereign_adm_generate_best_games(requested_count=5)


def test_central_ml_pre_gp_block_notice() -> None:
    block = build_ml_hierarchy_block_operational_payload(_sample_hierarchy_bundle())
    notice = build_central_ml_pre_gp_block_notice({"pre_gp_hierarchy_block": block})
    assert notice.get("available") is True
    assert notice.get("message") == CENTRAL_ML_PRE_GP_BLOCK_MESSAGE
    assert notice.get("responsible_agent") == "agent_estatistico"


def test_build_gp_quality_operational_payload_delivered() -> None:
    bundle = {
        "hierarchy_applied": True,
        "gp_closure_allowed": False,
        "gp_quality_tier": QUALITY_TIER_REPROVADO,
        "gp_quality_reasons": ["diversity_score=0.36 abaixo de 0.55"],
        "gp_quality_classification": {
            "diversity_score": 0.36,
            "similarity_score": 9.47,
        },
        "stage_results": {
            STAGE_DIVERSITY: {
                "passed": False,
                "stage_label": "Etapa 2: Diversidade",
                "responsible_agent": "agent_estatistico",
            }
        },
        "blocking_responsible_agent": "agent_estatistico",
    }
    payload = build_gp_quality_operational_payload(bundle, delivered_count=20, requested_count=20)
    assert payload["gp_delivered"] is True
    assert payload["gp_quality_tier"] == QUALITY_TIER_REPROVADO
    assert payload["gp_delivered_count"] == 20


def test_build_marker_v69() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v81"


def test_session_snapshot_key_constant() -> None:
    assert SESSION_HIERARCHY_BLOCK_KEY == "adm_ml_hierarchy_block_snapshot"
