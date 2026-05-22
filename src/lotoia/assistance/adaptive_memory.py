from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH
from lotoia.memory import InstitutionalMemoryRegistry

from .contextual_recommendation import build_contextual_recommendations
from .explainable_analytics import build_explainable_analytics
from .operational_guidance import build_operational_guidance


@dataclass(frozen=True, slots=True)
class AdaptiveAssistanceMemorySnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    memory: dict[str, Any]
    memory_items: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "memory": self.memory,
            "memory_items": self.memory_items,
            "metadata": self.metadata,
        }


def build_adaptive_assistance_memory(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    registry = InstitutionalMemoryRegistry(effective_db_path)
    contextual = build_contextual_recommendations(effective_db_path, limit=limit)
    explainable = build_explainable_analytics(effective_db_path, limit=limit)
    guidance = build_operational_guidance(effective_db_path, limit=limit)

    latest_execution_id = "-"
    latest_snapshot = registry.list_snapshots(limit=1)
    if latest_snapshot:
        latest_execution_id = latest_snapshot[0].execution_id
    execution_memory = registry.get_execution_memory(latest_execution_id) if latest_execution_id not in {"", "-"} else {"snapshot_count": 0, "state_count": 0, "lineage_count": 0, "replay_count": 0, "latest_snapshot": None, "latest_state": None, "snapshots": [], "states": [], "lineage": [], "replays": []}
    replay = registry.get_execution_replay(latest_execution_id) if latest_execution_id not in {"", "-"} else None

    state = "memoria_adaptativa" if execution_memory.get("snapshot_count", 0) > 0 else "memoria_observacao"
    memory_items = [
        {
            "topic": "Contexto",
            "value": contextual.get("state", "-"),
            "interpretation": contextual.get("summary", {}).get("historical_trend", "-"),
        },
        {
            "topic": "Explicabilidade",
            "value": explainable.get("state", "-"),
            "interpretation": explainable.get("summary", {}).get("historical_trend", "-"),
        },
        {
            "topic": "Orientacao",
            "value": guidance.get("state", "-"),
            "interpretation": guidance.get("summary", {}).get("drift", 0.0),
        },
        {
            "topic": "Replay",
            "value": "sim" if replay else "nao",
            "interpretation": latest_execution_id,
        },
    ]

    snapshot = AdaptiveAssistanceMemorySnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "execution_id": latest_execution_id,
            "snapshot_count": execution_memory.get("snapshot_count", 0),
            "state_count": execution_memory.get("state_count", 0),
            "lineage_count": execution_memory.get("lineage_count", 0),
            "replay_count": execution_memory.get("replay_count", 0),
        },
        memory={
            "execution_memory": execution_memory,
            "replay_available": bool(replay),
            "latest_snapshot": execution_memory.get("latest_snapshot"),
            "latest_state": execution_memory.get("latest_state"),
        },
        memory_items=memory_items,
        metadata={
            "layer": "adaptive_assistance_memory_engine",
            "contextual_state": contextual.get("state", "-"),
            "explainable_state": explainable.get("state", "-"),
            "guidance_state": guidance.get("state", "-"),
        },
    )
    return snapshot.to_dict()
