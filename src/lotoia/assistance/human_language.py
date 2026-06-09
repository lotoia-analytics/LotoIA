from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from lotoia.database.database import DEFAULT_DATABASE_PATH

from .adaptive_memory import build_adaptive_assistance_memory
from .explainable_analytics import build_explainable_analytics
from .operational_guidance import build_operational_guidance


@dataclass(frozen=True, slots=True)
class HumanAnalyticalLanguageSnapshot:
    created_at: datetime
    source: str
    state: str
    summary: dict[str, Any]
    phrases: list[str]
    highlights: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "state": self.state,
            "summary": self.summary,
            "phrases": self.phrases,
            "highlights": self.highlights,
            "metadata": self.metadata,
        }


def _humanize_state(value: str) -> str:
    mapping = {
        "fully_live": "presença viva",
        "live_monitoring": "monitoramento vivo",
        "guided": "assistido",
        "watch": "em observação",
        "explicado": "explicado",
        "observacao": "em observação",
        "memoria_adaptativa": "memória adaptativa ativa",
        "memoria_observacao": "memória sob observação",
        "resumo_ativo": "resumo ativo",
        "resumo_em_observacao": "resumo em observação",
        "stable": "estável",
        "attention": "atenção",
    }
    return mapping.get(value, value.replace("_", " "))


def build_human_analytical_language(
    db_path: Path | None = None,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    effective_db_path = db_path or DEFAULT_DATABASE_PATH
    guidance = build_operational_guidance(effective_db_path, limit=limit)
    explainable = build_explainable_analytics(effective_db_path, limit=limit)
    memory = build_adaptive_assistance_memory(effective_db_path, limit=limit)

    guidance_summary = guidance.get("summary", {})
    explainable_summary = explainable.get("summary", {})
    memory_summary = memory.get("summary", {})
    state = "linguagem_humana" if guidance_summary.get("state") == "guided" else "linguagem_guiada"

    phrases = [
        f"Agora o sistema está {_humanize_state(str(guidance_summary.get('state', '-')))}.",
        f"A saúde operacional segue {_humanize_state(str(guidance_summary.get('health_status', '-')))}.",
        f"O drift está em {explainable_summary.get('drift', 0.0)} e a leitura está {_humanize_state(str(explainable.get('state', '-')))}.",
        f"A memória institucional está {_humanize_state(str(memory_summary.get('state', '-')))}.",
    ]
    highlights = [
        {
            "topic": "Estado atual",
            "value": _humanize_state(str(guidance_summary.get("state", "-"))),
            "interpretation": "leitura humana da orientação operacional",
        },
        {
            "topic": "Saúde",
            "value": _humanize_state(str(guidance_summary.get("health_status", "-"))),
            "interpretation": "sinal operacional convertido para linguagem executiva",
        },
        {
            "topic": "Drift",
            "value": explainable_summary.get("drift", 0.0),
            "interpretation": "variação apresentada em leitura simples",
        },
        {
            "topic": "Memória",
            "value": _humanize_state(str(memory_summary.get("state", "-"))),
            "interpretation": "continuidade temporal traduzida para o usuário",
        },
    ]

    snapshot = HumanAnalyticalLanguageSnapshot(
        created_at=datetime.now(UTC),
        source=str(effective_db_path),
        state=state,
        summary={
            "state": state,
            "guidance_state": _humanize_state(str(guidance_summary.get("state", "-"))),
            "health_status": _humanize_state(str(guidance_summary.get("health_status", "-"))),
            "drift": explainable_summary.get("drift", 0.0),
            "memory_state": _humanize_state(str(memory_summary.get("state", "-"))),
        },
        phrases=phrases,
        highlights=highlights,
        metadata={
            "layer": "human_analytical_language_engine",
            "guidance_state": guidance_summary.get("state", "-"),
            "explainable_state": explainable.get("state", "-"),
            "memory_state": memory_summary.get("state", "-"),
        },
    )
    return snapshot.to_dict()
