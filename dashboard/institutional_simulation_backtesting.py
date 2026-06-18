"""Simulação Institucional / Backtesting — read-only no Painel ADM (M-VIS-036)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES

SIMULATION_BACKTESTING_READ_ONLY_ALERT = (
    "Simulação Institucional / Backtesting — read-only. Nenhuma geração real, purge, "
    "recalibração automática ou mutação de histórico é executada nesta tela."
)

INSTITUTIONAL_ALERTS: tuple[str, ...] = (
    "Backtesting institucional é diagnóstico — não promessa de acerto.",
    "Corte temporal obrigatório: concurso X usa apenas dados até X-1.",
    "Walk-forward é mandatório — sem vazamento temporal.",
    "Nenhuma simulação desta tela executa geração operacional.",
    "Conferir Resultados ≠ Simulação Institucional ≠ Geração.",
)

TEMPORAL_CUT_RULE = (
    "Para simular ou avaliar o concurso X, usar exclusivamente dados disponíveis até X-1. "
    "Nunca incluir resultado futuro na feature engineering ou no ranking."
)

SIX_BASES_QUOTE = "Hit isolado não é veredicto. Backtesting informa as 6 bases — não decide o Núcleo."

FLOW_SEPARATION_ROWS: tuple[dict[str, str], ...] = (
    {
        "fluxo": "Conferir Resultados",
        "proposito": "Confronto seleção persistida × resultado oficial importado",
        "persistencia": "Usa jogos e concursos já no PostgreSQL",
        "geracao": "Não gera",
        "backtesting": "Não — conferência operacional observada",
    },
    {
        "fluxo": "Simular Resultados (session)",
        "proposito": "Cenário hipotético / stress com dezenas digitadas pelo ADM",
        "persistencia": "Session-only — não substitui reconciliação oficial",
        "geracao": "Não gera",
        "backtesting": "Não — comparação efêmera",
    },
    {
        "fluxo": "Simulação Institucional / Backtesting",
        "proposito": "Governança walk-forward, janelas 10/20/30, corte temporal",
        "persistencia": "Read-only — preparação diagnóstica",
        "geracao": "Proibida nesta missão",
        "backtesting": "Conceitual/diagnóstico — execução automática proibida",
    },
    {
        "fluxo": "Replay institucional",
        "proposito": "Releitura do último lote × concurso corrente",
        "persistencia": "Observacional",
        "geracao": "Não gera",
        "backtesting": "Parcial — sem walk-forward completo",
    },
    {
        "fluxo": "Geração operacional",
        "proposito": "Produzir jogos via path soberano (bloqueado)",
        "persistencia": "PostgreSQL — Lei 001",
        "geracao": "BLOQUEADA (LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0)",
        "backtesting": "Fora de escopo desta tela",
    },
)

WALK_FORWARD_WINDOWS: tuple[dict[str, str], ...] = (
    {
        "janela": "10 concursos",
        "uso": "Diagnóstico rápido de estabilidade recente",
        "corte": "Dados até X-1 para prever/avaliar X",
    },
    {
        "janela": "20 concursos",
        "uso": "Equilíbrio entre sensibilidade e robustez",
        "corte": "Walk-forward comparável — sem misturar futuro",
    },
    {
        "janela": "30 concursos",
        "uso": "Estabilidade multi-ciclo (Base 6)",
        "corte": "Janelas comparáveis entre si",
    },
)

BACKTESTING_SECURITY_STATUS: dict[str, str] = {
    "execucao_automatica": "False — proibida nesta tela",
    "geracao_real": "False — bloqueada",
    "purge": "False — protegido",
    "ml_operacional": "False — assistivo apenas",
    "recalibracao_automatica": "False — proibida",
    "vazamento_temporal": "monitorado — corte X-1 obrigatório",
    "decisao_final": "governança + evidência Git",
}

BACKTESTING_SIX_BASES_ROWS: tuple[dict[str, str], ...] = tuple(
    {
        "base": BASE_LABELS_PT[name],
        "leitura_backtesting": {
            "forca_acerto": "Hits agregados em janela walk-forward — hit isolado ≠ veredicto",
            "diversidade": "Entropia/perfil ao longo da janela temporal",
            "baixa_redundancia": "Overlap entre cartões avaliados na janela",
            "controle_prefixo_sufixo": "Distribuição prefixo/sufixo na janela",
            "cobertura_dezenas_criticas": "Presença de reforços/blind spots na janela",
            "estabilidade_multi_concurso": "Variância das métricas em 10/20/30 concursos",
        }[name],
        "status_painel": "read-only — métrica operacional pendente de missão futura",
    }
    for name in BASE_NAMES
)

TEMPORAL_LEAKAGE_RISKS: tuple[dict[str, str], ...] = (
    {"risco": "Feature com resultado futuro", "mitigacao": "Corte X-1 em toda engenharia"},
    {"risco": "Misturar janelas incomparáveis", "mitigacao": "10/20/30 walk-forward padronizado"},
    {"risco": "Backtesting → geração", "mitigacao": "Separação fluxo + geração bloqueada"},
    {"risco": "Hit isolado como promoção", "mitigacao": "Avaliação pelas 6 bases"},
    {"risco": "Session simulation como verdade", "mitigacao": "Simular Resultados ≠ Simulação Institucional"},
)


def build_simulation_backtesting_snapshot(*, generation_blocked: bool) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    flow_rows = [dict(row) for row in FLOW_SEPARATION_ROWS]
    for row in flow_rows:
        if row.get("fluxo") == "Geração operacional":
            if generation_blocked:
                row["proposito"] = "Produzir jogos via path soberano (bloqueado)"
                row["geracao"] = "BLOQUEADA (LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0)"
            else:
                row["proposito"] = "Produzir jogos via path soberano controlado (M-GER-044)"
                row["geracao"] = "CONTROLADA — label CORE_002 obrigatório"
    from dashboard.institutional_sovereign_generation import sovereign_generation_status_label

    return {
        "read_only_alert": SIMULATION_BACKTESTING_READ_ONLY_ALERT,
        "institutional_alerts": list(INSTITUTIONAL_ALERTS),
        "temporal_cut_rule": TEMPORAL_CUT_RULE,
        "six_bases_quote": SIX_BASES_QUOTE,
        "flow_separation": flow_rows,
        "walk_forward_windows": [dict(row) for row in WALK_FORWARD_WINDOWS],
        "backtesting_security": dict(BACKTESTING_SECURITY_STATUS),
        "six_bases_backtesting": [dict(row) for row in BACKTESTING_SIX_BASES_ROWS],
        "temporal_leakage_risks": [dict(row) for row in TEMPORAL_LEAKAGE_RISKS],
        "generation_status": "BLOQUEADA" if generation_blocked else sovereign_generation_status_label(),
        "execucao_backtest_automatica": False,
        "geracao_real": False,
    }


def render_institutional_simulation_backtesting_page(*, generation_blocked: bool) -> None:
    """Renderiza Simulação Institucional / Backtesting (somente leitura)."""
    payload = build_simulation_backtesting_snapshot(generation_blocked=generation_blocked)

    st.info(SIMULATION_BACKTESTING_READ_ONLY_ALERT)
    for alert in INSTITUTIONAL_ALERTS:
        st.warning(alert)
    st.markdown(f"*{TEMPORAL_CUT_RULE}*")
    st.markdown(f"*{SIX_BASES_QUOTE}*")

    status_cols = st.columns(3)
    status_cols[0].metric("Geração", payload["generation_status"])
    status_cols[1].metric("Backtest automático", "False")
    status_cols[2].metric("Vazamento temporal", "Monitorado")

    st.markdown("##### Separação de fluxos — Conferir ≠ Simular ≠ Backtesting ≠ Geração")
    st.dataframe(
        pd.DataFrame(payload["flow_separation"]),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Use **Conferir Resultados** para confronto oficial persistido. "
        "Use **Simular Resultados** apenas para stress session-only. "
        "Esta tela governa backtesting institucional read-only."
    )

    st.markdown("##### Walk-forward — janelas de validação")
    st.dataframe(
        pd.DataFrame(payload["walk_forward_windows"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Status de segurança backtesting")
    st.dataframe(
        pd.DataFrame([{"campo": k, "valor": v} for k, v in payload["backtesting_security"].items()]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Backtesting × 6 Bases (diagnóstico — não decide Núcleo)")
    st.dataframe(
        pd.DataFrame(payload["six_bases_backtesting"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Riscos de vazamento temporal")
    st.dataframe(
        pd.DataFrame(payload["temporal_leakage_risks"]),
        hide_index=True,
        use_container_width=True,
    )

    st.info(
        "Execução automática de backtest com geração real permanece **fora do escopo** "
        "desta missão. Qualquer evolução operacional exige missão dedicada, ADR e evidência Git."
    )
