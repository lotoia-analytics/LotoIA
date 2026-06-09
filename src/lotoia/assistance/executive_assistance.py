from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from lotoia.observability import build_live_institutional_presence
from lotoia.analytics import build_executive_analytical_report, build_institutional_historical_intelligence


@dataclass(frozen=True, slots=True)
class ExecutiveAssistanceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    recommendations: list[dict[str, Any]]
    explanation: list[str]
    guidance: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
            "guidance": self.guidance,
            "metadata": self.metadata,
        }


def build_executive_assistance(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    presence = build_live_institutional_presence(effective_db_path, limit=limit)
    executive_report = build_executive_analytical_report()
    historical_report = build_institutional_historical_intelligence()

    presence_summary = presence.get("summary", {})
    executive_status = str(executive_report.get("status", "observacao"))
    historical_summary = historical_report.get("summary", {})
    state = "assistido" if presence_summary.get("presence") == "fully_live" and executive_status == "saudavel" else "orientado"

    recommendations = [
        {
            "topic": "Estado atual",
            "recommendation": "Manter observação executiva e acompanhar a telemetria viva.",
            "priority": "alta" if state != "assistido" else "media",
        },
        {
            "topic": "Historico",
            "recommendation": f"Tendencia historica {historical_summary.get('trend', 'indefinida')}.",
            "priority": "media",
        },
        {
            "topic": "Governanca",
            "recommendation": "Preservar rastreabilidade e evitar ajustes automáticos.",
            "priority": "alta",
        },
    ]
    explanation = [
        f"Presenca institucional: {presence_summary.get('presence', '-')}",
        f"Saude operacional: {presence_summary.get('health_status', '-')}",
        f"Headline executiva: {executive_report.get('headline', '-')}",
        f"Trend historico: {historical_summary.get('trend', '-')}",
    ]
    guidance = [
        "Acompanhar alertas executivos antes de qualquer ação.",
        "Priorizar estabilidade sobre expansão de comportamento.",
        "Usar a leitura humana antes de qualquer interpretação técnica detalhada.",
    ]
    snapshot = ExecutiveAssistanceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": presence_summary.get("presence", "-"),
            "health_status": presence_summary.get("health_status", "-"),
            "telemetry_status": presence_summary.get("telemetry_status", "-"),
            "executive_status": executive_status,
            "historical_trend": historical_summary.get("trend", "-"),
        },
        recommendations=recommendations,
        explanation=explanation,
        guidance=guidance,
        metadata={
            "layer": "executive_assistance_engine",
            "presence_state": presence_summary.get("presence", "-"),
            "executive_status": executive_status,
        },
    )
    return snapshot.to_dict()
