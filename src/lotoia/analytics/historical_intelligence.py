from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from lotoia.analytics.intelligence_layer import build_executive_analytical_report
from lotoia.combinatorics.expansion_store import list_expansion_events

DEFAULT_ANALYTICS_DIR = Path("reports") / "analytics"
DEFAULT_INSTITUTIONAL_HISTORICAL_REPORT = Path("reports") / "analytics" / "institutional_historical_intelligence.json"
DEFAULT_INSTITUTIONAL_ANALYTICS_SNAPSHOT = Path("reports") / "analytics" / "institutional_analytics_snapshot.json"
DEFAULT_INSTITUTIONAL_ANALYTICAL_TIMELINE = Path("reports") / "analytics" / "institutional_analytical_timeline.json"
INSTITUTIONAL_ANALYTICS_SCHEMA_VERSION = "institutional-analytics-v1.0.0"


@dataclass(frozen=True)
class InstitutionalVerdictSnapshot:
    created_at: str
    status: str
    headline: str
    recommendation: str
    confidence: str
    structural_health: float
    drift: float
    coverage_11: float
    source: str


@dataclass(frozen=True)
class InstitutionalAnalyticalTimelineEntry:
    created_at: str
    status: str
    previous_status: str
    status_transition: str
    headline: str
    recommendation: str
    trend: str
    latest_status: str
    verdict_count: int
    confidence: str
    source: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_institutional_analytics_snapshot(
    report_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICS_SNAPSHOT,
) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def load_institutional_analytical_timeline(
    report_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICAL_TIMELINE,
) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _load_institutional_snapshots(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> list[dict[str, Any]]:
    if not report_dir.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(report_dir.glob("institutional_analytics_snapshot*.json"), key=lambda item: item.stat().st_mtime):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, Mapping):
            continue
        snapshots.append({"_path": str(path), **dict(payload)})
    return snapshots


