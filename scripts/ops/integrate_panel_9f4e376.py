#!/usr/bin/env python3
"""Integrate structural coverage + sidebar from commit 9f4e376 into institutional_app."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "dashboard" / "institutional_app.py"
PORT = ROOT / "dashboard"

HELPER_FILES = (
    "_port_ml_source_caption.py",
    "_port_ml_adm_user.py",
    "_port_evidence_base.py",
    "_port_ranking_tables.py",
    "_port_central_ml.py",
)

SIDEBAR = '''def _render_sidebar(page: str, snapshot: dict[str, Any]) -> str:
    _apply_institutional_styles()
    _render_sidebar_logo()
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-nav-hint">Navegação institucional</div>', unsafe_allow_html=True)
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption(f"commit={_resolve_active_commit()}")

    def _nav_entry(label: str, page_id: str | None = None, *, disabled: bool = False) -> None:
        resolved_page_id = page_id or PAGE_TARGETS.get(label, label)
        if st.sidebar.button(label, key=f"nav_{resolved_page_id}", disabled=disabled):
            st.session_state["institutional_page_id"] = str(resolved_page_id)
            st.rerun()

    st.sidebar.markdown('<div class="lotoia-sidebar-group">Núcleo Operacional</div>', unsafe_allow_html=True)
    for label, page_id in [
        ("Painel Inicial Institucional", "home"),
        ("Gerador ADM - Lei 15 Limpo", "clean_law15_generation"),
        ("Conferir Resultados", "conference"),
        ("Simular Resultados", "simulation"),
    ]:
        _nav_entry(label, page_id)

    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Históricos e Rastreabilidade</div>', unsafe_allow_html=True)
    for label, page_id in [
        ("Histórico Analítico", "history_analytical"),
        ("Histórico Institucional", "history_institutional"),
        ("Comparativos histórico", "comparative_history"),
    ]:
        _nav_entry(label, page_id)

    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Auditoria Observacional</div>', unsafe_allow_html=True)
    for label, page_id in [
        ("Auditoria Runtime", "audit"),
        ("Conferência por concurso", "audit_monitoring_conference"),
        ("Dezenas faltantes", "audit_monitoring_missing_numbers"),
        ("Dezenas sobrando", "audit_monitoring_extra_numbers"),
    ]:
        _nav_entry(label, page_id)

    st.sidebar.markdown('<div class="lotoia-sidebar-subgroup">Analítico observacional</div>', unsafe_allow_html=True)
    for label, page_id in [
        ("Benchmark resumido", "summary_benchmark"),
        ("Métricas HB", "hb_metrics"),
        ("Cobertura estrutural", "structural_coverage"),
    ]:
        _nav_entry(label, page_id)

    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-group">Diagnósticos ML</div>', unsafe_allow_html=True)
    for label, page_id in [
        ("Central de Diagnósticos ML", "central_ml_diagnostics"),
        ("Vazamento lateral", "audit_monitoring_side_leak"),
        ("Evolução 13 -> 14", "audit_monitoring_13_to_14"),
        ("Evolução 14 -> 15", "audit_monitoring_14_to_15"),
    ]:
        _nav_entry(label, page_id)
    st.sidebar.caption(
        "Camadas observacionais disponíveis. Não geram jogos, não recalibram Lei 15 e não alteram histórico."
    )

    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-sidebar-subgroup">Área bloqueada / restrita</div>', unsafe_allow_html=True)
    for label, page_id in [("Limpar Históricos", "clear_histories"), ("Apagar Histórico", "delete_history")]:
        _nav_entry(label, page_id)
    st.sidebar.caption("Ações destrutivas continuam protegidas pela confirmação interna da tela.")

    choice = _canonical_page_id(st.session_state.get("institutional_page_id") or page)
    allowed_pages = {
        "home",
        "fallback",
        "generation",
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
        "audit_monitoring_side_leak",
        "audit_monitoring_13_to_14",
        "audit_monitoring_14_to_15",
        "central_ml_diagnostics",
        "clear_histories",
        "delete_history",
    }
    if choice not in allowed_pages:
        choice = _canonical_page_id(page)
    if choice not in allowed_pages:
        choice = "fallback"
    st.session_state["institutional_page_id"] = choice
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice
'''

IMPORT_BLOCK = '''
from lotoia.governance.analysis_batch_labels import BATCH_LABEL_UI_OPTIONS
from lotoia.observability.card_structure_diagnostics import load_card_structure_diagnostics_from_db
from lotoia.observability.ml_diagnostic_panels import (
    ACTIVE_ALERT_STATUSES,
    ALERT_001,
    CENTRAL_EMPTY_NO_RECURRENT_MESSAGE,
    STATUS_PENDENTE,
    VERDICT_ACCEPT_DIAGNOSTIC,
    VERDICT_REJECT,
    VERDICT_REQUEST_MORE_EVIDENCE,
    _evidence_base_identifiable,
    build_central_ml_diagnostics_payload,
    list_ml_diagnostic_decisions,
    register_ml_diagnostic_verdict,
)
from dashboard.display_dataframe import make_arrow_safe_dataframe, strip_adm_technical_columns, strip_adm_technical_records
'''

RUNTIME_CONST = "RUNTIME_GENERATION_CARD_FORMATS = tuple(range(15, LEI15A_REGISTRATION_MAX_FORMAT + 1))\n"

MAIN_ROUTE = '''    elif page == "central_ml_diagnostics":
        _render_central_ml_diagnostics_page(snapshot)
'''


def _replace_function(text: str, name: str, new_body: str) -> str:
    pattern = rf"def {re.escape(name)}\(.*?\n(?:(?!^def ).*\n)*"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise SystemExit(f"function not found: {name}")
    return text[: match.start()] + new_body.rstrip() + "\n\n\n" + text[match.end() :]


def main() -> None:
    text = APP.read_text(encoding="utf-8")
    helpers = "\n\n".join((PORT / name).read_text(encoding="utf-8") for name in HELPER_FILES)
    cobertura = (PORT / "_port_cobertura.py").read_text(encoding="utf-8")

    if "BATCH_LABEL_UI_OPTIONS" not in text:
        anchor = "from lotoia.governance.lei15_15a_core_realignment_v3 import get_v3_mode"
        text = text.replace(anchor, anchor + IMPORT_BLOCK)

    if "RUNTIME_GENERATION_CARD_FORMATS" not in text:
        anchor = "LEI15A_REGISTRATION_PENDING_FORMATS = (21, 22, 23)"
        text = text.replace(anchor, anchor + "\n" + RUNTIME_CONST.rstrip())

    if "_render_structural_coverage_ranking_tables" not in text:
        marker = "def _render_cobertura_estrutural_page"
        text = _replace_function(text, "_render_cobertura_estrutural_page", helpers + "\n\n" + cobertura)
    else:
        if "_render_central_ml_diagnostics_page" not in text:
            insert_at = text.index("def _render_cobertura_estrutural_page")
            text = text[:insert_at] + helpers + "\n\n" + text[insert_at:]
        text = _replace_function(text, "_render_cobertura_estrutural_page", cobertura)

    text = _replace_function(text, "_render_sidebar", SIDEBAR)

    if 'elif page == "central_ml_diagnostics"' not in text:
        anchor = '    elif page == "structural_coverage":\n        _render_cobertura_estrutural_page(snapshot)'
        text = text.replace(
            anchor,
            MAIN_ROUTE.rstrip() + "\n" + anchor,
        )

    APP.write_text(text, encoding="utf-8")
    print("integrated", APP)


if __name__ == "__main__":
    main()
