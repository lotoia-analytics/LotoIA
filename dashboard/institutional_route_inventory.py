"""Inventário de rotas do Painel ADM — órfãs, legadas e aliases (M-PLAT-040 / M-VIS-057)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

ROUTE_INVENTORY_ALERT = (
    "Inventário de rotas read-only — nenhuma rota é alterada, removida ou executada nesta seção."
)

ROUTE_INVENTORY_MISSION = "M-PLAT-040"
MENU_CLEANUP_MISSION = "M-VIS-057"
MENU_UI_MISSION = "M-UI-MENU-001"

# Rotas permitidas mas ocultas do menu lateral (M-UI-MENU-001).
HIDDEN_SIDEBAR_PAGE_IDS: frozenset[str] = frozenset(
    {
        "governance_read_only",
        "restricted_controlled_cleanup",
        "central_ml_diagnostics",
    }
)

# Fallbacks seguros — rotas removidas do menu (M-VIS-057).
LEGACY_PAGE_ALIASES: dict[str, str] = {
    "generation": "clean_law15_generation",
    "clear_histories": "restricted_controlled_cleanup",
    "delete_history": "restricted_controlled_cleanup",
    "Central de Diagnósticos ML": "central_ml_diagnostics",
    "Central ML Assistiva": "central_ml_diagnostics",
    "central_ml": "central_ml_diagnostics",
    "ml_diagnostics": "central_ml_diagnostics",
    "institutional_supervised_ml": "central_ml_diagnostics",
    "ml_assistive": "central_ml_diagnostics",
    "core_002_read_only": "governance_read_only",
    "Núcleo Lei 15 — CORE_002": "governance_read_only",
    "comparative_history": "structural_coverage",
    "Comparativos histórico": "structural_coverage",
    "audit": "fallback",
    "Auditoria Runtime": "fallback",
    "audit_monitoring_conference": "conference",
    "Conferência por concurso": "conference",
    "audit_monitoring_missing_numbers": "structural_coverage",
    "Dezenas faltantes": "structural_coverage",
    "audit_monitoring_extra_numbers": "structural_coverage",
    "Dezenas sobrando": "structural_coverage",
    "summary_benchmark": "structural_coverage",
    "Benchmark resumido": "structural_coverage",
    "hb_metrics": "structural_coverage",
    "Métricas HB": "structural_coverage",
    "institutional_simulation_backtesting": "simulation",
    "Simulação Institucional / Backtesting": "simulation",
    "audit_monitoring_side_leak": "central_ml_diagnostics",
    "Vazamento Lateral Constitucional": "central_ml_diagnostics",
    "Vazamento lateral": "central_ml_diagnostics",
    "audit_monitoring_13_to_14": "central_ml_diagnostics",
    "Evolução 13 -> 14": "central_ml_diagnostics",
    "audit_monitoring_14_to_15": "central_ml_diagnostics",
    "Evolução 14 -> 15": "central_ml_diagnostics",
}

INSTITUTIONAL_ALLOWED_PAGES: frozenset[str] = frozenset(
    {
        "home",
        "fallback",
        "governance_read_only",
        "clean_law15_generation",
        "conference",
        "simulation",
        "history_analytical",
        "history_institutional",
        "structural_coverage",
        "central_ml_diagnostics",
        "restricted_controlled_cleanup",
    }
)

OFFICIAL_SIDEBAR_MENU: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Operacional",
        (
            ("Gerar Jogos", "clean_law15_generation"),
            ("Conferir Resultados", "conference"),
            ("Histórico Analítico", "history_analytical"),
            ("Cobertura Estrutural", "structural_coverage"),
            ("Simular Resultados", "simulation"),
        ),
    ),
    (
        "Análise",
        (
            ("Análise ML", "central_ml_diagnostics"),
        ),
    ),
    (
        "Referência",
        (
            ("Painel Inicial Institucional", "home"),
            ("Histórico Institucional", "history_institutional"),
        ),
    ),
)

ACTIVE_ROUTE_ROWS: tuple[dict[str, str], ...] = tuple(
    {"page_id": page_id, "label": label, "grupo": group_name}
    for group_name, entries in OFFICIAL_SIDEBAR_MENU
    for label, page_id in entries
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
    {
        "alias": "Central de Diagnósticos ML",
        "destino": "central_ml_diagnostics",
        "motivo": "Label legado — Central ML operacional supervisionada (M-ML-VIS-053B)",
    },
    {
        "alias": "Central ML Assistiva",
        "destino": "central_ml_diagnostics",
        "motivo": "M-VIS-057 — redireciona para Central ML Calibração Supervisionada",
    },
    {
        "alias": "ml_diagnostics",
        "destino": "central_ml_diagnostics",
        "motivo": "Alias legado — Central ML",
    },
    {
        "alias": "institutional_supervised_ml",
        "destino": "central_ml_diagnostics",
        "motivo": "Módulo interno — rota de menu central_ml_diagnostics",
    },
    {
        "alias": "institutional_simulation_backtesting",
        "destino": "simulation",
        "motivo": "M-VIS-057 — Simulação Institucional → Simular Resultados",
    },
    {
        "alias": "summary_benchmark",
        "destino": "structural_coverage",
        "motivo": "M-VIS-057 — Benchmark → Cobertura Estrutural",
    },
    {
        "alias": "hb_metrics",
        "destino": "structural_coverage",
        "motivo": "M-VIS-057 — Métricas HB → Cobertura Estrutural",
    },
    {
        "alias": "comparative_history",
        "destino": "structural_coverage",
        "motivo": "M-VIS-057 — Comparativos → Cobertura Estrutural",
    },
    {
        "alias": "audit_monitoring_conference",
        "destino": "conference",
        "motivo": "M-VIS-057 — Conferência por concurso → Conferir Resultados",
    },
    {
        "alias": "core_002_read_only",
        "destino": "governance_read_only",
        "motivo": "M-VIS-057 — Núcleo Lei 15 standalone → Governança Institucional",
    },
)

REMOVED_ROUTE_ROWS: tuple[dict[str, str], ...] = (
    {"page_id": "strategies_analysis", "label": "Análises Estratégicas", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "strategies_test", "label": "Testar Estratégias", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "strategies_simulation", "label": "Simular Estratégias", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "institutional_replay", "label": "Replay institucional", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "operational_statistics", "label": "Estatísticas operacionais", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "hb_geometry", "label": "HB Geometry", "estado": "REMOVIDA DO MENU — fallback"},
    {"page_id": "audit_monitoring", "label": "Auditoria e Monitoramento", "estado": "REMOVIDA DO MENU — sub-rotas redirecionadas"},
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
    {"page_id": "audit", "label": "Auditoria Runtime", "estado": "M-VIS-057 — removida do menu → fallback"},
    {"page_id": "core_002_read_only", "label": "Núcleo Lei 15 — CORE_002", "estado": "M-VIS-057 — removida → Governança Institucional"},
    {"page_id": "comparative_history", "label": "Comparativos histórico", "estado": "M-VIS-057 — removida → Cobertura Estrutural"},
    {"page_id": "summary_benchmark", "label": "Benchmark resumido", "estado": "M-VIS-057 — removida → Cobertura Estrutural"},
    {"page_id": "hb_metrics", "label": "Métricas HB", "estado": "M-VIS-057 — removida → Cobertura Estrutural"},
    {
        "page_id": "institutional_simulation_backtesting",
        "label": "Simulação Institucional / Backtesting",
        "estado": "M-VIS-057 — removida → Simular Resultados",
    },
    {
        "page_id": "audit_monitoring_conference",
        "label": "Conferência por concurso",
        "estado": "M-VIS-057 — removida → Conferir Resultados",
    },
    {
        "page_id": "audit_monitoring_missing_numbers",
        "label": "Dezenas faltantes",
        "estado": "M-VIS-057 — removida → Cobertura Estrutural",
    },
    {
        "page_id": "audit_monitoring_extra_numbers",
        "label": "Dezenas sobrando",
        "estado": "M-VIS-057 — removida → Cobertura Estrutural",
    },
    {
        "page_id": "audit_monitoring_side_leak",
        "label": "Vazamento Lateral Constitucional",
        "estado": "M-VIS-057 — removida → Central ML",
    },
    {
        "page_id": "audit_monitoring_13_to_14",
        "label": "Evolução 13 → 14",
        "estado": "M-VIS-057 — removida → Central ML",
    },
    {
        "page_id": "audit_monitoring_14_to_15",
        "label": "Evolução 14 → 15",
        "estado": "M-VIS-057 — removida → Central ML",
    },
    {
        "page_id": "governance_read_only",
        "label": "Governança Institucional — read-only",
        "estado": "M-UI-MENU-001 — oculta do menu lateral; rota protegida permanece",
    },
    {
        "page_id": "restricted_controlled_cleanup",
        "label": "Área Restrita — Limpeza Controlada",
        "estado": "M-UI-MENU-001 — oculta do menu lateral; aliases seguros permanecem",
    },
    {
        "page_id": "central_ml_diagnostics",
        "label": "Central ML — Calibração Supervisionada",
        "estado": "M-OPS-079 — oculta do menu lateral; rota analítica opt-in permanece",
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
    "Gerar Jogos",
    "Conferir Resultados",
    "Simular Resultados",
    "Cobertura Estrutural",
    "Análise ML",
    "Histórico Analítico",
    "Histórico Institucional",
    "Painel Inicial Institucional",
    "Governança Institucional — read-only (oculta do menu)",
    "Área Restrita — Limpeza Controlada (oculta do menu)",
    "Lei 15A — Camada futura inoperante (via Governança)",
)

ROUTE_GUARDS: tuple[str, ...] = (
    "Nenhuma rota legada chama generate_best_games diretamente.",
    "Nenhuma rota legada chama _generate_direct_15_games.",
    "batch_label=None rejeitado no path ADM (M-LEI15-003).",
    "Purge real bloqueado — aliases delete_history/clear_histories → Área Restrita.",
    "public_app fora do escopo deste inventário.",
    "M-VIS-057 — menu lateral enxuto; rotas antigas redirecionam com fallback seguro.",
    "M-UI-MENU-001 — governança e status constitucional ocultos do menu operacional.",
    "M-OPS-079 — Central ML oculta do menu; ML opt-in via variável de ambiente.",
)


def official_sidebar_page_ids() -> frozenset[str]:
    return frozenset(page_id for _group, entries in OFFICIAL_SIDEBAR_MENU for _label, page_id in entries)


def resolve_institutional_page_id(page_id: str) -> str:
    """Aplica aliases legados seguros após canonicalização."""
    normalized = str(page_id or "").strip()
    if not normalized:
        return "home"
    resolved = LEGACY_PAGE_ALIASES.get(normalized, normalized)
    if resolved != normalized:
        return resolve_institutional_page_id(resolved)
    return resolved


def is_allowed_institutional_page(page_id: str) -> bool:
    resolved = resolve_institutional_page_id(page_id)
    return resolved in INSTITUTIONAL_ALLOWED_PAGES


def build_route_inventory_snapshot(*, app_build: str) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": ROUTE_INVENTORY_ALERT,
        "mission_id": ROUTE_INVENTORY_MISSION,
        "menu_cleanup_mission": MENU_CLEANUP_MISSION,
        "menu_ui_mission": MENU_UI_MISSION,
        "app_build": app_build,
        "active_routes": [dict(row) for row in ACTIVE_ROUTE_ROWS],
        "blocked_routes": [dict(row) for row in BLOCKED_ROUTE_ROWS],
        "alias_routes": [dict(row) for row in ALIAS_ROUTE_ROWS],
        "removed_routes": [dict(row) for row in REMOVED_ROUTE_ROWS],
        "pending_routes": [dict(row) for row in PENDING_ROUTE_ROWS],
        "constitutional_labels": list(CONSTITUTIONAL_LABELS),
        "route_guards": list(ROUTE_GUARDS),
        "allowed_pages_count": len(INSTITUTIONAL_ALLOWED_PAGES),
        "official_sidebar_count": len(official_sidebar_page_ids()),
        "hidden_sidebar_page_ids": sorted(HIDDEN_SIDEBAR_PAGE_IDS),
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
            f"Itens oficiais no sidebar: `{payload['official_sidebar_count']}`. "
            "Rotas fora do conjunto caem em fallback institucional."
        )