def _load_executive_reports(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> list[dict[str, Any]]:
    if not report_dir.exists():
        return []
    reports: list[dict[str, Any]] = []
    for path in sorted(report_dir.glob("*executive*report*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        report = payload.get("report", payload)
        if not isinstance(report, Mapping):
            continue
        reports.append(
            {
                "created_at": str(payload.get("generated_at", payload.get("created_at", ""))),
                "status": str(report.get("status", "")),
                "headline": str(report.get("headline", "")),
                "recommendation": str(report.get("recommendation", "")),
                "confidence": str(report.get("confidence", "")),
                "structural_health": _safe_float(report.get("structural_health", 0.0)),
                "drift": _safe_float(report.get("drift", 0.0)),
                "coverage_11": _safe_float(report.get("coverage_11", 0.0)),
                "source": str(payload.get("source", report.get("source", ""))),
                "_path": str(path),
            }
        )
    return reports


def build_institutional_historical_intelligence(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    snapshots = _load_executive_reports(report_dir)
    expansion_events = list_expansion_events(limit=50)
    if not snapshots:
        return {
            "source": str(report_dir),
            "timeline": [],
            "summary": {
                "trend": "insuficiente",
                "stability_trend": 0.0,
                "drift_trend": 0.0,
                "confidence_trend": 0.0,
                "expanded_event_count": len(expansion_events),
            },
        }

    timeline = []
    previous = None
    stability_trend = 0.0
    drift_trend = 0.0
    confidence_trend = 0.0

    confidence_weight = {"alta": 1.0, "moderada": 0.5, "baixa": 0.0}
    for snapshot in sorted(snapshots, key=lambda item: item.get("_path", "")):
        if previous is not None:
            stability_trend += snapshot["structural_health"] - previous["structural_health"]
            drift_trend += snapshot["drift"] - previous["drift"]
            confidence_trend += confidence_weight.get(snapshot["confidence"], 0.0) - confidence_weight.get(previous["confidence"], 0.0)
        timeline.append(
            InstitutionalVerdictSnapshot(
                created_at=snapshot["created_at"],
                status=snapshot["status"],
                headline=snapshot["headline"],
                recommendation=snapshot["recommendation"],
                confidence=snapshot["confidence"],
                structural_health=round(snapshot["structural_health"], 4),
                drift=round(snapshot["drift"], 4),
                coverage_11=round(snapshot["coverage_11"], 4),
                source=snapshot["source"],
            ).__dict__
        )
        previous = snapshot

    first = timeline[0]
    last = timeline[-1]
    trend = "estavel"
    if last["structural_health"] > first["structural_health"] and last["drift"] <= first["drift"]:
        trend = "melhoria controlada"
    elif last["structural_health"] < first["structural_health"] and last["drift"] > first["drift"]:
        trend = "degradacao"

    return {
        "source": str(report_dir),
        "timeline": timeline,
        "summary": {
            "trend": trend,
            "stability_trend": round(stability_trend, 4),
            "drift_trend": round(drift_trend, 4),
            "confidence_trend": round(confidence_trend, 4),
            "verdict_count": len(timeline),
            "latest_status": last["status"],
            "latest_headline": last["headline"],
            "latest_recommendation": last["recommendation"],
            "expanded_event_count": len(expansion_events),
        },
        "expanded_events": [
            {
                "id": event.get("id"),
                "created_at": event.get("created_at", ""),
                "origin": event.get("origin", "expanded"),
                "selected_numbers": event.get("selected_numbers", []),
                "total_combinations": event.get("total_combinations", 0),
                "generated_count": event.get("generated_count", 0),
                "estimated_cost": event.get("estimated_cost", 0.0),
                "runtime_ms": event.get("runtime_ms", 0.0),
                "complete": bool(event.get("complete", False)),
                "stopped_reason": event.get("stopped_reason", ""),
            }
            for event in expansion_events
        ],
    }


def persist_institutional_historical_intelligence(
    report_path: Path = DEFAULT_INSTITUTIONAL_HISTORICAL_REPORT,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    report = build_institutional_historical_intelligence(report_dir)
    payload = {
        "source": str(report_dir),
        "schema_version": INSTITUTIONAL_ANALYTICS_SCHEMA_VERSION,
        "generated_by": "build_institutional_historical_intelligence",
        "report": report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def persist_institutional_analytics_snapshot(
    report_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICS_SNAPSHOT,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence(report_dir)
    payload = {
        "source": str(report_dir),
        "schema_version": INSTITUTIONAL_ANALYTICS_SCHEMA_VERSION,
        "generated_by": "persist_institutional_analytics_snapshot",
        "executive_report": executive_report,
        "historical_report": historical_report,
        "summary": {
            "headline": executive_report.get("headline", ""),
            "status": executive_report.get("status", ""),
            "trend": historical_report.get("summary", {}).get("trend", ""),
            "latest_status": historical_report.get("summary", {}).get("latest_status", ""),
            "verdict_count": historical_report.get("summary", {}).get("verdict_count", 0),
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def publish_institutional_analytics(
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
    executive_report_path: Path = Path("reports") / "analytics" / "executive_analytical_report.json",
    historical_report_path: Path = DEFAULT_INSTITUTIONAL_HISTORICAL_REPORT,
    snapshot_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICS_SNAPSHOT,
    timeline_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICAL_TIMELINE,
) -> dict[str, Any]:
    executive_payload = build_executive_analytical_report()
    executive_report_path.parent.mkdir(parents=True, exist_ok=True)
    executive_report_path.write_text(
        json.dumps(
            {
                "source": str(Path("reports") / "longitudinal" / "baseline_hard_longitudinal.json"),
                "generated_at": executive_payload.get("generated_at", ""),
                "schema_version": INSTITUTIONAL_ANALYTICS_SCHEMA_VERSION,
                "generated_by": "publish_institutional_analytics",
                "report": executive_payload,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    historical_payload = persist_institutional_historical_intelligence(historical_report_path, report_dir=report_dir)
    snapshot_payload = persist_institutional_analytics_snapshot(snapshot_path, report_dir=report_dir)
    timeline_payload = persist_institutional_analytical_timeline(timeline_path, report_dir=report_dir)
    return {
        "executive_report": executive_payload,
        "historical_report": historical_payload,
        "snapshot": snapshot_payload,
        "timeline": timeline_payload,
    }


def build_institutional_analytical_timeline(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    snapshots = _load_institutional_snapshots(report_dir)
    if not snapshots:
        snapshot = load_institutional_analytics_snapshot()
        if snapshot:
            snapshots = [{"_path": str(DEFAULT_INSTITUTIONAL_ANALYTICS_SNAPSHOT), **snapshot}]

    timeline: list[dict[str, Any]] = []
    previous_snapshot: dict[str, Any] | None = None
    for snapshot in snapshots:
        executive_report = snapshot.get("executive_report", {})
        historical_report = snapshot.get("historical_report", {})
        summary = snapshot.get("summary", {})
        historical_summary = historical_report.get("summary", {}) if isinstance(historical_report, Mapping) else {}
        previous_status = ""
        status_transition = "inicio"
        if previous_snapshot is not None:
            previous_exec = previous_snapshot.get("executive_report", {})
            previous_summary = previous_snapshot.get("summary", {})
            previous_status = str(previous_summary.get("status", previous_exec.get("status", "")))
            current_status = str(summary.get("status", executive_report.get("status", "")))
            if previous_status and current_status and previous_status != current_status:
                status_transition = f"{previous_status} -> {current_status}"
            elif current_status:
                status_transition = f"mantido em {current_status}"
        timeline.append(
            InstitutionalAnalyticalTimelineEntry(
                created_at=str(executive_report.get("generated_at", "")),
                status=str(summary.get("status", executive_report.get("status", ""))),
                previous_status=previous_status,
                status_transition=status_transition,
                headline=str(summary.get("headline", executive_report.get("headline", ""))),
                recommendation=str(executive_report.get("recommendation", "")),
                trend=str(historical_summary.get("trend", "")),
                latest_status=str(historical_summary.get("latest_status", "")),
                verdict_count=int(historical_summary.get("verdict_count", 0)),
                confidence=str(executive_report.get("confidence", "")),
                source=str(snapshot.get("source", "")),
            ).__dict__
        )
        previous_snapshot = snapshot

    if not timeline:
        return {
            "source": str(report_dir),
            "timeline": [],
            "summary": {
                "trend": "insuficiente",
                "verdict_count": 0,
                "latest_status": "",
                "latest_headline": "",
                "latest_recommendation": "",
            },
        }

    last = timeline[-1]
    trend = "estavel"
    if len(timeline) >= 2:
        if timeline[-1]["verdict_count"] > timeline[0]["verdict_count"]:
            trend = "acumulacao institucional"
        if timeline[-1]["trend"] == "melhoria controlada":
            trend = "melhoria institucional"
        elif timeline[-1]["trend"] == "degradacao":
            trend = "alerta institucional"

    return {
        "source": str(report_dir),
        "timeline": timeline,
        "summary": {
            "trend": trend,
            "verdict_count": last["verdict_count"],
            "latest_status": last["latest_status"],
            "latest_headline": last["headline"],
            "latest_recommendation": last["recommendation"],
            "latest_transition": last["status_transition"],
        },
    }


def persist_institutional_analytical_timeline(
    report_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICAL_TIMELINE,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    timeline = build_institutional_analytical_timeline(report_dir)
    payload = {
        "source": str(report_dir),
        "schema_version": INSTITUTIONAL_ANALYTICS_SCHEMA_VERSION,
        "generated_by": "build_institutional_analytical_timeline",
        "report": timeline,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def ensure_institutional_analytical_timeline(
    report_path: Path = DEFAULT_INSTITUTIONAL_ANALYTICAL_TIMELINE,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    payload = load_institutional_analytical_timeline(report_path)
    if payload:
        return payload
    return persist_institutional_analytical_timeline(report_path, report_dir=report_dir)
