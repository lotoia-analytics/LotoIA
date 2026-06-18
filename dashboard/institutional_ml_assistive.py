"""Central ML Assistiva + Vazamento Lateral Constitucional — M-VIS-035 / M-ML-045."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.institutional_supervised_ml import (
    CONSTITUTIONAL_BLOCKS,
    EMPTY_ML_EVENTS_MESSAGE,
    SUPERVISED_ML_DISCLAIMER,
    SUPERVISED_ML_GOVERNANCE_ALERT,
    SUPERVISED_ML_STATUS_ACTIVE,
    VIS_MISSION_ID,
    build_ml_six_bases_operational_summary,
    build_supervised_ml_activation_snapshot,
    build_supervised_ml_operational_event_detail,
    build_supervised_ml_operational_panel_snapshot,
    is_adm_supervised_ml_active,
    is_ml_operational_enabled,
    supervised_ml_status_label,
)
from lotoia.governance.lei15_core_six_bases_evaluation import BASE_LABELS_PT, BASE_NAMES

ML_ASSISTIVE_READ_ONLY_ALERT = (
    "Central ML Assistiva — read-only. Nenhuma geração, recalibração automática, "
    "promoção de política ou purge é executada nesta tela."
)

ML_ASSISTIVE_OPERATIONAL_ALERT = (
    "Central ML Assistiva — ML operacional supervisionado ativo sobre CORE_002. "
    "Pontuação, reranking e diagnóstico operam exclusivamente via generate_best_games "
    "no Gerador ADM — esta tela permanece sem comandos executáveis de geração."
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

GUARDIAN_OPERATIONAL_QUOTE = (
    "O ML operacional supervisionado pontua, reranqueia e diagnostica dentro do path "
    "soberano CORE_002 — subordinado à Lei 15 e às 6 Bases. Hit isolado não é veredicto."
)

INSTITUTIONAL_ML_ALERTS: tuple[str, ...] = (
    "ML assistivo — sem efeito operacional automático.",
    "Nenhuma recomendação ML executa geração.",
    "Toda decisão operacional exige missão, governança e evidência Git.",
    "Vazamento lateral é diagnóstico de risco, não comando de geração.",
)

INSTITUTIONAL_ML_OPERATIONAL_ALERTS: tuple[str, ...] = (
    "ML operacional supervisionado — ativo somente sobre CORE_002.",
    "Geração por ML fora do path soberano permanece proibida.",
    "Decision trace, feature attribution e lineage são persistidos no PostgreSQL.",
    "Vazamento lateral continua monitorando risco constitucional.",
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

SEPARATION_MATRIX_OPERATIONAL_ROWS: tuple[dict[str, str], ...] = (
    {
        "camada": "Diagnóstico",
        "papel": "ML pontua, classifica risco e explica via 6 Bases",
        "efeito_operacional": "Ativo no lote CORE_002 — supervisionado",
    },
    {
        "camada": "Reranking",
        "papel": "score_ml reranqueia subordinado ao híbrido estrutural",
        "efeito_operacional": "Ativo — não substitui compose_sovereign_gp",
    },
    {
        "camada": "Trace",
        "papel": "Decision trace + feature attribution + lineage",
        "efeito_operacional": "Persistido em generation_events / generated_games",
    },
    {
        "camada": "Decisão institucional",
        "papel": "Governança, missão por agente, ADR, evidência Git",
        "efeito_operacional": "Veredito ADM sobre promoções e mutações",
    },
    {
        "camada": "Proibições",
        "papel": "Lei 15A, public_app, legado, purge, hit isolado",
        "efeito_operacional": "Bloqueado — fail-closed",
    },
)

ML_SECURITY_STATUS_READ_ONLY: dict[str, str] = {
    "ml_operacional": "False — desativado",
    "geracao_por_ml": "proibida",
    "recalibracao_automatica": "proibida",
    "promocao_automatica": "proibida",
    "generation_cmd": "False — bloqueado, não executável",
    "recalibration_cmd": "False — bloqueado, não executável",
    "comandos_executaveis": "não",
    "decisao_final": "governança",
}

ML_SECURITY_STATUS_OPERATIONAL: dict[str, str] = {
    "ml_operacional": "True — supervisionado sobre CORE_002",
    "geracao_por_ml": "permitida somente via path soberano ADM",
    "recalibracao_automatica": "proibida",
    "promocao_automatica": "proibida",
    "generation_cmd": "False — painel ML não executa geração",
    "recalibration_cmd": "False — bloqueado, não executável",
    "comandos_executaveis": "não nesta tela",
    "decisao_final": "governança + trace PostgreSQL",
    "decision_trace": "ativo — persistido",
    "feature_attribution": "ativo — persistido",
    "ml_six_bases": "ativo — leitura supervisionada",
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
    "Simulação Institucional / Backtesting — página dedicada M-VIS-036 (read-only).",
    "Walk-forward com corte temporal: concurso X usa apenas dados até X-1.",
    "Janelas comparáveis: 10 / 20 / 30 concursos.",
    "Execução automática de backtest com geração real — fora de escopo; missão futura.",
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

SIDE_LEAK_ML_045_MONITOR_ROWS: tuple[dict[str, str], ...] = (
    {
        "risco": "ML fora do CORE_002",
        "bloqueio": "BLK-ML-FREE-001",
        "descricao": "ML operacional somente com label STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    },
    {
        "risco": "ML sem batch_label soberano",
        "bloqueio": "BLK-ML-FREE-001",
        "descricao": "batch_label=None ou label não soberano rejeitado fail-closed",
    },
    {
        "risco": "ML via public_app",
        "bloqueio": "BLK-PUBLIC-APP-001",
        "descricao": "public_app não gera e não expõe ML operacional",
    },
    {
        "risco": "ML tentando operar Lei 15A",
        "bloqueio": "BLK-LEI15A-001",
        "descricao": "Lei 15A permanece futura/subordinada/inoperante",
    },
    {
        "risco": "ML tentando alterar Núcleo",
        "bloqueio": "BLK-CORE002-001",
        "descricao": "LEI15_CORE_002 soberano — ML subordinado, sem mutação de papéis/pesos",
    },
    {
        "risco": "ML sem decision trace",
        "bloqueio": "BLK-ML-NO-TRACE-001",
        "descricao": "Persistência PostgreSQL exige trace/attribution/lineage no context_json",
    },
    {
        "risco": "Rota legada _generate_direct_15_games",
        "bloqueio": "BLK-LEGACY-GEN-001",
        "descricao": "Geração legada bloqueada — path único generate_best_games",
    },
)

SIDE_LEAK_DOES_NOT: tuple[str, ...] = (
    "Não gera jogos.",
    "Não bloqueia banco sozinho.",
    "Não altera Núcleo.",
    "Não muda política.",
    "Não executa purge.",
    "Não ativa ML fora do CORE_002.",
    "Não substitui decisão institucional.",
)

EVOLUTION_HISTORICAL_NOTE = (
    "Evolução 13→14 / 14→15: evidência histórica e diagnóstica — sem promessa de acerto "
    "e sem recalibração automática."
)


def build_ml_assistive_snapshot() -> dict[str, Any]:
    """Snapshot institucional — reflete status operacional supervisionado quando ativo."""
    operational = is_adm_supervised_ml_active()
    activation = build_supervised_ml_activation_snapshot()
    return {
        "read_only_alert": ML_ASSISTIVE_OPERATIONAL_ALERT if operational else ML_ASSISTIVE_READ_ONLY_ALERT,
        "guardian_quote": GUARDIAN_OPERATIONAL_QUOTE if operational else GUARDIAN_ANALYTIC_QUOTE,
        "institutional_alerts": list(
            INSTITUTIONAL_ML_OPERATIONAL_ALERTS if operational else INSTITUTIONAL_ML_ALERTS
        ),
        "six_bases_quote": SIX_BASES_QUOTE,
        "separation_matrix": [
            dict(row)
            for row in (
                SEPARATION_MATRIX_OPERATIONAL_ROWS if operational else SEPARATION_MATRIX_ROWS
            )
        ],
        "ml_security_status": dict(
            ML_SECURITY_STATUS_OPERATIONAL if operational else ML_SECURITY_STATUS_READ_ONLY
        ),
        "ml_six_bases_relation": (
            build_ml_six_bases_operational_summary()
            if operational
            else [dict(row) for row in ML_SIX_BASES_RELATION]
        ),
        "future_simulation_prep": list(FUTURE_SIMULATION_PREP),
        "generation_cmd": False,
        "recalibration_cmd": False,
        "ml_operacional": operational,
        "ml_operational_status": supervised_ml_status_label(),
        "supervised_ml_activation": activation,
        "decision_trace_enabled": operational,
        "feature_attribution_enabled": operational,
        "ml_six_bases_enabled": operational,
    }


def build_constitutional_side_leak_snapshot() -> dict[str, Any]:
    """Snapshot read-only vazamento lateral — sem efeitos colaterais."""
    ml_monitoring = is_ml_operational_enabled()
    risk_rows = [dict(row) for row in SIDE_LEAK_RISK_ROWS]
    if ml_monitoring:
        risk_rows.extend(dict(row) for row in SIDE_LEAK_ML_045_MONITOR_ROWS)
    return {
        "read_only_alert": SIDE_LEAK_READ_ONLY_ALERT,
        "status": (
            "Diagnóstico constitucional read-only + monitoramento ML operacional CORE_002."
            if ml_monitoring
            else "Diagnóstico constitucional read-only."
        ),
        "definition": (
            "Diagnóstico de risco de uma política, lote, tela ou leitura produzir "
            "interpretação indevida ou operação fora do caminho soberano."
        ),
        "measures": (
            "sobra_real = cartao_final − resultado_oficial — dezena em cartão final "
            "e fora do resultado oficial."
        ),
        "risk_rows": risk_rows,
        "ml_045_monitor_rows": [dict(row) for row in SIDE_LEAK_ML_045_MONITOR_ROWS],
        "constitutional_blocks": [
            "BLK-CORE002-001",
            "BLK-LEI15A-001",
            "BLK-PURGE-001",
            "BLK-PUBLIC-APP-001",
            "BLK-LEGACY-GEN-001",
            "BLK-ML-FREE-001",
            "BLK-ML-NO-TRACE-001",
        ],
        "does_not": list(SIDE_LEAK_DOES_NOT),
        "generation_cmd": False,
        "recalibration_cmd": False,
        "ml_operacional_monitoring": ml_monitoring,
    }


def render_ml_assistive_governance_section() -> None:
    """Bloco institucional — Central ML Assistiva."""
    payload = build_ml_assistive_snapshot()
    operational = bool(payload.get("ml_operacional"))

    if operational:
        st.success(str(payload.get("ml_operational_status") or SUPERVISED_ML_STATUS_ACTIVE))
        st.info(ML_ASSISTIVE_OPERATIONAL_ALERT)
        st.caption(SUPERVISED_ML_GOVERNANCE_ALERT)
        st.caption(SUPERVISED_ML_DISCLAIMER)
    else:
        st.info(ML_ASSISTIVE_READ_ONLY_ALERT)

    for alert in payload["institutional_alerts"]:
        st.warning(alert)
    st.markdown(f"*{payload['guardian_quote']}*")
    st.markdown(f"*{SIX_BASES_QUOTE}*")

    st.markdown("##### Status de segurança ML")
    security_cols = st.columns(4)
    security_cols[0].metric("ML operacional", "True" if operational else "False")
    security_cols[1].metric("generation_cmd", "False")
    security_cols[2].metric("recalibration_cmd", "False")
    security_cols[3].metric("Decisão final", "Governança + trace" if operational else "Governança")
    st.dataframe(
        pd.DataFrame([{"campo": k, "valor": v} for k, v in payload["ml_security_status"].items()]),
        hide_index=True,
        use_container_width=True,
    )

    if operational:
        st.markdown("##### Decision trace / Feature attribution / Lineage")
        st.caption(
            "Leitura operacional em PostgreSQL — consulte o bloco "
            "**ML operacional supervisionado (PostgreSQL)** abaixo para o último evento persistido."
        )
        activation = dict(payload.get("supervised_ml_activation") or {})
        st.caption(
            f"missão={activation.get('mission_id')} | batch_label={activation.get('batch_label')} | "
            f"persistência={activation.get('persistence')}"
        )

    st.markdown("##### Separação: diagnóstico → operação")
    st.dataframe(
        pd.DataFrame(payload["separation_matrix"]),
        hide_index=True,
        use_container_width=True,
    )

    section_title = (
        "##### ML × 6 Bases (operacional supervisionado)"
        if operational
        else "##### ML × 6 Bases (assistivo — não decide sozinho)"
    )
    st.markdown(section_title)
    st.dataframe(
        pd.DataFrame(payload["ml_six_bases_relation"]),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "O ML ajuda a ler as 6 Bases dentro do CORE_002, mas não decide sozinho."
        if operational
        else "O ML pode ajudar a ler as 6 Bases, mas não decide sozinho."
    )

    st.markdown("##### Integração — Simulação Institucional (M-VIS-036)")
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
    if payload.get("ml_operacional_monitoring"):
        st.markdown("##### Monitoramento ML operacional (M-ML-045)")
        st.caption(
            "Bloqueios ativos: BLK-ML-FREE-001 (ML livre proibido), "
            "BLK-ML-NO-TRACE-001 (ML sem rastreabilidade proibido)."
        )
        st.dataframe(
            pd.DataFrame(payload.get("ml_045_monitor_rows") or []),
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


def render_supervised_ml_operational_panel(
    db_path: Any,
    *,
    selected_generation_event_id: int | None = None,
) -> dict[str, Any]:
    """Painel operacional supervisionado — leitura PostgreSQL (M-ML-VIS-053)."""
    payload = build_supervised_ml_operational_panel_snapshot(
        db_path,
        generation_event_id=selected_generation_event_id,
    )
    st.markdown("### ML operacional supervisionado (PostgreSQL)")
    st.caption(
        f"Fonte: `{payload.get('source')}` | Tabelas: `{payload.get('tables')}` | "
        f"Missão: `{payload.get('mission_id')}`"
    )

    if payload.get("ml_operational_active"):
        st.success(str(payload.get("ml_operational_status") or SUPERVISED_ML_STATUS_ACTIVE))
    else:
        st.warning(str(payload.get("ml_operational_status") or "BLOQUEADO"))

    status_cols = st.columns(4)
    status_cols[0].metric("CORE_002", "ativo" if payload.get("ml_operational_active") else "bloqueado")
    status_cols[1].metric("ml_enabled", "True" if payload.get("ml_operational_active") else "False")
    status_cols[2].metric("public_app ML", "False")
    status_cols[3].metric("Lei 15A", "inoperante")

    guard_cols = st.columns(2)
    guard_cols[0].metric("generation_cmd", "False")
    guard_cols[1].metric("recalibration_cmd", "False")

    st.markdown("##### Bloqueios constitucionais ML")
    st.dataframe(
        pd.DataFrame([{"bloqueio": code} for code in payload.get("constitutional_blocks") or CONSTITUTIONAL_BLOCKS]),
        hide_index=True,
        use_container_width=True,
    )

    events = list(payload.get("events") or [])
    if not events:
        st.warning(str(payload.get("empty_message") or EMPTY_ML_EVENTS_MESSAGE))
        return payload

    event_labels = [
        (
            f"GE {int(row.get('generation_event_id', 0) or 0)} — "
            f"{row.get('batch_label', '-')} — "
            f"{int(row.get('persisted_games', 0) or 0)} jogos — "
            f"ml_scored={int(row.get('ml_scored_games', 0) or 0)}"
        )
        for row in events
    ]
    label_to_id = {
        label: int(row.get("generation_event_id", 0) or 0)
        for label, row in zip(event_labels, events, strict=True)
    }
    default_index = 0
    selected_id = int(payload.get("selected_generation_event_id") or events[0].get("generation_event_id") or 0)
    for index, row in enumerate(events):
        if int(row.get("generation_event_id", 0) or 0) == selected_id:
            default_index = index
            break
    selected_label = st.selectbox(
        "Últimos eventos ML operacionais",
        options=event_labels,
        index=default_index,
        key="central_ml_operational_event_select",
    )
    resolved_id = int(label_to_id.get(selected_label, selected_id) or selected_id)
    selected_event = build_supervised_ml_operational_event_detail(db_path, resolved_id)

    if not isinstance(selected_event, dict):
        st.info("Evento ML selecionado sem detalhe disponível no PostgreSQL.")
        return payload

    meta_cols = st.columns(5)
    meta_cols[0].metric("generation_event_id", str(selected_event.get("generation_event_id", "-")))
    meta_cols[1].metric("batch_label", str(selected_event.get("batch_label", "-"))[:28])
    meta_cols[2].metric("Jogos persistidos", int(selected_event.get("persisted_games", 0) or 0))
    meta_cols[3].metric("Jogos pontuados", int(selected_event.get("ml_scored_games", 0) or 0))
    meta_cols[4].metric("Formato", f"{int(selected_event.get('card_format', 15) or 15)}D")
    detail_cols = st.columns(4)
    detail_cols[0].write(f"ml_enabled: `{bool(selected_event.get('ml_enabled'))}`")
    detail_cols[1].write(f"requested_count: `{int(selected_event.get('requested_count', 0) or 0)}`")
    detail_cols[2].write(f"missão: `{selected_event.get('supervised_ml_mission', '-')}`")
    detail_cols[3].write(f"created_at: `{selected_event.get('created_at', '-')}`")

    trace = dict(selected_event.get("decision_trace") or {})
    st.markdown("##### Decision Trace")
    if trace.get("status") == "persistido":
        st.caption(f"Status: persistido | jogos com trace: {int(trace.get('total_jogos', 0) or 0)}")
        sample = dict(trace.get("sample") or {})
        st.dataframe(
            pd.DataFrame(
                [
                    {"campo": key, "valor": str(value)}
                    for key, value in sample.items()
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Decision trace ausente neste evento — fallback controlado sem quebra de página.")

    attribution = dict(selected_event.get("feature_attribution") or {})
    st.markdown("##### Feature Attribution")
    if attribution.get("status") == "persistido":
        st.caption(f"Status: persistido | jogos: {int(attribution.get('total_jogos', 0) or 0)}")
        sample = dict(attribution.get("sample") or {})
        if sample:
            st.json(sample)
        top_factors = list(attribution.get("top_factors") or [])
        if top_factors:
            st.dataframe(pd.DataFrame(top_factors), hide_index=True, use_container_width=True)
    else:
        st.info("Feature attribution ausente neste evento — fallback controlado sem quebra de página.")

    st.markdown("##### ML × 6 Bases")
    six_bases = list(selected_event.get("ml_six_bases_reading") or [])
    if six_bases:
        st.dataframe(pd.DataFrame(six_bases), hide_index=True, use_container_width=True)
        st.caption("Hit isolado não é veredicto — leitura supervisionada das seis bases.")
    else:
        st.info("ML × 6 Bases ausente — exibindo template operacional.")
        st.dataframe(
            pd.DataFrame(build_ml_six_bases_operational_summary()),
            hide_index=True,
            use_container_width=True,
        )

    st.caption(SUPERVISED_ML_GOVERNANCE_ALERT)
    st.caption(SUPERVISED_ML_DISCLAIMER)
    return payload
