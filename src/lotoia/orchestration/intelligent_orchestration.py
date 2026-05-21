from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from lotoia.analytics import (
    build_adaptive_institutional_intelligence,
    build_analytical_intelligence,
    build_executive_analytical_report,
    build_institutional_analytical_timeline,
    build_institutional_historical_intelligence,
)
from lotoia.observability import build_observational_stabilization_report

DEFAULT_ORCHESTRATION_DIR = Path("reports") / "orchestration"
DEFAULT_ORCHESTRATION_REPORT = DEFAULT_ORCHESTRATION_DIR / "intelligent_operational_orchestration.json"
INTELLIGENT_ORCHESTRATION_SCHEMA_VERSION = "intelligent-operational-orchestration-v1.0.0"


def _safe_dict(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, Mapping) else {}


def _safe_list(payload: Any) -> list[dict[str, Any]]:
    return list(payload) if isinstance(payload, list) else []


def build_intelligent_operational_orchestration(report_dir: Path = DEFAULT_ORCHESTRATION_DIR) -> dict[str, Any]:
    analytics_summary = build_analytical_intelligence()
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence()
    adaptive_report = build_adaptive_institutional_intelligence()
    observability_report = build_observational_stabilization_report()
    timeline_report = build_institutional_analytical_timeline()

    adaptive_summary = _safe_dict(adaptive_report.get("summary"))
    historical_summary = _safe_dict(historical_report.get("summary"))
    executive_summary = _safe_dict(executive_report.get("report", executive_report))
    observability_summary = _safe_dict(observability_report.get("summary"))
    timeline_summary = _safe_dict(timeline_report.get("summary"))

    critical_state = (
        str(executive_summary.get("status", "")) != "saudavel"
        or str(observability_summary.get("stability_note", "")).strip() == "homepage em observacao"
    )
    strong_stability = str(historical_summary.get("trend", "")) in {"estavel", "melhoria controlada"}
    elevated_drift = float(analytics_summary.get("analytical_summary", {}).get("drift", 0.0)) > 0.25
    important_change = int(historical_summary.get("verdict_count", 0)) >= 2 or int(adaptive_summary.get("memory_depth", 0)) >= 2

    priority = "critical" if critical_state else "attention" if elevated_drift else "stable" if strong_stability else "observation"
    recommendation = str(executive_summary.get("recommendation", "") or adaptive_summary.get("latest_recommendation", "") or "monitorar")

    events = [
        {
            "layer": "executive",
            "status": str(executive_summary.get("status", "")),
            "headline": str(executive_summary.get("headline", "")),
            "recommendation": recommendation,
            "confidence": str(executive_summary.get("confidence", "")),
        },
        {
            "layer": "historical",
            "trend": str(historical_summary.get("trend", "")),
            "verdict_count": int(historical_summary.get("verdict_count", 0)),
            "latest_status": str(historical_summary.get("latest_status", "")),
        },
        {
            "layer": "observability",
            "homepage_priority": str(observability_summary.get("homepage_priority", "")),
            "stability_note": str(observability_summary.get("stability_note", "")),
            "snapshot_ready": bool(observability_summary.get("institutional_snapshot_ready")),
            "timeline_ready": bool(observability_summary.get("institutional_timeline_ready")),
        },
        {
            "layer": "adaptive",
            "trend": str(adaptive_summary.get("trend", "")),
            "memory_depth": int(adaptive_summary.get("memory_depth", 0)),
            "persistent_changes": int(adaptive_summary.get("persistent_changes", 0)),
        },
    ]

    strategic_memory = _safe_list(adaptive_report.get("operational_memory", {}).get("timeline", []))[-5:]
    storytelling = [
        f"Contexto executivo: {executive_summary.get('headline', 'sem headline')}",
        f"Prioridade operacional: {priority}",
        f"Tendencia historica: {historical_summary.get('trend', 'indefinida')}",
        f"Memoria adaptativa: {adaptive_summary.get('memory_depth', 0)} checkpoints",
        f"Timeline institucional: {timeline_summary.get('latest_transition', 'sem transicao')}",
    ]

    report = {
        "source": str(report_dir),
        "schema_version": INTELLIGENT_ORCHESTRATION_SCHEMA_VERSION,
        "generated_by": "build_intelligent_operational_orchestration",
        "summary": {
            "orchestration_state": "coordenada" if not critical_state else "atencao",
            "priority": priority,
            "critical_state": critical_state,
            "strong_stability": strong_stability,
            "elevated_drift": elevated_drift,
            "important_change": important_change,
            "timeline_depth": int(timeline_summary.get("verdict_count", 0)),
            "memory_depth": int(adaptive_summary.get("memory_depth", 0)),
        },
        "context": {
            "executive": executive_summary,
            "historical": historical_summary,
            "adaptive": adaptive_summary,
            "observability": observability_summary,
            "timeline": timeline_summary,
        },
        "decision_context": {
            "status": str(executive_summary.get("status", "observacao")),
            "headline": str(executive_summary.get("headline", "")),
            "recommendation": recommendation,
            "comparison": "historical trend and adaptive memory aligned" if strong_stability else "historical alignment requires monitoring",
        },
        "operational_priority": {
            "priority": priority,
            "critical_state": critical_state,
            "strong_stability": strong_stability,
            "elevated_drift": elevated_drift,
            "important_change": important_change,
        },
        "events": events,
        "strategic_memory": strategic_memory,
        "storytelling": storytelling,
    }
    return report


def persist_intelligent_operational_orchestration(
    report_path: Path = DEFAULT_ORCHESTRATION_REPORT,
    *,
    report_dir: Path = DEFAULT_ORCHESTRATION_DIR,
) -> dict[str, Any]:
    report = build_intelligent_operational_orchestration(report_dir)
    payload = {
        "source": str(report_dir),
        "schema_version": INTELLIGENT_ORCHESTRATION_SCHEMA_VERSION,
        "generated_by": "persist_intelligent_operational_orchestration",
        "report": report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_intelligent_operational_orchestration(
    report_path: Path = DEFAULT_ORCHESTRATION_REPORT,
) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}
