from __future__ import annotations

import json
from pathlib import Path

from lotoia.analytics.adaptive_intelligence import (
    build_adaptive_institutional_intelligence,
    build_institutional_pattern_detection,
    build_operational_memory,
    build_temporal_adaptive_analysis,
    load_adaptive_institutional_intelligence,
    persist_adaptive_institutional_intelligence,
    publish_adaptive_institutional_intelligence,
)


def _write_executive_report(path: Path, *, generated_at: str, status: str, headline: str, recommendation: str, confidence: str, structural_health: float, drift: float, trend: str = "estavel") -> None:
    path.write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "source": "reports/longitudinal/baseline_hard_longitudinal.json",
                "schema_version": "institutional-analytics-v1.0.0",
                "generated_by": "test",
                "report": {
                    "status": status,
                    "headline": headline,
                    "recommendation": recommendation,
                    "confidence": confidence,
                    "structural_health": structural_health,
                    "drift": drift,
                    "trend": trend,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_build_adaptive_institutional_intelligence_uses_persisted_reports(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "analytics"
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_executive_report(
        report_dir / "executive_analytical_report_1.json",
        generated_at="2026-05-21T00:00:00+00:00",
        status="saudavel",
        headline="baseline consistente",
        recommendation="monitorar",
        confidence="alta",
        structural_health=0.93,
        drift=0.12,
    )
    _write_executive_report(
        report_dir / "executive_analytical_report_2.json",
        generated_at="2026-05-22T00:00:00+00:00",
        status="saudavel",
        headline="baseline consistente",
        recommendation="monitorar",
        confidence="alta",
        structural_health=0.94,
        drift=0.11,
    )

    payload = build_adaptive_institutional_intelligence(report_dir)

    assert payload["schema_version"] == "adaptive-institutional-v1.0.0"
    assert payload["operational_memory"]["summary"]["memory_depth"] == 2
    assert payload["temporal_analysis"]["summary"]["memory_depth"] == 2
    assert payload["pattern_detection"]["summary"]["pattern"] in {"recorrencia institucional", "mudanca estrutural persistente", "observacao"}
    assert payload["adaptive_presence"]["summary"]["presence"] in {"adaptativa", "observacional"}


def test_persist_and_load_adaptive_institutional_intelligence(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "analytics"
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_executive_report(
        report_dir / "executive_analytical_report_1.json",
        generated_at="2026-05-21T00:00:00+00:00",
        status="saudavel",
        headline="baseline consistente",
        recommendation="monitorar",
        confidence="alta",
        structural_health=0.93,
        drift=0.12,
    )

    report_path = tmp_path / "reports" / "analytics" / "adaptive_institutional_memory.json"
    payload = persist_adaptive_institutional_intelligence(report_path, report_dir=report_dir)
    loaded = load_adaptive_institutional_intelligence(report_path)

    assert loaded["schema_version"] == "adaptive-institutional-v1.0.0"
    assert payload["schema_version"] == "adaptive-institutional-v1.0.0"
    assert loaded["operational_memory"]["summary"]["memory_depth"] == 1


def test_adaptive_pattern_and_timeline_are_persistable(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports" / "analytics"
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_executive_report(
        report_dir / "executive_analytical_report_1.json",
        generated_at="2026-05-21T00:00:00+00:00",
        status="saudavel",
        headline="baseline consistente",
        recommendation="monitorar",
        confidence="alta",
        structural_health=0.93,
        drift=0.12,
    )
    _write_executive_report(
        report_dir / "executive_analytical_report_2.json",
        generated_at="2026-05-22T00:00:00+00:00",
        status="saudavel",
        headline="baseline consistente",
        recommendation="monitorar",
        confidence="alta",
        structural_health=0.94,
        drift=0.11,
    )

    temporal = build_temporal_adaptive_analysis(report_dir)
    pattern = build_institutional_pattern_detection(report_dir)
    published = publish_adaptive_institutional_intelligence(
        report_dir=report_dir,
        memory_path=tmp_path / "reports" / "analytics" / "adaptive_institutional_memory.json",
        timeline_path=tmp_path / "reports" / "analytics" / "adaptive_institutional_timeline.json",
        insights_path=tmp_path / "reports" / "analytics" / "adaptive_institutional_insights.json",
    )

    assert temporal["summary"]["memory_depth"] == 2
    assert pattern["summary"]["memory_depth"] == 2
    assert published["adaptive_memory"]["schema_version"] == "adaptive-institutional-v1.0.0"
    assert published["adaptive_timeline"]["schema_version"] == "adaptive-institutional-v1.0.0"
    assert published["adaptive_insights"]["schema_version"] == "adaptive-institutional-v1.0.0"
