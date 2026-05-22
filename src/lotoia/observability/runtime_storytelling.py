from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .live_telemetry import build_live_telemetry_snapshot
from .operational_health import build_operational_health_snapshot


@dataclass(frozen=True, slots=True)
class RuntimeStorySnapshot:
    created_at: datetime
    source: str
    headline: str
    summary: dict[str, Any]
    narrative: list[str]
    timeline: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "headline": self.headline,
            "summary": self.summary,
            "narrative": self.narrative,
            "timeline": self.timeline,
            "alerts": self.alerts,
            "metadata": self.metadata,
        }


def build_runtime_storytelling(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    telemetry = build_live_telemetry_snapshot(db_path=db_path, limit=limit)
    health = build_operational_health_snapshot(db_path=db_path, limit=limit)

    active_signals = telemetry.get("live_signals", [])
    signal_count = sum(1 for item in active_signals if item.get("status") == "active")
    headline = (
        "plataforma viva e coordenada"
        if health.get("status") == "healthy"
        else "plataforma em observacao"
        if health.get("status") == "degraded"
        else "plataforma em atencao"
    )

    narrative = [
        f"Estado atual: {telemetry.get('summary', {}).get('telemetry_status', '-')}",
        f"Saude operacional: {health.get('status', '-')}",
        f"Sinais ativos: {signal_count}",
        f"Execucao recente: {telemetry.get('summary', {}).get('latest_execution_id', '-')}",
        f"Atividade do ciclo: {telemetry.get('summary', {}).get('activity_level', '-')}",
    ]
    timeline = [
        {
            "marker": "telemetry",
            "status": telemetry.get("summary", {}).get("telemetry_status", "-"),
            "execution_id": telemetry.get("summary", {}).get("latest_execution_id", "-"),
        },
        {
            "marker": "health",
            "status": health.get("status", "-"),
            "score": health.get("score", 0.0),
        },
        {
            "marker": "signals",
            "status": "active" if signal_count else "idle",
            "count": signal_count,
        },
    ]
    alerts = list(telemetry.get("alerts", []))
    if health.get("alerts"):
        alerts.extend(health.get("alerts", []))

    snapshot = RuntimeStorySnapshot(
        created_at=datetime.now(UTC),
        source=str(db_path) if db_path else "",
        headline=headline,
        summary={
            "telemetry_status": telemetry.get("summary", {}).get("telemetry_status", "-"),
            "runtime_awareness": telemetry.get("summary", {}).get("runtime_awareness", "-"),
            "health_status": health.get("status", "-"),
            "health_score": health.get("score", 0.0),
            "active_signals": signal_count,
        },
        narrative=narrative,
        timeline=timeline,
        alerts=alerts,
        metadata={
            "layer": "runtime_storytelling",
            "telemetry_status": telemetry.get("summary", {}).get("telemetry_status", "-"),
            "health_status": health.get("status", "-"),
        },
    )
    return snapshot.to_dict()
