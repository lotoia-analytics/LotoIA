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
    EMPTY_ML_EVENTS_MESSAGE,
    SUPERVISED_ML_STATUS_ACTIVE,
    VIS_MISSION_ID,
    build_supervised_ml_operational_event_detail,
    build_supervised_ml_operational_panel_snapshot,
    load_supervised_ml_operational_events_from_db,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, resolve_core_002_batch_label


def test_build_marker_v32() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v33"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_central_ml_page_integrates_operational_panel() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "Central ML — Operacional Supervisionada" in source
    assert "render_supervised_ml_operational_panel" in source
    assert "render_ml_assistive_governance_section" in source


def test_operational_panel_module_exports() -> None:
    assert callable(ml_assistive.render_supervised_ml_operational_panel)
    assert callable(supervised_ml.load_supervised_ml_operational_events_from_db)
    assert callable(supervised_ml.build_supervised_ml_operational_panel_snapshot)


@pytest.fixture
def sqlite_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _persist_ml_event(db_path: Path, *, ge_id_hint: int = 171) -> int:
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    trace = supervised_ml.build_game_decision_trace(
        {"numbers": list(range(1, 16)), "score_ml": 0.42},
        ml_enabled=True,
    )
    attribution = supervised_ml.build_game_feature_attribution(
        {
            "score_ml_details": {
                "score_ml": 0.42,
                "model_version": "test-v1",
                "feature_schema_version": "fs-1",
                "attribution": [{"feature": "structural_gap", "weight": 0.12}],
                "features": {"gap_mean": 1.2},
                "calibration": {},
            }
        }
    )
    six_bases = supervised_ml.build_ml_six_bases_operational_summary()
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={
                "selected_quantity": 1,
                "ml_scored_games": 1,
                "decision_trace": [trace],
                "feature_attribution": [attribution],
                "ml_six_bases_reading": six_bases,
                "supervised_ml_mission": "M-ML-045",
                "ml_operational_status": SUPERVISED_ML_STATUS_ACTIVE,
                "selected_card_format": 15,
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
                context_json={
                    "decision_trace": trace,
                    "feature_attribution": attribution,
                    "score_ml": 0.42,
                },
            )
        )
        session.commit()
    assert ge_id > 0
    return ge_id


def test_load_supervised_ml_operational_events_from_db(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "ml_panel.db"
    ge_id = _persist_ml_event(db_path)
    events = load_supervised_ml_operational_events_from_db(db_path)
    assert len(events) == 1
    assert events[0]["generation_event_id"] == ge_id
    assert events[0]["batch_label"] == BATCH_LABEL
    assert events[0]["ml_enabled"] is True
    assert events[0]["decision_trace_status"] == "persistido"
    assert events[0]["feature_attribution_status"] == "persistido"
    assert events[0]["ml_six_bases_status"] == "persistido"


def test_operational_panel_snapshot_empty_state(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "empty_ml_panel.db"
    create_database(db_path)
    payload = build_supervised_ml_operational_panel_snapshot(db_path)
    assert payload["mission_id"] == VIS_MISSION_ID
    assert payload["available"] is False
    assert payload["empty_message"] == EMPTY_ML_EVENTS_MESSAGE
    assert payload["source"] == "postgresql"
    assert payload["public_app_ml"] is False
    assert payload["lei15a_operational"] is False


def test_operational_event_detail_includes_trace_attribution_and_six_bases(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "ml_detail.db"
    ge_id = _persist_ml_event(db_path)
    detail = build_supervised_ml_operational_event_detail(db_path, ge_id)
    assert detail is not None
    assert detail["generation_event_id"] == ge_id
    assert detail["batch_label"] == BATCH_LABEL
    assert detail["decision_trace"]["status"] == "persistido"
    assert detail["feature_attribution"]["status"] == "persistido"
    assert len(detail["ml_six_bases_reading"]) == 6
    assert "BLK-ML-FREE-001" in detail["constitutional_blocks"]


def test_render_operational_panel_without_name_error(
    tmp_path: Path,
    sqlite_db_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "ml_render.db"
    _persist_ml_event(db_path)

    class _StreamlitStub:
        def markdown(self, *_args, **_kwargs) -> None:
            return None

        def caption(self, *_args, **_kwargs) -> None:
            return None

        def success(self, *_args, **_kwargs) -> None:
            return None

        def warning(self, *_args, **_kwargs) -> None:
            return None

        def info(self, *_args, **_kwargs) -> None:
            return None

        def metric(self, *_args, **_kwargs) -> None:
            return None

        def write(self, *_args, **_kwargs) -> None:
            return None

        def columns(self, spec):
            return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

        def dataframe(self, *_args, **_kwargs) -> None:
            return None

        def selectbox(self, *_args, **_kwargs):
            return _kwargs.get("options", [""])[0]

        def json(self, *_args, **_kwargs) -> None:
            return None

    monkeypatch.setattr(ml_assistive, "st", _StreamlitStub())
    payload = ml_assistive.render_supervised_ml_operational_panel(db_path)
    assert payload["available"] is True
    assert payload["ml_operational_status"] == SUPERVISED_ML_STATUS_ACTIVE


def test_m_ml_045_regression_supervised_helpers_still_available() -> None:
    assert callable(supervised_ml.build_supervised_ml_persistence_bundle)
    assert supervised_ml.MISSION_ID == "M-ML-045"
