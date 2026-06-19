"""M-ML-074-DIAG-00 — investigação causal GP 15D (read-only)."""

from __future__ import annotations

import inspect

from lotoia.governance.institutional_agent_routing_matrix import enrich_hierarchy_bundle
from lotoia.ml.gp_delivery_causal_diagnostic import (
    CLASSIFICATION,
    DIAG_VERSION,
    MISSION_ID,
    build_gp_delivery_causal_report,
)
from lotoia.ml.ml_operational_hierarchy import MAX_REMEDIATION_ATTEMPTS


def test_build_gp_delivery_causal_report_structure() -> None:
    report = build_gp_delivery_causal_report()
    assert report["mission_id"] == MISSION_ID
    assert report["diag_version"] == DIAG_VERSION
    assert report["classification"] == CLASSIFICATION == "B"
    assert report["functional_changes"] is False
    assert report["purge_executed"] is False
    assert len(report["flow_steps"]) >= 9
    assert len(report["component_table"]) == 10
    assert report["divergence_point"]["file"].endswith("basic_generator.py")
    assert "gp_closure_allowed" in report["divergence_point"]["condition"]


def test_recovery_attempts_evidence() -> None:
    report = build_gp_delivery_causal_report()
    rec = report["recovery_attempts"]
    assert rec["exists"] is True
    assert rec["max_per_stage"] == MAX_REMEDIATION_ATTEMPTS == 5
    assert "diversidade" in rec["stages"]
    assert "cobertura" in rec["stages"]


def test_metrics_are_hard_gates() -> None:
    report = build_gp_delivery_causal_report()
    assert report["metrics_are_hard_gates"] is True
    assert "0.55" in report["hard_gate_evidence"]
    assert "DIVERSITY_LOW_THRESHOLD" in report["hard_gate_evidence"]


def test_agents_do_not_affect_gp_closure_decision() -> None:
    report = build_gp_delivery_causal_report()
    assert report["agents_affect_decision"] is False

    source = inspect.getsource(enrich_hierarchy_bundle)
    assert "gp_closure_allowed" not in source.replace("source.get(\"gp_closure_allowed\"", "")

    bundle = enrich_hierarchy_bundle(
        {
            "gp_closure_allowed": False,
            "current_stage": "diversidade",
            "stage_results": {
                "diversidade": {
                    "passed": False,
                    "failures": ["diversity_score=0.34 abaixo de 0.55"],
                    "corrective_actions": ["rerank_diversidade"],
                }
            },
        }
    )
    assert bundle["gp_closure_allowed"] is False
    assert bundle.get("blocking_responsible_agent")


def test_blocking_point_before_compose_gp() -> None:
    report = build_gp_delivery_causal_report()
    hierarchy_blk = next(
        bp for bp in report["blocking_points"] if bp["id"] == "BLK-HIERARCHY-073"
    )
    assert hierarchy_blk["before_compose_gp"] is True
    assert hierarchy_blk["intentional"] is True


def test_component_table_required_names() -> None:
    report = build_gp_delivery_causal_report()
    names = {row["component"] for row in report["component_table"]}
    required = {
        "generate_best_games",
        "structural_pool_15d_generator",
        "pre_final_pool_ml_calibration",
        "ml_operational_hierarchy",
        "structural_policy_15d",
        "coverage_evidence_interpreter",
        "agent_routing_matrix",
        "compose_sovereign_gp",
        "Central ML",
        "Cobertura Estrutural",
    }
    assert required <= names


def test_recommended_next_mission() -> None:
    report = build_gp_delivery_causal_report()
    assert "M-ML-074" in report["recommended_next_mission"]
    assert "substituição" in report["recommended_next_mission"].lower()
