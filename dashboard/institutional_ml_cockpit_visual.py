"""Camada visual da Central ML — referência M-UI-ML-001 (display only)."""

from __future__ import annotations

import html
import re
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any, Literal

import streamlit as st

MetricTone = Literal["ok", "warn", "bad", "info"]

_METRIC_ICONS: dict[str, str] = {
    "Similaridade média": "📊",
    "Sobreposição máxima": "🔀",
    "Quase repetidos críticos": "⚠️",
    "Dezenas subcobertas": "🎯",
    "Score diversidade": "🌐",
    "Pares em atenção": "👁️",
    "Formato": "🎴",
}

_VERDICT_HEADLINES: dict[str, str] = {
    "APROVADO": "Lote estruturalmente saudável",
    "APROVADO COM ALERTA": "Atenção estrutural — monitorar",
    "PRECISA CALIBRAR": "Calibração supervisionada recomendada",
    "REPROVADO": "Lote reprovado — revisão obrigatória",
    "BLOQUEADO PARA OFICIALIZAÇÃO": "Bloqueado para oficialização",
}

_HIT_REASON_FRAGMENTS = (
    "ausência de captura 13/14/15",
    "ausencia de captura 13/14/15",
    "captura 13/14/15",
    "captura 13/14",
    "baixa força de captura",
    "zero hits",
    "ausência de jogos 13/14/15",
)

_PLAN_HIT_FRAGMENTS = (
    "captura 13/14",
    "13/14/15",
    "zero hits",
    "ausência de captura",
)


