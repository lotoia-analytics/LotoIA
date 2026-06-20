"""M-ML-076-FIX-01 — hits 13/14/15 fora do veredito estrutural e liberação."""

from __future__ import annotations

import inspect
from typing import Any

import dashboard.institutional_ml_calibration_cockpit as cockpit
from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.ml_operational_verdict import (
    HITS_SEPARATION_MISSION_ID,
    VERDICT_APROVADO,
    VERDICT_PRECISA_CALIBRAR,
    VERDICT_REPROVADO,
    build_structural_verdict_hits_separation_trace,
    evaluate_ml_operational_verdict,
)
from lotoia.ml.overlap_format_thresholds import evaluate_format_overlap_verdict
from lotoia.observability.coverage_evidence_interpreter import (
    build_calibration_plan,
    build_historical_hit_analytics_summary,
    interpret_coverage_evidence,
)


def _edge_metrics(*, hits_13: int, hits_14: int = 0, hits_15: int = 0) -> dict[str, Any]:
    """Cenário limítrofe da auditoria M-ML-076-AUDIT-00 (sim=0,56, QR=2)."""
    return {
        "similaridade_media": 0.56,
        "sobreposicao_maxima": 10,
        "quase_repetidos_criticos": 2,
        "pares_em_atencao": 4,
        "dezenas_subcobertas": 0,
        "diversity_score": 0.44,
        "total_jogos": 20,
        "desempenho_13_hits": hits_13,
        "desempenho_14_hits": hits_14,
        "desempenho_15_hits": hits_15,
        "formatos_analisados": [15],
        "primary_format_size": 15,
    }


def _format_analyses() -> list[dict[str, Any]]:
    return [
        evaluate_format_overlap_verdict(
            15,
            10,
            {"similaridade_media": 0.56, "quase_repetidos": 2},
        ),
    ]


def test_build_marker_v78_hits_separation() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v81"


def test_separation_trace_fields() -> None:
    trace = build_structural_verdict_hits_separation_trace()
    assert trace["structural_verdict_ignores_hits"] is True
    assert trace["hits_evaluation_scope"] == "historical_analytics_only"
    assert trace["hit_metrics_excluded_from_release"] is True
    assert trace["m_ml_076_fix_01_applied"] is True
    assert trace["hits_separation_mission_id"] == HITS_SEPARATION_MISSION_ID


def test_counterfactual_same_structure_hits_zero_vs_positive() -> None:
    """Mesma estrutura: hits=0 e hits>=1 devem produzir mesmo veredito estrutural."""
    base = _edge_metrics(hits_13=0)
    with_hits = _edge_metrics(hits_13=3, hits_14=1, hits_15=1)
    formats = _format_analyses()

    zero_payload = evaluate_ml_operational_verdict(base, format_analyses=formats)
    hits_payload = evaluate_ml_operational_verdict(with_hits, format_analyses=formats)

    assert zero_payload["ml_verdict"] == hits_payload["ml_verdict"]
    assert zero_payload["official_release_allowed"] == hits_payload["official_release_allowed"]
    assert zero_payload["ml_verdict"] == VERDICT_APROVADO
    assert zero_payload["official_release_allowed"] is True
    assert "captura_ausente_redundancia" not in zero_payload["trace"]["rule_triggers"]
    assert "captura_ausente_redundancia" not in hits_payload["trace"]["rule_triggers"]


def test_zero_hits_not_penalized_on_borderline_structure() -> None:
    payload = evaluate_ml_operational_verdict(
        _edge_metrics(hits_13=0),
        format_analyses=_format_analyses(),
    )
    assert payload["ml_verdict"] == VERDICT_APROVADO
    assert payload["official_release_allowed"] is True
    reason = str(payload.get("motivo_principal") or payload.get("ml_verdict_reason") or "").lower()
    for forbidden in ("captura 13/14", "ausência de captura", "zero hits", "baixa força de captura"):
        assert forbidden not in reason


def test_high_redundancy_with_zero_hits_still_blocks_structurally() -> None:
    """Estrutura realmente crítica continua bloqueada — sem depender de hits."""
    metrics = {
        "similaridade_media": 0.58,
        "sobreposicao_maxima": 12,
        "quase_repetidos_criticos": 25,
        "pares_em_atencao": 18,
        "dezenas_subcobertas": 2,
        "diversity_score": 0.42,
        "total_jogos": 20,
        "desempenho_13_hits": 0,
        "desempenho_14_hits": 0,
        "desempenho_15_hits": 0,
        "formatos_analisados": [15],
        "primary_format_size": 15,
    }
    formats = [
        evaluate_format_overlap_verdict(
            15,
            12,
            {"similaridade_media": 0.58, "quase_repetidos": 25},
        ),
    ]
    zero_hits = evaluate_ml_operational_verdict(metrics, format_analyses=formats)
    with_hits = evaluate_ml_operational_verdict(
        {**metrics, "desempenho_13_hits": 5},
        format_analyses=formats,
    )
    assert zero_hits["ml_verdict"] == with_hits["ml_verdict"]
    assert zero_hits["ml_verdict"] in {VERDICT_PRECISA_CALIBRAR, VERDICT_REPROVADO}
    assert not zero_hits["official_release_allowed"]
    assert "captura_ausente" not in str(zero_hits.get("ml_verdict_reason") or "").lower()


