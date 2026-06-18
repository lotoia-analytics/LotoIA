"""Lei 15A redefinida — camada futura subordinada ao CORE_002, inoperante (M-GOV-038)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

LEI15A_FORMAL_STATUS = "REDEFINIDA / FUTURA / SUBORDINADA AO CORE_002 / INOPERANTE"

LEI15A_MANDATORY_QUOTE = (
    "A Lei 15A é uma camada futura subordinada ao LEI15_CORE_002. "
    "No estado atual, está redefinida e inoperante: não gera, não expande, "
    "não altera Núcleo, não ativa mecânica 15+1/15+2 e não possui efeito operacional."
)

LEI15A_READ_ONLY_ALERT = (
    "Lei 15A — governança read-only. Camada futura subordinada ao CORE_002. "
    "Nenhuma geração, expansão, calibração ou alteração de Núcleo é executada nesta tela."
)

CONSTITUTIONAL_POINTS: tuple[str, ...] = (
    "LEI15_CORE_002 continua soberano.",
    "Lei 15A não é Núcleo soberano.",
    "Lei 15A não pode sobrescrever CORE_002.",
    "Lei 15A não pode liberar geração.",
    "Lei 15A não pode operar expansão agora.",
    "Lei 15A não pode reativar a mecânica antiga 15+1/15+2.",
    "Lei 15A não pode criar jogos.",
    "Lei 15A não pode alterar pesos/papéis das dezenas.",
    "Lei 15A não pode alterar generate_best_games.",
    "Lei 15A não pode alterar banco/schema.",
    "Lei 15A não pode ser usada por ML de forma operacional.",
    "Qualquer uso futuro exige missão própria, agente, escopo, testes, ADR e autorização.",
)

PROHIBITIONS: tuple[str, ...] = (
    "Não gera jogos.",
    "Não expande formatos 16D–23D operacionalmente.",
    "Não reativa mecânica 15+1/15+2.",
    "Não altera LEI15_CORE_002.",
    "Não altera papéis/pesos do Núcleo.",
    "Não chama generate_best_games por causa da Lei 15A.",
    "Não altera banco/schema.",
    "Não executa purge.",
    "Não ativa ML operacional.",
    "Não altera public_app.",
)

FUTURE_USE_ROWS: tuple[dict[str, str], ...] = (
    {"requisito": "Missão própria", "status": "obrigatório"},
    {"requisito": "Agente responsável roteado", "status": "obrigatório"},
    {"requisito": "Escopo delimitado", "status": "obrigatório"},
    {"requisito": "Testes e validação", "status": "obrigatório"},
    {"requisito": "ADR ou registro de governança", "status": "obrigatório"},
    {"requisito": "Evidência Git", "status": "obrigatório"},
    {"requisito": "Autorização institucional", "status": "obrigatório"},
)

STATUS_ROWS: tuple[dict[str, str], ...] = (
    {"campo": "Lei 15A", "valor": "REDEFINIDA"},
    {"campo": "Camada", "valor": "FUTURA"},
    {"campo": "Subordinação", "valor": "LEI15_CORE_002"},
    {"campo": "Operação", "valor": "INOPERANTE"},
    {"campo": "Geração", "valor": "PROIBIDA"},
    {"campo": "Expansão 15+1/15+2", "valor": "NÃO REATIVADA"},
    {"campo": "ML operacional", "valor": "PROIBIDO"},
)

GOVERNANCE_DOC_PATH = "docs/governance/LEI_15A_CAMADA_FUTURA_SUBORDINADA_CORE_002.md"


def build_lei15a_governance_snapshot(*, generation_blocked: bool) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": LEI15A_READ_ONLY_ALERT,
        "mandatory_quote": LEI15A_MANDATORY_QUOTE,
        "formal_status": LEI15A_FORMAL_STATUS,
        "constitutional_points": list(CONSTITUTIONAL_POINTS),
        "prohibitions": list(PROHIBITIONS),
        "future_use_requirements": [dict(row) for row in FUTURE_USE_ROWS],
        "status_rows": [dict(row) for row in STATUS_ROWS],
        "core_sovereignty": "LEI15_CORE_002 permanece soberano",
        "generation_status": "BLOQUEADA" if generation_blocked else "HABILITADA",
        "governance_doc": GOVERNANCE_DOC_PATH,
        "mission_id": "M-GOV-038",
    }


def render_lei15a_governance_section(*, generation_blocked: bool) -> None:
    """Bloco institucional read-only — Lei 15A redefinida / inoperante."""
    payload = build_lei15a_governance_snapshot(generation_blocked=generation_blocked)

    st.markdown("##### Lei 15A — Camada Futura Subordinada ao CORE_002")
    st.info(LEI15A_READ_ONLY_ALERT)
    st.markdown(f"*{LEI15A_MANDATORY_QUOTE}*")

    status_cols = st.columns(4)
    status_cols[0].metric("Status formal", "REDEFINIDA")
    status_cols[1].metric("Camada", "FUTURA")
    status_cols[2].metric("Subordinação", "CORE_002")
    status_cols[3].metric("Operação", "INOPERANTE")

    st.markdown("##### Status constitucional Lei 15A")
    st.dataframe(
        pd.DataFrame(payload["status_rows"]),
        hide_index=True,
        use_container_width=True,
    )

    st.success(payload["core_sovereignty"])
    if payload["generation_status"] == "BLOQUEADA":
        st.success(f"Geração: **{payload['generation_status']}** — Lei 15A não libera geração.")
    else:
        st.error(f"Geração: **{payload['generation_status']}** — estado inesperado para Lei 15A inoperante.")

    st.markdown("##### Pontos constitucionais")
    for point in CONSTITUTIONAL_POINTS:
        st.markdown(f"- {point}")

    st.markdown("##### Requisitos para uso futuro")
    st.dataframe(
        pd.DataFrame(payload["future_use_requirements"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### O que a Lei 15A não faz (estado atual)")
    for item in PROHIBITIONS:
        st.markdown(f"- {item}")

    st.caption(f"Documento: `{GOVERNANCE_DOC_PATH}` — missão `{payload['mission_id']}`.")
