from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_assistive as ml_assistive
import dashboard.institutional_supervised_ml as supervised_ml
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import (
    CALIBRATION_MISSION_ID,
    build_calibration_event_summary,
    build_supervised_ml_operational_event_detail,
    build_supervised_ml_persistence_bundle,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, resolve_core_002_batch_label
from lotoia.ml.supervised_output_calibration import (
    CALIBRATION_ENGINE_ROLE,
    CALIBRATION_VERSION,
    STATUS_ACTIVE,
    apply_supervised_output_calibration,
)


def test_build_marker_v34() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v35"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_persistence_bundle_includes_calibration_fields() -> None:
    games = [
        {
            "numbers": list(range(1, 16)),
            "score_ml": 0.5,
            "calibration_applied": True,
            "ml_calibration_status": "aprovado",
            "ml_calibration_net": 0.8,
            "ml_calibration_penalty": 0.1,
            "ml_calibration_boost": 0.9,
            "ml_calibration_actions": ["reforco_dezena_07=0.90"],
            "ml_enabled": True,
        }
    ]
    _, calibration_bundle = apply_supervised_output_calibration(
        [{"numbers": list(range(1, 16)), "profile_score": 10.0, "score_ml": 0.5}],
        ml_enabled=True,
    )
    bundle = build_supervised_ml_persistence_bundle(
        games,
        batch_label=BATCH_LABEL,
        ml_enabled=True,
        calibration_bundle=calibration_bundle,
    )
    assert bundle["calibration_applied"] is True
    assert bundle["calibration_engine_role"] == CALIBRATION_ENGINE_ROLE
    assert bundle["calibration_version"] == CALIBRATION_VERSION
    assert bundle["supervised_ml_mission"] == CALIBRATION_MISSION_ID
    assert bundle["ml_operational_status"] == STATUS_ACTIVE
    assert bundle["decision_trace"][0]["calibration_applied"] is True
    assert "supervised_output_calibration" in bundle["decision_trace"][0]["reranked_by"]


def test_persist_generation_history_wires_calibration_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_persist(**kwargs):
        captured.update(kwargs)
        return {"generation_event_id": 99}

    def _fake_expand(games, _fmt):
        return list(games)

    def _fake_matrix(*_args, **_kwargs):
        return [{"row": 1}]

    def _fake_rows(games):
        return [{"game": 1} for _ in games]

    def _fake_contract(**_kwargs):
        return {"persistence_allowed": True}

    monkeypatch.setattr(institutional_app, "_persist_generation_snapshot", _fake_persist)
    monkeypatch.setattr(institutional_app, "_expand_generation_games_for_format", _fake_expand)
    monkeypatch.setattr(institutional_app, "build_institutional_matrix_rows", _fake_matrix)
    monkeypatch.setattr(
        institutional_app,
        "_build_games_table_rows_from_generation_games",
        _fake_rows,
    )
    monkeypatch.setattr(
        institutional_app,
        "validate_lei15_lei15a_runtime_contract",
        lambda **_kwargs: {"persistence_allowed": True},
    )
    monkeypatch.setattr(institutional_app, "_load_latest_contest_summary", lambda: None)
    monkeypatch.setattr(institutional_app, "_attach_operational_generation_label", lambda x: x)

    _, calibration_bundle = apply_supervised_output_calibration(
        [
            {
                "numbers": list(range(1, 16)),
                "profile_score": 12.0,
                "score_ml": 0.4,
                "core_numbers": list(range(1, 16)),
                "final_card_numbers": list(range(1, 16)),
            }
        ],
        ml_enabled=True,
    )
    result = {
        "games": [
            {
                "numbers": list(range(1, 16)),
                "core_numbers": list(range(1, 16)),
                "final_card_numbers": list(range(1, 16)),
                "calibration_applied": True,
                "score_ml": 0.4,
                "ml_enabled": True,
            }
        ],
        "ml_enabled": True,
        "requested_count": 1,
        "calibration_bundle": calibration_bundle,
        "calibration_applied": True,
        "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
        "commander_report": {"status_comandante_saida": "APROVADO"},
        "seed": 1,
        "batch_id": "test-batch",
        "analysis_batch_label": BATCH_LABEL,
    }
    snapshot = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )
    assert snapshot.get("generation_event_id") == 99
    context = dict(captured.get("generation_context") or {})
    assert context.get("calibration_applied") is True
    assert context.get("calibration_engine_role") == CALIBRATION_ENGINE_ROLE
    assert context.get("decision_trace")
    assert context.get("calibration_decision_trace")
    assert context.get("calibration_feature_attribution")


