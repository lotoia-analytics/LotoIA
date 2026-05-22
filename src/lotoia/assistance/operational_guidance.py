from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.analytics import build_executive_analytical_report
from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.observability import build_live_institutional_presence


@dataclass(frozen=True, slots=True)
class OperationalGuidanceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    guidance: list[dict[str, Any]]
    narrative: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "guidance": self.guidance,
            "narrative": self.narrative,
            "metadata": self.metadata,
        }


def build_operational_guidance(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    presence = build_live_institutional_presence(effective_db_path, limit=limit)
    executive_report = build_executive_analytical_report()

    presence_summary = presence.get("summary", {})
    executive_summary = executive_report.get("analytical_summary", {})
    structural_health = float(executive_summary.get("structural_health", 0.0))
    drift = float(executive_summary.get("drift", 0.0))
    telemetry_status = str(presence_summary.get("telemetry_status", "-"))
    health_status = str(presence_summary.get("health_status", "-"))

    state = "guided" if presence_summary.get("presence") == "fully_live" and structural_health >= 0.75 else "watch"
    guidance = [
        {
            "topic": "Estado atual",
            "recommendation": "Manter leitura executiva aberta e acompanhar sinais vivos antes de agir.",
            "priority": "alta",
        },
        {
            "topic": "Risco",
            "recommendation": "Se drift ou saúde piorarem, pausar qualquer ampliação de escopo.",
            "priority": "alta",
        },
        {
            "topic": "Evolução",
            "recommendation": "Comparar o momento atual com a linha temporal antes de qualquer ajuste.",
            "priority": "media",
        },
        {
            "topic": "Técnica",
            "recommendation": "Preservar rastreabilidade e confiar na leitura humana assistida.",
            "priority": "media",
        },
    ]
    narrative = [
        f"Saude {health_status}",
        f"Telemetria {telemetry_status}",
        f"Drift {round(drift, 4)}",
        f"Structural health {round(structural_health, 4)}",
    ]

    snapshot = OperationalGuidanceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": presence_summary.get("presence", "-"),
            "health_status": health_status,
            "telemetry_status": telemetry_status,
            "structural_health": round(structural_health, 4),
            "drift": round(drift, 4),
        },
        guidance=guidance,
        narrative=narrative,
        metadata={
            "layer": "operational_guidance_engine",
            "presence_state": presence_summary.get("presence", "-"),
            "executive_status": executive_summary.get("confidence", "-"),
        },
    )
    return snapshot.to_dict()
