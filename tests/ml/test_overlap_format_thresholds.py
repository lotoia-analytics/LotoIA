from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import build_ml_calibration_cockpit_snapshot
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.ml.overlap_format_thresholds import (
    LEVEL_CRITICO,
    LEVEL_RUIM,
    MISSION_ID,
    SUPPORTED_FORMAT_SIZES,
    build_format_overlap_threshold,
    build_overlap_format_memory,
    build_per_format_overlap_analysis,
    classify_overlap_for_format,
    evaluate_format_overlap_verdict,
)
from lotoia.observability.coverage_evidence_interpreter import build_calibration_plan, get_structural_coverage_evidence


def test_build_marker_v43() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v45"


@pytest.mark.parametrize(
    ("game_size", "bom_max", "atencao", "ruim", "critico"),
    [
        (15, 12, 13, 14, 15),
        (16, 13, 14, 15, 16),
        (17, 14, 15, 16, 17),
        (18, 15, 16, 17, 18),
        (19, 16, 17, 18, 19),
        (20, 17, 18, 19, 20),
        (21, 18, 19, 20, 21),
        (22, 19, 20, 21, 22),
        (23, 20, 21, 22, 23),
    ],
)
def test_format_thresholds_15d_to_23d(
    game_size: int,
    bom_max: int,
    atencao: int,
    ruim: int,
    critico: int,
) -> None:
    threshold = build_format_overlap_threshold(game_size)
    assert threshold["bom_max"] == bom_max
    assert threshold["atencao"] == atencao
    assert threshold["ruim"] == ruim
    assert threshold["critico"] == critico


def test_overlap_memory_registers_all_formats() -> None:
    memory = build_overlap_format_memory()
    assert memory["mission_id"] == MISSION_ID
    assert len(memory["thresholds"]) == len(SUPPORTED_FORMAT_SIZES)
    assert memory["supported_formats"] == [f"{size}D" for size in SUPPORTED_FORMAT_SIZES]


def test_overlap_equal_format_size_is_critical() -> None:
    for size in SUPPORTED_FORMAT_SIZES:
        result = classify_overlap_for_format(size, size)
        assert result["level"] == LEVEL_CRITICO
        assert "CRÍTICO" in result["verdict"]


def test_overlap_n_minus_one_is_ruim() -> None:
    for size in SUPPORTED_FORMAT_SIZES:
        result = classify_overlap_for_format(size - 1, size)
        assert result["level"] == LEVEL_RUIM


def test_17d_critical_clone_verdict_example() -> None:
    verdict = evaluate_format_overlap_verdict(
        17,
        17,
        {
            "similaridade_media": 0.62,
            "quase_repetidos": 100,
            "diversity_score": 0.38,
        },
    )
    assert verdict["level"] == LEVEL_CRITICO
    assert "17D" in verdict["verdict"]
    assert "Penalizar overlap extremo" in verdict["recommended_action"]


def test_calibration_plan_uses_format_specific_action() -> None:
    analysis = evaluate_format_overlap_verdict(17, 17, {"similaridade_media": 0.7, "quase_repetidos": 50})
    plan = build_calibration_plan(
        {"sobreposicao_maxima": 17, "similaridade_media": 0.7, "quase_repetidos": 50},
        format_analyses=[analysis],
    )
    joined = " ".join(plan["plan_items"]).lower()
    assert "17d" in joined
    assert any("clone" in item.lower() or "overlap" in item.lower() for item in plan["plan_items"])


def test_per_format_analysis_from_payload() -> None:
    payload = {
        "summary": {"formatos_analisados": [17], "total_jogos": 10},
        "redundancia_por_formato": {
            "17": {
                "sobreposicao_maxima": 17,
                "similaridade_media_entre_jogos": 0.65,
                "cartoes_quase_repetidos": 4,
            }
        },
    }
    analyses = build_per_format_overlap_analysis(payload, {"sobreposicao_maxima": 17})
    assert len(analyses) == 1
    assert analyses[0]["formato"] == "17D"
    assert analyses[0]["level"] == LEVEL_CRITICO


def test_cockpit_snapshot_includes_overlap_memory(tmp_path: Path) -> None:
    db_path = tmp_path / "overlap_format.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={"selected_quantity": 2, "ml_scored_games": 2},
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
        for idx in range(1, 3):
            session.add(
                GeneratedGame(
                    generation_event_id=ge_id,
                    target_contest=3712,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=idx,
                    numbers=list(range(idx, idx + 15)),
                    profile_type="HYBRID",
                    final_score={},
                    quadra_score={},
                    context_json={},
                )
            )
        session.commit()

    evidence = get_structural_coverage_evidence(db_path)
    if evidence.get("available"):
        assert evidence.get("overlap_format_memory")
        assert evidence.get("overlap_format_mission_id") == MISSION_ID
    snapshot = build_ml_calibration_cockpit_snapshot(db_path)
    assert snapshot.get("overlap_format_mission_id") == MISSION_ID
    if snapshot.get("coverage_evidence", {}).get("available"):
        assert snapshot.get("overlap_format_memory")
