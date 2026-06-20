"""Painel M-CORE-003 — monitoramento contínuo de viés prefixo/sufixo no dashboard."""

from __future__ import annotations

from typing import Any, Mapping

import pandas as pd
import streamlit as st

from lotoia.observability.m_core_003_bias_monitoring import (
    MISSION_ID,
    build_m_core_003_bias_monitoring_report,
    build_m_core_003_bias_monitoring_report_from_db,
)

PANEL_TITLE = "Monitoramento M-CORE-003 — razão de viés prefixo/sufixo"
PANEL_SECTION_TITLE = "Monitoramento M-CORE-003 — Figura 5A (razão de viés)"
PANEL_CAPTION = (
    "Compara padrões prefixo3/sufixo3 dos jogos operacionais persistidos com a frequência "
    "histórica dos 3.714 concursos oficiais. Painel observacional — não altera geração nem calibração."
)


def _ratio_table_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in list(report.get("ratio_rows") or []):
        rows.append(
            {
                "tipo": "prefixo" if row.get("kind") == "prefix" else "sufixo",
                "padrão": row.get("pattern"),
                "gerado_%": row.get("generated_pct"),
                "histórico_%": row.get("historical_pct"),
                "razão": row.get("ratio"),
                "severidade": row.get("severity"),
            }
        )
    return rows


def render_m_core_003_bias_monitoring_panel(
    *,
    db_path: Any,
    generation_event_ids: list[int] | None = None,
    games: list[list[int]] | None = None,
    expanded: bool = True,
) -> dict[str, Any]:
    """Renderiza scorecard de razão de viés (Figura 5A do relatório M-CORE-003)."""
    if games:
        report = build_m_core_003_bias_monitoring_report(
            games,
            games_count=len(games),
            generation_event_ids=generation_event_ids,
        )
    else:
        report = build_m_core_003_bias_monitoring_report_from_db(
            db_path,
            generation_event_ids=generation_event_ids,
        )

    st.markdown(f"### {PANEL_SECTION_TITLE}")
    st.caption(PANEL_CAPTION)

    if not report.get("available"):
        st.info("Sem jogos operacionais válidos para monitoramento M-CORE-003.")
        return report

    verdict = str(report.get("verdict") or "—")
    if report.get("compliance"):
        st.success(verdict)
    elif int(report.get("severe_bias_count", 0) or 0) > 0:
        st.error(verdict)
    else:
        st.warning(verdict)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Jogos analisados", int(report.get("games_count", 0) or 0))
    metric_cols[1].metric("Viés severo (>3x)", int(report.get("severe_bias_count", 0) or 0))
    metric_cols[2].metric("Viés moderado (>2x)", int(report.get("moderate_bias_count", 0) or 0))
    metric_cols[3].metric(
        f"Watchlist {report.get('watchlist_pattern', '—')}",
        f"{float(report.get('watchlist_ratio', 0.0) or 0.0):.2f}x",
    )

    entropy_cols = st.columns(4)
    entropy_cols[0].metric("Entropia prefixos", float(report.get("entropy_prefix", 0.0) or 0.0))
    entropy_cols[1].metric("Entropia sufixos", float(report.get("entropy_suffix", 0.0) or 0.0))
    entropy_cols[2].metric("Padrões prefixo distintos", int(report.get("distinct_prefix_patterns", 0) or 0))
    entropy_cols[3].metric("Padrões sufixo distintos", int(report.get("distinct_suffix_patterns", 0) or 0))

    with st.expander(PANEL_TITLE, expanded=expanded):
        ratio_rows = _ratio_table_rows(report)
        if ratio_rows:
            st.markdown("##### Padrões com razão de viés acima de 2x")
            st.dataframe(pd.DataFrame(ratio_rows), hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum padrão acima de 2x — alinhamento saudável com o histórico oficial.")

        critical = dict(report.get("critical_pattern_01_04_06") or {})
        if critical:
            st.warning(
                "Padrão crítico 01-04-06 ainda acima do limiar: "
                f"{critical.get('ratio', '—')}x "
                f"(gerado {critical.get('generated_pct', '—')}% vs histórico "
                f"{critical.get('historical_pct', '—')}%)."
            )
        else:
            st.caption("Padrão crítico 01-04-06: suprimido ou dentro do limiar.")

        st.caption(f"missão={MISSION_ID} | baseline=3.714 concursos oficiais Lotofácil")
    return report
