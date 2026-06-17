"""Conferir Resultados — Auditoria de Lotes Reais Persistidos (M-VIS-037)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

CONFERENCE_READ_ONLY_ALERT = (
    "Conferir Resultados — auditoria read-only de lotes persistidos. "
    "Não gera jogos, não simula resultado e não altera Núcleo ou histórico."
)

CONFERENCE_MANDATORY_QUOTE = (
    "Conferir Resultados é auditoria de produção gerada e persistida. "
    "Simular Resultados é laboratório. Conferir não gera, não simula e não usa "
    "session_state como fonte soberana."
)

INSTITUTIONAL_ALERTS: tuple[str, ...] = (
    "Conferência não gera jogos.",
    "Conferência não simula resultado.",
    "Fonte soberana: PostgreSQL.",
    "session_state/cache/tela não são verdade operacional.",
    "Apenas lotes persistidos podem ser auditados institucionalmente.",
)

LEI_001_RULE = (
    "Lei 001 — PostgreSQL é a fonte soberana. Conferir Resultados prioriza "
    "generation_events, generated_games, batch_label, concursos oficiais persistidos "
    "e trilha auditável de lote real."
)

BATCH_LABEL_NOTE = (
    "batch_label identifica o lote persistido a ser auditado, não autoriza geração."
)

SOVEREIGN_SOURCE_ROWS: tuple[dict[str, str], ...] = (
    {"fonte": "generation_events", "papel": "Evento de geração persistido no PostgreSQL"},
    {"fonte": "generated_games", "papel": "Jogos persistidos vinculados ao evento/lote"},
    {"fonte": "batch_label", "papel": "Identificador institucional do lote auditado"},
    {"fonte": "imported_contests", "papel": "Resultado oficial importado e persistido"},
    {"fonte": "reconciliation_runs", "papel": "Trilha de conferência persistida"},
    {"fonte": "reconciliation_games", "papel": "Detalhe jogo-a-jogo da conferência"},
)

REJECTED_SOURCE_ROWS: tuple[dict[str, str], ...] = (
    {"fonte": "CSV local", "motivo": "Backup/export — não verdade operacional (Lei 001)"},
    {"fonte": "session_state", "motivo": "Estado de UI — não fonte soberana"},
    {"fonte": "cache", "motivo": "Camada efêmera — não substitui PostgreSQL"},
    {"fonte": "tela", "motivo": "Renderização visual — não persistência"},
    {"fonte": "lote temporário", "motivo": "Sem trilha auditável institucional"},
    {"fonte": "geração em memória", "motivo": "Fora do PostgreSQL — bloqueado"},
    {"fonte": "simulação local", "motivo": "Use Simular Resultados — laboratório session-only"},
    {"fonte": "replay histórico", "motivo": "Observacional — não lote real de produção"},
    {"fonte": "payload manual sem persistência", "motivo": "Rejeitado por Lei 001"},
)

FLOW_SEPARATION_ROWS: tuple[dict[str, str], ...] = (
    {
        "fluxo": "Conferir Resultados",
        "proposito": "Auditoria de lote real persistido × resultado oficial",
        "fonte": "PostgreSQL (Lei 001)",
        "geracao": "Não gera",
    },
    {
        "fluxo": "Simular Resultados",
        "proposito": "Laboratório session-only — stress hipotético",
        "fonte": "Session — não soberana",
        "geracao": "Não gera",
    },
    {
        "fluxo": "Simulação Institucional / Backtesting",
        "proposito": "Governança walk-forward — corte temporal X-1",
        "fonte": "Read-only diagnóstico",
        "geracao": "Proibida",
    },
    {
        "fluxo": "Geração operacional",
        "proposito": "Produzir jogos (path soberano bloqueado)",
        "fonte": "PostgreSQL quando autorizado",
        "geracao": "BLOQUEADA",
    },
)

EMPTY_STATE_MESSAGES: tuple[str, ...] = (
    "Sem lote persistido para conferir.",
    "Ação bloqueada por Lei 001.",
    "Use Simulação Institucional para laboratório histórico.",
)

CONFERENCE_PROHIBITIONS: tuple[str, ...] = (
    "Não é calibração automática.",
    "Não altera Núcleo (LEI15_CORE_002).",
    "Não cria lote.",
    "Não chama generate_best_games.",
    "Não chama _generate_direct_15_games.",
    "Não aceita batch_label=None como lote institucional soberano.",
)


def build_conference_audit_snapshot(
    *,
    generation_blocked: bool,
    has_persisted_batches: bool,
    persisted_generation_events: int = 0,
    persisted_games: int = 0,
    reconciliation_runs: int = 0,
) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": CONFERENCE_READ_ONLY_ALERT,
        "mandatory_quote": CONFERENCE_MANDATORY_QUOTE,
        "institutional_alerts": list(INSTITUTIONAL_ALERTS),
        "lei_001_rule": LEI_001_RULE,
        "batch_label_note": BATCH_LABEL_NOTE,
        "sovereign_sources": [dict(row) for row in SOVEREIGN_SOURCE_ROWS],
        "rejected_sources": [dict(row) for row in REJECTED_SOURCE_ROWS],
        "flow_separation": [dict(row) for row in FLOW_SEPARATION_ROWS],
        "empty_state_messages": list(EMPTY_STATE_MESSAGES),
        "prohibitions": list(CONFERENCE_PROHIBITIONS),
        "generation_status": "BLOQUEADA" if generation_blocked else "HABILITADA",
        "has_persisted_batches": has_persisted_batches,
        "persisted_generation_events": persisted_generation_events,
        "persisted_games": persisted_games,
        "reconciliation_runs": reconciliation_runs,
        "sovereign_db": "PostgreSQL",
    }


def render_conference_governance_section(
    *,
    generation_blocked: bool,
    has_persisted_batches: bool,
    persisted_generation_events: int = 0,
    persisted_games: int = 0,
    reconciliation_runs: int = 0,
) -> None:
    """Bloco institucional read-only — Conferir Resultados / Lei 001."""
    payload = build_conference_audit_snapshot(
        generation_blocked=generation_blocked,
        has_persisted_batches=has_persisted_batches,
        persisted_generation_events=persisted_generation_events,
        persisted_games=persisted_games,
        reconciliation_runs=reconciliation_runs,
    )

    st.info(CONFERENCE_READ_ONLY_ALERT)
    for alert in INSTITUTIONAL_ALERTS:
        st.warning(alert)
    st.markdown(f"*{CONFERENCE_MANDATORY_QUOTE}*")
    st.markdown(f"*{LEI_001_RULE}*")
    st.caption(BATCH_LABEL_NOTE)

    status_cols = st.columns(4)
    status_cols[0].metric("Fonte soberana", payload["sovereign_db"])
    status_cols[1].metric("generation_events", persisted_generation_events)
    status_cols[2].metric("generated_games", persisted_games)
    status_cols[3].metric("Geração", payload["generation_status"])

    st.markdown("##### Fontes soberanas (PostgreSQL — Lei 001)")
    st.dataframe(
        pd.DataFrame(payload["sovereign_sources"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Fontes rejeitadas como verdade operacional")
    st.dataframe(
        pd.DataFrame(payload["rejected_sources"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Separação de fluxos")
    st.dataframe(
        pd.DataFrame(payload["flow_separation"]),
        hide_index=True,
        use_container_width=True,
    )

    if not has_persisted_batches:
        for message in EMPTY_STATE_MESSAGES:
            st.error(message)
    else:
        st.success("Lote(s) persistido(s) disponível(is) para auditoria institucional.")

    st.markdown("##### O que Conferir Resultados não faz")
    for item in CONFERENCE_PROHIBITIONS:
        st.markdown(f"- {item}")
