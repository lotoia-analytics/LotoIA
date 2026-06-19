"""Camada visual da Central ML — referência M-UI-ML-001 (display only)."""

from __future__ import annotations

import html
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
        .lotoia-cml-section-shell {
            border: 1px solid #dbe5ef;
            border-radius: 1rem;
            background: #ffffff;
            box-shadow: 0 8px 20px rgba(18, 52, 86, 0.04);
            padding: 1rem 1.1rem 1.05rem;
            margin-bottom: 0.85rem;
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
        .lotoia-cml-metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
            gap: 0.65rem;
        }
        .lotoia-cml-metric-card {
            position: relative;
            border: 1px solid #e2eaf2;
            border-radius: 0.9rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbfe 100%);
            padding: 0.8rem 0.85rem 0.9rem;
            min-height: 108px;
        }
        .lotoia-cml-metric-card.tone-ok { border-color: rgba(46, 204, 113, 0.28); }
        .lotoia-cml-metric-card.tone-warn { border-color: rgba(243, 156, 18, 0.35); }
        .lotoia-cml-metric-card.tone-bad { border-color: rgba(231, 76, 60, 0.35); }
        .lotoia-cml-metric-card.tone-info { border-color: rgba(79, 142, 247, 0.28); }
        .lotoia-cml-metric-icon {
            font-size: 1.1rem;
            margin-bottom: 0.35rem;
        }
        .lotoia-cml-metric-label {
            font-size: 0.68rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6d8094;
            line-height: 1.25;
            padding-right: 3rem;
        }
        .lotoia-cml-metric-value {
            font-size: 1.45rem;
            font-weight: 800;
            color: #123456;
            line-height: 1.1;
            margin-top: 0.2rem;
        }
        .lotoia-cml-metric-badge {
            position: absolute;
            top: 0.65rem;
            right: 0.65rem;
            font-size: 0.62rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 0.18rem 0.45rem;
            border-radius: 999px;
        }
        .lotoia-cml-metric-badge.ok {
            background: rgba(46, 204, 113, 0.14);
            color: #1f8f4d;
            border: 1px solid rgba(46, 204, 113, 0.28);
        }
        .lotoia-cml-metric-badge.warn {
            background: rgba(243, 156, 18, 0.14);
            color: #a66a00;
            border: 1px solid rgba(243, 156, 18, 0.28);
        }
        .lotoia-cml-metric-badge.bad {
            background: rgba(231, 76, 60, 0.12);
            color: #b83227;
            border: 1px solid rgba(231, 76, 60, 0.28);
        }
        .lotoia-cml-metric-badge.info {
            background: rgba(79, 142, 247, 0.12);
            color: #2f6fd6;
            border: 1px solid rgba(79, 142, 247, 0.28);
        }
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
        .lotoia-cml-plan-list {
            margin: 0;
            padding-left: 1.2rem;
            color: #27415d;
            line-height: 1.65;
            font-size: 0.94rem;
        }
        .lotoia-cml-plan-list li {
            margin-bottom: 0.45rem;
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
    cards: list[str] = []
    for label, value in metrics:
        tone = _metric_tone_for_label(label, value)
        icon = _METRIC_ICONS.get(label, "📌")
        if isinstance(value, float):
            display = f"{value:.4f}".rstrip("0").rstrip(".")
        else:
            display = _esc(value)
        cards.append(
            f"""
            <div class="lotoia-cml-metric-card tone-{tone}">
              <span class="lotoia-cml-metric-badge {tone}">{_badge_label(tone)}</span>
              <div class="lotoia-cml-metric-icon">{icon}</div>
              <div class="lotoia-cml-metric-label">{_esc(label)}</div>
              <div class="lotoia-cml-metric-value">{display}</div>
            </div>
            """
        )
    st.markdown(
        f'<div class="lotoia-cml-metric-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


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
    st.markdown(
        f"""
        <div class="lotoia-cml-verdict {tone}">
          <div class="lotoia-cml-verdict-title">{_esc(headline)}</div>
          <div class="lotoia-cml-verdict-copy">
            <strong>Veredito ML:</strong> {_esc(normalized)}<br/>
            {_esc(reason)}
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
    if not plan_items:
        st.markdown(
            '<div class="lotoia-cml-section-sub">Nenhum plano pendente — aguardando evidências da Cobertura Estrutural.</div>',
            unsafe_allow_html=True,
        )
        return
    items = "".join(f"<li>{_esc(item)}</li>" for item in plan_items)
    st.markdown(f'<ol class="lotoia-cml-plan-list">{items}</ol>', unsafe_allow_html=True)


def render_constitutional_chip_row(chips: list[tuple[str, str, str]]) -> None:
    pills = []
    for label, value, tone in chips:
        pills.append(
            f'<span class="lotoia-pill lotoia-pill-{tone}">{_esc(label)}: {_esc(value)}</span>'
        )
    st.markdown(f'<div class="lotoia-cml-chip-row">{"".join(pills)}</div>', unsafe_allow_html=True)


def begin_section_shell() -> None:
    st.markdown('<div class="lotoia-cml-section-shell">', unsafe_allow_html=True)


def end_section_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
