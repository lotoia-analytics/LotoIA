"""Inventário de rotas do Painel ADM — órfãs, legadas e aliases (M-PLAT-040)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

ROUTE_INVENTORY_ALERT = (
    "Inventário de rotas read-only — nenhuma rota é alterada, removida ou executada nesta seção."
)

ROUTE_INVENTORY_MISSION = "M-PLAT-040"

LEGACY_PAGE_ALIASES: dict[str, str] = {
    "generation": "clean_law15_generation",
    "clear_histories": "restricted_controlled_cleanup",
    "delete_history": "restricted_controlled_cleanup",
}

INSTITUTIONAL_ALLOWED_PAGES: frozenset[str] = frozenset(
    {
        "home",
        "fallback",
        "governance_read_only",
        "core_002_read_only",
        "clean_law15_generation",
        "conference",
        "simulation",
        "history_analytical",
        "history_institutional",
        "comparative_history",
        "audit",
        "audit_monitoring_conference",
        "audit_monitoring_missing_numbers",
        "audit_monitoring_extra_numbers",
        "summary_benchmark",
        "hb_metrics",
        "structural_coverage",
        "institutional_simulation_backtesting",
        "audit_monitoring_side_leak",
        "audit_monitoring_13_to_14",
        "audit_monitoring_14_to_15",
        "central_ml_diagnostics",
        "restricted_controlled_cleanup",
    }
)

ACTIVE_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {"page_id": "governance_read_only", "label": "Governança Institucional — read-only", "grupo": "Governança"},
    {"page_id": "core_002_read_only", "label": "Núcleo Lei 15 — CORE_002", "grupo": "Governança"},
    {"page_id": "home", "label": "Painel Inicial Institucional", "grupo": "Núcleo Operacional"},
    {
        "page_id": "conference",
        "label": "Conferir Resultados — Auditoria de Lotes Persistidos",
        "grupo": "Núcleo Operacional",
    },
    {"page_id": "simulation", "label": "Simular Resultados", "grupo": "Núcleo Operacional"},
    {"page_id": "structural_coverage", "label": "Cobertura Estrutural", "grupo": "Analítico observacional"},
    {
        "page_id": "institutional_simulation_backtesting",
        "label": "Simulação Institucional / Backtesting",
        "grupo": "Analítico observacional",
    },
    {"page_id": "central_ml_diagnostics", "label": "Central ML Assistiva", "grupo": "Diagnósticos ML"},
    {
        "page_id": "audit_monitoring_side_leak",
        "label": "Vazamento Lateral Constitucional",
        "grupo": "Diagnósticos ML",
    },
    {
        "page_id": "restricted_controlled_cleanup",
        "label": "Área Restrita — Limpeza Controlada",
        "grupo": "Área Restrita",
    },
)

BLOCKED_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {
        "page_id": "clean_law15_generation",
        "label": "Gerador ADM CORE_002 — Geração Soberana Controlada",
        "motivo": "Geração soberana controlada ativa — path generate_best_games (M-GER-044)",
    },
)

ALIAS_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {
        "alias": "generation",
        "destino": "clean_law15_generation",
        "motivo": "Rota órfã legada — redireciona para gerador bloqueado sem geração",
    },
    {
        "alias": "Gerar Jogos",
        "destino": "clean_law15_generation",
        "motivo": "Label legado — não expõe path de geração direta",
    },
    {
        "alias": "clear_histories",
        "destino": "restricted_controlled_cleanup",
        "motivo": "Alias M-DADOS-039 — limpeza de sessão sem purge",
    },
    {
        "alias": "delete_history",
        "destino": "restricted_controlled_cleanup",
        "motivo": "Alias M-DADOS-039 — purge real bloqueado",
    },
    {
        "alias": "Apagar Histórico",
        "destino": "restricted_controlled_cleanup",
        "motivo": "Label ambíguo substituído por Área Restrita",
    },
    {
        "alias": "Limpar Históricos",
        "destino": "restricted_controlled_cleanup",
        "motivo": "Label ambíguo — redireciona para limpeza controlada",
    },
)

REMOVED_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {"page_id": "strategies_analysis", "label": "Análises Estratégicas", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "strategies_test", "label": "Testar Estratégias", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "strategies_simulation", "label": "Simular Estratégias", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "institutional_replay", "label": "Replay institucional", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "operational_statistics", "label": "Estatísticas operacionais", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "hb_geometry", "label": "HB Geometry", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "audit_monitoring", "label": "Auditoria e Monitoramento", "estado": "REMOVIDA DO MENU — sub-rotas ativas"},
    {
        "page_id": "audit_monitoring_group_performance",
        "label": "Desempenho por grupo",
        "estado": "REMOVIDA DO MENU — fallback",
    },
    {
        "page_id": "audit_monitoring_offline_hypotheses",
        "label": "Hipóteses para teste offline",
        "estado": "REMOVIDA DO MENU — fallback",
    },
)

PENDING_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {
        "page_id": "lei15a_operational",
        "label": "Lei 15A operacional (legado)",
        "estado": "PENDENTE — camada futura inoperante (M-GOV-038); sem rota de menu",
    },
)

CONSTITUTIONAL_LABELS: tuple[str, ...] = (
    "Governança Institucional — read-only",
    "Núcleo Lei 15 — CORE_002",
    "Cobertura Estrutural",
    "Central ML Assistiva",
    "Vazamento Lateral Constitucional",
    "Simulação Institucional / Backtesting",
    "Conferir Resultados — Auditoria de Lotes Persistidos",
    "Área Restrita — Limpeza Controlada",
    "Lei 15A — Camada futura inoperante (via Governança)",
    "Gerador ADM CORE_002 — Geração Soberana Controlada",
)

ROUTE_GUARDS: tuple[str, ...] = (
    "Nenhuma rota legada chama generate_best_games diretamente.",
    "Nenhuma rota legada chama _generate_direct_15_games.",
    "batch_label=None rejeitado no path ADM (M-LEI15-003).",
    "Purge real bloqueado — aliases delete_history/clear_histories → Área Restrita.",
    "public_app fora do escopo deste inventário.",
)


def resolve_institutional_page_id(page_id: str) -> str:
    """Aplica aliases legados seguros após canonicalização."""
    normalized = str(page_id or "").strip()
    if not normalized:
        return "home"
    return LEGACY_PAGE_ALIASES.get(normalized, normalized)


def is_allowed_institutional_page(page_id: str) -> bool:
    resolved = resolve_institutional_page_id(page_id)
    return resolved in INSTITUTIONAL_ALLOWED_PAGES


def build_route_inventory_snapshot(*, app_build: str) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": ROUTE_INVENTORY_ALERT,
        "mission_id": ROUTE_INVENTORY_MISSION,
        "app_build": app_build,
        "active_routes": [dict(row) for row in ACTIVE_ROUTE_ROWS],
        "blocked_routes": [dict(row) for row in BLOCKED_ROUTE_ROWS],
        "alias_routes": [dict(row) for row in ALIAS_ROUTE_ROWS],
        "removed_routes": [dict(row) for row in REMOVED_ROUTE_ROWS],
        "pending_routes": [dict(row) for row in PENDING_ROUTE_ROWS],
        "constitutional_labels": list(CONSTITUTIONAL_LABELS),
        "route_guards": list(ROUTE_GUARDS),
        "allowed_pages_count": len(INSTITUTIONAL_ALLOWED_PAGES),
        "legacy_aliases": dict(LEGACY_PAGE_ALIASES),
        "inventory_doc": "docs/governance/INVENTARIO_ROTAS_PAINEL_ADM_M_PLAT_040.md",
    }


def render_route_inventory_section(*, app_build: str) -> None:
    """Bloco read-only — inventário de rotas ADM."""
    payload = build_route_inventory_snapshot(app_build=app_build)

    st.markdown("##### Inventário de Rotas — Painel ADM (M-PLAT-040)")
    st.info(ROUTE_INVENTORY_ALERT)
    st.caption(f"Build: `{app_build}` — documento: `{payload['inventory_doc']}`")

    tab_ativas, tab_bloqueadas, tab_aliases, tab_removidas, tab_guardas = st.tabs(
        ["Rotas ativas", "Rotas bloqueadas", "Aliases seguros", "Removidas do menu", "Guardas"]
    )

    with tab_ativas:
        st.dataframe(pd.DataFrame(payload["active_routes"]), hide_index=True, use_container_width=True)
        st.markdown("##### Labels constitucionais padronizados")
        for label in CONSTITUTIONAL_LABELS:
            st.markdown(f"- {label}")

    with tab_bloqueadas:
        st.dataframe(pd.DataFrame(payload["blocked_routes"]), hide_index=True, use_container_width=True)

    with tab_aliases:
        st.dataframe(pd.DataFrame(payload["alias_routes"]), hide_index=True, use_container_width=True)

    with tab_removidas:
        st.dataframe(pd.DataFrame(payload["removed_routes"]), hide_index=True, use_container_width=True)
        if payload["pending_routes"]:
            st.markdown("##### Pendências institucionais")
            st.dataframe(pd.DataFrame(payload["pending_routes"]), hide_index=True, use_container_width=True)

    with tab_guardas:
        for guard in ROUTE_GUARDS:
            st.markdown(f"- {guard}")
        st.success(
            f"Páginas permitidas no menu: `{payload['allowed_pages_count']}`. "
            "Rotas fora do conjunto caem em fallback institucional."
        )
