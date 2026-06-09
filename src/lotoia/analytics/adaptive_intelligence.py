from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from lotoia.analytics.historical_intelligence import (
    build_institutional_analytical_timeline,
    build_institutional_historical_intelligence,
    load_institutional_analytics_snapshot,
)
from lotoia.analytics.intelligence_layer import build_executive_analytical_report

DEFAULT_ANALYTICS_DIR = Path("reports") / "analytics"
DEFAULT_ADAPTIVE_MEMORY_REPORT = DEFAULT_ANALYTICS_DIR / "adaptive_institutional_memory.json"
DEFAULT_ADAPTIVE_TIMELINE_REPORT = DEFAULT_ANALYTICS_DIR / "adaptive_institutional_timeline.json"
DEFAULT_ADAPTIVE_INSIGHTS_REPORT = DEFAULT_ANALYTICS_DIR / "adaptive_institutional_insights.json"
ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION = "adaptive-institutional-v1.0.0"


@dataclass(frozen=True)
class AdaptiveOperationalSnapshot:
    created_at: str
    status: str
    headline: str
    recommendation: str
    confidence: str
    structural_health: float
    drift: float
    trend: str
    source: str


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_json(report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def load_adaptive_institutional_intelligence(
    report_path: Path = DEFAULT_ADAPTIVE_MEMORY_REPORT,
) -> dict[str, Any]:
    return _load_json(report_path)


def load_adaptive_institutional_timeline(
    report_path: Path = DEFAULT_ADAPTIVE_TIMELINE_REPORT,
) -> dict[str, Any]:
    return _load_json(report_path)


def load_adaptive_institutional_insights(
    report_path: Path = DEFAULT_ADAPTIVE_INSIGHTS_REPORT,
) -> dict[str, Any]:
    return _load_json(report_path)


def _collect_executive_reports(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> list[dict[str, Any]]:
    if not report_dir.exists():
        return []
    reports: list[dict[str, Any]] = []
    for path in sorted(report_dir.glob("*executive*report*.json"), key=lambda item: item.stat().st_mtime):
        payload = _load_json(path)
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
                "trend": str(report.get("trend", "")),
                "source": str(payload.get("source", report.get("source", ""))),
                "_path": str(path),
            }
        )
    return reports