def test_basic_generator_exports_calibration_in_payload(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    from lotoia.generator.basic_generator import generate_best_games

    pool = [
        {
            "numbers": [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24],
            "profile_score": 10.0,
            "final_score": {"final_score": 10.0},
        }
    ]

    def _mock_pool(pool_size, *, seed, history, config):
        return [dict(pool[0]) for _ in range(max(pool_size, 3))]

    def _mock_compose(games, count, config, *, game_size=15):
        return list(games[:count])

    monkeypatch.setattr(
        "lotoia.generation.lei15_core_002.build_sovereign_pool",
        _mock_pool,
    )
    monkeypatch.setattr(
        "lotoia.generation.lei15_core_002.compose_sovereign_gp",
        _mock_compose,
    )
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")

    payload = generate_best_games(
        count=1,
        seed=7,
        batch_label=BATCH_LABEL,
        ml_enabled=True,
    )
    assert payload.get("calibration_applied") is True
    assert payload.get("calibration_bundle", {}).get("calibration_applied") is True


def test_central_ml_panel_renders_calibration_section(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("DATABASE_URL", "LOTOIA_DATABASE_URL", "LOTOIA_DATABASE_POOLER_URL", "DATABASE_PUBLIC_URL"):
        monkeypatch.delenv(key, raising=False)
    db_path = tmp_path / "ml054.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    calibration_summary = build_calibration_event_summary(
        {
            "calibration_applied": True,
            "calibration_version": CALIBRATION_VERSION,
            "calibration_engine_role": CALIBRATION_ENGINE_ROLE,
            "diagnostics": {"issues": [{"descricao": "Quase repetidos elevado", "tipo": "quase_repetidos_alto"}]},
            "actions_applied": ["penalidade_redundancia_media=1.200"],
        }
    )
    trace = supervised_ml.build_game_decision_trace(
        {"numbers": list(range(1, 16)), "score_ml": 0.42, "calibration_applied": True},
        ml_enabled=True,
    )
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={
                "selected_quantity": 1,
                "ml_scored_games": 1,
                "decision_trace": [trace],
                "feature_attribution": [supervised_ml.build_game_feature_attribution({})],
                "ml_six_bases_reading": calibration_summary["six_bases_summary"],
                "supervised_ml_mission": CALIBRATION_MISSION_ID,
                "ml_operational_status": STATUS_ACTIVE,
                "selected_card_format": 15,
                **calibration_summary,
            },
            ml_enabled=1,
            seed=42,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label=batch_label,
            analysis_batch_type="LEI15_CORE_002_SOVEREIGN",
            analysis_batch_created_at=datetime.now(UTC),
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id)
        session.add(
            GeneratedGame(
                generation_event_id=ge_id,
                target_contest=3712,
                origin="institutional",
                generation_mode="hb_baseline",
                game_index=1,
                numbers=list(range(1, 16)),
                profile_type="HYBRID",
                final_score={},
                quadra_score={},
                context_json={"decision_trace": trace},
            )
        )
        session.commit()

    detail = build_supervised_ml_operational_event_detail(db_path, ge_id)
    assert detail is not None
    assert detail["calibration_applied"] is True
    assert detail["issues_detected"]

    panel_source = inspect.getsource(ml_assistive.render_supervised_ml_operational_panel)
    assert "Calibração supervisionada de saída" in panel_source
    assert "calibration_decision_trace" in panel_source


def test_imports_required_by_mission() -> None:
    import dashboard.institutional_app  # noqa: F401
    import dashboard.institutional_supervised_ml  # noqa: F401
