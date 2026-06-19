"""M-ML-071-FIX-01 — Central ML herda filtro de formato da Cobertura Estrutural."""

from __future__ import annotations

import inspect
from pathlib import Path

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_operational_structural_coverage import (
    CARD_FORMAT_FILTER_ALL_LABEL,
    CARD_FORMAT_FILTER_MISSION_ID,
    build_analyzed_card_format_caption,
    build_card_format_filter_options,
    filter_operational_generations_by_card_format,
    parse_card_format_filter_label,
    resolve_generation_event_ids_for_card_format,
)
from dashboard.institutional_supervised_ml import (
    CARD_FORMAT_FILTER_MISSION_ID as SNAPSHOT_MISSION_ID,
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


def _seed_mixed_formats_db(tmp_path: Path) -> tuple[Path, int, int]:
    db_path = tmp_path / "mixed_formats.db"
    create_database(db_path)
    ge_15 = _seed_gp_event(db_path, card_format=15, games_count=20)
    ge_17 = _seed_gp_event(db_path, card_format=17, games_count=20)
    return db_path, ge_15, ge_17


def test_format_filter_helpers_match_cobertura_catalog() -> None:
    generations = [
        {"generation_event_id": 1, "card_format": 15},
        {"generation_event_id": 2, "card_format": 17},
    ]
    options = build_card_format_filter_options(generations)
    assert options == [CARD_FORMAT_FILTER_ALL_LABEL, "15D", "17D"]
    assert parse_card_format_filter_label("15D") == 15
    assert parse_card_format_filter_label("17D") == 17
    assert parse_card_format_filter_label(CARD_FORMAT_FILTER_ALL_LABEL) is None
    assert build_analyzed_card_format_caption(15) == "Formato analisado: 15D"
    assert resolve_generation_event_ids_for_card_format(generations, 17) == [2]
    assert len(filter_operational_generations_by_card_format(generations, 15)) == 1


def test_cockpit_exposes_format_selector() -> None:
    source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    assert "central_ml_card_format_filter" in source
    assert "build_card_format_filter_options" in source
    assert "card_format_filter" in source
    assert "build_analyzed_card_format_caption" in source


def test_snapshot_filters_15d_only(tmp_path: Path) -> None:
    db_path, ge_15, ge_17 = _seed_mixed_formats_db(tmp_path)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, card_format_filter=15)
    assert snapshot["card_format_filter"] == 15
    assert snapshot["card_format_filter_mission_id"] == SNAPSHOT_MISSION_ID == CARD_FORMAT_FILTER_MISSION_ID
    assert snapshot["analyzed_card_format_caption"] == "Formato analisado: 15D"
    assert ge_15 in list(snapshot.get("scoped_generation_event_ids") or [])
    assert ge_17 not in list(snapshot.get("scoped_generation_event_ids") or [])
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert metrics.get("formatos_analisados") == [15]
    assert ge_17 not in list(metrics.get("generation_event_ids") or [])
    assert all(row.get("formato") == "15D" for row in list(snapshot.get("aggregate", {}).get("lot_rows") or []))


def test_snapshot_filters_17d_only(tmp_path: Path) -> None:
    db_path, ge_15, ge_17 = _seed_mixed_formats_db(tmp_path)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, card_format_filter=17)
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert metrics.get("formatos_analisados") == [17]
    assert ge_15 not in list(metrics.get("generation_event_ids") or [])
    assert ge_17 in list(metrics.get("generation_event_ids") or [])


def test_snapshot_all_formats_preserves_aggregate_mode(tmp_path: Path) -> None:
    db_path, ge_15, ge_17 = _seed_mixed_formats_db(tmp_path)
    snapshot = build_ml_calibration_cockpit_snapshot(db_path, card_format_filter=None)
    assert snapshot["aggregate_mode"] is True
    assert snapshot["card_format_filter"] is None
    coverage = dict(snapshot.get("coverage_evidence") or {})
    metrics = dict(coverage.get("metrics") or {})
    assert sorted(metrics.get("formatos_analisados") or []) == [15, 17]
    assert ge_15 in list(metrics.get("generation_event_ids") or [])
    assert ge_17 in list(metrics.get("generation_event_ids") or [])


def test_get_structural_coverage_evidence_respects_format_filter(tmp_path: Path) -> None:
    db_path, ge_15, ge_17 = _seed_mixed_formats_db(tmp_path)
    evidence_15 = get_structural_coverage_evidence(
        db_path,
        generation_event_ids=[ge_15],
        game_size=15,
        scope_label="Formato analisado: 15D",
    )
    metrics_15 = dict(evidence_15.get("metrics") or {})
    assert metrics_15.get("formatos_analisados") == [15]
    assert ge_17 not in list(metrics_15.get("generation_event_ids") or [])

    evidence_all = get_structural_coverage_evidence(db_path)
    metrics_all = dict(evidence_all.get("metrics") or {})
    assert sorted(metrics_all.get("formatos_analisados") or []) == [15, 17]