def build_operational_memory(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    executive_reports = _collect_executive_reports(report_dir)
    if not executive_reports:
        return {
            "source": str(report_dir),
            "timeline": [],
            "summary": {
                "trend": "insuficiente",
                "persistent_changes": 0,
                "recurring_statuses": 0,
                "memory_depth": 0,
            },
        }

    timeline: list[dict[str, Any]] = []
    recurring_statuses = 0
    persistent_changes = 0
    previous = None
    for report in executive_reports:
        if previous is not None:
            if report["status"] == previous["status"]:
                recurring_statuses += 1
            if abs(report["structural_health"] - previous["structural_health"]) >= 0.01 or abs(report["drift"] - previous["drift"]) >= 0.01:
                persistent_changes += 1
        timeline.append(
            AdaptiveOperationalSnapshot(
                created_at=report["created_at"],
                status=report["status"],
                headline=report["headline"],
                recommendation=report["recommendation"],
                confidence=report["confidence"],
                structural_health=round(report["structural_health"], 4),
                drift=round(report["drift"], 4),
                trend=report["trend"],
                source=report["source"],
            ).__dict__
        )
        previous = report

    first = timeline[0]
    last = timeline[-1]
    trend = "estavel"
    if last["structural_health"] > first["structural_health"] and last["drift"] <= first["drift"]:
        trend = "evolucao positiva"
    elif last["structural_health"] < first["structural_health"] and last["drift"] > first["drift"]:
        trend = "pressao adaptativa"
    elif recurring_statuses > 0:
        trend = "recorrencia operacional"

    return {
        "source": str(report_dir),
        "timeline": timeline,
        "summary": {
            "trend": trend,
            "persistent_changes": persistent_changes,
            "recurring_statuses": recurring_statuses,
            "memory_depth": len(timeline),
            "latest_status": last["status"],
            "latest_headline": last["headline"],
            "latest_recommendation": last["recommendation"],
        },
    }


def build_temporal_adaptive_analysis(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    operational_memory = build_operational_memory(report_dir)
    historical_report = build_institutional_historical_intelligence(report_dir)
    historical_summary = historical_report.get("summary", {})
    timeline = operational_memory.get("timeline", [])

    if not timeline:
        return {
            "source": str(report_dir),
            "summary": {
                "trend": "insuficiente",
                "recurring_statuses": 0,
                "persistent_changes": 0,
                "memory_depth": 0,
            },
        }

    timeline_frame = pd.DataFrame(timeline)
    if timeline_frame.empty:
        average_health_delta = 0.0
        drift_delta = 0.0
    else:
        average_health_delta = _safe_float(timeline_frame["structural_health"].iloc[-1]) - _safe_float(timeline_frame["structural_health"].iloc[0])
        drift_delta = _safe_float(timeline_frame["drift"].iloc[-1]) - _safe_float(timeline_frame["drift"].iloc[0])

    trend = operational_memory.get("summary", {}).get("trend", "estavel")
    if average_health_delta > 0.01 and drift_delta <= 0.01:
        trend = "evolucao estrutural"
    elif average_health_delta < -0.01 and drift_delta > 0.01:
        trend = "pressao persistente"

    return {
        "source": str(report_dir),
        "summary": {
            "trend": trend,
            "recurring_statuses": operational_memory.get("summary", {}).get("recurring_statuses", 0),
            "persistent_changes": operational_memory.get("summary", {}).get("persistent_changes", 0),
            "memory_depth": operational_memory.get("summary", {}).get("memory_depth", 0),
            "average_health_delta": round(average_health_delta, 4),
            "drift_delta": round(drift_delta, 4),
            "historical_trend": historical_summary.get("trend", ""),
        },
    }


def build_institutional_pattern_detection(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    temporal = build_temporal_adaptive_analysis(report_dir)
    summary = temporal.get("summary", {})
    recurring_statuses = int(summary.get("recurring_statuses", 0))
    persistent_changes = int(summary.get("persistent_changes", 0))
    pattern = "observacao"
    if recurring_statuses >= persistent_changes and recurring_statuses > 0:
        pattern = "recorrencia institucional"
    elif persistent_changes > recurring_statuses:
        pattern = "mudanca estrutural persistente"

    return {
        "source": str(report_dir),
        "summary": {
            "pattern": pattern,
            "recurring_statuses": recurring_statuses,
            "persistent_changes": persistent_changes,
            "memory_depth": int(summary.get("memory_depth", 0)),
        },
    }


def build_executive_strategic_memory(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    snapshot = load_institutional_analytics_snapshot()
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence(report_dir)
    timeline = build_institutional_analytical_timeline(report_dir)
    important_events = []
    for item in timeline.get("timeline", [])[-5:]:
        important_events.append(
            {
                "created_at": item.get("created_at", ""),
                "headline": item.get("headline", ""),
                "status_transition": item.get("status_transition", ""),
                "recommendation": item.get("recommendation", ""),
                "trend": item.get("trend", ""),
            }
        )
    return {
        "source": str(report_dir),
        "timeline": important_events,
        "summary": {
            "latest_headline": executive_report.get("headline", ""),
            "latest_status": executive_report.get("status", ""),
            "trend": historical_report.get("summary", {}).get("trend", ""),
            "snapshot_status": snapshot.get("summary", {}).get("status", ""),
            "memory_depth": len(important_events),
        },
    }


def build_user_operational_intelligence(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    return {
        "source": str(report_dir),
        "summary": {
            "mode": "institucional",
            "context": "sem memoria individual persistida adicional",
            "rastreabilidade": "artefatos institucionais",
        },
    }


def build_adaptive_executive_insights(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    pattern = build_institutional_pattern_detection(report_dir)
    temporal = build_temporal_adaptive_analysis(report_dir)
    operational_memory = build_operational_memory(report_dir)
    return {
        "source": str(report_dir),
        "insights": [
            {
                "metric": "continuity",
                "interpretation": "memoria operacional persistente" if operational_memory.get("summary", {}).get("memory_depth", 0) else "memoria insuficiente",
            },
            {
                "metric": "pattern",
                "interpretation": pattern.get("summary", {}).get("pattern", "observacao"),
            },
            {
                "metric": "trend",
                "interpretation": temporal.get("summary", {}).get("trend", "observacao"),
            },
        ],
        "summary": {
            "pattern": pattern.get("summary", {}).get("pattern", "observacao"),
            "trend": temporal.get("summary", {}).get("trend", "observacao"),
            "memory_depth": operational_memory.get("summary", {}).get("memory_depth", 0),
        },
    }


def build_longitudinal_evolution_v2(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    temporal = build_temporal_adaptive_analysis(report_dir)
    operational_memory = build_operational_memory(report_dir)
    historical = build_institutional_historical_intelligence(report_dir)
    timeline = build_institutional_analytical_timeline(report_dir)
    return {
        "source": str(report_dir),
        "summary": {
            "trend": temporal.get("summary", {}).get("trend", "observacao"),
            "stability_evolution": historical.get("summary", {}).get("stability_trend", 0.0),
            "drift_evolution": historical.get("summary", {}).get("drift_trend", 0.0),
            "confidence_evolution": historical.get("summary", {}).get("confidence_trend", 0.0),
            "memory_depth": operational_memory.get("summary", {}).get("memory_depth", 0),
            "timeline_depth": len(timeline.get("timeline", [])),
        },
    }


def build_observational_learning_layer(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    pattern = build_institutional_pattern_detection(report_dir)
    temporal = build_temporal_adaptive_analysis(report_dir)
    return {
        "source": str(report_dir),
        "summary": {
            "learning_mode": "observational_governed",
            "pattern": pattern.get("summary", {}).get("pattern", "observacao"),
            "trend": temporal.get("summary", {}).get("trend", "observacao"),
            "memory_depth": temporal.get("summary", {}).get("memory_depth", 0),
        },
    }


def build_strategic_analytical_timeline(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    executive_memory = build_executive_strategic_memory(report_dir)
    pattern = build_institutional_pattern_detection(report_dir)
    timeline = build_institutional_analytical_timeline(report_dir)
    adaptive_rows = []
    for row in timeline.get("timeline", []):
        adaptive_rows.append(
            {
                "created_at": row.get("created_at", ""),
                "status": row.get("status", ""),
                "headline": row.get("headline", ""),
                "recommendation": row.get("recommendation", ""),
                "status_transition": row.get("status_transition", ""),
                "trend": row.get("trend", ""),
                "source": row.get("source", ""),
            }
        )
    return {
        "source": str(report_dir),
        "timeline": adaptive_rows,
        "summary": {
            "trend": timeline.get("summary", {}).get("trend", ""),
            "latest_headline": timeline.get("summary", {}).get("latest_headline", executive_memory.get("summary", {}).get("latest_headline", "")),
            "latest_transition": timeline.get("summary", {}).get("latest_transition", ""),
            "pattern": pattern.get("summary", {}).get("pattern", "observacao"),
            "memory_depth": executive_memory.get("summary", {}).get("memory_depth", 0),
        },
    }


def build_adaptive_institutional_presence(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    memory = build_operational_memory(report_dir)
    insights = build_adaptive_executive_insights(report_dir)
    timeline = build_strategic_analytical_timeline(report_dir)
    consistency = min(
        1.0,
        round(
            0.5 * float(memory.get("summary", {}).get("memory_depth", 0) > 0)
            + 0.3 * min(1.0, float(memory.get("summary", {}).get("persistent_changes", 0)))
            + 0.2 * min(1.0, float(timeline.get("summary", {}).get("memory_depth", 0))),
            3,
        ),
    )
    return {
        "source": str(report_dir),
        "summary": {
            "presence": "adaptativa" if consistency >= 0.80 else "observacional",
            "consistency": consistency,
            "memory_depth": memory.get("summary", {}).get("memory_depth", 0),
            "pattern": insights.get("summary", {}).get("pattern", "observacao"),
            "trend": insights.get("summary", {}).get("trend", "observacao"),
        },
    }


def build_adaptive_institutional_intelligence(report_dir: Path = DEFAULT_ANALYTICS_DIR) -> dict[str, Any]:
    operational_memory = build_operational_memory(report_dir)
    temporal_analysis = build_temporal_adaptive_analysis(report_dir)
    pattern_detection = build_institutional_pattern_detection(report_dir)
    strategic_memory = build_executive_strategic_memory(report_dir)
    user_intelligence = build_user_operational_intelligence(report_dir)
    adaptive_insights = build_adaptive_executive_insights(report_dir)
    longitudinal_v2 = build_longitudinal_evolution_v2(report_dir)
    observational_learning = build_observational_learning_layer(report_dir)
    strategic_timeline = build_strategic_analytical_timeline(report_dir)
    adaptive_presence = build_adaptive_institutional_presence(report_dir)

    return {
        "source": str(report_dir),
        "schema_version": ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION,
        "operational_memory": operational_memory,
        "temporal_analysis": temporal_analysis,
        "pattern_detection": pattern_detection,
        "strategic_memory": strategic_memory,
        "user_operational_intelligence": user_intelligence,
        "adaptive_insights": adaptive_insights,
        "longitudinal_evolution_v2": longitudinal_v2,
        "observational_learning": observational_learning,
        "strategic_timeline": strategic_timeline,
        "adaptive_presence": adaptive_presence,
    }


def persist_adaptive_institutional_intelligence(
    report_path: Path = DEFAULT_ADAPTIVE_MEMORY_REPORT,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    payload = build_adaptive_institutional_intelligence(report_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def persist_adaptive_institutional_timeline(
    report_path: Path = DEFAULT_ADAPTIVE_TIMELINE_REPORT,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    payload = build_strategic_analytical_timeline(report_dir)
    wrapper = {
        "source": str(report_dir),
        "schema_version": ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION,
        "generated_by": "build_strategic_analytical_timeline",
        "report": payload,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")
    return wrapper


def persist_adaptive_institutional_insights(
    report_path: Path = DEFAULT_ADAPTIVE_INSIGHTS_REPORT,
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
) -> dict[str, Any]:
    payload = build_adaptive_executive_insights(report_dir)
    wrapper = {
        "source": str(report_dir),
        "schema_version": ADAPTIVE_INSTITUTIONAL_SCHEMA_VERSION,
        "generated_by": "build_adaptive_executive_insights",
        "report": payload,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")
    return wrapper


def publish_adaptive_institutional_intelligence(
    *,
    report_dir: Path = DEFAULT_ANALYTICS_DIR,
    memory_path: Path = DEFAULT_ADAPTIVE_MEMORY_REPORT,
    timeline_path: Path = DEFAULT_ADAPTIVE_TIMELINE_REPORT,
    insights_path: Path = DEFAULT_ADAPTIVE_INSIGHTS_REPORT,
) -> dict[str, Any]:
    memory = persist_adaptive_institutional_intelligence(memory_path, report_dir=report_dir)
    timeline = persist_adaptive_institutional_timeline(timeline_path, report_dir=report_dir)
    insights = persist_adaptive_institutional_insights(insights_path, report_dir=report_dir)
    return {
        "adaptive_memory": memory,
        "adaptive_timeline": timeline,
        "adaptive_insights": insights,
    }