def test_interpret_coverage_evidence_no_capture_decision_block() -> None:
    interpretation = interpret_coverage_evidence(_edge_metrics(hits_13=0))
    blocks = list(interpretation.get("decision_blocks") or [])
    issue_types = {str(row.get("issue_type") or "") for row in blocks}
    assert "captura_13_14_ausente" not in issue_types
    motivo = str(interpretation.get("motivo_principal") or "").lower()
    assert "captura 13/14" not in motivo
    assert "ausência de captura" not in motivo


def test_calibration_plan_excludes_capture_actions() -> None:
    plan = build_calibration_plan(_edge_metrics(hits_13=0))
    joined = " ".join(plan.get("plan_items") or []).lower()
    assert "captura 13/14" not in joined
    assert "13/14/15" not in joined
    assert "zero hits" not in joined


def test_historical_hit_analytics_still_available() -> None:
    analytics = build_historical_hit_analytics_summary(_edge_metrics(hits_13=2, hits_14=1))
    assert analytics["available"] is True
    assert analytics["desempenho_13_hits"] == 2
    assert analytics["desempenho_14_hits"] == 1
    assert analytics["hits_evaluation_scope"] == "historical_analytics_only"


def test_verdict_payload_includes_separation_trace() -> None:
    payload = evaluate_ml_operational_verdict(_edge_metrics(hits_13=0), format_analyses=_format_analyses())
    assert payload["structural_verdict_ignores_hits"] is True
    assert payload["m_ml_076_fix_01_applied"] is True
    assert payload["trace"]["hit_metrics_excluded_from_release"] is True
    snapshot_hits = payload["metrics_snapshot"]
    assert snapshot_hits["desempenho_13_hits"] == 0


def test_central_ml_hits_only_in_technical_audit() -> None:
    audit_source = inspect.getsource(cockpit._render_technical_audit_section)
    diagnosis_source = inspect.getsource(cockpit._render_diagnosis_card)
    decision_source = inspect.getsource(cockpit._render_decision_evidence_card)
    assert "_render_historical_hit_analytics_card" in audit_source
    assert "auditoria_hits_analiticos" in audit_source
    assert "desempenho_13_hits" not in diagnosis_source
    assert "captura 13/14" not in decision_source.lower()


def test_promotion_block_reason_never_uses_captura_ausente() -> None:
    from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict
    from lotoia.operations.lot_operational_status import (
        promote_post_calibration_consumer_lot_visibility,
        build_lot_status_context,
    )

    verdict_payload = evaluate_ml_operational_verdict(
        _edge_metrics(hits_13=0),
        format_analyses=_format_analyses(),
    )
    context = build_lot_status_context(ml_verdict_payload=verdict_payload)
    promoted = promote_post_calibration_consumer_lot_visibility(
        context,
        authorized_plan={
            "calibration_plan_loaded_from_db": True,
            "calibration_plan_applied_to_generation": True,
            "calibration_plan_source_generation_event_id": 10,
            "calibration_trace_id": "trace-edge",
        },
        promotion_context={
            "generated_games_count": 20,
            "requested_count": 20,
            "persistence_supported": True,
            "persistence_blocked": False,
            "runtime_contract_broken": False,
            "hierarchy_delivery_blocked": False,
            "gp_quality_tier": "APROVADO",
            "ml_verdict": verdict_payload["ml_verdict"],
            "official_release_allowed": verdict_payload["official_release_allowed"],
        },
    )
    reason = str(promoted.get("promotion_block_reason") or "").lower()
    assert "captura_ausente" not in reason
    assert context.get("structural_verdict_ignores_hits") is True


def test_card_structure_diagnostics_still_exposes_hits() -> None:
    from lotoia.statistics.card_structure import analyze_stuck_games

    official = list(range(1, 16))
    games = [{"numbers": official, "hits": 13}]
    payload = analyze_stuck_games(games, official_numbers=official)
    assert len(payload["jogos_com_13_hits"]) == 1
