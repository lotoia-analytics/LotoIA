"""M-ML-075-DIAG-00 — auditoria causal calibração → geração seguinte (read-only)."""

from __future__ import annotations

import inspect

from lotoia.ml.calibration_causal_diagnostic import (
    CLASSIFICATION,
    DIAG_VERSION,
    MISSION_ID,
    build_calibration_causal_report,
    compare_consecutive_generations,
    extract_generation_calibration_evidence,
)


def test_build_calibration_causal_report_structure() -> None:
    report = build_calibration_causal_report()
    assert report["mission_id"] == MISSION_ID
    assert report["diag_version"] == DIAG_VERSION
    assert report["classification"] == CLASSIFICATION == "D"
    assert report["functional_changes"] is False
    assert report["purge_executed"] is False
    assert len(report["flow_steps"]) >= 8
    assert len(report["component_table"]) >= 8
    assert report["replay_experiment"]["deltas"]["redundancy_penalty"] >= 0


def test_extract_generation_calibration_evidence() -> None:
    evidence = extract_generation_calibration_evidence(
        {
            "calibration_applied": True,
            "diversity_score": 0.3337,
            "cockpit_calibration_workflow": {
                "calibration_authorized": True,
                "cockpit_apply_next_generation": True,
                "parametros_sugeridos": {"redundancy_penalty_boost": 1.2},
                "trace": {"mission_id": "M-ML-VIS-058-FIX-01"},
            },
            "pre_final_pool_ml_calibration": {
                "final_diversity_score": 0.3337,
                "final_similarity_score": 0.6663,
                "diversity_delta": 0.0,
                "authorized_calibration_plan": {
                    "parametros_sugeridos": {"redundancy_penalty_boost": 1.2},
                },
            },
            "ml_hierarchy_bundle": {"gp_quality_tier": "REPROVADO"},
            "ml_verdict": "REPROVADO",
        }
    )
    assert evidence["calibration_applied"] is True
    assert evidence["calibration_authorized"] is True
    assert evidence["cockpit_apply_next_generation"] is True
    assert evidence["gp_quality_tier"] == "REPROVADO"
    assert evidence["diversity_score"] == 0.3337


def test_compare_consecutive_generations_operational_pattern() -> None:
    """Padrão reportado: N calibrado, N+1 pior diversidade, sem carry-forward de plano."""
    gen_n = {
        "id": 100,
        "context_json": {
            "calibration_applied": True,
            "diversity_score": 0.365,
            "cockpit_calibration_workflow": {
                "calibration_authorized": True,
                "cockpit_apply_next_generation": True,
                "parametros_sugeridos": {
                    "redundancy_penalty_boost": 1.2,
                    "missing_numbers_boost": 1.2,
                    "dezenas_subcobertas": ["07", "11", "23"],
                },
            },
            "pre_final_pool_ml_calibration": {
                "final_diversity_score": 0.365,
                "final_similarity_score": 0.635,
                "authorized_calibration_plan": {
                    "parametros_sugeridos": {"redundancy_penalty_boost": 1.2},
                },
            },
        },
    }
    gen_n1 = {
        "id": 101,
        "context_json": {
            "calibration_applied": True,
            "diversity_score": 0.3337,
            "cockpit_calibration_workflow": {},
            "pre_final_pool_ml_calibration": {
                "final_diversity_score": 0.3337,
                "final_similarity_score": 0.6663,
                "authorized_calibration_plan": {},
            },
            "ml_hierarchy_bundle": {"gp_quality_tier": "REPROVADO"},
            "ml_verdict": "REPROVADO",
        },
    }
    comparison = compare_consecutive_generations(gen_n, gen_n1)
    assert comparison["deltas"]["diversity_score"] < 0
    assert comparison["deltas"]["plan_carried_forward"] is False
    assert comparison["generation_n1"]["evidence"]["ml_verdict"] == "REPROVADO"


def test_no_functional_generator_changes() -> None:
    from lotoia.generator import basic_generator

    source = inspect.getsource(basic_generator.generate_best_games)
    assert "M-ML-075" not in source


def test_audit_script_exists() -> None:
    from pathlib import Path

    script = Path("scripts/ops/m_ml_075_diag_00_calibration_causal_audit.py")
    assert script.is_file()
    assert "build_calibration_causal_report" in script.read_text(encoding="utf-8")
