from __future__ import annotations

import json
import tempfile
from pathlib import Path

from lotoia.orchestration import (
    build_intelligent_operational_orchestration,
    load_intelligent_operational_orchestration,
    persist_intelligent_operational_orchestration,
)


def test_build_intelligent_operational_orchestration_returns_context(monkeypatch) -> None:
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_analytical_intelligence",
        lambda: {"analytical_summary": {"drift": 0.12}},
    )
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_executive_analytical_report",
        lambda: {
            "status": "saudavel",
            "headline": "baseline longitudinal consistente",
            "recommendation": "manter baseline hard e monitorar longitudinalmente",
            "confidence": "alta",
        },
    )
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_institutional_historical_intelligence",
        lambda: {"summary": {"trend": "estavel", "verdict_count": 2, "latest_status": "saudavel"}},
    )
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_adaptive_institutional_intelligence",
        lambda: {"summary": {"trend": "evolucao estrutural", "memory_depth": 3, "persistent_changes": 1, "latest_recommendation": "monitorar"}},
    )
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_observational_stabilization_report",
        lambda: {"summary": {"homepage_priority": "institutional_first", "stability_note": "cockpit institucional validado", "institutional_snapshot_ready": True, "institutional_timeline_ready": True}},
    )
    monkeypatch.setattr(
        "lotoia.orchestration.intelligent_orchestration.build_institutional_analytical_timeline",
        lambda: {"summary": {"latest_transition": "observacao -> saudavel", "verdict_count": 2}},
    )

    payload = build_intelligent_operational_orchestration(Path("reports") / "orchestration")

    assert payload["schema_version"] == "intelligent-operational-orchestration-v1.0.0"
    assert payload["summary"]["orchestration_state"] in {"coordenada", "atencao"}
    assert payload["summary"]["memory_depth"] >= 0
    assert payload["decision_context"]["headline"] == "baseline longitudinal consistente"
    assert payload["events"]
    assert payload["live_coordination"]["state"] in {"live", "monitoring"}
    assert payload["signal_engine"]["state"] in {"stable", "attention", "observation"}
    assert payload["institutional_presence"]["presence_state"] in {"coordenada", "adaptativa"}


def test_persist_and_load_intelligent_operational_orchestration(monkeypatch) -> None:
    temp_root = Path(tempfile.mkdtemp(dir=Path.cwd()))
    orchestration_dir = temp_root / "reports" / "orchestration"
    orchestration_dir.mkdir(parents=True, exist_ok=True)
    report_path = orchestration_dir / "intelligent_operational_orchestration.json"

    monkeypatch.chdir(temp_root)
    payload = persist_intelligent_operational_orchestration(report_path, report_dir=orchestration_dir)
    loaded = load_intelligent_operational_orchestration(report_path)

    assert report_path.exists()
    assert payload["schema_version"] == "intelligent-operational-orchestration-v1.0.0"
    assert loaded["schema_version"] == "intelligent-operational-orchestration-v1.0.0"
    assert loaded["generated_by"] == "persist_intelligent_operational_orchestration"
