"""M-ML-075-FIX-02 — separação semântica calibração pré-final vs plano autorizado N→N+1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import build_ml_calibration_result_card
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.ml.authorized_ml_calibration_plan import (
    MISSION_ID,
    PRE_FINAL_CALIBRATION_MISSION_ID,
    build_calibration_semantics_trace,
    build_calibration_semantics_ui_labels,
    build_runtime_calibration_plan_from_memory,
    build_validation_report_from_consumed_plan,
    mark_calibration_plan_consumed,
    patch_generation_event_calibration_semantics,
    persist_authorized_ml_calibration_plan,
)
from lotoia.operations.lot_operational_status import promote_post_calibration_consumer_lot_visibility

SAMPLE_PARAMS: dict[str, Any] = {
    "redundancy_penalty_boost": 1.25,
    "max_overlap_penalty": 1.2,
    "missing_numbers_boost": 1.4,
}


def _seed_generation_event(
    db_path: Path,
    *,
    event_id_context: dict[str, Any] | None = None,
) -> int:
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json=dict(event_id_context or {}),
            ml_enabled=1,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        )
        session.add(event)
        session.commit()
        return int(event.id or 0)


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for key in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "LOTOIA_DATABASE_POOLER_URL", "DATABASE_PUBLIC_URL"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "m_ml_075_fix_02.db"
    create_database(path)
    return path


def test_pre_final_separate_from_authorized_plan_applied() -> None:
    semantics = build_calibration_semantics_trace(
        ml_bundle={"calibration_applied": True, "pre_final_calibration_applied": True},
        pre_final_trace={"pre_final_calibration_applied": True},
        authorized_plan=build_runtime_calibration_plan_from_memory(
            {"source_generation_event_id": 10, "calibration_trace_id": "trace-1", "plan_items": ["a"]}
        ),
        ml_verdict="REPROVADO",
        gp_quality_tier="REPROVADO",
        target_generation_event_id=99,
    )
    assert semantics["pre_final_calibration_applied"] is True
    assert semantics["pre_final_calibration_mission_id"] == PRE_FINAL_CALIBRATION_MISSION_ID
    assert semantics["authorized_plan_loaded_from_db"] is True
    assert semantics["authorized_plan_applied_to_generation"] is True
    assert semantics["authorized_plan_source_generation_event_id"] == 10
    assert semantics["authorized_plan_target_generation_event_id"] == 99
    assert semantics["authorized_plan_mission_id"] == MISSION_ID
    assert semantics["ml_verdict_after_authorized_plan"] == "REPROVADO"
    assert semantics["gp_quality_tier_after_authorized_plan"] == "REPROVADO"
    assert semantics["calibration_applied"] is True
    assert semantics["calibration_applied_legacy_compatibility"] is True


def test_n_plus_1_reprovado_still_shows_authorized_plan_applied() -> None:
    semantics = build_calibration_semantics_trace(
        authorized_plan=build_runtime_calibration_plan_from_memory(
            {
                "source_generation_event_id": 5,
                "calibration_trace_id": "trace-reprov",
                "plan_items": ["item"],
                "parametros_sugeridos": SAMPLE_PARAMS,
            }
        ),
        ml_verdict="REPROVADO",
        gp_quality_tier="REPROVADO",
        target_generation_event_id=88,
    )
    assert semantics["authorized_plan_applied_to_generation"] is True
    assert semantics["ml_verdict_after_authorized_plan"] == "REPROVADO"
    labels = build_calibration_semantics_ui_labels(semantics)
    assert "aplicado nesta geração" in labels["authorized_plan_applied_label"]
    assert "REPROVADO" in labels["verdict_after_authorized_plan_label"]


def test_ui_labels_not_ambiguous() -> None:
    labels = build_calibration_semantics_ui_labels(
        {
            "pre_final_calibration_applied": True,
            "authorized_plan_loaded_from_db": True,
            "authorized_plan_applied_to_generation": False,
            "ml_verdict_after_authorized_plan": "APROVADO",
            "gp_quality_tier_after_authorized_plan": "APROVADO",
        }
    )
    assert "Calibração pré-final aplicada" in labels["pre_final_calibration_label"]
    assert "PostgreSQL" in labels["authorized_plan_loaded_label"]
    assert "não aplicado" in labels["authorized_plan_applied_label"]
    assert "calibration_applied" not in labels["pre_final_calibration_label"].lower()


def test_validation_report_uses_source_and_target_ids(db_path: Path) -> None:
    source_id = _seed_generation_event(
        db_path,
        event_id_context={
            "pre_final_pool_ml_calibration": {
                "final_diversity_score": 0.40,
                "final_similarity_score": 0.60,
            },
            "diversity_score": 0.40,
        },
    )
    target_id = _seed_generation_event(
        db_path,
        event_id_context={
            "authorized_plan_loaded_from_db": True,
            "authorized_plan_applied_to_generation": True,
            "authorized_plan_source_generation_event_id": source_id,
            "authorized_plan_target_generation_event_id": 0,
            "calibration_plan_loaded_from_db": True,
            "calibration_plan_applied_to_generation": True,
            "calibration_plan_source_generation_event_id": source_id,
            "pre_final_pool_ml_calibration": {
                "final_diversity_score": 0.55,
                "final_similarity_score": 0.45,
            },
            "diversity_score": 0.55,
            "ml_verdict_after_authorized_plan": "APROVADO",
            "gp_quality_tier_after_authorized_plan": "APROVADO",
        },
    )
    plan = persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["trace"],
        db_path=db_path,
    )
    mark_calibration_plan_consumed(
        int(plan["memory_row_id"]),
        target_generation_event_id=target_id,
        metrics_before={"diversity_score": 0.40, "similarity_score": 0.60, "sobreposicao_maxima": 0},
        metrics_after={"diversity_score": 0.55, "similarity_score": 0.45, "sobreposicao_maxima": 0},
        db_path=db_path,
    )
    patch_generation_event_calibration_semantics(
        target_id,
        semantics_patch=build_calibration_semantics_trace(
            authorized_plan=build_runtime_calibration_plan_from_memory(plan),
            ml_verdict="APROVADO",
            gp_quality_tier="APROVADO",
            target_generation_event_id=target_id,
        ),
        db_path=db_path,
    )
    consumed = {**plan, "target_generation_event_id": target_id, "status": "applied_once"}
    report = build_validation_report_from_consumed_plan(consumed, db_path=db_path)
    assert report["source_generation_event_id"] == source_id
    assert report["target_generation_event_id"] == target_id
    assert report["authorized_plan_source_generation_event_id"] == source_id
    assert report["authorized_plan_target_generation_event_id"] == target_id
    assert report["calibration_effect"] in {"improved", "neutral", "worsened", "insufficient_data"}
    assert report.get("authorized_plan_applied_to_generation") is True


def test_n_plus_1_loaded_from_db_flag_in_persist_context(
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import dashboard.institutional_app as institutional_app

    authorized_plan = build_runtime_calibration_plan_from_memory(
        persist_authorized_ml_calibration_plan(
            source_generation_event_id=42,
            parametros_sugeridos=SAMPLE_PARAMS,
            plan_items=["trace"],
            db_path=db_path,
        )
    )
    captured: dict[str, Any] = {}

    def _capture_persist(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"generation_event_id": 99, "batch_id": "test"}

    monkeypatch.setattr(institutional_app.st.session_state, "get", lambda key, default=None: {})
    monkeypatch.setattr(institutional_app, "_persist_generation_snapshot", _capture_persist)
    monkeypatch.setattr(institutional_app, "_attach_operational_generation_label", lambda x: x)
    monkeypatch.setattr(institutional_app, "_load_latest_contest_summary", lambda: None)
    monkeypatch.setattr(institutional_app, "_invalidate_operational_structural_cache", lambda: None)
    monkeypatch.setattr(institutional_app, "_supersede_prior_lots_for_calibration", lambda **_: None)
    monkeypatch.setattr(
        institutional_app,
        "validate_lei15_lei15a_runtime_contract",
        lambda **_: {"persistence_allowed": True},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_supervised_ml_persistence_bundle",
        lambda *a, **k: {
            "calibration_applied": False,
            "pre_final_calibration_applied": True,
            "policy_mode": "test",
        },
    )
    monkeypatch.setattr(
        institutional_app,
        "evaluate_batch_ml_verdict_from_games",
        lambda *a, **k: {"ml_verdict": "REPROVADO", "official_release_allowed": False},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_lot_status_context",
        lambda **_: {"official_release_allowed": False, "lot_operational_status": "pending"},
    )
    monkeypatch.setattr(
        institutional_app,
        "defer_lot_status_for_structural_coverage",
        lambda ctx, **_: ctx,
    )
    institutional_app._persist_clean_law15_generation_history(
        result={
            "games": [{"numbers": list(range(1, 16)), "core_numbers": list(range(1, 16))}],
            "authorized_calibration_plan": authorized_plan,
            "ml_enabled": True,
            "pre_final_pool_ml_calibration": {"pre_final_calibration_applied": True},
            "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
            "gp_quality_tier": "REPROVADO",
        },
        selected_card_format=15,
    )

    context = dict(captured.get("generation_context") or {})
    assert context.get("pre_final_calibration_applied") is True
    assert context.get("authorized_plan_loaded_from_db") is True
    assert context.get("authorized_plan_applied_to_generation") is True
    assert context.get("ml_verdict_after_authorized_plan") == "REPROVADO"
    assert context.get("pre_final_calibration_mission_id") == PRE_FINAL_CALIBRATION_MISSION_ID
    assert context.get("authorized_plan_mission_id") == MISSION_ID


def test_promotion_reprovado_keeps_authorized_plan_applied() -> None:
    plan = build_runtime_calibration_plan_from_memory(
        {
            "calibration_plan_loaded_from_db": True,
            "calibration_plan_applied_to_generation": True,
            "calibration_plan_source_generation_event_id": 7,
            "calibration_trace_id": "t-1",
            "plan_items": ["x"],
        }
    )
    promoted = promote_post_calibration_consumer_lot_visibility(
        {"lot_operational_status": "pending_structural_review", "ml_verdict": "REPROVADO"},
        authorized_plan=plan,
        promotion_context={
            "generated_games_count": 2,
            "requested_count": 2,
            "persistence_supported": True,
            "gp_quality_tier": "REPROVADO",
            "ml_verdict": "REPROVADO",
            "official_release_allowed": False,
        },
    )
    assert promoted["authorized_plan_applied_to_generation"] is True
    assert promoted["ml_verdict_after_authorized_plan"] == "REPROVADO"
    assert promoted.get("promoted_to_official_conference") is False


def test_result_card_ui_fields_not_ambiguous() -> None:
    card = build_ml_calibration_result_card(
        {
            "pre_final_calibration_applied": True,
            "authorized_plan_loaded_from_db": True,
            "authorized_plan_applied_to_generation": True,
            "ml_verdict_after_authorized_plan": "ATENÇÃO",
            "gp_quality_tier_after_authorized_plan": "ATENÇÃO",
            "calibration_applied": True,
        },
        workflow_status="applied",
        decision_at="2026-01-01T00:00:00Z",
        apply_next_generation=False,
    )
    assert card["pre_final_calibration_applied"] is True
    assert card["authorized_plan_applied_to_generation"] is True
    assert card["ml_verdict_after_authorized_plan"] == "ATENÇÃO"


def test_build_marker_v74() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v78"
