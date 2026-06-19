"""M-ML-071-FIX-01 — Central ML herda seletor de Geração operacional da Cobertura."""

from __future__ import annotations

import inspect
from pathlib import Path

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_operational_structural_coverage import (
    OPERATIONAL_GENERATION_ALL_LABEL,
    OPERATIONAL_GENERATION_FILTER_MISSION_ID,
    OPERATIONAL_GENERATION_SELECTOR_KEY,
    build_operational_generation_dropdown_options,
    build_operational_generation_scope_caption,
    load_operational_core_002_generations,
    resolve_operational_generation_selection,
)
from dashboard.institutional_supervised_ml import (
    OPERATIONAL_GENERATION_FILTER_MISSION_ID as SNAPSHOT_MISSION_ID,
    build_ml_calibration_cockpit_snapshot,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.coverage_evidence_interpreter import get_structural_coverage_evidence


def _seed_gp_event(
    db_path: Path,
    *,
    card_format: int,
    games_count: int = 20,
) -> int:
    numbers = list(range(1, int(card_format) + 1))
    batch_label = resolve_core_002_batch_label(int(card_format))
    with get_session(db_path) as session:
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers}],
            context_json={
                "selected_quantity": games_count,
                "ml_scored_games": games_count,
                "selected_card_format": int(card_format),
                "card_format": int(card_format),
                "operational_status": "active",
                "active_reading_scope": True,
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
        for index in range(games_count):
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
                    context_json={
                        "selected_card_format": int(card_format),
                        "card_format": int(card_format),
                        "final_card_numbers": numbers,
                    },
                )
            )
        session.commit()
        return ge_id


def _seed_mixed_formats_db(tmp_path: Path) -> tuple[Path, int, int, list[dict]]:
    db_path = tmp_path / "mixed_formats.db"
    create_database(db_path)
    ge_15 = _seed_gp_event(db_path, card_format=15, games_count=20)
    ge_17 = _seed_gp_event(db_path, card_format=17, games_count=20)
    generations = load_operational_core_002_generations(db_path)
    return db_path, ge_15, ge_17, generations


def _selection_for_ge(generations: list[dict], ge_id: int) -> dict:
    for row in generations:
        if int(row.get("generation_event_id", 0) or 0) == int(ge_id):
            return resolve_operational_generation_selection(
                str(row.get("dropdown_label") or ""),
                generations,
            )
    raise AssertionError(f"generation_event_id {ge_id} not found")


def test_operational_generation_dropdown_matches_cobertura() -> None:
    generations = [
        {
            "generation_event_id": 4,
            "card_format": 17,
            "games_count": 20,
            "dropdown_label": "Geração 001 — GE 4 — 17D — CORE_002 — 20 jogos",
            "operational_generation_label": "001",
        },
        {
            "generation_event_id": 5,
            "card_format": 15,
            "games_count": 20,
            "dropdown_label": "Geração 002 — GE 5 — 15D — CORE_002 — 20 jogos",
            "operational_generation_label": "002",
        },
    ]
    options = build_operational_generation_dropdown_options(generations)
    assert options[0] == OPERATIONAL_GENERATION_ALL_LABEL
    assert any("17D" in item for item in options)
    assert any("15D" in item for item in options)
    selected = resolve_operational_generation_selection(options[2], generations)
    assert selected["generation_event_id"] == 5
    assert selected["card_format"] == 15
    assert build_operational_generation_scope_caption(selected) == "Formato analisado: 15D"


def test_cockpit_reuses_cobertura_operational_generation_selector() -> None:
    source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    assert "OPERATIONAL_GENERATION_SELECTOR_KEY" in source
    assert 'st.selectbox(\n        "Geração operacional"' in source or '"Geração operacional"' in source
    assert "build_operational_generation_dropdown_options" in source
    assert "resolve_operational_generation_selection" in source
    assert "central_ml_card_format_filter" not in source
    assert "build_card_format_filter_options" not in source


def test_snapshot_scoped_to_selected_15d_generation(tmp_path: Path) -> None:
    db_path, ge_15, ge_17, generations = _seed_mixed_formats_db(tmp_path)
    selection = _selection_for_ge(generations, ge_15)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection)
    assert snapshot["aggregate_mode"] is False
    assert snapshot["selected_generation_event_id"] == ge_15
    assert snapshot["selected_card_format"] == 15
    assert snapshot["analyzed_card_format_caption"] == "Formato analisado: 15D"
    assert snapshot["operational_generation_filter_mission_id"] == SNAPSHOT_MISSION_ID == OPERATIONAL_GENERATION_FILTER_MISSION_ID
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert metrics.get("formatos_analisados") == [15]
    assert ge_17 not in list(metrics.get("generation_event_ids") or [])


def test_snapshot_scoped_to_selected_17d_generation(tmp_path: Path) -> None:
    db_path, ge_15, ge_17, generations = _seed_mixed_formats_db(tmp_path)
    selection = _selection_for_ge(generations, ge_17)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection)
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert metrics.get("formatos_analisados") == [17]
    assert ge_15 not in list(metrics.get("generation_event_ids") or [])
    assert ge_17 in list(metrics.get("generation_event_ids") or [])


def test_snapshot_all_operational_generations_preserves_aggregate_mode(tmp_path: Path) -> None:
    db_path, ge_15, ge_17, generations = _seed_mixed_formats_db(tmp_path)
    selection = resolve_operational_generation_selection(OPERATIONAL_GENERATION_ALL_LABEL, generations)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, operational_selection=selection)
    assert snapshot["aggregate_mode"] is True
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert sorted(metrics.get("formatos_analisados") or []) == [15, 17]
    assert ge_15 in list(metrics.get("generation_event_ids") or [])
    assert ge_17 in list(metrics.get("generation_event_ids") or [])


def test_get_structural_coverage_evidence_respects_operational_selection(tmp_path: Path) -> None:
    db_path, ge_15, ge_17, generations = _seed_mixed_formats_db(tmp_path)
    selection = _selection_for_ge(generations, ge_15)
    evidence_15 = get_structural_coverage_evidence(
        db_path,
        generation_event_id=int(selection["generation_event_id"]),
        game_size=int(selection["card_format"]),
        scope_label=build_operational_generation_scope_caption(selection),
    )
    metrics_15 = dict(evidence_15.get("metrics") or {})
    assert metrics_15.get("formatos_analisados") == [15]
    assert ge_17 not in list(metrics_15.get("generation_event_ids") or [])
