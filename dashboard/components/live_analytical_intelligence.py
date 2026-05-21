from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import streamlit as st

from .design_system import render_institutional_design_system

DEFAULT_LONGITUDINAL_REPORT = Path("reports") / "longitudinal" / "baseline_hard_longitudinal.json"


def _latest_value(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if frame.empty or column not in frame.columns:
        return default
    try:
        value = frame[column].dropna().iloc[-1]
        return float(value)
    except Exception:
        return default


def _first_last_delta(frame: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if frame.empty or column not in frame.columns or len(frame[column].dropna()) < 2:
        return default
    series = frame[column].dropna()
    try:
        return float(series.iloc[-1]) - float(series.iloc[0])
    except Exception:
        return default


def _direction_label(delta: float, positive: str, negative: str, neutral: str = "estavel") -> str:
    if delta > 0.01:
        return positive
    if delta < -0.01:
        return negative
    return neutral


def _load_longitudinal_report(report_path: Path = DEFAULT_LONGITUDINAL_REPORT) -> dict[str, Any]:
    if not report_path.exists():
        return {}
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _format_checkpoint_label(frame: pd.DataFrame, index: int) -> str:
    if frame.empty or "checkpoint" not in frame.columns or index >= len(frame):
        return "-"
    try:
        return str(frame.iloc[index]["checkpoint"])
    except Exception:
        return "-"


def render_live_analytical_intelligence(
    analytical_report: Mapping[str, Any],
    executive_report: Mapping[str, Any],
    historical_report: Mapping[str, Any],
    snapshot_report: Mapping[str, Any],
    timeline: pd.DataFrame,
    observability_report: Mapping[str, Any],
) -> None:
    render_institutional_design_system()
    summary = analytical_report.get("analytical_summary", {})
    insights = analytical_report.get("insights", [])
    comparisons = analytical_report.get("comparisons", [])
    historical_summary = historical_report.get("summary", {}) if isinstance(historical_report, Mapping) else {}
    snapshot_summary = snapshot_report.get("summary", {}) if isinstance(snapshot_report, Mapping) else {}
    obs_summary = observability_report.get("summary", {}) if isinstance(observability_report, Mapping) else {}
    longitudinal_report = _load_longitudinal_report()
    longitudinal_runs = longitudinal_report.get("runs", []) if isinstance(longitudinal_report, Mapping) else []
    longitudinal_summary = longitudinal_report.get("summary", {}) if isinstance(longitudinal_report, Mapping) else {}
    longitudinal_frame = pd.DataFrame(
        [
            {
                "checkpoint": run.get("checkpoint", ""),
                "average_hits": run.get("result", {}).get("lotoia", {}).get("average_hits", 0.0),
                "stability_window_sd": run.get("result", {}).get("lotoia", {}).get("stability_window_sd", 0.0),
                "final_score_hit_correlation": run.get("result", {}).get("lotoia", {}).get("final_score_hit_correlation", 0.0),
                "contests_analyzed": run.get("result", {}).get("contests_analyzed", 0),
            }
            for run in longitudinal_runs
            if isinstance(run, Mapping)
        ]
    )

    st.markdown("### Inteligencia viva")
    top_left, top_right = st.columns([1.2, 0.8], gap="large")
    with top_left:
        st.markdown(
            f"""
            <div class="lotoia-card-shell" style="padding: 0.95rem 1rem;">
                <div class="lotoia-muted-label">Evolucao</div>
                <div class="lotoia-executive-title" style="font-size: 1.05rem; margin: 0.35rem 0 0.4rem 0;">
                    Evolucao da estabilidade, confiança, drift e cobertura
                </div>
                <div style="font-size: 0.92rem; color: #4b5f74; line-height: 1.5;">
                    O baseline permanece sob leitura institucional. A evolucao temporal mostra como a plataforma se comporta ao longo dos checkpoints persistidos.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        evo_cols = st.columns(4)
        evo_cols[0].metric("Estabilidade", f"{float(summary.get('structural_health', 0.0)):.2f}")
        evo_cols[1].metric("Confianca", str(summary.get("confidence", "-")))
        evo_cols[2].metric("Drift", f"{float(summary.get('drift', 0.0)):.2f}")
        evo_cols[3].metric("Cobertura 11+", f"{float(summary.get('coverage_11', 0.0)):.2f}")
        if not timeline.empty:
            trend_frame = timeline.copy()
            for column in ["structural_health", "drift", "coverage_10", "coverage_11"]:
                if column not in trend_frame.columns:
                    trend_frame[column] = 0.0
            trend_frame.index = pd.RangeIndex(start=1, stop=len(trend_frame) + 1)
            st.line_chart(trend_frame[["structural_health", "drift", "coverage_10", "coverage_11"]], height=240)
        else:
            st.info("Nenhuma timeline institucional consolidada ainda.")
    with top_right:
        stability_delta = _first_last_delta(timeline, "structural_health", summary.get("structural_health", 0.0))
        drift_delta = _first_last_delta(timeline, "drift", summary.get("drift", 0.0))
        coverage10_delta = _first_last_delta(timeline, "coverage_10", summary.get("coverage_10", 0.0))
        coverage11_delta = _first_last_delta(timeline, "coverage_11", summary.get("coverage_11", 0.0))
        runtime_badge = "atualizacao contextual viva" if len(timeline) >= 3 else "observacao em consolidacao"
        memory_continuity = 0.0
        if not longitudinal_frame.empty:
            memory_continuity = min(
                1.0,
                round(
                    0.45
                    + 0.2 * float(longitudinal_summary.get("stability_index", 0.0))
                    + 0.15 * float(summary.get("structural_health", 0.0))
                    + 0.2 * (1.0 if len(timeline) >= 3 else 0.5),
                    3,
                ),
            )
        st.markdown(
            f"""
            <div class="lotoia-card-shell" style="padding: 0.95rem 1rem;">
                <div class="lotoia-muted-label">Interpretacao</div>
                <div class="lotoia-executive-title" style="font-size: 1.05rem; margin: 0.35rem 0 0.4rem 0;">
                    Leitura temporal interpretativa
                </div>
                <div style="font-size: 0.92rem; color: #4b5f74; line-height: 1.6;">
                    {summary.get('interpretation', executive_report.get('headline', 'baseline longitudinal consistente'))}
                </div>
                <div style="margin-top: 0.55rem; font-size: 0.88rem; color: #4b5f74; line-height: 1.55;">
                    A estabilidade { _direction_label(stability_delta, 'melhorou', 'recuou') }.
                    O drift { _direction_label(drift_delta, 'cresceu levemente', 'reduziu') }.
                    A cobertura 10+ { _direction_label(coverage10_delta, 'ganhou tracao', 'perdeu tracao') }.
                    A cobertura 11+ { _direction_label(coverage11_delta, 'ganhou tracao', 'perdeu tracao') }.
                </div>
                <div style="margin-top: 0.55rem; display: flex; flex-wrap: wrap; gap: 0.35rem;">
                    <span style="padding: 0.28rem 0.62rem; border-radius: 999px; background: #eef7f0; color: #204c33; font-size: 0.82rem; font-weight: 700;">{historical_summary.get('trend', 'estavel')}</span>
                    <span style="padding: 0.28rem 0.62rem; border-radius: 999px; background: #eef4fb; color: #123456; font-size: 0.82rem; font-weight: 700;">snapshot {snapshot_summary.get('status', executive_report.get('status', '-'))}</span>
                    <span style="padding: 0.28rem 0.62rem; border-radius: 999px; background: #fff4e8; color: #8b4f18; font-size: 0.82rem; font-weight: 700;">obs {obs_summary.get('stability_note', 'monitorado')}</span>
                    <span style="padding: 0.28rem 0.62rem; border-radius: 999px; background: #edf4ff; color: #24416a; font-size: 0.82rem; font-weight: 700;">runtime {runtime_badge}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="margin-top: 0.45rem; display: flex; flex-wrap: wrap; gap: 0.35rem;">
                <span class="lotoia-analytical-badge">live pulse</span>
                <span class="lotoia-trend-pill">memory {memory_continuity:.2f}</span>
                <span class="lotoia-trend-pill">{runtime_badge}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"Memoria operacional percebida: {memory_continuity:.2f}")
        if comparisons:
            comparison_frame = pd.DataFrame(comparisons)
            st.dataframe(comparison_frame, hide_index=True, use_container_width=True)
        else:
            st.info("Comparacoes longitudinais ainda nao disponiveis nesta janela.")

    st.markdown("### Evolucao longitudinal")
    if longitudinal_frame.empty:
        st.info("Baseline longitudinal ainda nao foi consolidado para comparacao viva.")
    else:
        long_cols = st.columns(min(4, len(longitudinal_frame)))
        for column, (_, row) in zip(long_cols, longitudinal_frame.head(len(long_cols)).iterrows(), strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-card-shell" style="padding: 0.85rem;">
                        <div class="lotoia-muted-label">checkpoint {row.get('checkpoint', '-')}</div>
                        <div class="lotoia-executive-title" style="font-size: 0.98rem; margin: 0.32rem 0 0.35rem 0;">média de acertos {float(row.get('average_hits', 0.0)):.2f}</div>
                        <div style="font-size: 0.88rem; color: #4b5f74; line-height: 1.45;">estabilidade {float(row.get('stability_window_sd', 0.0)):.2f} | correlação {float(row.get('final_score_hit_correlation', 0.0)):.2f}</div>
                        <div style="margin-top: 0.35rem; font-size: 0.82rem; color: #6b7f93;">{int(row.get('contests_analyzed', 0))} concursos analisados</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        if {"checkpoint", "average_hits", "stability_window_sd"}.issubset(longitudinal_frame.columns):
            chart_frame = longitudinal_frame.copy()
            chart_frame["checkpoint"] = chart_frame["checkpoint"].astype(str)
            chart_frame = chart_frame.set_index("checkpoint")
            st.line_chart(chart_frame[["average_hits", "stability_window_sd", "final_score_hit_correlation"]], height=240)
        st.caption(
            f"baseline={longitudinal_report.get('baseline_mode', executive_report.get('baseline_mode', '-'))}"
            f" | cobertura10={longitudinal_summary.get('coverage_10', 0.0)}"
            f" | cobertura11={longitudinal_summary.get('coverage_11', 0.0)}"
            f" | estabilidade={longitudinal_summary.get('stability_index', 0.0)}"
        )
        comparative_cols = st.columns(4)
        comparative_items = [
            ("Hits delta", _first_last_delta(longitudinal_frame, "average_hits", 0.0)),
            ("Stability delta", _first_last_delta(longitudinal_frame, "stability_window_sd", 0.0)),
            ("Correlation delta", _first_last_delta(longitudinal_frame, "final_score_hit_correlation", 0.0)),
            ("Memory depth", float(len(longitudinal_frame))),
        ]
        for column, (label, value) in zip(comparative_cols, comparative_items, strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                        <div class="lotoia-muted-label">{label}</div>
                        <div style="margin-top: 0.45rem;">
                            <span class="lotoia-trend-pill">{value:.2f}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### Graficos")
    if longitudinal_frame.empty:
        st.info("Graficos executivos ainda dependem do longitudinal consolidado.")
    else:
        graphic_cols = st.columns(3)
        graphic_metrics = [
            (
                "Media de acertos",
                float(_latest_value(longitudinal_frame, "average_hits", 0.0)),
                _first_last_delta(longitudinal_frame, "average_hits", 0.0),
                "media de acertos",
            ),
            (
                "Estabilidade",
                float(_latest_value(longitudinal_frame, "stability_window_sd", 0.0)),
                _first_last_delta(longitudinal_frame, "stability_window_sd", 0.0),
                "estabilidade da janela",
            ),
            (
                "Score x acertos",
                float(_latest_value(longitudinal_frame, "final_score_hit_correlation", 0.0)),
                _first_last_delta(longitudinal_frame, "final_score_hit_correlation", 0.0),
                "correlacao score x hits",
            ),
        ]
        for column, (label, latest, delta, caption) in zip(graphic_cols, graphic_metrics, strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-card-shell" style="padding: 0.85rem;">
                        <div class="lotoia-muted-label">{label}</div>
                        <div class="lotoia-executive-title" style="font-size: 0.98rem; margin: 0.32rem 0 0.35rem 0;">
                            {latest:.2f}
                        </div>
                        <div style="font-size: 0.88rem; color: #4b5f74; line-height: 1.45;">
                            tendencia { _direction_label(delta, 'ascendente', 'descendente') } | delta {delta:.2f}
                        </div>
                        <div style="margin-top: 0.35rem; font-size: 0.82rem; color: #6b7f93;">
                            {caption}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        trend_graph_frame = longitudinal_frame.copy()
        if "checkpoint" in trend_graph_frame.columns:
            trend_graph_frame["checkpoint"] = trend_graph_frame["checkpoint"].astype(str)
            trend_graph_frame = trend_graph_frame.set_index("checkpoint")
        st.line_chart(
            trend_graph_frame[["average_hits", "stability_window_sd", "final_score_hit_correlation"]],
            height=220,
        )

    st.markdown("### Narrativa evolutiva")
    if timeline.empty:
        st.info("Checkpoint historico ainda nao consolidado para storytelling.")
    else:
        story_cards = st.columns(min(3, len(timeline)))
        for column, (_, row) in zip(story_cards, timeline.head(len(story_cards)).iterrows(), strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-card-shell" style="padding: 0.85rem;">
                        <div class="lotoia-muted-label">{row.get("created_at", "-")}</div>
                        <div class="lotoia-executive-title" style="font-size: 0.98rem; margin: 0.32rem 0 0.35rem 0;">{row.get("headline", "-")}</div>
                        <div style="font-size: 0.88rem; color: #4b5f74; line-height: 1.45;">{row.get("status_transition", "-")}</div>
                        <div style="margin-top: 0.35rem; font-size: 0.82rem; color: #6b7f93;">{row.get("recommendation", "-")}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### Live analytical comparisons")
    comp_col1, comp_col2 = st.columns(2, gap="large")
    with comp_col1:
        st.metric("Trend stability", f"{_latest_value(timeline, 'structural_health', summary.get('structural_health', 0.0)):.2f}")
        st.metric("Trend drift", f"{_latest_value(timeline, 'drift', summary.get('drift', 0.0)):.2f}")
        st.metric("Confidence evolution", f"{_first_last_delta(timeline, 'verdict_count', historical_summary.get('verdict_count', 0)):.2f}")
    with comp_col2:
        st.metric("Coverage 10+ evolution", f"{_first_last_delta(timeline, 'coverage_10', summary.get('coverage_10', 0.0)):.2f}")
        st.metric("Coverage 11+ evolution", f"{_first_last_delta(timeline, 'coverage_11', summary.get('coverage_11', 0.0)):.2f}")
        st.metric("Memoria operacional", f"{len(timeline)} checkpoints")

    st.markdown("### Memoria operacional")
    memory_cols = st.columns(3)
    memory_cols[0].metric("Latest status", str(historical_summary.get("latest_status", snapshot_summary.get("status", "-"))))
    memory_cols[1].metric("Latest transition", str(historical_summary.get("latest_transition", "inicio")))
    memory_cols[2].metric("Snapshots", f"{len(timeline)} / {len(longitudinal_frame) if not longitudinal_frame.empty else 0}")
    if not longitudinal_frame.empty:
        memory_frame = longitudinal_frame.tail(4).copy()
        if not memory_frame.empty:
            memory_frame["memory_state"] = memory_frame.apply(
                lambda row: f"{row.get('checkpoint', '-')}: {float(row.get('average_hits', 0.0)):.2f} | "
                f"{float(row.get('stability_window_sd', 0.0)):.2f} | {float(row.get('final_score_hit_correlation', 0.0)):.2f}",
                axis=1,
            )
            st.dataframe(
                memory_frame[["checkpoint", "average_hits", "stability_window_sd", "final_score_hit_correlation", "memory_state"]],
                hide_index=True,
                use_container_width=True,
            )
            st.progress(memory_continuity)
    continuity_label = "forte" if memory_continuity >= 0.80 else "em consolidacao"
    st.caption(f"Continuidade executiva {continuity_label}: {memory_continuity:.2f}")

    st.markdown("### Resumo evolutivo")
    if longitudinal_frame.empty:
        st.info("Resumo evolutivo institucional ainda depende do longitudinal consolidado.")
    else:
        first_checkpoint = _format_checkpoint_label(longitudinal_frame, 0)
        latest_checkpoint = _format_checkpoint_label(longitudinal_frame, len(longitudinal_frame) - 1)
        first_hits = _latest_value(longitudinal_frame.head(1), "average_hits", 0.0)
        latest_hits = _latest_value(longitudinal_frame, "average_hits", 0.0)
        first_stability = _latest_value(longitudinal_frame.head(1), "stability_window_sd", 0.0)
        latest_stability = _latest_value(longitudinal_frame, "stability_window_sd", 0.0)
        trend_direction = _direction_label(
            _first_last_delta(longitudinal_frame, "average_hits", 0.0),
            "evolutiva",
            "com ajuste",
        )
        evolution_cols = st.columns(3)
        evolution_entries = [
            ("Checkpoint inicial", first_checkpoint),
            ("Checkpoint final", latest_checkpoint),
            ("Direcao institucional", trend_direction),
        ]
        for column, (label, value) in zip(evolution_cols, evolution_entries, strict=True):
            with column:
                st.markdown(
                    f"""
                    <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                        <div class="lotoia-muted-label">{label}</div>
                        <div style="margin-top: 0.45rem;">
                            <span class="lotoia-analytical-badge">{value}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        st.caption(
            f"resumo longitudinal: acertos {first_hits:.2f} -> {latest_hits:.2f} | "
            f"estabilidade {first_stability:.2f} -> {latest_stability:.2f} | "
            f"checkpoints {len(longitudinal_frame)}"
        )

    st.markdown("### Insights executivos")
    insight_messages = [
        f"Baseline hard manteve {'estabilidade' if summary.get('structural_health', 0.0) >= 0.80 else 'observacao'} nos checkpoints recentes.",
        f"Longitudinal apresentou {'baixa' if longitudinal_summary.get('stability_index', 0.0) >= 0.80 else 'media'} variabilidade.",
        f"Monitoramento segue {obs_summary.get('stability_note', 'monitorado')}.",
        f"Memoria operacional {'continua' if memory_continuity >= 0.80 else 'ainda consolidando'} o estado institucional.",
    ]
    for message in insight_messages:
        st.info(message)

    st.markdown("### Insights executivos")
    if insights:
        insights_frame = pd.DataFrame(insights)
        st.dataframe(insights_frame, hide_index=True, use_container_width=True)
    else:
        st.info("Insights executivos ainda nao consolidados nesta leitura.")

    st.markdown("### Presenca institucional")
    presence_cols = st.columns(4)
    presence_items = [
        ("Continuity", "memoria ativa" if memory_continuity >= 0.80 else "memoria consolidando"),
        ("Evolution", longitudinal_summary.get("trend", historical_summary.get("trend", "estavel"))),
        ("Confidence", str(summary.get("confidence", executive_report.get("confidence", "-")))),
        ("Health", "sistema vivo" if float(summary.get("structural_health", 0.0)) >= 0.80 else "observacao"),
    ]
    for column, (label, value) in zip(presence_cols, presence_items, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                    <div class="lotoia-muted-label">{label}</div>
                    <div style="margin-top: 0.45rem;">
                        <span class="lotoia-analytical-badge">{value}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    consistency_score = min(
        1.0,
        round(
            0.5 * memory_continuity
            + 0.3 * float(longitudinal_summary.get("stability_index", 0.0))
            + 0.2 * float(summary.get("structural_health", 0.0)),
            3,
        ),
    )
    st.markdown("### Selo de consistencia")
    seal_cols = st.columns(3)
    seal_items = [
        ("Consistency", f"{consistency_score:.2f}"),
        ("Traceability", "artifacts reais"),
        ("Estado institucional", "continua" if consistency_score >= 0.80 else "em consolidacao"),
    ]
    for column, (label, value) in zip(seal_cols, seal_items, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                    <div class="lotoia-muted-label">{label}</div>
                    <div style="margin-top: 0.45rem;">
                        <span class="lotoia-trend-pill">{value}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    final_posture = "madura" if consistency_score >= 0.80 and memory_continuity >= 0.80 else "em consolidacao"
    st.markdown("### Final institutional posture")
    final_cols = st.columns(2)
    final_items = [
        ("Posture", final_posture),
        ("Signal", "continuity" if consistency_score >= 0.80 else "monitoramento"),
    ]
    for column, (label, value) in zip(final_cols, final_items, strict=True):
        with column:
            st.markdown(
                f"""
                <div class="lotoia-card-shell" style="padding: 0.8rem 0.9rem;">
                    <div class="lotoia-muted-label">{label}</div>
                    <div style="margin-top: 0.45rem;">
                        <span class="lotoia-trend-pill">{value}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    final_message = (
        "A leitura institucional permanece consistente e observavel."
        if final_posture == "madura"
        else "A leitura institucional segue em consolidacao com memoria viva."
    )
    st.caption(final_message)
    executive_summary = (
        "Resumo executivo: a plataforma sustenta continuidade, memoria e consistencia institucional."
        if final_posture == "madura"
        else "Resumo executivo: a plataforma segue consolidando continuidade e memoria institucional."
    )
    st.info(executive_summary)
    st.caption(f"Profundidade da timeline: {len(timeline)} checkpoints")
