from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_calibration_cockpit as cockpit
import dashboard.institutional_ml_assistive as ml_assistive
from dashboard.institutional_supervised_ml import (
    AGGREGATE_SCOPE_LABEL,
    VIS_COCKPIT_MISSION_ID,
    build_ml_calibration_cockpit_snapshot,
    build_ml_calibration_recommendations,
    resolve_recalibration_display_status,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label


def test_recalibration_status_active_when_supervised_calibration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    status = resolve_recalibration_display_status()
    assert status["supervised_calibration_active"] is True
    assert status["pill_status"] == "ATIVA COM SUPERVISÃO"
    assert "BLOQUEADA" in status["ml_free_status"]


def test_recalibration_status_blocked_when_calibration_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "0")
    status = resolve_recalibration_display_status()
    assert status["supervised_calibration_active"] is False
    assert status["pill_status"] == "BLOQUEADA"


def test_central_ml_page_uses_cockpit_not_legacy_panel() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "render_ml_calibration_cockpit" in source
    assert "render_supervised_ml_operational_panel" not in source
    assert "Governança ML assistiva (referência institucional)" in source


def test_cockpit_render_module_has_required_sections() -> None:
    module_source = inspect.getsource(cockpit)
    render_source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    assert "COCKPIT_TITLE" in module_source
    assert "Diagnóstico geral da saída" in module_source
    assert "Ação recomendada" in module_source
    assert "Evidências e decisão" in module_source
    assert "Impacto esperado" in module_source
    assert "Diagnosticar saída geral" in module_source
    assert "Autorizar calibração" in module_source
    assert "Detalhes por lote" in module_source
    assert "Proteções constitucionais ativas" in module_source
    assert "expanded=False" in module_source
    assert "Auditoria Técnica" in module_source
    assert "Lote analisado" not in module_source
    assert "OPERATIONAL_GENERATION_SELECTOR_KEY" in render_source
    assert "Geração operacional" in render_source


def test_home_page_recalibration_status_not_generic_blocked() -> None:
    source = inspect.getsource(institutional_app._render_home_page)
    assert 'resolve_recalibration_display_status()' in source
    assert '_render_home_status_pill("Recalibração", "BLOQUEADA"' not in source


@pytest.fixture
def sqlite_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DATABASE_URL",
        "LOTOIA_DATABASE_URL",
        "LOTOIA_DATABASE_POOLER_URL",
        "DATABASE_PUBLIC_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def _persist_calibrated_event(db_path: Path) -> int:
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={
                "selected_quantity": 5,
                "ml_scored_games": 5,
                "calibration_applied": True,
                "calibration_diagnostics": {
                    "issues": [
                        {"tipo": "quase_repetidos_alto", "descricao": "Quase repetidos elevado"},
                        {"tipo": "dezena_subcoberta", "descricao": "Dezena 11 subcoberta"},
                    ],
                    "redundancy": {"cartoes_quase_repetidos": 80, "sobreposicao_media": 11.2},
                },
                "issues_detected": ["Quase repetidos elevado", "Dezena 11 subcoberta"],
                "calibration_actions_applied": ["penalidade_redundancia_media=1.200"],
                "diversity_score": 0.42,
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
                context_json={},
            )
        )
        session.commit()
    return ge_id


def test_cockpit_snapshot_builds_diagnosis_and_recommendations(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "cockpit.db"
    ge_id = _persist_calibrated_event(db_path)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path)
    assert snapshot["mission_id"] == VIS_COCKPIT_MISSION_ID
    assert snapshot["aggregate_mode"] is True
    assert snapshot["scope_label"] == AGGREGATE_SCOPE_LABEL
    assert snapshot["diagnosis"]["available"] is True
    assert snapshot["diagnosis"]["total_events"] >= 1
    assert snapshot["lot_details"]
    assert int(snapshot["lot_details"][0]["generation_event_id"]) == ge_id
    assert snapshot["recommendations"]
    assert snapshot["constitutional_summary"]["calibracao_supervisionada"] in {"ATIVA", "INATIVA"}


def test_recommendations_from_issues() -> None:
    event = {
        "calibration_diagnostics": {
            "issues": [
                {"tipo": "prefixo_excessivo"},
                {"tipo": "dezena_subcoberta"},
            ]
        }
    }
    recs = build_ml_calibration_recommendations(event)
    assert recs
    assert any("subcobert" in item.lower() or "dezena" in item.lower() or "refor" in item.lower() for item in recs)


def test_render_cockpit_without_name_error(
    tmp_path: Path,
    sqlite_db_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "cockpit_render.db"
    _persist_calibrated_event(db_path)

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

        def columns(self, spec):
            return [self for _ in range(len(spec) if isinstance(spec, list) else spec)]

        def container(self, **_kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def divider(self) -> None:
            return None

        def button(self, *_args, **_kwargs):
            return False

        def expander(self, *_args, **_kwargs):
            return self

        def dataframe(self, *_args, **_kwargs) -> None:
            return None

        def json(self, *_args, **_kwargs) -> None:
            return None

        def error(self, *_args, **_kwargs) -> None:
            return None

        def selectbox(self, _label, *, options, **kwargs):
            return options[0] if options else None

        def error(self, *_args, **_kwargs) -> None:
            return None

        def session_state(self):
            return {}

    stub = _StreamlitStub()
    monkeypatch.setattr(cockpit, "st", stub)
    monkeypatch.setattr(cockpit.st, "session_state", {}, raising=False)
    payload = cockpit.render_ml_calibration_cockpit(db_path)
    assert payload["mission_id"] == VIS_COCKPIT_MISSION_ID


def test_ml_assistive_shows_calibration_active_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_LEI15_CORE_002_GENERATION_ENABLED", "1")
    monkeypatch.setenv("LOTOIA_ML_OUTPUT_CALIBRATION_ENABLED", "1")
    source = inspect.getsource(ml_assistive.render_ml_assistive_governance_section)
    assert "Calibração ML" in source


def test_imports_required_by_mission() -> None:
    import dashboard.institutional_app  # noqa: F401
    import dashboard.institutional_ml_calibration_cockpit  # noqa: F401
