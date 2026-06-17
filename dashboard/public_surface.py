"""Canal público seguro — separado do Painel ADM institucional (M-PLAT-041)."""

from __future__ import annotations

from typing import Any

import streamlit as st

PUBLIC_SURFACE_ALERT = (
    "Canal público/comercial LotoIA — em preparação. "
    "Não é o Painel ADM institucional."
)

PUBLIC_MANDATORY_DISCLAIMERS: tuple[str, ...] = (
    "Canal público em preparação.",
    "Sem geração ativa neste canal.",
    "Sem apostas automáticas.",
    "Sem promessa de acerto.",
    "Sem operação financeira.",
    "Sem integração Caixa ativa.",
    "Sem acesso ao Painel ADM institucional.",
)

PUBLIC_POSITIONING = (
    "LotoIA é uma plataforma estatística estrutural com assistência supervisionada "
    "incremental. Este canal público não expõe governança interna, histórico "
    "institucional, simulação/backtesting, ML assistivo interno, área restrita "
    "ou rotas administrativas."
)

PUBLIC_NOT_OFFERED: tuple[str, ...] = (
    "Governança Institucional — read-only",
    "Núcleo Lei 15 — CORE_002 (ADM)",
    "Gerador ADM CORE_002 — BLOQUEADO",
    "Conferir Resultados — Auditoria de Lotes Persistidos (ADM)",
    "Simulação Institucional / Backtesting (ADM)",
    "Central ML Assistiva (ADM)",
    "Vazamento Lateral Constitucional (ADM)",
    "Área Restrita — Limpeza Controlada (ADM)",
    "Cobertura Estrutural interna (ADM)",
    "Histórico institucional interno (ADM)",
)

PUBLIC_CHANNEL_STATUS_ROWS: tuple[dict[str, str], ...] = (
    {"campo": "Canal", "valor": "Público / comercial — preparação"},
    {"campo": "Geração", "valor": "INATIVA neste canal"},
    {"campo": "Purge", "valor": "PROIBIDO"},
    {"campo": "ADM", "valor": "NÃO ACESSÍVEL"},
    {"campo": "Apostas automáticas", "valor": "NÃO"},
    {"campo": "Promessa de acerto", "valor": "NÃO"},
    {"campo": "Integração Caixa", "valor": "NÃO ATIVA"},
)


def build_public_surface_snapshot(*, public_build: str) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": PUBLIC_SURFACE_ALERT,
        "mandatory_disclaimers": list(PUBLIC_MANDATORY_DISCLAIMERS),
        "positioning": PUBLIC_POSITIONING,
        "not_offered": list(PUBLIC_NOT_OFFERED),
        "status_rows": [dict(row) for row in PUBLIC_CHANNEL_STATUS_ROWS],
        "public_build": public_build,
        "mission_id": "M-PLAT-041",
    }


def render_public_app(*, public_build: str) -> None:
    """Renderiza entrada pública segura — sem ADM, geração ou purge."""
    payload = build_public_surface_snapshot(public_build=public_build)

    st.title("LotoIA — Canal Público")
    st.info(PUBLIC_SURFACE_ALERT)

    for disclaimer in PUBLIC_MANDATORY_DISCLAIMERS:
        st.warning(disclaimer)

    st.markdown(PUBLIC_POSITIONING)

    st.markdown("##### Status do canal público")
    st.table(payload["status_rows"])

    st.markdown("##### O que este canal **não** oferece")
    for item in PUBLIC_NOT_OFFERED:
        st.markdown(f"- {item}")

    st.caption(
        f"Build público: `{public_build}`. "
        "Painel ADM institucional disponível somente via entrypoint dedicado "
        "(`dashboard/institutional_app.py`)."
    )
