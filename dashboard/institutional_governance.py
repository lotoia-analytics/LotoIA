"""Bloco read-only de Governança Institucional no Painel ADM — M-VIS-032."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st

from dashboard.institutional_build import LOTOIA_PANEL_PRODUCTION_URL

GOVERNANCE_READ_ONLY_ALERT = (
    "Governança read-only — nenhuma ação operacional é executada nesta tela."
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOCS = REPO_ROOT / "docs" / "governance"
GESTAO_PROJETOS_DIR = GOVERNANCE_DOCS / "gestao_projetos"

MISSION_ROWS: tuple[dict[str, str], ...] = (
    {
        "id": "M-GOV-030",
        "titulo": "Gestão de Projetos — Fase 0",
        "status": "CONCLUIDA",
        "agentes": "agent_governanca + agent_plataforma",
        "evidencia": "PR #121 — merge 7a10363",
    },
    {
        "id": "M-OPS-INC-001",
        "titulo": "Incidente deploy — artefato não versionado",
        "status": "CONCLUIDA",
        "agentes": "agent_plataforma + agent_governanca",
        "evidencia": "hotfix f0c1261 — build v6",
    },
    {
        "id": "M-VIS-031",
        "titulo": "Painel ADM Fase 1 — bloqueios constitucionais",
        "status": "CONCLUIDA / VALIDADA EM PRODUÇÃO",
        "agentes": "agent_visual + agent_plataforma",
        "evidencia": "PR #125 — merge a5a3f2f — PR #126 fechamento 510cccb",
    },
    {
        "id": "M-VIS-032",
        "titulo": "Governança read-only no Painel ADM",
        "status": "EM EXECUCAO / AGUARDANDO REVIEW",
        "agentes": "agent_visual + agent_governanca + agent_plataforma",
        "evidencia": "branch cursor/m-vis-032-governanca-read-only-cae6",
    },
)

BLOCK_ROWS: tuple[dict[str, str], ...] = (
    {
        "codigo": "BLK-GERACAO-001",
        "descricao": "Geração soberana bloqueada — Gerador ADM CORE_002 inoperante",
        "estado": "ATIVO — mitigado M-VIS-031",
    },
    {
        "codigo": "BLK-PURGE-001",
        "descricao": "Limpeza Controlada bloqueada — histórico protegido",
        "estado": "ATIVO — mitigado M-VIS-031",
    },
    {
        "codigo": "BLK-ADM-001",
        "descricao": "Rotas ADM órfãs / status constitucional — Fase 1 defensiva",
        "estado": "ATIVO — mitigado M-VIS-031",
    },
    {
        "codigo": "BLK-DEPLOY-001",
        "descricao": "Deploy manual fora do fluxo Git/Railway",
        "estado": "REMOVIDO — monitoramento M-OPS-INC-001",
    },
)

LAW_ROWS: tuple[dict[str, str], ...] = (
    {
        "nome": "Lei 001",
        "referencia": "Fonte única da verdade — PostgreSQL operacional",
        "path": "docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md",
    },
    {
        "nome": "Lei 15",
        "referencia": "Núcleo operacional 15D — LEI15_CORE_002 soberano",
        "path": "docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md",
    },
    {
        "nome": "ADR-047",
        "referencia": "Transição constitucional pós-auditoria — geração bloqueada",
        "path": "docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md",
    },
    {
        "nome": "Política ML assistivo",
        "referencia": "ML auxiliar — sem efeito operacional automático",
        "path": "docs/governance/POLITICA_ML_ASSISTIVO.md",
    },
    {
        "nome": "Política de Preservação de Histórico",
        "referencia": "Purge protegido — evidência institucional",
        "path": "docs/governance/POLITICA_PRESERVACAO_HISTORICO_LOTOIA.md",
    },
    {
        "nome": "Política de Gestão de Projetos",
        "referencia": "Fase 0 documental — missões e veredictos",
        "path": "docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md",
    },
    {
        "nome": "Inventário Painel ADM",
        "referencia": "PR #124 — merge 328d26f — read-only conceitual",
        "path": "docs/governance/INVENTARIO_REDesenHO_CONCEITUAL_PAINEL_ADM_LEI15_CORE002.md",
    },
)

VERDICT_ROWS: tuple[dict[str, str], ...] = (
    {
        "veredicto": "M-VIS-031 FECHADA FORMALMENTE — PAINEL ADM FASE 1 VALIDADO EM PRODUÇÃO",
        "origem": "PR #126 — merge 510cccb",
    },
    {
        "veredicto": "M-GOV-030 FECHADA FORMALMENTE — GESTÃO DE PROJETOS FASE 0 APROVADA EM MAIN",
        "origem": "PR #121 — merge 7a10363",
    },
    {
        "veredicto": "LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL",
        "origem": "Auditoria constitucional 2026-06-17 — M-GOV-027",
    },
    {
        "veredicto": "ADR-047 — TRANSIÇÃO CONSTITUCIONAL REGISTRADA",
        "origem": "LEI15_CORE_002 — geração bloqueada até missão autorizada",
    },
)


def _read_doc_excerpt(relative_path: str, *, max_lines: int = 14) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        return f"(documento não encontrado: {relative_path})"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[:max_lines]).strip()


def _doc_exists(relative_path: str) -> bool:
    return (REPO_ROOT / relative_path).exists()


def build_governance_snapshot(
    *,
    app_build: str,
    active_commit: str,
    generation_blocked: bool,
    inventory_reference: str,
) -> dict[str, Any]:
    """Snapshot read-only para testes e renderização — sem efeitos colaterais."""
    railway_commit = (
        os.getenv("RAILWAY_GIT_COMMIT_SHA")
        or os.getenv("RAILWAY_GIT_COMMIT")
        or os.getenv("GIT_COMMIT")
        or "-"
    )
    return {
        "read_only_alert": GOVERNANCE_READ_ONLY_ALERT,
        "gestao_projetos_fase": "Fase 0 — documental/Git",
        "gestao_projetos_policy_status": "POLITICA_GESTAO_PROJETOS_FASE_0_FORMALIZADA",
        "missions": [dict(row) for row in MISSION_ROWS],
        "next_authorized_mission": "M-VIS-032",
        "blocks": [dict(row) for row in BLOCK_ROWS],
        "laws": [
            {**dict(row), "disponivel": _doc_exists(row["path"])} for row in LAW_ROWS
        ],
        "veredicts": [dict(row) for row in VERDICT_ROWS],
        "generation_status": "BLOQUEADA" if generation_blocked else "HABILITADA",
        "purge_status": "PROTEGIDO",
        "git_railway": {
            "build": app_build,
            "commit_ativo": active_commit,
            "railway_commit_env": railway_commit[:12] if railway_commit != "-" else "-",
            "production_url": LOTOIA_PANEL_PRODUCTION_URL,
            "railway_service": os.getenv("RAILWAY_SERVICE_NAME", "-"),
            "railway_environment": os.getenv("RAILWAY_ENVIRONMENT", "-"),
            "deploy_mode": "GitHub → Railway (sem deploy manual nesta tela)",
        },
        "inventory_reference": inventory_reference,
        "quadro_excerpt": _read_doc_excerpt("docs/governance/gestao_projetos/QUADRO_PROJETOS_MISSOES.md"),
        "registro_excerpt": _read_doc_excerpt(
            "docs/governance/gestao_projetos/REGISTRO_MISSOES_INSTITUCIONAL.md",
            max_lines=18,
        ),
        "policy_excerpt": _read_doc_excerpt("docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md"),
    }


def render_governance_read_only_page(
    *,
    snapshot: dict[str, Any],
    app_build: str,
    active_commit: str,
    generation_blocked: bool,
    inventory_reference: str,
    render_constitutional_panel: Callable[..., None],
    render_diagnostic_caption: Callable[[], None],
) -> None:
    """Renderiza a área de Governança Institucional — somente leitura."""
    _ = snapshot
    payload = build_governance_snapshot(
        app_build=app_build,
        active_commit=active_commit,
        generation_blocked=generation_blocked,
        inventory_reference=inventory_reference,
    )

    st.subheader("Governança Institucional — read-only")
    st.info(GOVERNANCE_READ_ONLY_ALERT)
    render_diagnostic_caption()

    tab_gestao, tab_missoes, tab_bloqueios, tab_leis, tab_git = st.tabs(
        [
            "Gestão de Projetos — Fase 0",
            "Missões institucionais",
            "Bloqueios ativos",
            "Leis e ADRs",
            "Git / Railway",
        ]
    )

    with tab_gestao:
        st.markdown("##### Gestão de Projetos — Fase 0")
        st.markdown(
            f"**Modo:** `{payload['gestao_projetos_fase']}`  \n"
            f"**Política:** `{payload['gestao_projetos_policy_status']}`"
        )
        st.markdown("**Excerto — Política de Gestão de Projetos**")
        st.code(payload["policy_excerpt"], language="markdown")
        st.markdown("**Excerto — Quadro de Projetos e Missões**")
        st.code(payload["quadro_excerpt"], language="markdown")
        st.markdown("**Excerto — Registro Institucional de Missões**")
        st.code(payload["registro_excerpt"], language="markdown")
        st.caption(
            "Documentos lidos do repositório versionado — sem edição, merge ou deploy pelo painel."
        )

    with tab_missoes:
        st.markdown("##### Missões recentes")
        st.dataframe(
            pd.DataFrame(payload["missions"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown(
            f"**Próxima missão autorizada / em execução:** `{payload['next_authorized_mission']}`"
        )
        st.markdown("##### Veredictos constitucionais relevantes")
        st.dataframe(
            pd.DataFrame(payload["veredicts"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("##### Confirmação operacional")
        gen_status = payload["generation_status"]
        purge_status = payload["purge_status"]
        if gen_status == "BLOQUEADA":
            st.success(f"Geração: **{gen_status}** (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`)")
        else:
            st.error(f"Geração: **{gen_status}** — estado inesperado na Fase 1 ADM")
        st.success(f"Purge / histórico: **{purge_status}**")

    with tab_bloqueios:
        st.markdown("##### Bloqueios institucionais")
        st.dataframe(
            pd.DataFrame(payload["blocks"]),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Exibição informativa — nenhum bloqueio é alterado nesta tela.")

    with tab_leis:
        st.markdown("##### Leis, ADRs e políticas principais")
        law_rows = []
        for row in payload["laws"]:
            law_rows.append(
                {
                    "documento": row["nome"],
                    "referencia": row["referencia"],
                    "path": row["path"],
                    "versionado": "sim" if row["disponivel"] else "ausente",
                }
            )
        st.dataframe(pd.DataFrame(law_rows), hide_index=True, use_container_width=True)
        st.caption(f"Inventário Painel ADM: {inventory_reference}")

    with tab_git:
        st.markdown("##### Git / Railway — informativo")
        git_info = payload["git_railway"]
        info_cols = st.columns(3)
        info_cols[0].metric("Build ativo", git_info["build"])
        info_cols[1].metric("Commit ativo", git_info["commit_ativo"])
        info_cols[2].metric("Commit Railway (env)", git_info["railway_commit_env"])
        st.markdown(
            f"- **URL produção:** `{git_info['production_url']}`\n"
            f"- **Serviço Railway:** `{git_info['railway_service']}`\n"
            f"- **Ambiente Railway:** `{git_info['railway_environment']}`\n"
            f"- **Modo deploy:** {git_info['deploy_mode']}"
        )
        st.caption("Sem chamada de API externa destrutiva e sem execução de deploy.")

    st.markdown("---")
    render_constitutional_panel(compact=False)