def inject_central_ml_visual_styles() -> None:
    st.markdown(
        """
        <style>
        .lotoia-cml-page {
            max-width: 1180px;
            margin: 0 auto;
        }
        .lotoia-cml-hero {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
            padding: 1rem 1.15rem;
            border: 1px solid #dbe5ef;
            border-radius: 1rem;
            background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
            box-shadow: 0 10px 24px rgba(18, 52, 86, 0.06);
        }
        .lotoia-cml-hero-kicker {
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #6d8094;
            margin-bottom: 0.2rem;
        }
        .lotoia-cml-hero-title {
            font-size: 1.55rem;
            font-weight: 800;
            color: #123456;
            line-height: 1.15;
        }
        .lotoia-cml-hero-sub {
            color: #5d7084;
            font-size: 0.92rem;
            margin-top: 0.35rem;
        }
        .lotoia-cml-hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.38rem 0.8rem;
            border-radius: 999px;
            background: rgba(46, 204, 113, 0.12);
            color: #1f8f4d;
            border: 1px solid rgba(46, 204, 113, 0.35);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .lotoia-cml-section-head {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.85rem;
        }
        .lotoia-cml-section-index {
            width: 2rem;
            height: 2rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #123456;
            color: #ffffff;
            font-size: 0.95rem;
            font-weight: 800;
            flex: 0 0 auto;
        }
        .lotoia-cml-section-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: #123456;
            line-height: 1.2;
        }
        .lotoia-cml-section-sub {
            font-size: 0.82rem;
            color: #6d8094;
            margin-top: 0.12rem;
        }
        .lotoia-cml-metric-shell {
            border-radius: 0.85rem !important;
            padding: 0.55rem 0.65rem 0.35rem !important;
            min-height: 6.5rem;
        }
        .lotoia-cml-metric-shell.tone-ok {
            border-color: rgba(46, 204, 113, 0.35) !important;
            background: linear-gradient(180deg, #ffffff 0%, #f6fcf8 100%) !important;
        }
        .lotoia-cml-metric-shell.tone-warn {
            border-color: rgba(243, 156, 18, 0.4) !important;
            background: linear-gradient(180deg, #ffffff 0%, #fffaf3 100%) !important;
        }
        .lotoia-cml-metric-shell.tone-bad {
            border-color: rgba(231, 76, 60, 0.4) !important;
            background: linear-gradient(180deg, #ffffff 0%, #fff7f6 100%) !important;
        }
        .lotoia-cml-metric-shell.tone-info {
            border-color: rgba(79, 142, 247, 0.35) !important;
            background: linear-gradient(180deg, #ffffff 0%, #f6f9ff 100%) !important;
        }
        .lotoia-cml-metric-badge-line {
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.15rem;
        }
        .lotoia-cml-metric-badge-line.ok { color: #1f8f4d; }
        .lotoia-cml-metric-badge-line.warn { color: #a66a00; }
        .lotoia-cml-metric-badge-line.bad { color: #b83227; }
        .lotoia-cml-metric-badge-line.info { color: #2f6fd6; }
        .lotoia-cml-verdict {
            border-radius: 0.95rem;
            padding: 1rem 1.1rem;
            margin-bottom: 0.75rem;
            border: 1px solid transparent;
        }
        .lotoia-cml-verdict.success {
            background: rgba(46, 204, 113, 0.10);
            border-color: rgba(46, 204, 113, 0.28);
        }
        .lotoia-cml-verdict.warning {
            background: rgba(243, 156, 18, 0.10);
            border-color: rgba(243, 156, 18, 0.28);
        }
        .lotoia-cml-verdict.danger {
            background: rgba(231, 76, 60, 0.10);
            border-color: rgba(231, 76, 60, 0.28);
        }
        .lotoia-cml-verdict-title {
            font-size: 1.08rem;
            font-weight: 800;
            color: #123456;
            margin-bottom: 0.35rem;
        }
        .lotoia-cml-verdict-copy {
            color: #4d6278;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        .lotoia-cml-verdict-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.65rem;
            margin-top: 0.75rem;
        }
        .lotoia-cml-meta-box {
            border: 1px solid #e2eaf2;
            border-radius: 0.8rem;
            background: rgba(255, 255, 255, 0.72);
            padding: 0.7rem 0.8rem;
        }
        .lotoia-cml-meta-label {
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6d8094;
            margin-bottom: 0.2rem;
        }
        .lotoia-cml-meta-value {
            color: #123456;
            font-size: 0.9rem;
            font-weight: 700;
            line-height: 1.45;
        }
        .lotoia-cml-plan-card {
            border: 1px solid #e2eaf2;
            border-radius: 0.8rem;
            background: #fbfdff;
            padding: 0.65rem 0.85rem;
            margin-bottom: 0.5rem;
            font-size: 0.92rem;
            color: #27415d;
            line-height: 1.5;
        }
        .lotoia-cml-plan-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.35rem;
            height: 1.35rem;
            border-radius: 999px;
            background: #123456;
            color: #fff;
            font-size: 0.72rem;
            font-weight: 800;
            margin-right: 0.45rem;
        }
        .lotoia-cml-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.65rem 0 0.85rem;
        }
        .lotoia-cml-audit-hint {
            font-size: 0.84rem;
            color: #6d8094;
            margin-bottom: 0.35rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.lotoia-cml-section-marker) {
            padding: 0.85rem 1rem 1rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 8px 20px rgba(18, 52, 86, 0.04);
        }
        div[data-testid="stExpander"]:has(.lotoia-cml-audit-marker) {
            border: 1px solid #dbe5ef;
            border-radius: 0.95rem;
            background: #fbfdff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else "—"))


def sanitize_structural_display_reason(reason: str) -> str:
    """Remove frases de hits da exibição operacional (dados legados no PostgreSQL)."""
    text = str(reason or "").strip()
    if not text:
        return "Sem bloqueios estruturais."
    for fragment in _HIT_REASON_FRAGMENTS:
        text = re.sub(re.escape(fragment), "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"^[\s,;.\-]+|[\s,;.\-]+$", "", text)
    text = re.sub(r",\s*,", ",", text)
    return text.strip() or "Sem bloqueios estruturais."


def filter_operational_plan_items(plan_items: list[str]) -> list[str]:
    """Remove recomendações de captura 13/14/15 da visão operacional principal."""
    filtered: list[str] = []
    for item in plan_items:
        lowered = str(item or "").lower()
        if any(fragment in lowered for fragment in _PLAN_HIT_FRAGMENTS):
            continue
        filtered.append(str(item))
    return filtered


def _metric_tone_for_label(label: str, value: Any) -> MetricTone:
    if label == "Formato":
        return "info"
    try:
        if label == "Similaridade média":
            number = float(value)
            if number >= 0.65:
                return "bad"
            if number >= 0.55:
                return "warn"
            return "ok"
        if label == "Sobreposição máxima":
            number = int(float(value))
            if number >= 14:
                return "bad"
            if number >= 12:
                return "warn"
            return "ok"
        if label == "Quase repetidos críticos":
            number = int(float(value))
            if number >= 50:
                return "bad"
            if number >= 20:
                return "warn"
            return "ok"
        if label == "Dezenas subcobertas":
            number = int(float(value))
            if number >= 3:
                return "bad"
            if number >= 1:
                return "warn"
            return "ok"
        if label == "Score diversidade":
            number = float(value)
            if number < 0.40:
                return "bad"
            if number < 0.55:
                return "warn"
            return "ok"
        if label == "Pares em atenção":
            number = int(float(value))
            if number >= 20:
                return "bad"
            if number >= 10:
                return "warn"
            return "ok"
    except (TypeError, ValueError):
        return "info"
    return "info"


def _badge_label(tone: MetricTone) -> str:
    return {"ok": "OK", "warn": "ATENÇÃO", "bad": "CRÍTICO", "info": "INFO"}[tone]


def _format_metric_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value if value is not None else "—")


@contextmanager
def section_shell() -> Iterator[None]:
    """Container nativo Streamlit — evita HTML partido entre chamadas."""
    st.markdown('<div class="lotoia-cml-section-marker"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        yield


def begin_section_shell() -> None:
    """Compatibilidade legada — preferir section_shell()."""
    st.markdown('<div class="lotoia-cml-section-marker"></div>', unsafe_allow_html=True)
    st.session_state["_lotoia_cml_section_open"] = True


def end_section_shell() -> None:
    """Compatibilidade legada — no-op (container nativo substitui div partido)."""
    st.session_state.pop("_lotoia_cml_section_open", None)


def render_central_ml_header(*, subtitle: str, supervised_active: bool) -> None:
    badge = "Operacional" if supervised_active else "Inativo"
    st.markdown(
        f"""
        <div class="lotoia-cml-page">
          <div class="lotoia-cml-hero">
            <div>
              <div class="lotoia-cml-hero-kicker">Central ML</div>
              <div class="lotoia-cml-hero-title">Decisão de Calibração</div>
              <div class="lotoia-cml-hero-sub">{_esc(subtitle)}</div>
            </div>
            <div class="lotoia-cml-hero-badge">● {badge}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(section_index: int, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="lotoia-cml-section-head">
          <span class="lotoia-cml-section-index">{section_index}</span>
          <div>
            <div class="lotoia-cml-section-title">{_esc(title)}</div>
            <div class="lotoia-cml-section-sub">{_esc(subtitle)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_grid(metrics: list[tuple[str, Any]]) -> None:
    """Grade de métricas com componentes nativos — evita HTML cru na tela."""
    columns_per_row = 4
    for row_start in range(0, len(metrics), columns_per_row):
        row = metrics[row_start : row_start + columns_per_row]
        cols = st.columns(columns_per_row)
        for col_index, (label, value) in enumerate(row):
            tone = _metric_tone_for_label(label, value)
            icon = _METRIC_ICONS.get(label, "📌")
            display = _format_metric_value(value)
            with cols[col_index]:
                with st.container(border=True):
                    st.caption(f"{icon} · {_badge_label(tone)}")
                    st.metric(label=label, value=display)


def _verdict_tone(verdict: str) -> str:
    normalized = str(verdict or "").strip().upper()
    if normalized in {"REPROVADO", "BLOQUEADO PARA OFICIALIZAÇÃO"}:
        return "danger"
    if normalized in {"PRECISA CALIBRAR", "APROVADO COM ALERTA"}:
        return "warning"
    return "success"


def render_verdict_banner(
    *,
    verdict: str,
    reason: str,
    release_label: str,
    next_action: str,
    operator_decision: str,
) -> None:
    normalized = str(verdict or "APROVADO").strip().upper()
    headline = _VERDICT_HEADLINES.get(normalized, normalized or "Veredito indisponível")
    tone = _verdict_tone(normalized)
    display_reason = sanitize_structural_display_reason(reason)
    st.markdown(
        f"""
        <div class="lotoia-cml-verdict {tone}">
          <div class="lotoia-cml-verdict-title">{_esc(headline)}</div>
          <div class="lotoia-cml-verdict-copy">
            <strong>Veredito ML:</strong> {_esc(normalized)}<br/>
            {_esc(display_reason)}
          </div>
          <div class="lotoia-cml-verdict-meta">
            <div class="lotoia-cml-meta-box">
              <div class="lotoia-cml-meta-label">Liberação oficial</div>
              <div class="lotoia-cml-meta-value">{_esc(release_label)}</div>
            </div>
            <div class="lotoia-cml-meta-box">
              <div class="lotoia-cml-meta-label">Próxima ação</div>
              <div class="lotoia-cml-meta-value">{_esc(next_action)}</div>
            </div>
            <div class="lotoia-cml-meta-box">
              <div class="lotoia-cml-meta-label">Decisão operador</div>
              <div class="lotoia-cml-meta-value">{_esc(operator_decision)}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_plan_list(plan_items: list[str]) -> None:
    visible_items = filter_operational_plan_items(plan_items)
    if not visible_items:
        st.info("Nenhum plano pendente — aguardando evidências da Cobertura Estrutural.")
        return
    for index, item in enumerate(visible_items, start=1):
        st.markdown(
            f"""
            <div class="lotoia-cml-plan-card">
              <span class="lotoia-cml-plan-index">{index}</span>
              {_esc(item)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_constitutional_chip_row(chips: list[tuple[str, str, str]]) -> None:
    pills = []
    for label, value, tone in chips:
        pills.append(
            f'<span class="lotoia-pill lotoia-pill-{tone}">{_esc(label)}: {_esc(value)}</span>'
        )
    st.markdown(f'<div class="lotoia-cml-chip-row">{"".join(pills)}</div>', unsafe_allow_html=True)
