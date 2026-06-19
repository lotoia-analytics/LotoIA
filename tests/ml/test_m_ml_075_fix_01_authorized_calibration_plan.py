"""M-ML-075-FIX-01 — persistência e aplicação automática de calibração autorizada."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import resolve_authorized_calibration_plan
from lotoia.database.database import GeneratedGame, GenerationEvent, ScientificInstitutionalMemory, create_database, get_session
from lotoia.ml.authorized_ml_calibration_plan import (
    EFFECT_IMPROVED,
    EFFECT_NEUTRAL,
    MEMORY_KIND,
    MISSION_ID,
    STATUS_ACTIVE,
    STATUS_APPLIED_ONCE,
    build_runtime_calibration_plan_from_memory,
    build_validation_report_from_consumed_plan,
    compare_generations_n_vs_n1,
    extract_module_operational_params,
    load_active_authorized_ml_calibration_plan,
    mark_calibration_plan_consumed,
    persist_authorized_ml_calibration_plan,
    resolve_authorized_calibration_plan_from_db,
)
from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations
from lotoia.ml.ml_operational_hierarchy import build_gp_quality_classification


SAMPLE_PARAMS: dict[str, Any] = {
    "redundancy_penalty_boost": 1.25,
    "max_overlap_penalty": 1.2,
    "near_duplicate_penalty": 1.15,
    "prefix_penalty": 1.3,
    "suffix_penalty": 1.2,
    "missing_numbers_boost": 1.4,
    "diversity_floor_boost": 1.1,
    "discourage_penalty_boost": 1.2,
    "dezenas_subcobertas": ["07", "11", "23"],
    "prefixo_alvo": "01-02-03",
    "sufixo_alvo": "23-24-25",
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
    path = tmp_path / "m_ml_075_fix_01.db"
    create_database(path)
    return path


def test_persist_authorized_ml_calibration_plan(db_path: Path) -> None:
    source_id = _seed_generation_event(
        db_path,
        event_id_context={"diversity_score": 0.35, "pre_final_pool_ml_calibration": {"final_diversity_score": 0.35}},
    )
    persisted = persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["aumentar_penalidade_similaridade", "reforcar_dezenas_subcobertas"],
        db_path=db_path,
    )
    assert persisted["mission_id"] == MISSION_ID
    assert persisted["memory_kind"] == MEMORY_KIND
    assert persisted["status"] == STATUS_ACTIVE
    assert persisted["apply_to_next_generation"] is True
    assert persisted["authorized_by_operator"] is True
    assert int(persisted["memory_row_id"]) > 0
    assert persisted["parametros_sugeridos"]["redundancy_penalty_boost"] == 1.25

    with get_session(db_path) as session:
        row = session.get(ScientificInstitutionalMemory, int(persisted["memory_row_id"]))
        assert row is not None
        assert row.memory_kind == MEMORY_KIND
        assert row.structural_status == STATUS_ACTIVE


def test_n_plus_1_loads_plan_from_postgresql(db_path: Path) -> None:
    source_id = _seed_generation_event(db_path)
    persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["penalizar_overlap"],
        db_path=db_path,
    )
    loaded = resolve_authorized_calibration_plan_from_db(db_path)
    assert loaded is not None
    assert loaded["calibration_plan_loaded_from_db"] is True
    assert loaded["calibration_plan_applied_to_generation"] is True
    assert loaded["calibration_plan_source_generation_event_id"] == source_id
    assert loaded["parametros_sugeridos"]["max_overlap_penalty"] == 1.2


def test_session_state_absent_still_allows_application(db_path: Path) -> None:
    source_id = _seed_generation_event(db_path)
    persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["diversidade"],
        db_path=db_path,
    )
    plan = resolve_authorized_calibration_plan({}, db_path=db_path, prefer_database=True)
    assert plan is not None
    assert plan["calibration_plan_loaded_from_db"] is True
    assert plan.get("trace", {}).get("loaded_from_db") is True


def test_parametros_sugeridos_reach_m_ml_072(db_path: Path) -> None:
    plan = build_runtime_calibration_plan_from_memory(
        persist_authorized_ml_calibration_plan(
            source_generation_event_id=1,
            parametros_sugeridos=SAMPLE_PARAMS,
            plan_items=["pool_estrutural"],
            db_path=db_path,
        )
    )
    ops = extract_module_operational_params(plan)
    mp = ops["modules"]["M-ML-072"]
    assert ops["applied"] is True
    assert mp["missing_numbers_boost"] == 1.4
    assert mp["dezenas_subcobertas"] == ["07", "11", "23"]
    assert mp["redundancy_penalty_boost"] == 1.25


def test_parametros_sugeridos_reach_m_stat_002(db_path: Path) -> None:
    plan = build_runtime_calibration_plan_from_memory(
        persist_authorized_ml_calibration_plan(
            source_generation_event_id=1,
            parametros_sugeridos=SAMPLE_PARAMS,
            plan_items=["top_slice"],
            db_path=db_path,
        )
    )
    mp = extract_module_operational_params(plan)["modules"]["M-STAT-002"]
    assert mp["prefixo_alvo"] == "01-02-03"
    assert mp["sufixo_alvo"] == "23-24-25"
    assert mp["max_overlap"] < 12
    assert mp["min_material_diversity_gain"] >= 0.20


def test_parametros_sugeridos_reach_m_ml_074(db_path: Path) -> None:
    plan = build_runtime_calibration_plan_from_memory(
        persist_authorized_ml_calibration_plan(
            source_generation_event_id=1,
            parametros_sugeridos=SAMPLE_PARAMS,
            plan_items=["recovery"],
            db_path=db_path,
        )
    )
    mp = extract_module_operational_params(plan)["modules"]["M-ML-074"]
    assert mp["redundancy_penalty_boost"] >= 1.15
    assert mp["max_overlap_penalty"] >= 1.15
    assert mp["missing_numbers_boost"] >= 1.1


def test_generation_context_calibration_plan_loaded_from_db_flag(
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
        lambda *a, **k: {"calibration_applied": False, "policy_mode": "test"},
    )
    monkeypatch.setattr(
        institutional_app,
        "evaluate_batch_ml_verdict_from_games",
        lambda *a, **k: {"ml_verdict": "APROVADO", "official_release_allowed": True},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_lot_status_context",
        lambda **_: {"official_release_allowed": True},
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
            "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        },
        selected_card_format=15,
    )

    context = dict(captured.get("generation_context") or {})
    assert context.get("calibration_plan_loaded_from_db") is True
    assert context.get("calibration_plan_applied_to_generation") is True
    assert int(context.get("calibration_plan_source_generation_event_id", 0)) == 42
    assert context.get("calibration_trace_id")


def test_consumed_after_n_plus_1_generation(db_path: Path) -> None:
    source_id = _seed_generation_event(
        db_path,
        event_id_context={
            "pre_final_pool_ml_calibration": {"final_diversity_score": 0.30, "final_similarity_score": 0.70},
        },
    )
    persisted = persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["consume"],
        db_path=db_path,
    )
    target_id = _seed_generation_event(
        db_path,
        event_id_context={
            "pre_final_pool_ml_calibration": {"final_diversity_score": 0.36, "final_similarity_score": 0.64},
        },
    )
    result = mark_calibration_plan_consumed(
        int(persisted["memory_row_id"]),
        target_generation_event_id=target_id,
        metrics_before={"diversity_score": 0.30, "similarity_score": 0.70, "sobreposicao_maxima": 12},
        metrics_after={"diversity_score": 0.36, "similarity_score": 0.64, "sobreposicao_maxima": 11},
        db_path=db_path,
    )
    assert result["updated"] is True
    assert result["status"] == STATUS_APPLIED_ONCE
    assert result["calibration_effect"] == EFFECT_IMPROVED
    assert load_active_authorized_ml_calibration_plan(db_path) is None


def test_validate_result_n_vs_n1(db_path: Path) -> None:
    source_id = _seed_generation_event(
        db_path,
        event_id_context={
            "pre_final_pool_ml_calibration": {"final_diversity_score": 0.32, "final_similarity_score": 0.68},
        },
    )
    target_id = _seed_generation_event(
        db_path,
        event_id_context={
            "pre_final_pool_ml_calibration": {"final_diversity_score": 0.34, "final_similarity_score": 0.66},
        },
    )
    persisted = persist_authorized_ml_calibration_plan(
        source_generation_event_id=source_id,
        parametros_sugeridos=SAMPLE_PARAMS,
        plan_items=["validar"],
        db_path=db_path,
    )
    mark_calibration_plan_consumed(
        int(persisted["memory_row_id"]),
        target_generation_event_id=target_id,
        metrics_before={"diversity_score": 0.32, "similarity_score": 0.68},
        metrics_after={"diversity_score": 0.34, "similarity_score": 0.66},
        db_path=db_path,
    )
    consumed = dict(persisted)
    consumed["status"] = STATUS_APPLIED_ONCE
    consumed["target_generation_event_id"] = target_id
    report = build_validation_report_from_consumed_plan(consumed, db_path=db_path)
    assert report["source_generation_event_id"] == source_id
    assert report["target_generation_event_id"] == target_id
    assert report["validation_outcome"] in {"melhorou", "neutro", "piorou", "inconclusivo"}
    assert "deltas" in report


def test_compare_generations_classifies_improved_and_neutral() -> None:
    improved = compare_generations_n_vs_n1(
        {"pre_final_pool_ml_calibration": {"final_diversity_score": 0.30, "final_similarity_score": 0.70}},
        {"pre_final_pool_ml_calibration": {"final_diversity_score": 0.35, "final_similarity_score": 0.65}},
    )
    assert improved["calibration_effect"] == EFFECT_IMPROVED
    neutral = compare_generations_n_vs_n1(
        {"pre_final_pool_ml_calibration": {"final_diversity_score": 0.30, "final_similarity_score": 0.70}},
        {"pre_final_pool_ml_calibration": {"final_diversity_score": 0.301, "final_similarity_score": 0.699}},
    )
    assert neutral["calibration_effect"] == EFFECT_NEUTRAL


def test_m_ml_073b_uses_calibration_plan_evidence() -> None:
    plan = build_runtime_calibration_plan_from_memory(
        {
            "mission_id": MISSION_ID,
            "plan_items": ["classificar"],
            "parametros_sugeridos": SAMPLE_PARAMS,
            "calibration_trace_id": "trace-123",
            "source_generation_event_id": 7,
            "authorized_at": "2026-06-18T00:00:00Z",
            "memory_row_id": 1,
        }
    )
    quality = build_gp_quality_classification({}, calibration_plan=plan)
    assert quality["calibration_plan_applied"] is True
    assert quality["calibration_trace_id"] == "trace-123"
    assert quality["calibration_plan_source_generation_event_id"] == 7


def test_build_marker_v70() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v72"


def test_promote_post_calibration_consumer_lot_visibility_reprovado_not_forced_pending() -> None:
    from lotoia.operations.lot_operational_status import promote_post_calibration_consumer_lot_visibility

    promoted = promote_post_calibration_consumer_lot_visibility(
        {
            "lot_operational_status": "rejected",
            "active_reading_scope": False,
            "ml_verdict": "REPROVADO",
        },
        authorized_plan={
            "calibration_plan_loaded_from_db": True,
            "calibration_plan_applied_to_generation": True,
            "calibration_plan_source_generation_event_id": 10,
            "calibration_trace_id": "trace-abc",
        },
        promotion_context={
            "generated_games_count": 20,
            "requested_count": 20,
            "persistence_supported": True,
            "gp_quality_tier": "REPROVADO",
            "ml_verdict": "REPROVADO",
            "official_release_allowed": False,
        },
    )
    assert promoted["lot_operational_status"] == "rejected"
    assert promoted["active_reading_scope"] is True
    assert promoted["calibration_plan_consumer_generation"] is True
    assert promoted["post_calibration_promotion_evaluated"] is True
    assert promoted["promoted_to_analytical_history"] is False
    assert promoted["promotion_block_reason"]


def test_plan_loaded_consumer_visible_in_operational_loaders(tmp_path: Path) -> None:
    from lotoia.observability.card_structure_diagnostics import (
        _event_eligible_for_active_structural_reading,
        load_operational_card_structure_diagnostics_from_db,
    )

    db_path = tmp_path / "consumer-visible.db"
    create_database(db_path)
    batch_label = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
    numbers = list(range(1, 16))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={
                "lot_operational_status": "pending_structural_review",
                "active_reading_scope": True,
                "calibration_plan_consumer_generation": True,
                "calibration_plan_loaded_from_db": True,
                "ml_verdict": "REPROVADO",
                "selected_card_format": 15,
                "card_format": 15,
                "selected_quantity": 20,
                "ml_scored_games": 20,
            },
            ml_enabled=1,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label=batch_label,
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id or 0)
        for index in range(20):
            session.add(
                GeneratedGame(
                    generation_event_id=ge_id,
                    lead_id=None,
                    target_contest=3700,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index + 1,
                    numbers=numbers,
                    profile_type="recorrente",
                    final_score={"final_score": 0.5},
                    quadra_score={},
                    context_json={"selected_card_format": 15, "final_card_numbers": numbers},
                )
            )
        session.commit()

    context = {
        "calibration_plan_consumer_generation": True,
        "active_reading_scope": True,
        "lot_operational_status": "pending_structural_review",
        "ml_verdict": "REPROVADO",
    }
    assert _event_eligible_for_active_structural_reading(context) is True
    generations = load_operational_core_002_generations(db_path)
    assert any(int(row["generation_event_id"]) == ge_id for row in generations)
    diagnostics = load_operational_card_structure_diagnostics_from_db(
        db_path,
        generation_event_id=ge_id,
        game_size=15,
    )
    abertura = dict(diagnostics.get("abertura") or {})
    assert abertura or int(diagnostics.get("total_jogos", 0) or 0) > 0
