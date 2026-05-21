from __future__ import annotations

import json
from pathlib import Path

from lotoia.analytics import (
    build_analytical_intelligence,
    build_institutional_analytical_timeline,
    build_institutional_historical_intelligence,
    ensure_institutional_analytical_timeline,
    load_institutional_analytical_timeline,
    publish_institutional_analytics,
    interpret_longitudinal_report,
    persist_institutional_analytical_timeline,
    persist_institutional_analytics_snapshot,
    persist_executive_analytical_report,
    persist_institutional_historical_intelligence,
)


def test_analytical_intelligence_interprets_longitudinal_report(tmp_path: Path) -> None:
    report_path = tmp_path / "baseline_hard_longitudinal.json"
    report_path.write_text(
        json.dumps(
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "baseline_mode": "hard",
                "summary": {
                    "stability_index": 0.92,
                    "coverage_10": 0.40,
                    "coverage_11": 0.10,
                    "average_hits": 9.1,
                    "hits_standard_deviation": 1.2,
                    "drift": 0.18,
                    "runtime_profile": "incremental_longitudinal",
                },
                "runs": [
                    {"checkpoint": 10, "result": {"lotoia": {"average_hits": 9.0, "standard_deviation": 1.3, "final_score_hit_correlation": 0.21, "stability_window_sd": 0.8}}},
                    {"checkpoint": 25, "result": {"lotoia": {"average_hits": 9.2, "standard_deviation": 1.1, "final_score_hit_correlation": 0.25, "stability_window_sd": 0.7}}},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    insights = interpret_longitudinal_report(report)
    payload = build_analytical_intelligence(report_path)

    assert payload["baseline_mode"] == "hard"
    assert payload["analytical_summary"]["structural_health"] == 0.92
    assert payload["analytical_summary"]["confidence"] == "alta"
    assert len(payload["insights"]) >= 5
    assert any(insight.metric == "longitudinal_profile" for insight in insights)
    assert payload["comparisons"][0]["label"] == "média de acertos"


def test_persist_executive_analytical_report(tmp_path: Path) -> None:
    longitudinal_report = tmp_path / "baseline_hard_longitudinal.json"
    longitudinal_report.write_text(
        json.dumps(
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "baseline_mode": "hard",
                "summary": {
                    "stability_index": 0.91,
                    "coverage_10": 0.50,
                    "coverage_11": 0.20,
                    "average_hits": 9.4,
                    "hits_standard_deviation": 1.0,
                    "drift": 0.12,
                    "runtime_profile": "incremental_longitudinal",
                },
                "runs": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report_path = tmp_path / "reports" / "analytics" / "executive_analytical_report.json"
    payload = persist_executive_analytical_report(report_path, longitudinal_report_path=longitudinal_report)

    assert report_path.exists()
    assert payload["report"]["status"] == "saudavel"
    assert payload["source"] == str(longitudinal_report)


def test_institutional_historical_intelligence_reads_verdict_history(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    first_report = analytics_dir / "executive_analytical_report_001.json"
    second_report = analytics_dir / "executive_analytical_report_002.json"
    first_report.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-21T00:00:00+00:00",
                "source": "reports/longitudinal/baseline_hard_longitudinal.json",
                "report": {
                    "status": "observacao",
                    "headline": "baseline longitudinal consistente",
                    "recommendation": "manter baseline hard com observacao reforcada",
                    "confidence": "moderada",
                    "structural_health": 0.74,
                    "drift": 0.24,
                    "coverage_11": 0.18,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    second_report.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-22T00:00:00+00:00",
                "source": "reports/longitudinal/baseline_hard_longitudinal.json",
                "report": {
                    "status": "saudavel",
                    "headline": "baseline longitudinal consistente",
                    "recommendation": "manter baseline hard e monitorar longitudinalmente",
                    "confidence": "alta",
                    "structural_health": 0.92,
                    "drift": 0.12,
                    "coverage_11": 0.25,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = build_institutional_historical_intelligence(analytics_dir)

    assert payload["summary"]["trend"] == "melhoria controlada"
    assert payload["summary"]["verdict_count"] == 2
    assert payload["summary"]["latest_status"] == "saudavel"
    assert payload["timeline"][-1]["confidence"] == "alta"


def test_persist_institutional_historical_intelligence(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    report_path = analytics_dir / "institutional_historical_intelligence.json"
    payload = persist_institutional_historical_intelligence(report_path, report_dir=analytics_dir)

    assert report_path.exists()
    assert payload["source"] == str(analytics_dir)
    assert payload["schema_version"] == "institutional-analytics-v1.0.0"
    assert payload["generated_by"] == "build_institutional_historical_intelligence"
    assert "report" in payload


def test_persist_institutional_analytics_snapshot(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    longitudinal_report = tmp_path / "baseline_hard_longitudinal.json"
    longitudinal_report.write_text(
        json.dumps(
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "baseline_mode": "hard",
                "summary": {
                    "stability_index": 0.94,
                    "coverage_10": 0.52,
                    "coverage_11": 0.21,
                    "average_hits": 9.5,
                    "hits_standard_deviation": 0.9,
                    "drift": 0.11,
                    "runtime_profile": "incremental_longitudinal",
                },
                "runs": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    executive_path = analytics_dir / "executive_analytical_report.json"
    persist_executive_analytical_report(executive_path, longitudinal_report_path=longitudinal_report)
    report_path = analytics_dir / "institutional_analytics_snapshot.json"
    payload = persist_institutional_analytics_snapshot(report_path, report_dir=analytics_dir)

    assert report_path.exists()
    assert payload["summary"]["status"] == "saudavel"
    assert payload["summary"]["trend"] in {"estavel", "melhoria controlada"}
    assert payload["schema_version"] == "institutional-analytics-v1.0.0"
    assert payload["generated_by"] == "persist_institutional_analytics_snapshot"


def test_publish_institutional_analytics(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    longitudinal_report = tmp_path / "baseline_hard_longitudinal.json"
    longitudinal_report.write_text(
        json.dumps(
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "baseline_mode": "hard",
                "summary": {
                    "stability_index": 0.93,
                    "coverage_10": 0.51,
                    "coverage_11": 0.23,
                    "average_hits": 9.6,
                    "hits_standard_deviation": 0.8,
                    "drift": 0.10,
                    "runtime_profile": "incremental_longitudinal",
                },
                "runs": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    result = publish_institutional_analytics(
        report_dir=analytics_dir,
        executive_report_path=analytics_dir / "executive_analytical_report.json",
        historical_report_path=analytics_dir / "institutional_historical_intelligence.json",
        snapshot_path=analytics_dir / "institutional_analytics_snapshot.json",
    )

    assert (analytics_dir / "executive_analytical_report.json").exists()
    assert (analytics_dir / "institutional_historical_intelligence.json").exists()
    assert (analytics_dir / "institutional_analytics_snapshot.json").exists()
    assert result["snapshot"]["summary"]["status"] == "saudavel"
    assert result["historical_report"]["schema_version"] == "institutional-analytics-v1.0.0"
    assert result["historical_report"]["generated_by"] == "build_institutional_historical_intelligence"


def test_institutional_analytical_timeline(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    longitudinal_report = tmp_path / "baseline_hard_longitudinal.json"
    longitudinal_report.write_text(
        json.dumps(
            {
                "created_at": "2026-05-21T00:00:00+00:00",
                "baseline_mode": "hard",
                "summary": {
                    "stability_index": 0.95,
                    "coverage_10": 0.52,
                    "coverage_11": 0.21,
                    "average_hits": 9.6,
                    "hits_standard_deviation": 0.8,
                    "drift": 0.10,
                    "runtime_profile": "incremental_longitudinal",
                },
                "runs": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    publish_institutional_analytics(
        report_dir=analytics_dir,
        executive_report_path=analytics_dir / "executive_analytical_report.json",
        historical_report_path=analytics_dir / "institutional_historical_intelligence.json",
        snapshot_path=analytics_dir / "institutional_analytics_snapshot.json",
    )
    payload = persist_institutional_analytical_timeline(
        analytics_dir / "institutional_analytical_timeline.json",
        report_dir=analytics_dir,
    )

    assert payload["schema_version"] == "institutional-analytics-v1.0.0"
    assert payload["generated_by"] == "build_institutional_analytical_timeline"
    assert payload["report"]["summary"]["trend"] in {"estavel", "acumulacao institucional", "melhoria institucional"}
    assert build_institutional_analytical_timeline(analytics_dir)["summary"]["latest_status"] == "saudavel"


def test_institutional_analytical_timeline_tracks_transitions(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    first_snapshot = analytics_dir / "institutional_analytics_snapshot_001.json"
    second_snapshot = analytics_dir / "institutional_analytics_snapshot_002.json"
    first_snapshot.write_text(
        json.dumps(
            {
                "source": str(analytics_dir),
                "schema_version": "institutional-analytics-v1.0.0",
                "generated_by": "persist_institutional_analytics_snapshot",
                "executive_report": {"generated_at": "2026-05-21T00:00:00+00:00", "status": "observacao", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard com observacao reforcada", "confidence": "moderada"},
                "historical_report": {"summary": {"trend": "estavel", "latest_status": "observacao", "verdict_count": 1}},
                "summary": {"headline": "baseline longitudinal consistente", "status": "observacao", "trend": "estavel", "latest_status": "observacao", "verdict_count": 1},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    second_snapshot.write_text(
        json.dumps(
            {
                "source": str(analytics_dir),
                "schema_version": "institutional-analytics-v1.0.0",
                "generated_by": "persist_institutional_analytics_snapshot",
                "executive_report": {"generated_at": "2026-05-22T00:00:00+00:00", "status": "saudavel", "headline": "baseline longitudinal consistente", "recommendation": "manter baseline hard e monitorar longitudinalmente", "confidence": "alta"},
                "historical_report": {"summary": {"trend": "melhoria controlada", "latest_status": "saudavel", "verdict_count": 2}},
                "summary": {"headline": "baseline longitudinal consistente", "status": "saudavel", "trend": "melhoria controlada", "latest_status": "saudavel", "verdict_count": 2},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    timeline = build_institutional_analytical_timeline(analytics_dir)

    assert timeline["summary"]["latest_transition"] == "observacao -> saudavel"
    assert timeline["timeline"][-1]["status_transition"] == "observacao -> saudavel"


def test_load_and_ensure_institutional_analytical_timeline(tmp_path: Path) -> None:
    analytics_dir = tmp_path / "reports" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)
    report_path = analytics_dir / "institutional_analytical_timeline.json"
    assert load_institutional_analytical_timeline(report_path) == {}

    payload = ensure_institutional_analytical_timeline(report_path, report_dir=analytics_dir)
    loaded = load_institutional_analytical_timeline(report_path)

    assert payload["schema_version"] == "institutional-analytics-v1.0.0"
    assert loaded["schema_version"] == "institutional-analytics-v1.0.0"
