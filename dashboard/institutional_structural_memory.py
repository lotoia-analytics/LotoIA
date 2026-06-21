"""Painel M-MEMORY-001 — linha do tempo de viés estrutural (leitura de memória)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pandas as pd
import streamlit as st

from lotoia.operations.operational_structural_memory import (
    DEFAULT_TIMELINE_LIMIT,
    MISSION_ID,
    STATUS_CRITICAL_BIAS,
    build_bias_timeline_trend,
    load_operational_structural_memory_for_event,
    load_operational_structural_memory_timeline,
)

PANEL_TITLE = "Memória Evolutiva — Linha do Tempo de Viés"
PANEL_CAPTION = (
    "Leitura histórica persistida em `operational_structural_memory` (PostgreSQL). "
    "Os dados permanecem após limpeza da fila operacional (M-OPS-080)."
)


def render_structural_memory_timeline_panel(
    db_path: Any,
    *,
    selected_generation_event_id: int | None = None,
    limit: int = DEFAULT_TIMELINE_LIMIT,
) -> dict[str, Any]:
    timeline = load_operational_structural_memory_timeline(db_path, limit=limit)
    trend = build_bias_timeline_trend(timeline)
    selected_memory = None
    if int(selected_generation_event_id or 0) > 0:
        selected_memory = load_operational_structural_memory_for_event(
            db_path,
            int(selected_generation_event_id),
        )

    st.markdown(f"### {PANEL_TITLE}")
    st.caption(PANEL_CAPTION)

    if not timeline:
        st.info(
            "Nenhuma memória estrutural persistida ainda. "
            "Gere um lote CORE_002 — a cobertura será gravada automaticamente ao persistir."
        )
        return {
            "mission_id": MISSION_ID,
            "available": False,
            "timeline": [],
            "trend": trend,
            "selected_memory": selected_memory,
        }

    metric_cols = st.columns(4)
    metric_cols[0].metric("Gerações na memória", int(trend.get("points", 0) or 0))
    metric_cols[1].metric("Desvio oficial (último)", f"{float(trend.get('latest_score', 0.0) or 0.0):.1f}%")
    metric_cols[2].metric("Tendência", str(trend.get("trend") or "—"))
    metric_cols[3].metric("Lotes críticos", int(trend.get("critical_bias_count", 0) or 0))

    chart_rows = [
        {
            "generation_event_id": int(row.get("generation_event_id", 0) or 0),
            "desvio_oficial_%": float(row.get("official_divergence_score") or 0.0),
            "status": str(row.get("memory_status") or ""),
            "recorded_at": str(row.get("recorded_at") or "")[:19],
        }
        for row in reversed(timeline)
    ]
    if chart_rows:
        st.line_chart(
            pd.DataFrame(chart_rows).set_index("generation_event_id")["desvio_oficial_%"],
            height=220,
        )

    table_rows = _timeline_table_rows(timeline)
    st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True)

    if selected_memory:
        st.markdown("##### Memória do lote selecionado")
        sel_cols = st.columns(4)
        sel_cols[0].metric("GE", int(selected_memory.get("generation_event_id", 0) or 0))
        sel_cols[1].metric(
            "Desvio oficial",
            f"{float(selected_memory.get('official_divergence_score', 0.0) or 0.0):.1f}%",
        )
        sel_cols[2].metric("Status", str(selected_memory.get("memory_status") or "—"))
        sel_cols[3].metric(
            "Alertas",
            len(list(selected_memory.get("bias_alerts") or [])),
        )
        if str(selected_memory.get("memory_status") or "") == STATUS_CRITICAL_BIAS:
            st.error("STATUS_CRITICAL_BIAS — viés acima do limiar institucional (15%).")
        alerts = list(selected_memory.get("bias_alerts") or [])
        if alerts:
            st.markdown("**Alertas de viés persistidos**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "tipo": alert.get("kind"),
                            "padrão": alert.get("pattern"),
                            "severidade": alert.get("severity"),
                            "mensagem": alert.get("message"),
                        }
                        for alert in alerts[:20]
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )

    st.caption(f"missão={MISSION_ID} | janela={limit} gerações | fonte=operational_structural_memory")
    return {
        "mission_id": MISSION_ID,
        "available": True,
        "timeline": timeline,
        "trend": trend,
        "selected_memory": selected_memory,
    }


def _timeline_table_rows(timeline: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in timeline:
        alerts = list(row.get("bias_alerts") or [])
        rows.append(
            {
                "GE": int(row.get("generation_event_id", 0) or 0),
                "gravado_em": str(row.get("recorded_at") or "")[:19],
                "desvio_oficial_%": float(row.get("official_divergence_score") or 0.0),
                "status": str(row.get("memory_status") or ""),
                "alertas": len(alerts),
                "prefixos_distintos": len(dict(row.get("prefix_distribution") or {})),
                "sufixos_distintos": len(dict(row.get("suffix_distribution") or {})),
            }
        )
    return rows
