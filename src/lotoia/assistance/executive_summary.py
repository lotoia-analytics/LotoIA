from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.observability import build_live_institutional_presence

from .contextual_recommendation import build_contextual_recommendations
from .explainable_analytics import build_explainable_analytics
from .operational_guidance import build_operational_guidance


@dataclass(frozen=True, slots=True)
class ExecutiveSummarySnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    bullets: list[str]
    highlights: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "bullets": self.bullets,
            "highlights": self.highlights,
            "metadata": self.metadata,
        }


def build_executive_summary(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    presence = build_live_institutional_presence(effective_db_path, limit=limit)
    contextual = build_contextual_recommendations(effective_db_path, limit=limit)
    explainable = build_explainable_analytics(effective_db_path, limit=limit)
    guidance = build_operational_guidance(effective_db_path, limit=limit)

    presence_summary = presence.get("summary", {})
    contextual_summary = contextual.get("summary", {})
    explainable_summary = explainable.get("summary", {})
    guidance_summary = guidance.get("summary", {})

    state = "resumo_ativo" if presence_summary.get("presence") == "fully_live" and guidance_summary.get("state") == "guided" else "resumo_em_observacao"
    bullets = [
        f"Presenca: {presence_summary.get('presence', '-')}",
        f"Saude: {presence_summary.get('health_status', '-')}",
        f"Historico: {contextual_summary.get('historical_trend', '-')}",
        f"Drift: {explainable_summary.get('drift', 0.0)}",
    ]
    highlights = [
        {
            "topic": "Presenca institucional",
            "value": presence_summary.get("presence", "-"),
            "interpretation": "ambiente vivo e auditavel" if presence_summary.get("presence") == "fully_live" else "ambiente sob monitoramento",
        },
        {
            "topic": "Tendencia historica",
            "value": contextual_summary.get("historical_trend", "-"),
            "interpretation": contextual.get("state", "-"),
        },
        {
            "topic": "Saude operacional",
            "value": guidance_summary.get("health_status", "-"),
            "interpretation": guidance.get("state", "-"),
        },
        {
            "topic": "Leitura explicavel",
            "value": explainable_summary.get("structural_health", 0.0),
            "interpretation": explainable.get("state", "-"),
        },
    ]

    snapshot = ExecutiveSummarySnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": presence_summary.get("presence", "-"),
            "health_status": presence_summary.get("health_status", "-"),
            "telemetry_status": presence_summary.get("telemetry_status", "-"),
            "historical_trend": contextual_summary.get("historical_trend", "-"),
            "drift": explainable_summary.get("drift", 0.0),
            "guidance_state": guidance_summary.get("state", "-"),
        },
        bullets=bullets,
        highlights=highlights,
        metadata={
            "layer": "executive_summary_engine",
            "contextual_state": contextual.get("state", "-"),
            "explainable_state": explainable.get("state", "-"),
        },
    )
    return snapshot.to_dict()
