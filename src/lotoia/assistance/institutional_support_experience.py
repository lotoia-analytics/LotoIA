from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .adaptive_memory import build_adaptive_assistance_memory
from .contextual_recommendation import build_contextual_recommendations
from .executive_summary import build_executive_summary
from .explainable_analytics import build_explainable_analytics
from .human_language import build_human_analytical_language
from .operational_guidance import build_operational_guidance


@dataclass(frozen=True, slots=True)
class InstitutionalSupportExperienceSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    experience: list[dict[str, Any]]
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


def build_institutional_support_experience(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    contextual = build_contextual_recommendations(effective_db_path, limit=limit)
    explainable = build_explainable_analytics(effective_db_path, limit=limit)
    guidance = build_operational_guidance(effective_db_path, limit=limit)
    summary = build_executive_summary(effective_db_path, limit=limit)
    memory = build_adaptive_assistance_memory(effective_db_path, limit=limit)
    language = build_human_analytical_language(effective_db_path, limit=limit)

    experience = [
        {
            "topic": "Contexto",
            "state": contextual.get("state", "-"),
            "interpretation": contextual.get("summary", {}).get("historical_trend", "-"),
        },
        {
            "topic": "Explicabilidade",
            "state": explainable.get("state", "-"),
            "interpretation": explainable.get("summary", {}).get("historical_trend", "-"),
        },
        {
            "topic": "Orientacao",
            "state": guidance.get("state", "-"),
            "interpretation": guidance.get("summary", {}).get("drift", 0.0),
        },
        {
            "topic": "Resumo",
            "state": summary.get("state", "-"),
            "interpretation": summary.get("summary", {}).get("guidance_state", "-"),
        },
        {
            "topic": "Memoria",
            "state": memory.get("state", "-"),
            "interpretation": memory.get("summary", {}).get("state", "-"),
        },
        {
            "topic": "Linguagem",
            "state": language.get("state", "-"),
            "interpretation": language.get("summary", {}).get("guidance_state", "-"),
        },
    ]
    state = "experiencia_assistida" if language.get("state") == "linguagem_humana" else "experiencia_em_observacao"
    narrative = [
        f"Contexto {contextual.get('state', '-')}",
        f"Explicacao {explainable.get('state', '-')}",
        f"Orientacao {guidance.get('state', '-')}",
        f"Memoria {memory.get('state', '-')}",
        f"Linguagem {language.get('state', '-')}",
    ]

    snapshot = InstitutionalSupportExperienceSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "presence": contextual.get("summary", {}).get("presence", "-"),
            "health_status": guidance.get("summary", {}).get("health_status", "-"),
            "memory_state": memory.get("summary", {}).get("state", "-"),
            "language_state": language.get("state", "-"),
        },
        experience=experience,
        narrative=narrative,
        metadata={
            "layer": "institutional_support_experience_engine",
            "contextual_state": contextual.get("state", "-"),
            "explainable_state": explainable.get("state", "-"),
            "guidance_state": guidance.get("state", "-"),
            "summary_state": summary.get("state", "-"),
        },
    )
    return snapshot.to_dict()
