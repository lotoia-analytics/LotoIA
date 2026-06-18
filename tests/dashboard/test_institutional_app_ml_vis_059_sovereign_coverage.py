from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import (
    build_ml_calibration_cockpit_snapshot,
    build_sovereign_coverage_diagnosis_card,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.card_structure_diagnostics import (
    MISSION_ID_STRUCTURAL_SNAPSHOT,
    SCOPE_LABEL_ALL_OPERATIONAL,
    extract_operational_structural_metrics,
    get_structural_coverage_snapshot,
    load_operational_card_structure_diagnostics_from_db,
)
from lotoia.observability.coverage_evidence_interpreter import (
    SOVEREIGN_MISSION_ID,
    _attach_ml_operational_metadata,
    get_structural_coverage_evidence,
)


def test_build_marker_v41() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v41"


def test_extract_metrics_match_redundancia_gp_payload() -> None:
    payload = {
        "summary": {"total_jogos": 100, "total_geracoes": 5, "formatos_analisados": [15]},
        "evidence_base": {"generation_event_ids": [1, 2, 3], "formatos_analisados": [15]},
        "redundancia_gp": {
            "similaridade_media_entre_jogos": 0.6219,
            "sobreposicao_maxima": 17,
            "cartoes_quase_repetidos": 2842,
            "sobreposicao_media": 10.5,
            "dezenas_fora_em_muitos_jogos": [],
        },
        "abertura": {"prefixo_3_mais_gerado": {"estrutura": "01-02-03", "frequencia": 2}},
        "fechamento": {"sufixo_3_mais_gerado": {"estrutura": "23-24-25", "frequencia": 2}},
        "travamento_13_14": {"jogos_com_13_hits": [], "jogos_com_14_hits": [], "jogos_com_15_hits": []},
        "evidence_level": "LOCAL_DIAGNOSTIC",
    }
    metrics = extract_operational_structural_metrics(payload)
    redundancy = payload["redundancia_gp"]
    assert metrics["similaridade_media"] == redundancy["similaridade_media_entre_jogos"]
    assert metrics["sobreposicao_maxima"] == redundancy["sobreposicao_maxima"]
    assert metrics["quase_repetidos"] == redundancy["cartoes_quase_repetidos"]
    assert metrics["total_jogos"] == 100
    assert metrics["generation_event_ids"] == [1, 2, 3]


def test_get_structural_coverage_snapshot_same_as_loader(tmp_path: Path) -> None:
    db_path = tmp_path / "sovereign_coverage.db"
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

    loader_payload = load_operational_card_structure_diagnostics_from_db(db_path)
    snapshot = get_structural_coverage_snapshot(db_path)
    assert snapshot["available"] is True
    assert snapshot["mission_id"] == MISSION_ID_STRUCTURAL_SNAPSHOT
    assert snapshot["scope_label"] == SCOPE_LABEL_ALL_OPERATIONAL
    loader_metrics = extract_operational_structural_metrics(loader_payload)
    assert snapshot["metrics"]["similaridade_media"] == loader_metrics["similaridade_media"]
    assert snapshot["metrics"]["sobreposicao_maxima"] == loader_metrics["sobreposicao_maxima"]
    assert snapshot["metrics"]["quase_repetidos"] == loader_metrics["quase_repetidos"]
    assert snapshot["reading"]["coverage_snapshot_checksum"]


def test_attach_ml_metadata_does_not_override_structural_numbers() -> None:
    metrics = {
        "similaridade_media": 0.6219,
        "sobreposicao_maxima": 17,
        "quase_repetidos": 2842,
        "diversity_score": 0.3781,
    }
    aggregate = {
        "available": True,
        "calibrated_events": 2,
        "calibration_applied": True,
        "metrics": {
            "similaridade_media": 0.664,
            "quase_repetidos": 393,
            "diversity_score": 0.0,
        },
    }
    merged = _attach_ml_operational_metadata(metrics, aggregate)
    assert merged["similaridade_media"] == 0.6219
    assert merged["sobreposicao_maxima"] == 17
    assert merged["quase_repetidos"] == 2842
    assert merged["calibrated_events"] == 2


def test_central_ml_diagnosis_uses_sovereign_metrics(tmp_path: Path) -> None:
    db_path = tmp_path / "cockpit_sovereign.db"
    create_database(db_path)
    batch_label = resolve_core_002_batch_label(15)
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": list(range(1, 16))}],
            context_json={
                "selected_quantity": 3,
                "ml_scored_games": 3,
                "calibration_diagnostics": {
                    "redundancy": {
                        "cartoes_quase_repetidos": 999,
                        "sobreposicao_media": 14.0,
                        "similaridade_media_entre_jogos": 0.99,
                    }
                },
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
        for idx in range(1, 4):
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
    assert evidence.get("sovereign_mission_id") == SOVEREIGN_MISSION_ID
    sovereign_metrics = dict(evidence.get("metrics") or {})
    diagnosis = build_sovereign_coverage_diagnosis_card(evidence)
    diagnosis_metrics = dict(diagnosis.get("metrics") or {})
    assert diagnosis_metrics["similaridade_media"] == sovereign_metrics["similaridade_media"]
    assert diagnosis_metrics["quase_repetidos"] == sovereign_metrics["quase_repetidos"]
    assert diagnosis_metrics["sobreposicao_maxima"] == sovereign_metrics["sobreposicao_maxima"]
    assert diagnosis["coverage_source"] == "cobertura_estrutural"
    assert diagnosis["reading"]
    assert diagnosis["scope_label"] == SCOPE_LABEL_ALL_OPERATIONAL
    assert diagnosis_metrics["quase_repetidos"] != 999

    snapshot = build_ml_calibration_cockpit_snapshot(db_path)
    snap_metrics = dict(snapshot.get("diagnosis", {}).get("metrics") or {})
    assert snap_metrics["similaridade_media"] == sovereign_metrics["similaridade_media"]
    assert snap_metrics["quase_repetidos"] == sovereign_metrics["quase_repetidos"]


def test_recommendation_uses_sovereign_similaridade_in_evidence() -> None:
    metrics = {
        "similaridade_media": 0.6219,
        "sobreposicao_maxima": 17,
        "quase_repetidos": 2842,
        "diversity_score": 0.3781,
        "total_jogos": 5000,
    }
    from lotoia.observability.coverage_evidence_interpreter import interpret_coverage_evidence

    result = interpret_coverage_evidence(metrics)
    joined = " ".join(result.get("evidencias") or [])
    assert "0.622" in joined or "0.6219" in joined
    assert "2842" in joined or "17" in joined
