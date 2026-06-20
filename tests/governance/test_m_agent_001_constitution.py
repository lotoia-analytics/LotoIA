"""M-AGENT-001 — smoke da constituição do agent_operador_ml (read-only)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONSTITUTION_ARTIFACTS = (
    "ADRs/ADR_051_M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md",
    "docs/governance/M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md",
    "docs/governance/M_AGENT_001_ROADMAP_AUTONOMIA.md",
    "docs/governance/M_AGENT_001_MATRIZ_PERMISSOES.md",
    "docs/governance/M_AGENT_001_MATRIZ_RISCOS.md",
    "docs/governance/M_AGENT_001_MATRIZ_AUDITORIA.md",
)


def test_constitution_artifacts_exist() -> None:
    for relative in CONSTITUTION_ARTIFACTS:
        assert (ROOT / relative).is_file(), f"missing artifact: {relative}"


def test_official_agent_name_in_adr() -> None:
    adr = (ROOT / "ADRs/ADR_051_M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md").read_text(encoding="utf-8")
    assert "agent_operador_ml" in adr
    assert "**Status:** Accepted" in adr


def test_constitution_mission_statement() -> None:
    constitution = (ROOT / "docs/governance/M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md").read_text(
        encoding="utf-8"
    )
    assert "Produzir gerações de jogos com máxima qualidade estrutural e operacional" in constitution
    assert "agent_trace_id" in constitution
    assert "agent_operational_learning" in constitution
    assert "M-AGENT-002" in constitution


def test_no_runtime_implementation_claim() -> None:
    constitution = (ROOT / "docs/governance/M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md").read_text(
        encoding="utf-8"
    )
    assert "implementação runtime **não iniciada**" in constitution.lower() or "não iniciada" in constitution
