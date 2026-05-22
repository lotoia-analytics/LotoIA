from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .governance import build_assistance_governance
from .institutional_support_experience import build_institutional_support_experience
from .human_language import build_human_analytical_language
from .executive_summary import build_executive_summary


@dataclass(frozen=True, slots=True)
class FullExecutiveAssistancePresenceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    presence: list[dict[str, Any]]
    narrative: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "presence": self.presence,
            "narrative": self.narrative,
            "metadata": self.metadata,
        }


def build_full_executive_assistance_presence(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    support = build_institutional_support_experience(effective_db_path, limit=limit)
    governance = build_assistance_governance(effective_db_path, limit=limit)
    human = build_human_analytical_language(effective_db_path, limit=limit)
    summary = build_executive_summary(effective_db_path, limit=limit)

    state = "presenca_executiva_final" if governance.get("state") == "governada" and human.get("state") == "linguagem_humana" else "presenca_em_observacao"
    presence = [
        {
            "topic": "Suporte institucional",
            "state": support.get("state", "-"),
            "interpretation": support.get("summary", {}).get("state", "-"),
        },
        {
            "topic": "Governanca",
            "state": governance.get("state", "-"),
            "interpretation": governance.get("summary", {}).get("state", "-"),
        },
        {
            "topic": "Linguagem",
            "state": human.get("state", "-"),
            "interpretation": human.get("summary", {}).get("guidance_state", "-"),
        },
        {
            "topic": "Resumo",
            "state": summary.get("state", "-"),
            "interpretation": summary.get("summary", {}).get("guidance_state", "-"),
        },
    ]
    narrative = [
        f"Suporte {support.get('state', '-')}",
        f"Governanca {governance.get('state', '-')}",
        f"Linguagem {human.get('state', '-')}",
        f"Resumo {summary.get('state', '-')}",
    ]

    snapshot = FullExecutiveAssistancePresenceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "support_state": support.get("state", "-"),
            "governance_state": governance.get("state", "-"),
            "language_state": human.get("state", "-"),
            "summary_state": summary.get("state", "-"),
        },
        presence=presence,
        narrative=narrative,
        metadata={
            "layer": "full_executive_assistance_presence",
            "support_layer": support.get("metadata", {}).get("layer", "-"),
        },
    )
    return snapshot.to_dict()
