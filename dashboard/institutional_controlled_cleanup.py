"""Área Restrita — Limpeza Controlada protegida pela Lei 001 (M-DADOS-039)."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from lotoia.governance.history_preservation_policy import (
    GENERIC_PURGE_BLOCKED_TABLES,
    REGISTRY_ID,
    get_protected_batch_labels,
)

CONTROLLED_CLEANUP_READ_ONLY_ALERT = (
    "Área Restrita — Limpeza Controlada. Separa limpeza de sessão, cache visual e "
    "purge real. Histórico institucional persistido permanece protegido pela Lei 001."
)

CONTROLLED_CLEANUP_MANDATORY_QUOTE = (
    "Limpeza de sessão não é purge. Purge real é operação crítica, protegida pela "
    "Lei 001, e não pode apagar evidência institucional sem missão específica, "
    "dry-run, guarda por label e autorização."
)

LEI_001_GUARD = (
    "Lei 001 — PostgreSQL é a fonte soberana da verdade. Histórico institucional "
    "persistido não pode ser apagado por botão simples no Painel ADM."
)

INSTITUTIONAL_ALERTS: tuple[str, ...] = (
    "Limpeza de sessão não apaga PostgreSQL.",
    "Cache e tela podem ser limpos sem afetar verdade operacional.",
    "Purge real permanece BLOQUEADO nesta missão.",
    "Dry-run é o único caminho futuro aceitável para limpeza controlada.",
    "Autorização dual (agent_dados + agent_governanca) exigida para purge futuro.",
)

CLEANUP_SEPARATION_ROWS: tuple[dict[str, str], ...] = (
    {
        "tipo": "Limpeza de sessão",
        "escopo": "session_state institucional, estados visuais da UI",
        "persistencia": "Não altera PostgreSQL",
        "purge": "Não — permitido",
    },
    {
        "tipo": "Limpeza visual / cache local",
        "escopo": "st.cache_data, renderização, chaves efêmeras",
        "persistencia": "Não altera PostgreSQL",
        "purge": "Não — permitido",
    },
    {
        "tipo": "Dry-run limpeza controlada",
        "escopo": "scripts/ops/dry_run_history_cleanup_lotoia.py",
        "persistencia": "Somente diagnóstico — sem DELETE",
        "purge": "Não — único caminho futuro",
    },
    {
        "tipo": "Purge real",
        "escopo": "DELETE em tabelas operacionais/institucionais",
        "persistencia": "Alteraria PostgreSQL",
        "purge": "BLOQUEADO",
    },
)

PROTECTED_EVIDENCE_ROWS: tuple[dict[str, str], ...] = (
    {"artefato": "generation_events", "papel": "Evidência institucional de geração"},
    {"artefato": "generated_games", "papel": "Jogos persistidos — trilha auditável"},
    {"artefato": "imported_contests", "papel": "Base soberana de concursos oficiais"},
    {"artefato": "scientific_institutional_memory", "papel": "Memória institucional científica"},
    {"artefato": "scientific_calibration_decisions", "papel": "Memória científica / calibração"},
    {"artefato": "institutional_output_signatures", "papel": "Assinaturas de output institucional"},
    {"artefato": "reconciliation_runs", "papel": "Trilha de conferência persistida"},
    {"artefato": "reconciliation_games", "papel": "Detalhe jogo-a-jogo da conferência"},
    {"artefato": "lotes soberanos (batch_label)", "papel": "Identificadores protegidos por guarda de label"},
    {"artefato": "evidência de missões", "papel": "Registros Git / governança — não apagáveis por UI"},
)

DRY_RUN_REQUIREMENTS: tuple[str, ...] = (
    "Missão institucional específica autorizada.",
    "Backup verificável antes de qualquer DELETE.",
    "Dry-run obrigatório via script ops (sem execução real no painel).",
    "Guarda por batch_label — label desconhecido preserva (fail-closed).",
    "Autorização dual: agent_dados + agent_governanca.",
    "ADR ou registro de governança quando aplicável.",
)

PURGE_PROHIBITIONS: tuple[str, ...] = (
    "Não deleta generation_events.",
    "Não deleta generated_games.",
    "Não deleta imported_contests.",
    "Não deleta memória científica ou institucional.",
    "Não deleta output signatures.",
    "Não executa purge real pelo painel.",
    "Não transforma dry-run em execução real.",
    "Não usa confirmação simples para purge real.",
)

DRY_RUN_SCRIPT = "scripts/ops/dry_run_history_cleanup_lotoia.py"
PRESERVATION_POLICY_DOC = "docs/governance/POLITICA_PRESERVACAO_HISTORICO_LOTOIA.md"


def build_controlled_cleanup_snapshot(
    *,
    table_counts: dict[str, int] | None = None,
    table_latest: dict[str, str] | None = None,
    session_institutional_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    counts = table_counts or {}
    latest = table_latest or {}
    protected_labels = sorted(get_protected_batch_labels())
    protected_tables = sorted(GENERIC_PURGE_BLOCKED_TABLES)
    diagnostic_rows = [
        {
            "tabela": table,
            "contagem": int(counts.get(table, 0) or 0),
            "ultima_persistencia": str(latest.get(table, "-") or "-"),
            "purge_generico": "BLOQUEADO",
        }
        for table in protected_tables
    ]
    return {
        "read_only_alert": CONTROLLED_CLEANUP_READ_ONLY_ALERT,
        "mandatory_quote": CONTROLLED_CLEANUP_MANDATORY_QUOTE,
        "lei_001_guard": LEI_001_GUARD,
        "institutional_alerts": list(INSTITUTIONAL_ALERTS),
        "cleanup_separation": [dict(row) for row in CLEANUP_SEPARATION_ROWS],
        "protected_evidence": [dict(row) for row in PROTECTED_EVIDENCE_ROWS],
        "dry_run_requirements": list(DRY_RUN_REQUIREMENTS),
        "purge_prohibitions": list(PURGE_PROHIBITIONS),
        "purge_real_status": "BLOQUEADO",
        "dry_run_status": "OBRIGATÓRIO PARA LIMPEZA FUTURA",
        "history_status": "PROTEGIDO",
        "preservation_registry": REGISTRY_ID,
        "dry_run_script": DRY_RUN_SCRIPT,
        "preservation_policy_doc": PRESERVATION_POLICY_DOC,
        "protected_tables": protected_tables,
        "protected_labels_sample": protected_labels[:12],
        "protected_labels_total": len(protected_labels),
        "diagnostic_rows": diagnostic_rows,
        "session_institutional_keys": list(session_institutional_keys or []),
        "mission_id": "M-DADOS-039",
    }


def render_restricted_controlled_cleanup_page(
    *,
    table_counts: dict[str, int],
    table_latest: dict[str, str],
    session_institutional_keys: list[str],
    on_clear_session: Callable[[], None],
    on_clear_visual_cache: Callable[[], None],
    render_constitutional_panel: Callable[..., None],
    render_diagnostic_caption: Callable[[], None],
) -> None:
    """Área Restrita — Limpeza Controlada (read-only defensivo + limpeza de sessão)."""
    payload = build_controlled_cleanup_snapshot(
        table_counts=table_counts,
        table_latest=table_latest,
        session_institutional_keys=session_institutional_keys,
    )

    st.subheader("Área Restrita — Limpeza Controlada")
    st.info(CONTROLLED_CLEANUP_READ_ONLY_ALERT)
    for alert in INSTITUTIONAL_ALERTS:
        st.warning(alert)
    st.markdown(f"*{CONTROLLED_CLEANUP_MANDATORY_QUOTE}*")
    st.markdown(f"*{LEI_001_GUARD}*")
    render_diagnostic_caption()

    status_cols = st.columns(4)
    status_cols[0].metric("Lei 001", "SOBERANA")
    status_cols[1].metric("Purge real", payload["purge_real_status"])
    status_cols[2].metric("Dry-run futuro", payload["dry_run_status"])
    status_cols[3].metric("Histórico", payload["history_status"])

    tab_sessao, tab_protegido, tab_purge, tab_dryrun = st.tabs(
        [
            "Limpeza de Sessão",
            "Histórico Institucional Protegido",
            "Purge Real Bloqueado",
            "Dry-run Obrigatório",
        ]
    )

    with tab_sessao:
        st.markdown("##### Limpeza de Sessão")
        st.write(
            "Limpa apenas estados visuais e operacionais desta sessão (`session_state`, "
            "seleções de UI). **Não apaga PostgreSQL** nem evidência institucional."
        )
        st.caption(
            f"Chaves institucionais ativas: `{len(session_institutional_keys)}`"
        )
        st.code(
            "\n".join(session_institutional_keys) if session_institutional_keys else "-",
            language="text",
        )
        col_session, col_cache = st.columns(2)
        if col_session.button("Limpar session_state desta sessão", type="primary"):
            on_clear_session()
            st.success("Session_state institucional limpo — PostgreSQL intacto.")
            st.rerun()
        if col_cache.button("Limpar cache visual (st.cache_data)"):
            on_clear_visual_cache()
            st.success("Cache visual limpo — PostgreSQL intacto.")
            st.rerun()
        st.info("Limpeza de sessão ≠ purge. Verdade operacional permanece no PostgreSQL.")

    with tab_protegido:
        st.markdown("##### Histórico Institucional Protegido — Lei 001")
        st.dataframe(
            pd.DataFrame(payload["protected_evidence"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("##### Tabelas com purge genérico bloqueado")
        st.dataframe(
            pd.DataFrame(payload["diagnostic_rows"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown(
            f"**Labels/lotes protegidos (amostra — total `{payload['protected_labels_total']}`):**"
        )
        st.code(", ".join(payload["protected_labels_sample"]) or "-", language="text")
        st.caption(f"Política: `{PRESERVATION_POLICY_DOC}` — registro `{REGISTRY_ID}`.")

    with tab_purge:
        st.markdown("##### Purge Real — BLOQUEADO")
        st.error(
            "Operação bloqueada por Lei 001, ADR-047 e Política de Preservação de Histórico. "
            "Nenhum botão de purge real está disponível nesta área."
        )
        st.markdown("##### O que purge real **não** pode fazer agora")
        for item in PURGE_PROHIBITIONS:
            st.markdown(f"- {item}")
        render_constitutional_panel(compact=False)

    with tab_dryrun:
        st.markdown("##### Dry-run obrigatório para limpeza futura")
        st.markdown("##### Separação de tipos de limpeza")
        st.dataframe(
            pd.DataFrame(payload["cleanup_separation"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("##### Requisitos para qualquer purge futuro")
        for req in DRY_RUN_REQUIREMENTS:
            st.markdown(f"- {req}")
        st.info(
            f"Script de dry-run (somente diagnóstico): `{DRY_RUN_SCRIPT}`. "
            "Execução real exige missão própria — não disponível no painel."
        )
