"""M-UI-MODERN-001 — Dashboard visual de Cobertura Estrutural (UI/UX 2.0)."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import plotly.graph_objects as go
import streamlit as st

from lotoia.observability.m_core_003_bias_monitoring import load_operational_cards_for_bias_monitoring
from lotoia.observability.structural_fidelity_analytics import (
    MISSION_ID,
    VOLANTE_GRID,
    build_structural_intelligence_bundle,
    fidelity_score_from_memory_row,
    resolve_fidelity_status,
)
from lotoia.operations.operational_structural_memory import load_operational_structural_memory_timeline

PANEL_TITLE = "Dashboard de Inteligência Estrutural"
PANEL_CAPTION = (
    "Leitura visual observacional — Health Score, assinatura de dezenas, memória evolutiva "
    "e gaps de quadrantes. Não altera geração nem calibração."
)
TIMELINE_LIMIT = 100


def build_time_travel_options(
    operational_generations: Sequence[Mapping[str, Any]],
    memory_timeline: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    memory_by_ge = {
        int(row.get("generation_event_id", 0) or 0): dict(row)
        for row in memory_timeline
        if int(row.get("generation_event_id", 0) or 0) > 0
    }
    options: list[dict[str, Any]] = []
    for generation in operational_generations:
        ge_id = int(generation.get("generation_event_id", 0) or 0)
        if ge_id <= 0:
            continue
        label = str(generation.get("dropdown_label") or generation.get("operational_generation_label") or ge_id)
        recorded_at = str((memory_by_ge.get(ge_id) or {}).get("recorded_at") or generation.get("created_at") or "")
        options.append(
            {
                "generation_event_id": ge_id,
                "label": label,
                "recorded_at": recorded_at[:19],
                "memory": memory_by_ge.get(ge_id),
                "generation": dict(generation),
            }
        )
    return options


def _build_fidelity_gauge(score: float, *, status_color: str) -> go.Figure:
    value = float(score or 0.0)
    figure = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 34}},
            title={"text": "Structural Fidelity Score", "font": {"size": 16}},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": status_color},
                "steps": [
                    {"range": [0, 70], "color": "#f9d6d5"},
                    {"range": [70, 90], "color": "#f8efd6"},
                    {"range": [90, 100], "color": "#d7f0e2"},
                ],
                "threshold": {
                    "line": {"color": "#173b63", "width": 3},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    figure.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=10))
    return figure


def _build_dezena_radar_chart(
    generated_profile: Mapping[int, float],
    official_profile: Mapping[int, float],
) -> go.Figure:
    categories = [f"{number:02d}" for number in range(1, 26)]
    generated = [float(generated_profile.get(number, 0.0) or 0.0) * 100 for number in range(1, 26)]
    official = [float(official_profile.get(number, 0.0) or 0.0) * 100 for number in range(1, 26)]
    figure = go.Figure()
    figure.add_trace(
        go.Scatterpolar(
            r=generated + [generated[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="LotoIA",
            line_color="#1f5f8b",
            fillcolor="rgba(31, 95, 139, 0.35)",
        )
    )
    figure.add_trace(
        go.Scatterpolar(
            r=official + [official[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name="Oficial",
            line_color="#9bbad1",
            fillcolor="rgba(155, 186, 209, 0.25)",
        )
    )
    figure.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(generated + official + [1.0]) * 1.15],
            )
        ),
        showlegend=True,
        height=420,
        margin=dict(l=40, r=40, t=40, b=40),
        title="Radar de Dezenas — assinatura estrutural",
    )
    return figure


def _build_fidelity_timeline_chart(timeline: Sequence[Mapping[str, Any]]) -> go.Figure:
    ordered = list(reversed(list(timeline)))
    x_values = [int(row.get("generation_event_id", 0) or 0) for row in ordered]
    y_values = [fidelity_score_from_memory_row(row) for row in ordered]
    figure = go.Figure(
        data=[
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                line={"color": "#173b63", "width": 2},
                marker={"size": 7, "color": "#1f5f8b"},
                name="Fidelity Score",
            )
        ]
    )
    figure.add_hline(y=90, line_dash="dot", line_color="#1b8a5a", annotation_text="Soberano 90%")
    figure.add_hline(y=70, line_dash="dot", line_color="#c9a227", annotation_text="Alerta 70%")
    figure.update_layout(
        title="Linha do Tempo de Viés — Fidelity Score (memória M-MEMORY-001)",
        xaxis_title="Geração",
        yaxis_title="Fidelity Score (%)",
        yaxis=dict(range=[0, 100]),
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return figure


def _build_quadrant_heatmap(
    generated: Mapping[str, float],
    official: Mapping[str, float],
) -> go.Figure:
    labels = list(generated.keys())
    matrix = [
        [float(generated.get(label, 0.0) or 0.0) * 100, float(official.get(label, 0.0) or 0.0) * 100]
        for label in labels
    ]
    figure = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=["LotoIA", "Oficial"],
            y=labels,
            colorscale="Blues",
            text=[[f"{value:.1f}%" for value in row] for row in matrix],
            texttemplate="%{text}",
            textfont={"size": 12},
        )
    )
    figure.update_layout(
        title="Heatmap de Quadrantes — ocupação estrutural",
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return figure


def _build_volante_heatmap(matrix: Sequence[Sequence[float]], *, title: str) -> go.Figure:
    y_labels = [f"Linha {index + 1}" for index in range(len(matrix))]
    x_labels = [f"Col {index + 1}" for index in range(len(matrix[0]) if matrix else 0)]
    text = [[f"{value:.1f}%" for value in row] for row in matrix]
    figure = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=x_labels,
            y=y_labels,
            colorscale="YlGnBu",
            text=text,
            texttemplate="%{text}",
        )
    )
    figure.update_layout(title=title, height=280, margin=dict(l=20, r=20, t=50, b=20))
    return figure


def _render_insight_cards(insights: Sequence[Mapping[str, str]]) -> None:
    if not insights:
        return
    columns = st.columns(min(2, len(insights)))
    for index, card in enumerate(insights):
        with columns[index % len(columns)]:
            st.markdown(
                f"**{card.get('icon', '•')} {card.get('title', 'Insight')}**  \n"
                f"{card.get('message', '')}"
            )


def render_modern_structural_coverage_dashboard(
    db_path: Any,
    *,
    operational_generations: Sequence[Mapping[str, Any]],
    selected_generation_event_id: int | None = None,
    render_legacy_diagnostics: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Renderiza o dashboard visual M-UI-MODERN-001."""
    st.markdown(f"### {PANEL_TITLE}")
    st.caption(PANEL_CAPTION)

    memory_timeline = load_operational_structural_memory_timeline(db_path, limit=TIMELINE_LIMIT)
    travel_options = build_time_travel_options(operational_generations, memory_timeline)
    if not travel_options:
        st.info("Nenhuma geração operacional disponível para o modo Time Travel.")
        return {"available": False, "mission_id": MISSION_ID}

    labels = [
        f"{opt['label']} · {opt['recorded_at'] or 'sem memória'}"
        for opt in travel_options
    ]
    default_index = 0
    if int(selected_generation_event_id or 0) > 0:
        for index, option in enumerate(travel_options):
            if int(option.get("generation_event_id", 0) or 0) == int(selected_generation_event_id):
                default_index = index
                break
    else:
        default_index = max(0, len(travel_options) - 1)

    selected_index = st.select_slider(
        "Time Travel — navegue pelo histórico de gerações",
        options=list(range(len(travel_options))),
        value=default_index,
        format_func=lambda index: labels[int(index)],
        key="structural_coverage_time_travel_slider",
    )
    selected_option = travel_options[int(selected_index)]
    selected_ge_id = int(selected_option.get("generation_event_id", 0) or 0)
    st.session_state["structural_coverage_selected_ge_id"] = selected_ge_id

    cards, _resolved_ids = load_operational_cards_for_bias_monitoring(
        db_path,
        generation_event_ids=[selected_ge_id],
    )
    bundle = build_structural_intelligence_bundle(db_path, cards=cards)
    if not bundle.get("available"):
        st.warning("Sem cartões 15D válidos para o dashboard visual nesta geração.")
        return {"available": False, "mission_id": MISSION_ID, "generation_event_id": selected_ge_id}

    fidelity = dict(bundle.get("fidelity") or {})
    score = float(fidelity.get("structural_fidelity_score", 0.0) or 0.0)
    status = resolve_fidelity_status(score)

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Fidelity Score", f"{score:.1f}%")
    kpi_cols[1].metric("Status", str(fidelity.get("status_label") or status["label"]))
    kpi_cols[2].metric("Jogos analisados", int(bundle.get("games_count", 0) or 0))
    kpi_cols[3].metric(
        "Concursos oficiais",
        int(bundle.get("official_contests_used", 0) or 0),
    )

    chart_top = st.columns([1, 1.2])
    with chart_top[0]:
        st.plotly_chart(_build_fidelity_gauge(score, status_color=str(status["color"])), use_container_width=True)
    with chart_top[1]:
        st.plotly_chart(
            _build_dezena_radar_chart(
                fidelity.get("generated_profile") or {},
                fidelity.get("official_profile") or {},
            ),
            use_container_width=True,
        )

    _render_insight_cards(list(bundle.get("insights") or []))

    chart_mid = st.columns(2)
    with chart_mid[0]:
        if memory_timeline:
            st.plotly_chart(_build_fidelity_timeline_chart(memory_timeline), use_container_width=True)
        else:
            st.info("Memória evolutiva ainda vazia — gere um lote CORE_002 para popular a timeline.")
    with chart_mid[1]:
        st.plotly_chart(
            _build_quadrant_heatmap(
                dict(bundle.get("quadrant_generated") or {}),
                dict(bundle.get("quadrant_official") or {}),
            ),
            use_container_width=True,
        )

    with st.expander("Mapa do volante — frequência por dezena (LotoIA vs oficial)", expanded=False):
        volante_cols = st.columns(2)
        with volante_cols[0]:
            st.plotly_chart(
                _build_volante_heatmap(
                    list(bundle.get("volante_generated") or []),
                    title="LotoIA — ocupação do volante (%)",
                ),
                use_container_width=True,
            )
        with volante_cols[1]:
            st.plotly_chart(
                _build_volante_heatmap(
                    list(bundle.get("volante_official") or []),
                    title="Oficial — ocupação do volante (%)",
                ),
                use_container_width=True,
            )
        st.caption(
            "Grade 5×5 do volante Lotofácil: "
            + " · ".join(
                " ".join(f"{number:02d}" for number in row) for row in VOLANTE_GRID
            )
        )

    if render_legacy_diagnostics is not None:
        st.divider()
        st.subheader("Diagnóstico estrutural detalhado (modo legado)")
        st.caption(
            "Leitura observacional por geração — abertura, fechamento, gaps, redundância "
            "e comparação com concursos oficiais."
        )
        render_legacy_diagnostics()

    st.caption(
        f"missão={MISSION_ID} · integração M-MEMORY-001 · geração selecionada={selected_ge_id}"
    )
    return {
        "available": True,
        "mission_id": MISSION_ID,
        "generation_event_id": selected_ge_id,
        "structural_fidelity_score": score,
        "bundle": bundle,
        "memory_timeline_count": len(memory_timeline),
    }
