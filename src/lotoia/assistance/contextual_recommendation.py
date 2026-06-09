from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from lotoia.analytics import build_institutional_historical_intelligence
from lotoia.observability import build_live_institutional_presence


@dataclass(frozen=True, slots=True)
class ContextualRecommendationSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    recommendations: list[dict[str, Any]]
    explanation: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


def build_contextual_recommendations(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    presence = build_live_institutional_presence(effective_db_path, limit=limit)
    historical = build_institutional_historical_intelligence()

    presence_summary = presence.get("summary", {})
    historical_summary = historical.get("summary", {})
    trend = str(historical_summary.get("trend", "indefinida"))
    state = "stable" if presence_summary.get("memory_status") == "live" and trend in {"estavel", "melhoria controlada"} else "attention"

    recommendations = [
        {
            "topic": "Leitura operacional",
            "recommendation": "Observe a presença viva antes de qualquer interpretação técnica.",
            "priority": "alta",
        },
        {
            "topic": "Histórico",
            "recommendation": f"Tendência histórica atual: {trend}.",
            "priority": "media",
        },
        {
            "topic": "Estabilidade",
            "recommendation": "Priorize estabilidade e rastreabilidade; evite ajustes automáticos.",
            "priority": "alta",
        },
        {
            "topic": "Atenção operacional",
            "recommendation": "Se os alertas executivos estiverem ativos, mantenha a leitura guiada.",
            "priority": "media",
        },
    ]
    explanation = [
        f"Presenca institucional: {presence_summary.get('presence', '-')}",
        f"Saude operacional: {presence_summary.get('health_status', '-')}",
        f"Telemetria: {presence_summary.get('telemetry_status', '-')}",
        f"Trend historico: {trend}",
    ]
    snapshot = ContextualRecommendationSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": presence_summary.get("presence", "-"),
            "memory_status": presence_summary.get("memory_status", "-"),
            "health_status": presence_summary.get("health_status", "-"),
            "telemetry_status": presence_summary.get("telemetry_status", "-"),
            "historical_trend": trend,
        },
        recommendations=recommendations,
        explanation=explanation,
        metadata={
            "layer": "contextual_recommendation_engine",
            "trend": trend,
            "presence_state": presence_summary.get("presence", "-"),
        },
    )
    return snapshot.to_dict()
