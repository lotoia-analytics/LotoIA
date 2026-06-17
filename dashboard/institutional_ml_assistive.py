"""Central ML Assistiva + Vazamento Lateral Constitucional — read-only (M-VIS-035)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES

ML_ASSISTIVE_READ_ONLY_ALERT = (
    "Central ML Assistiva — read-only. Nenhuma geração, recalibração automática, "
    "promoção de política ou purge é executada nesta tela."
)

SIDE_LEAK_READ_ONLY_ALERT = (
    "Vazamento Lateral Constitucional — diagnóstico read-only. Não gera jogos, "
    "não altera Núcleo, não muda política e não substitui decisão institucional."
)

GUARDIAN_ANALYTIC_QUOTE = (
    "O ML da LotoIA atua como Guardião Analítico Assistivo: diagnostica, pontua, "
    "recomenda e alerta, mas não possui efeito operacional automático. Toda decisão "
    "derivada do ML precisa passar por governança, missão por agente e evidência Git."
)

INSTITUTIONAL_ML_ALERTS: tuple[str, ...] = (
    "ML assistivo — sem efeito operacional automático.",
    "Nenhuma recomendação ML executa geração.",
    "Toda decisão operacional exige missão, governança e evidência Git.",
    "Vazamento lateral é diagnóstico de risco, não comando de geração.",
)

SIX_BASES_QUOTE = "Hit isolado não é veredicto. O Núcleo é avaliado pelas 6 bases."

SEPARATION_MATRIX_ROWS: tuple[dict[str, str], ...] = (
    {
        "camada": "Diagnóstico",
        "papel": "ML observa, pontua e explica padrões estruturais",
        "efeito_operacional": "Nenhum",
    },
    {
        "camada": "Recomendação",
        "papel": "ML sugere leituras ou hipóteses para governança",
        "efeito_operacional": "Nenhum — não aplica automaticamente",
    },
    {
        "camada": "Alerta",
        "papel": "ML sinaliza risco (vazamento, recorrência, anomalia)",
        "efeito_operacional": "Nenhum — requer veredito ADM",
    },
    {
        "camada": "Decisão institucional",
        "papel": "Governança, missão por agente, ADR, evidência Git",
        "efeito_operacional": "Somente após autorização explícita",
    },
    {
        "camada": "Operação",
        "papel": "Geração, purge, recalibração, promoção de Núcleo",
        "efeito_operacional": "Bloqueada nesta missão — fora do escopo ML",
    },
)

ML_SECURITY_STATUS: dict[str, str] = {
    "ml_operacional": "False — desativado",
    "geracao_por_ml": "proibida",
    "recalibracao_automatica": "proibida",
    "promocao_automatica": "proibida",
    "generation_cmd": "False — bloqueado, não executável",
    "recalibration_cmd": "False — bloqueado, não executável",
    "comandos_executaveis": "não",
    "decisao_final": "governança",
}

ML_SIX_BASES_RELATION: tuple[dict[str, str], ...] = tuple(
    {
        "base": BASE_LABELS_PT[name],
        "papel_ml": {
            "forca_acerto": "Auxilia leitura de hits 12+/13+ — hit isolado ≠ veredicto",
            "diversidade": "Diagnostica colapso de perfis e concentração estrutural",
            "baixa_redundancia": "Sinaliza overlap e clones no lote",
            "controle_prefixo_sufixo": "Alerta vícios nas faixas 01–03 e 22–25",
            "cobertura_dezenas_criticas": "Observa reforços e blind spots — cobertura ≠ contagem cega",
            "estabilidade_multi_concurso": "Apoia leitura walk-forward 10/20/30 concursos",
        }[name],
        "decisao": "ML informa — Núcleo avaliado pelo conjunto das 6 bases",
    }
    for name in BASE_NAMES
)

FUTURE_SIMULATION_PREP: tuple[str, ...] = (
    "Replay histórico institucional (M-VIS-036 — futura, sem implementação agora).",
    "Walk-forward com corte temporal: concurso X usa apenas dados até X-1.",
    "Janelas comparáveis: 10 / 20 / 30 concursos.",
    "Backtesting futuro — diagnóstico e governança, sem efeito operacional automático.",
)

SIDE_LEAK_RISK_ROWS: tuple[dict[str, str], ...] = (
    {"risco": "Bypass de caminho soberano", "descricao": "Interpretar diagnóstico como autorização de geração"},
    {"risco": "Relabeling indevido", "descricao": "Promover V1/CAND-D/V2/V3/V4/baseline a Núcleo soberano"},
    {"risco": "Hit isolado como veredicto", "descricao": "Decidir Núcleo por acerto único, ignorando 6 bases"},
    {"risco": "Histórico confundido com Núcleo", "descricao": "Tratar lote legado como referência constitucional"},
    {"risco": "ML como decisão automática", "descricao": "Executar recomendação ML sem governança"},
    {"risco": "Diagnóstico → geração", "descricao": "Transformar alerta observacional em comando operacional"},
    {"risco": "Quebra Lei 001", "descricao": "Usar CSV ou fonte não operacional como verdade"},
    {"risco": "Furar M-LEI15-003", "descricao": "Bypass de generate_best_games ou batch_label legado"},
)

SIDE_LEAK_DOES_NOT: tuple[str, ...] = (
    "Não gera jogos.",
    "Não bloqueia banco sozinho.",
    "Não altera Núcleo.",
    "Não muda política.",
    "Não executa purge.",
    "Não ativa ML operacional.",
    "Não substitui decisão institucional.",
)

EVOLUTION_HISTORICAL_NOTE = (
    "Evolução 13→14 / 14→15: evidência histórica e diagnóstica — sem promessa de acerto "
    "e sem recalibração automática."
)


def build_ml_assistive_snapshot() -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": ML_ASSISTIVE_READ_ONLY_ALERT,
        "guardian_quote": GUARDIAN_ANALYTIC_QUOTE,
        "institutional_alerts": list(INSTITUTIONAL_ML_ALERTS),
        "six_bases_quote": SIX_BASES_QUOTE,
        "separation_matrix": [dict(row) for row in SEPARATION_MATRIX_ROWS],
        "ml_security_status": dict(ML_SECURITY_STATUS),
        "ml_six_bases_relation": [dict(row) for row in ML_SIX_BASES_RELATION],
        "future_simulation_prep": list(FUTURE_SIMULATION_PREP),
        "generation_cmd": False,
        "recalibration_cmd": False,
        "ml_operacional": False,
    }


def build_constitutional_side_leak_snapshot() -> dict[str, Any]:
    """Snapshot read-only vazamento lateral — sem efeitos colaterais."""
    return {
        "read_only_alert": SIDE_LEAK_READ_ONLY_ALERT,
        "status": "Diagnóstico constitucional read-only.",
        "definition": (
            "Diagnóstico de risco de uma política, lote, tela ou leitura produzir "
            "interpretação indevida ou operação fora do caminho soberano."
        ),
        "measures": (
            "sobra_real = cartao_final − resultado_oficial — dezena em cartão final "
            "e fora do resultado oficial."
        ),
        "risk_rows": [dict(row) for row in SIDE_LEAK_RISK_ROWS],
        "does_not": list(SIDE_LEAK_DOES_NOT),
        "generation_cmd": False,
        "recalibration_cmd": False,
    }


def render_ml_assistive_governance_section() -> None:
    """Bloco institucional read-only — Central ML Assistiva."""
    payload = build_ml_assistive_snapshot()

    st.info(ML_ASSISTIVE_READ_ONLY_ALERT)
    for alert in INSTITUTIONAL_ML_ALERTS:
        st.warning(alert)
    st.markdown(f"*{GUARDIAN_ANALYTIC_QUOTE}*")
    st.markdown(f"*{SIX_BASES_QUOTE}*")

    st.markdown("##### Status de segurança ML")
    security_cols = st.columns(4)
    security_cols[0].metric("ML operacional", "False")
    security_cols[1].metric("generation_cmd", "False")
    security_cols[2].metric("recalibration_cmd", "False")
    security_cols[3].metric("Decisão final", "Governança")
    st.dataframe(
        pd.DataFrame([{"campo": k, "valor": v} for k, v in payload["ml_security_status"].items()]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Separação: diagnóstico → operação")
    st.dataframe(
        pd.DataFrame(payload["separation_matrix"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### ML × 6 Bases (assistivo — não decide sozinho)")
    st.dataframe(
        pd.DataFrame(payload["ml_six_bases_relation"]),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("O ML pode ajudar a ler as 6 Bases, mas não decide sozinho.")

    st.markdown("##### Preparação futura — Simulação Institucional (M-VIS-036)")
    for item in payload["future_simulation_prep"]:
        st.markdown(f"- {item}")
    st.info(EVOLUTION_HISTORICAL_NOTE)


def render_constitutional_side_leak_section() -> None:
    """Bloco institucional read-only — Vazamento Lateral Constitucional."""
    payload = build_constitutional_side_leak_snapshot()

    st.info(SIDE_LEAK_READ_ONLY_ALERT)
    st.warning("Vazamento lateral é diagnóstico de risco, não comando de geração.")
    st.markdown(f"**Status:** {payload['status']}")
    st.write(payload["definition"])
    st.caption(payload["measures"])

    cmd_cols = st.columns(2)
    cmd_cols[0].metric("generation_cmd", "False — bloqueado")
    cmd_cols[1].metric("recalibration_cmd", "False — bloqueado")

    st.markdown("##### Riscos constitucionais monitorados")
    st.dataframe(
        pd.DataFrame(payload["risk_rows"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### O que este bloco não faz")
    for item in payload["does_not"]:
        st.markdown(f"- {item}")

    st.caption(
        "Consulte a **Central ML Assistiva** para drilldown auditável de alertas "
        "de vazamento lateral recorrente — sempre read-only."
    )
