from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .institutional_support_experience import build_institutional_support_experience


@dataclass(frozen=True, slots=True)
class AssistanceGovernanceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    rules: list[dict[str, Any]]
    narrative: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "rules": self.rules,
            "narrative": self.narrative,
            "metadata": self.metadata,
        }


def build_assistance_governance(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    support = build_institutional_support_experience(effective_db_path, limit=limit)
    support_summary = support.get("summary", {})

    state = "governada" if support_summary.get("state") == "experiencia_assistida" else "revisar"
    rules = [
        {
            "topic": "Rastreabilidade",
            "status": "ok",
            "detail": "A assistência usa presença, memória e observabilidade já governadas.",
        },
        {
            "topic": "Explicabilidade",
            "status": "ok",
            "detail": "As recomendações são humanas e auditáveis.",
        },
        {
            "topic": "Integridade contextual",
            "status": "ok",
            "detail": "Nenhuma decisão invisível é tomada pela camada assistiva.",
        },
        {
            "topic": "Consistência",
            "status": "ok" if support_summary.get("language_state") == "linguagem_humana" else "review",
            "detail": "A linguagem permanece alinhada com o cockpit executivo.",
        },
    ]
    narrative = [
        f"Estado {state}",
        f"Presenca {support_summary.get('presence', '-')}",
        f"Saude {support_summary.get('health_status', '-')}",
        f"Memoria {support_summary.get('memory_state', '-')}",
        f"Linguagem {support_summary.get('language_state', '-')}",
    ]

    snapshot = AssistanceGovernanceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": support_summary.get("presence", "-"),
            "health_status": support_summary.get("health_status", "-"),
            "memory_state": support_summary.get("memory_state", "-"),
            "language_state": support_summary.get("language_state", "-"),
        },
        rules=rules,
        narrative=narrative,
        metadata={
            "layer": "assistance_governance_layer",
            "support_state": support_summary.get("state", "-"),
        },
    )
    return snapshot.to_dict()
