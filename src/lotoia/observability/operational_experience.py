from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .live_operational_memory import build_live_operational_memory
from .real_time_governance import build_real_time_governance
from .runtime_storytelling import build_runtime_storytelling


@dataclass(frozen=True, slots=True)
class OperationalExperienceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    experience: dict[str, Any]
    narrative: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "experience": self.experience,
            "narrative": self.narrative,
            "metadata": self.metadata,
        }


def build_operational_experience(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    memory = build_live_operational_memory(effective_db_path, limit=limit)
    governance = build_real_time_governance(effective_db_path, limit=limit)
    story = build_runtime_storytelling(effective_db_path, limit=limit)

    state = "live" if governance.get("status") == "governed" and memory.get("summary", {}).get("memory_status") == "live" else "monitoring"
    narrative = [
        f"Experiencia: {state}",
        f"Headline: {story.get('headline', '-')}",
        f"Memoria: {memory.get('summary', {}).get('snapshot_count', 0)} snapshots",
        f"Governanca: {governance.get('status', '-')}",
    ]
    snapshot = OperationalExperienceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "health_status": governance.get("summary", {}).get("health_status", "-"),
            "health_score": governance.get("summary", {}).get("health_score", 0.0),
            "memory_status": memory.get("summary", {}).get("memory_status", "-"),
            "replay_ready": memory.get("summary", {}).get("replay_ready", False),
            "telemetry_status": story.get("summary", {}).get("telemetry_status", "-"),
            "runtime_awareness": story.get("summary", {}).get("runtime_awareness", "-"),
        },
        experience={
            "memory": memory,
            "governance": governance,
            "story": story,
        },
        narrative=narrative,
        metadata={
            "layer": "operational_experience_live",
            "governed": governance.get("status") == "governed",
            "memory_ready": memory.get("summary", {}).get("memory_status") == "live",
        },
    )
    return snapshot.to_dict()
