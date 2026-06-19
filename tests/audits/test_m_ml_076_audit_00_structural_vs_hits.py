"""M-ML-076-AUDIT-00 — smoke tests da auditoria estrutural vs hits."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audits.m_ml_076_audit_00_structural_vs_hits import MISSION_ID, run_audit


def test_audit_runs_and_classifies_hits_interference() -> None:
    payload = run_audit(db_path=None, output=None)
    assert payload["mission_id"] == MISSION_ID
    assert payload["classification"] in {"A", "B"}
    assert payload["hits_interfere_liberacao"] is False
    labels = [row["label"] for row in payload["synthetic_scenarios"]]
    assert any("limítrofe" in label for label in labels)
    edge = next(row for row in payload["synthetic_scenarios"] if "limítrofe" in row["label"])
    assert edge["counterfactual"]["verdict_differs"] is False
    assert edge["counterfactual"]["release_differs"] is False
    assert "captura_ausente_redundancia" not in edge["counterfactual"]["rule_triggers"]


def test_evidence_json_on_disk_matches_schema() -> None:
    evidence_path = Path("docs/audits/M-ML-076-AUDIT-00_evidence.json")
    if not evidence_path.exists():
        run_audit(db_path=None, output=evidence_path)
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert "audited_files" in payload
    assert "ml_operational_verdict.py" in payload["audited_files"][-8]
    assert payload["functional_integrity"]["code_changes_to_verdict"] is False
