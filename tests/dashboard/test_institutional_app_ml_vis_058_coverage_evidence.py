from __future__ import annotations

import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

import dashboard.institutional_ml_calibration_cockpit as cockpit
import dashboard.institutional_supervised_ml as supervised_ml
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_supervised_ml import (
    build_cockpit_persist_bundle,
    build_ml_calibration_cockpit_snapshot,
    build_ml_calibration_recommendations,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.observability.coverage_evidence_interpreter import (
    MISSION_ID,
    get_structural_coverage_evidence,
    interpret_coverage_evidence,
)


def test_build_marker_v39() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v44"


def test_interpret_diversidade_baixa_generates_coherent_recommendation() -> None:
    metrics = {
        "similaridade_media": 0.72,
        "sobreposicao_maxima": 14,
        "quase_repetidos": 30,
        "diversity_score": 0.0,
        "dezenas_subcobertas": 2,
        "prefixos_sufixos_viciados": True,
        "prefixo_mais_gerado": "01-02-03",
        "sufixo_mais_gerado": "23-24-25",
        "total_jogos": 50,
        "desempenho_13_hits": 0,
        "desempenho_14_hits": 0,
    }
    result = interpret_coverage_evidence(metrics, calibration_applied=False, trace_persistido=False)
    assert result["has_structural_issues"] is True
    assert any("diversidade" in item.lower() for item in result["problemas_detectados"])
    assert result["acoes_recomendadas"]
    assert "Estrutura estável" not in result["acoes_recomendadas"][0]
    primary = dict(result["primary_decision"] or {})
    assert primary.get("problema_detectado")
    assert primary.get("evidencia")
    assert primary.get("acao_recomendada")
    assert primary.get("impacto_esperado")


def test_interpret_similaridade_media_in_evidence() -> None:
    metrics = {"similaridade_media": 0.62, "sobreposicao_maxima": 12, "quase_repetidos": 5, "diversity_score": 0.38}
    result = interpret_coverage_evidence(metrics)
    assert any("Similaridade média" in ev for ev in result["evidencias"])


def test_interpret_sobreposicao_maxima_in_evidence() -> None:
    metrics = {"similaridade_media": 0.4, "sobreposicao_maxima": 14, "quase_repetidos": 0, "diversity_score": 0.6}
    result = interpret_coverage_evidence(metrics)
    assert any("Sobreposição máxima" in ev for ev in result["evidencias"])


def test_interpret_quase_repetidos_in_evidence() -> None:
    metrics = {"similaridade_media": 0.5, "sobreposicao_maxima": 10, "quase_repetidos": 25, "diversity_score": 0.5}
    result = interpret_coverage_evidence(metrics)
    assert any("Quase repetidos" in ev for ev in result["evidencias"])


def test_interpret_dezenas_subcobertas_recommendation() -> None:
    metrics = {
        "similaridade_media": 0.4,
        "sobreposicao_maxima": 10,
        "quase_repetidos": 0,
        "diversity_score": 0.6,
        "dezenas_subcobertas": 4,
        "issue_types": ["dezena_subcoberta"],
    }
    result = interpret_coverage_evidence(metrics)
    assert any("subcobert" in action.lower() for action in result["acoes_recomendadas"])


def test_interpret_prefixos_viciados_recommendation() -> None:
    metrics = {
        "similaridade_media": 0.4,
        "sobreposicao_maxima": 10,
        "quase_repetidos": 0,
        "diversity_score": 0.6,
        "prefixos_sufixos_viciados": True,
        "prefixo_mais_gerado": "01-02-03",
        "sufixo_mais_gerado": "23-24-25",
    }
    result = interpret_coverage_evidence(metrics)
    assert any("prefixo" in action.lower() or "sufixo" in action.lower() for action in result["acoes_recomendadas"])


def test_recommendations_use_coverage_evidence_not_generic_stable() -> None:
    coverage = {
        "available": True,
        "acoes_recomendadas": ["Aumentar penalidade de overlap e reforçar dezenas subcobertas."],
    }
    recs = build_ml_calibration_recommendations(None, coverage_evidence=coverage)
    assert recs == coverage["acoes_recomendadas"]
    assert "Estrutura estável" not in recs[0]


def test_persist_bundle_includes_coverage_trace_fields() -> None:
    bundle = build_cockpit_persist_bundle(
        workflow_status="autorizada",
        decision_at="2026-06-17T12:00:00+00:00",
        apply_next_generation=True,
        recommendations=["Penalizar overlap"],
        coverage_evidence={
            "available": True,
            "problemas_detectados": ["Diversidade baixa."],
            "evidencias": ["Score diversidade 0.0"],
            "impacto_esperado": "Melhor cobertura na próxima geração.",
            "primary_decision": {
                "impacto_esperado": "Melhor cobertura na próxima geração.",
                "trace": {"mission_id": MISSION_ID},
            },
        },
        operator_decision="autorizar",
    )
    assert bundle["coverage_evidence_mission"] == MISSION_ID
    assert bundle["calibration_authorized"] is True
    assert bundle["problemas_detectados"]
    assert bundle["evidencias"]
    assert bundle["trace"]["mission_id"] == MISSION_ID
    assert bundle["impacto_esperado"]


def test_cockpit_module_renders_decision_sections() -> None:
    source = inspect.getsource(cockpit)
    assert "Problema detectado" in source
    assert "Evidência" in source
    assert "Impacto esperado" in source
    assert "Cobertura Estrutural" in source
    assert "Snapshot Cobertura Estrutural" in source


def test_cockpit_snapshot_includes_coverage_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "coverage_evidence.db"
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
                "calibration_applied": False,
                "calibration_diagnostics": {
                    "issues": [{"tipo": "dezena_subcoberta", "descricao": "Dezena 11 subcoberta"}],
                    "redundancy": {"cartoes_quase_repetidos": 25, "sobreposicao_media": 11.0},
                },
                "issues_detected": ["Dezena 11 subcoberta"],
                "diversity_score": 0.0,
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

    snapshot = build_ml_calibration_cockpit_snapshot(db_path)
    assert snapshot.get("coverage_evidence_mission") == MISSION_ID
    coverage = dict(snapshot.get("coverage_evidence") or {})
    assert "coverage_evidence" in snapshot
    if coverage.get("available"):
        assert coverage.get("metrics")
        assert snapshot.get("decision_blocks") is not None
    assert snapshot.get("primary_decision") is not None or snapshot.get("recommendations")


def test_get_structural_coverage_evidence_mission_id() -> None:
    payload = get_structural_coverage_evidence("/tmp/nonexistent-for-empty.db")
    assert payload["mission_id"] == MISSION_ID
