from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.memory.memory_registry import InstitutionalMemoryRegistry

from .runtime_storytelling import build_runtime_storytelling


@dataclass(frozen=True, slots=True)
class LiveOperationalMemorySnapshot:
    created_at: datetime
    source: str
    execution_id: str
    headline: str
    summary: dict[str, Any]
    memory: dict[str, Any]
    story: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "execution_id": self.execution_id,
            "headline": self.headline,
            "summary": self.summary,
            "memory": self.memory,
            "story": self.story,
            "metadata": self.metadata,
        }


def build_live_operational_memory(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    registry = InstitutionalMemoryRegistry(effective_db_path)
    story = build_runtime_storytelling(effective_db_path, limit=limit)
    execution_id = str(story.get("summary", {}).get("latest_execution_id", "-"))
    if execution_id in {"", "-"}:
        registry_snapshots = registry.list_snapshots(limit=1)
        execution_id = registry_snapshots[0].execution_id if registry_snapshots else "-"
    memory = registry.get_execution_memory(execution_id) if execution_id not in {"", "-"} else {"execution_id": execution_id, "snapshot_count": 0, "state_count": 0, "lineage_count": 0, "replay_count": 0, "latest_snapshot": None, "latest_state": None, "state_map": {}, "snapshots": [], "states": [], "lineage": [], "replays": []}
    replay = registry.get_execution_replay(execution_id) if execution_id not in {"", "-"} else None
    headline = "memoria operacional viva" if memory.get("snapshot_count", 0) else "memoria operacional em monitoramento"
    snapshot = LiveOperationalMemorySnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        execution_id=execution_id,
        headline=headline,
        summary={
            "memory_status": "live" if memory.get("snapshot_count", 0) else "standby",
            "snapshot_count": memory.get("snapshot_count", 0),
            "state_count": memory.get("state_count", 0),
            "lineage_count": memory.get("lineage_count", 0),
            "replay_count": memory.get("replay_count", 0),
            "latest_execution_id": execution_id,
            "replay_ready": bool(replay),
        },
        memory=memory,
        story=story,
        metadata={
            "layer": "live_operational_memory",
            "replay_ready": bool(replay),
            "story_headline": story.get("headline", "-"),
        },
    )
    return snapshot.to_dict()
