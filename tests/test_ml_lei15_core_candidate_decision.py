from __future__ import annotations

from lotoia.ml.lei15_core_candidate_decision import (
    CANDIDATE_ID,
    build_ml_decision,
)


def test_ml_decision_defines_candidate() -> None:
    d = build_ml_decision()
    assert d["final_verdict"] == "NÚCLEO CANDIDATO DEFINIDO"
    assert d["proposed_architecture"]["candidate_id"] == CANDIDATE_ID
    assert d["ml_operational_effect"] is False
    assert d["lei15a_recommendation"]["open_now"] is False


def test_six_bases_projection_no_fraca() -> None:
    d = build_ml_decision()
    proj = d["six_bases_reading"]["proposed_cand_002_projected"]
    assert "fraca" not in proj.values()
    assert d["six_bases_reading"]["projected_balance_score"] >= 12
