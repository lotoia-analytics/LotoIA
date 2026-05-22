from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.analytics import build_executive_analytical_report, build_institutional_historical_intelligence
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.observability import build_live_institutional_presence


@dataclass(frozen=True, slots=True)
class ExplainableAnalyticsSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    explanation: list[dict[str, Any]]
    narrative: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "explanation": self.explanation,
            "narrative": self.narrative,
            "metadata": self.metadata,
        }


def build_explainable_analytics(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    presence = build_live_institutional_presence(effective_db_path, limit=limit)
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence()

    presence_summary = presence.get("summary", {})
    executive_summary = executive_report.get("analytical_summary", {})
    historical_summary = historical_report.get("summary", {})
    structural_health = float(executive_summary.get("structural_health", 0.0))
    drift = float(executive_summary.get("drift", 0.0))
    trend = str(historical_summary.get("trend", "indefinida"))

    state = "explicado" if structural_health >= 0.75 and presence_summary.get("presence") == "fully_live" else "observacao"
    explanation = [
        {
            "metric": "Saude estrutural",
            "value": round(structural_health, 4),
            "interpretation": executive_summary.get("interpretation", "-"),
            "confidence": executive_summary.get("confidence", "-"),
        },
        {
            "metric": "Drift",
            "value": round(drift, 4),
            "interpretation": "drift controlado" if drift <= 0.2 else "drift requer acompanhamento",
            "confidence": "alta" if drift <= 0.2 else "moderada",
        },
        {
            "metric": "Historico",
            "value": trend,
            "interpretation": "tendencia histórica consolidada" if trend in {"estavel", "melhoria controlada"} else "tendencia histórica sob observacao",
            "confidence": "alta" if trend in {"estavel", "melhoria controlada"} else "moderada",
        },
        {
            "metric": "Presenca institucional",
            "value": presence_summary.get("presence", "-"),
            "interpretation": "presenca viva e auditavel" if presence_summary.get("presence") == "fully_live" else "presenca em monitoramento",
            "confidence": "alta" if presence_summary.get("presence") == "fully_live" else "moderada",
        },
    ]
    narrative = [
        f"Saude estrutural {executive_summary.get('interpretation', '-')}",
        f"Drift {round(drift, 4)} com leitura {executive_summary.get('confidence', '-')}",
        f"Trend historico {trend}",
        f"Presenca {presence_summary.get('presence', '-')}",
    ]

    snapshot = ExplainableAnalyticsSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": presence_summary.get("presence", "-"),
            "health_status": presence_summary.get("health_status", "-"),
            "telemetry_status": presence_summary.get("telemetry_status", "-"),
            "structural_health": round(structural_health, 4),
            "drift": round(drift, 4),
            "historical_trend": trend,
        },
        explanation=explanation,
        narrative=narrative,
        metadata={
            "layer": "explainable_analytics_engine",
            "source_report": executive_report.get("source", "-"),
            "presence_state": presence_summary.get("presence", "-"),
        },
    )
    return snapshot.to_dict()
