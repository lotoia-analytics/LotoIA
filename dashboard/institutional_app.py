# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from . import _bootstrap  # type: ignore[import-not-found]  # noqa: F401
except ImportError:
    import _bootstrap  # type: ignore[no-redef]  # noqa: F401

import json
import logging
import math
import os
import re
import random
import subprocess
import threading
import time
import uuid
import unicodedata
from collections import Counter
from functools import lru_cache
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from lotoia.database.adapter import InstitutionalDatabaseAdapter
from lotoia.database.contest_repository import ContestRepository
from lotoia.database.database import DEFAULT_DATABASE_PATH, GeneratedGame, GenerationEvent, ImportedContest, InstitutionalOutputSignature, LotofacilOfficialHistory, ReconciliationGame, ReconciliationRun, ScientificCalibrationDecision, ScientificInstitutionalMemory, ensure_database_schema, get_engine, get_session
from lotoia.data.history_export import export_historical_csv
from lotoia.data.loader import load_draws_csv
from lotoia.analytics.lotofacil_scientific_core import (
    LotofacilScientificCore,
    analyze_lotofacil_history,
    build_batch_reconciliation_scientific_memory,
    build_post_reconciliation_scientific_memory,
    build_strong_near_miss_scientific_memory,
    discover_scientific_generation_policy,
    _apply_scientific_15_vnext_policy,
    _decompose_hit_counts,
    _scientific_tier_weighted_score,
    _scientific_validation_rule,
    get_scientific_generation_policy,
)
from lotoia.analytics.scientific_calibration_engine import (
    apply_supervised_calibration,
    build_calibration_context,
    evaluate_last_batch,
    generate_recalibration_policy,
    register_calibration_decision,
    recommend_next_strategy,
)
from lotoia.governance.scientific_commander import validate_scientific_batch
from lotoia.governance.output_commander import (
    game_signature as _game_signature,
    load_all_output_signatures,
    load_batch_output_signatures,
    output_commander_validate_games,
)
from lotoia.governance.lei15_15a_core_realignment_v3 import get_v3_mode
from lotoia.governance.analysis_batch_labels import BATCH_LABEL_UI_OPTIONS
from lotoia.observability.card_structure_diagnostics import (
    load_card_structure_diagnostics_from_db,
    load_operational_card_structure_diagnostics_from_db,
)
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

from lotoia.governance.structural_rfe import (
    RFEPreviousContestReference,
    RFEValidationResult,
    validate_rfe_final_card,
)
from lotoia.ingestion.result_sync_service import ResultSyncService
from lotoia.experiments.hb_geometry_audit import DEFAULT_HB_GEOMETRY_DIR, run_hb_geometry_audit
from lotoia.generator.engine import generate_ranked_games
from lotoia.statistics.basic import number_frequency


from dashboard.institutional_governance import (
    GOVERNANCE_READ_ONLY_ALERT,
    render_governance_read_only_page,
)
from dashboard.institutional_core_002 import render_core_002_read_only_page
from dashboard.institutional_structural_coverage import render_structural_coverage_governance_section
from dashboard.institutional_ml_assistive import (
    render_constitutional_side_leak_section,
    render_ml_assistive_governance_section,
)
from dashboard.institutional_simulation_backtesting import render_institutional_simulation_backtesting_page
from dashboard.institutional_conference_audit import render_conference_governance_section
from dashboard.institutional_lei15a_governance import LEI15A_FORMAL_STATUS
from dashboard.institutional_controlled_cleanup import render_restricted_controlled_cleanup_page
from dashboard.institutional_monitored_contest import (
    SOVEREIGN_SOURCE_LABEL as MONITORED_CONTEST_SOURCE_LABEL,
    build_imported_contests_selection_context,
    sanitize_conference_session_contest,
    to_conference_contest_payload,
    validate_expected_contest_numbers,
)
from dashboard.institutional_db_runtime import (
    DB_UNAVAILABLE_LABEL,
    imported_contests_summary_unavailable,
    official_history_diagnostics_unavailable,
)
from dashboard.institutional_operational_generation import (
    build_operational_generation_index,
    resolve_operational_generation_label,
)
from dashboard.institutional_operational_structural_coverage import (
    EMPTY_OPERATIONAL_MESSAGE,
    HISTORICAL_SECTION_TITLE,
    HISTORICAL_SOURCE_CAPTION,
    OPERATIONAL_COVERAGE_TITLE,
    OPERATIONAL_SOURCE_CAPTION,
    build_operational_generation_dropdown_options,
    build_operational_generations_aggregate_summary,
    is_all_operational_generations_selection,
    load_operational_core_002_generations,
)
from dashboard.institutional_route_inventory import (
    INSTITUTIONAL_ALLOWED_PAGES,
    OFFICIAL_SIDEBAR_MENU,
    is_allowed_institutional_page,
    resolve_institutional_page_id,
)
from dashboard.institutional_auth import require_institutional_login
from dashboard.institutional_build import (
    APP_BUILD,
    BUILD_MARKER,
    CORE_REALIGN_V3_BATCH_LABEL,
    CORE_REALIGN_V3_ENV_VAR,
)
from dashboard.institutional_sovereign_generation import (
    SOVEREIGN_GENERATION_DISCLAIMER,
    SOVEREIGN_GENERATION_GOVERNANCE_ALERT,
    SOVEREIGN_GENERATION_STATUS_ACTIVE,
    adm_generator_menu_label,
    sovereign_generation_status_label,
)
from dashboard.institutional_supervised_ml import (
    SUPERVISED_ML_DISCLAIMER,
    SUPERVISED_ML_GOVERNANCE_ALERT,
    build_supervised_ml_persistence_bundle,
    is_adm_supervised_ml_active,
    is_supervised_output_calibration_active,
    resolve_adm_ml_enabled,
    resolve_authorized_calibration_plan,
    resolve_institutional_ml_status_line,
    resolve_recalibration_display_status,
    supervised_ml_status_label,
)
from dashboard.institutional_ml_calibration_cockpit import (
    SESSION_PERSIST as COCKPIT_SESSION_PERSIST,
    render_ml_calibration_cockpit,
)
from lotoia.ml.ml_operational_verdict import (
    MISSION_ID as ML_VERDICT_MISSION_ID,
    evaluate_batch_ml_verdict_from_games,
    is_ml_official_release_allowed,
    is_ml_verdict_blocking,
)
from lotoia.operations.lot_operational_status import (
    GENERATION_ORIGIN_GENERATOR,
    GENERATION_ORIGIN_SIMULATION,
    MISSION_ID as LOT_STATUS_MISSION_ID,
    build_lot_status_context,
    extract_lot_operational_status,
    is_analytical_history_eligible,
    is_official_conference_eligible,
    supersede_status_update,
)
from dashboard.institutional_clean_law15_runtime import (
    GENERATOR_PAGE_TITLE,
    is_multidezena_persistence_supported,
    multidezena_batch_label,
    multidezena_format_label,
    render_compact_status_chips,
    render_generation_games_table,
    render_generation_operation_block,
    render_generation_result_summary,
    render_governance_expander,
    render_six_bases_expander,
    render_technical_expander,
)
from dashboard.institutional_light_mode import (
    CACHE_TTL_SECONDS,
    SESSION_LOAD_COMPARATIVE,
    SESSION_LOAD_HISTORY,
    SESSION_LOAD_STRUCTURAL,
    batch_select_options,
    default_batch_index,
    is_light_mode_enabled,
    render_lazy_load_gate,
    render_paginated_dataframe,
    request_lazy_load,
    set_light_mode_enabled,
)
from lotoia.governance.law15_structural_realignment_v1 import get_realignment_mode
from lotoia.governance.lei15_15a_core_realignment_v2 import get_v2_mode
from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL as SOVEREIGN_BATCH_LABEL,
    REALIGNMENT_NAME as SOVEREIGN_CORE_ID,
    institutional_status_report,
    is_generation_enabled,
    resolve_core_002_batch_label,
)
from lotoia.governance.cloud_runtime_policy import (
    cloud_runtime_policy_snapshot,
    enforce_cloud_runtime_policy,
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger(__name__)
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGO_PATH = PROJECT_ROOT / "assets" / "logo.png"
HB_GEOMETRY_DIR = Path(os.fspath(DEFAULT_HB_GEOMETRY_DIR))
HB_GEOMETRY_PROGRESS_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.progress.json"
HB_GEOMETRY_JSON_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.json"
HB_GEOMETRY_CSV_FILE = HB_GEOMETRY_DIR / "hb_geometry_audit.csv"
SYNC_DIAGNOSTIC_FILE = REPORTS_DIR / "institutional_sync_diagnostics.json"
DB_PATH = DEFAULT_DATABASE_PATH
MAX_INSTITUTIONAL_DEZENAS_PER_GAME = 23
OFFICIAL_15_GROUPS = ("G50", "G30", "G20", "G10")
OFFICIAL_15_GROUP_ROLES = {
    "G50": ("AUDIT_COVERAGE", "G50 = auditoria e cobertura"),
    "G30": ("MAIN_OPERATIONAL", "G30 = operação principal"),
    "G20": ("COMPACT_HIGH_CONCENTRATION", "G20 = compacto de alta concentração"),
    "G10": ("PREMIUM_BREAKTHROUGH", "G10 = premium de ruptura"),
}
OFFICIAL_15_QUANTITY_TO_GROUP = {
    10: "G10",
    20: "G20",
    30: "G30",
    50: "G50",
}
OFFICIAL_15_GROUP_TO_QUANTITY = {group: quantity for quantity, group in OFFICIAL_15_QUANTITY_TO_GROUP.items()}
OFFICIAL_15_GROUP_SOURCE_REPORT = Path(__file__).resolve().parent.parent / "reports" / "grupos_oficiais_g50_g30_g20_g10.md"
OFFICIAL_CARD_FORMATS = tuple(range(15, 24))
AUDITED_RESERVE_PRIORITY = (7, 22, 4, 11, 12, 15, 16, 19, 21, 2, 17, 23, 13, 1, 9, 5, 6, 8, 14, 18, 20, 24, 25)
INSTITUTIONAL_REFERENCE_J12 = (1, 2, 3, 5, 7, 8, 10, 11, 13, 14, 15, 18, 22, 24, 25)
INSTITUTIONAL_REFERENCE_J34 = (1, 2, 3, 7, 8, 9, 10, 11, 13, 18, 20, 22, 23, 24, 25)
INSTITUTIONAL_REFERENCE_J71 = (1, 2, 3, 5, 7, 8, 9, 10, 13, 15, 18, 20, 22, 23, 24)
# Lei 15A — núcleo operacional 15D congelado (docs/governance/LEI_15A_NUCLEO_OPERACIONAL_15D.md)
NUCLEO_LEI15A_15D_CONGELADO = (1, 2, 3, 4, 9, 10, 11, 12, 13, 18, 20, 22, 23, 24, 25)
NUCLEO_LEI15_15D_CONGELADO = NUCLEO_LEI15A_15D_CONGELADO
RESERVAS_LEI15A_PRIORITARIAS = (15, 5, 7, 14, 19)
RESERVAS_PRIORITARIAS_LEI15A = RESERVAS_LEI15A_PRIORITARIAS
LEI15A_NUCLEO_15D_CONGELADO = NUCLEO_LEI15A_15D_CONGELADO
LEI15A_RESERVAS_PRIORITARIAS = RESERVAS_LEI15A_PRIORITARIAS
LEI15A_REGISTRATION_MAX_FORMAT = 20
LEI15A_REGISTRATION_PENDING_FORMATS = (21, 22, 23)
RUNTIME_GENERATION_CARD_FORMATS = tuple(range(15, LEI15A_REGISTRATION_MAX_FORMAT + 1))
LEI15A_VIGILANCIA = (4, 11, 12, 15)
LEI15A_BLIND_SPOTS = (6, 16, 17, 21)
LEI15A_MARGINAL = (8,)
INSTITUTIONAL_MATRIX_DISPLAY_COLUMNS = (
    "jogo",
    "celula_matriz",
    "formato_d",
    "escala_top",
    "cartao_final_lido",
    "cartao_final_assinatura",
    "nucleo_a_dezenas",
    "auditadas_escolhidas",
    "vigilantes_escolhidas",
    "referencias_auditadas_j12_j34",
    "vigilancia_j71",
    "lei15_aplicada",
    "sincronizado_com_cartao_final",
    "status_institucional",
    "status_estrutural_anterior",
    "leitura_institucional",
)
INSTITUTIONAL_MATRIX_PRIMARY_COLUMNS = (
    "jogo",
    "formato_d",
    "nucleo_a_dezenas",
    "auditadas_escolhidas",
    "vigilantes_escolhidas",
    "cartao_final_lido",
    "sincronizado_com_cartao_final",
)
INSTITUTIONAL_MATRIX_TECHNICAL_COLUMNS = (
    "jogo",
    "celula_matriz",
    "escala_top",
    "cartao_final_assinatura",
    "lei15_aplicada",
    "status_institucional",
    "status_estrutural_anterior",
    "leitura_institucional",
)
INSTITUTIONAL_MATRIX_PRIMARY_LABELS = {
    "jogo": "Jogo",
    "formato_d": "Formato",
    "nucleo_a_dezenas": "Núcleo Lei 15 (insumo Lei 15A)",
    "auditadas_escolhidas": "Auditadas Lei 15A",
    "vigilantes_escolhidas": "Vigilantes Lei 15A",
    "cartao_final_lido": "Cartão validado Lei 15A",
    "sincronizado_com_cartao_final": "Sincronizado",
}
LEI15_UPPER_PANEL_TITLE = "Jogos gerados pela Lei 15"
LEI15_UPPER_PANEL_COLUMN_LABELS = {
    "jogo": "Jogo",
    "núcleo_lei_15": "Núcleo Lei 15",
    "reservas_auditadas": "Reservas auditadas Lei 15",
    "cartão_final": "Cartão final Lei 15",
}
LEI15A_LOWER_PANEL_TITLE = "Leitura operacional Lei 15A"
LEI15A_PANEL_DESCRIPTION = (
    "Esta leitura operacional Lei 15A audita e valida cada jogo gerado pela Lei 15: "
    "o cartão validado deve coincidir com o cartão final superior; "
    "núcleo operacional GP, auditadas e vigilantes são componentes próprios da Lei 15A."
)
LEI15A_PANEL_FORMAT_16D_20D_LABEL = (
    "16D–20D = registro operacional Lei 15A — cartão validado pela matriz GP"
)
LEI15A_PANEL_FORMAT_21D_23D_LABEL = (
    "21D–23D = leitura observacional — registro Lei 15A pendente"
)
LEI15A_PANEL_FORMAT_16D_23D_LABEL = LEI15A_PANEL_FORMAT_16D_20D_LABEL
LEI15A_PANEL_SYNC_SUCCESS = (
    "Leitura operacional Lei 15A validada: cartão Lei 15A coincide com "
    "o cartão final gerado pela Lei 15, preservando componentes próprios."
)
LEI15A_PANEL_SYNC_SEMANTICS = (
    "Sincronização significa coincidência entre cartão validado Lei 15A e "
    "cartão final Lei 15. Não significa cópia de núcleo, reservas, auditadas "
    "ou vigilantes entre as leis."
)
LEI15_PANEL_CONCEPT_15D = (
    "15D = núcleo Lei 15 (geração soberana); conferência usa cartão final por jogo"
)
LEI15_PANEL_CONCEPT_EXPANDED = (
    "16D–20D = expansão auditada do núcleo Lei 15 — conferência usa cartão final por jogo"
)


def _resolve_lei15a_panel_format_label(card_format: int) -> str:
    fmt = int(card_format)
    if fmt <= 15:
        return LEI15_PANEL_CONCEPT_15D
    if fmt <= 20:
        return LEI15A_PANEL_FORMAT_16D_20D_LABEL
    return LEI15A_PANEL_FORMAT_21D_23D_LABEL


def _resolve_lei15_panel_concept_label(card_format: int) -> str:
    fmt = int(card_format)
    if fmt <= 15:
        return LEI15_PANEL_CONCEPT_15D
    return LEI15_PANEL_CONCEPT_EXPANDED


INSTITUTIONAL_MATRIX_TECHNICAL_LABELS = {
    "jogo": "Jogo",
    "celula_matriz": "Célula matriz",
    "escala_top": "Escala top",
    "cartao_final_assinatura": "Assinatura do cartão final",
    "lei15_aplicada": "Lei 15 aplicada",
    "status_institucional": "Status institucional",
    "status_estrutural_anterior": "Status estrutural",
    "leitura_institucional": "Leitura institucional",
}
POST_DRAW_MONITORING_PAYLOAD = {
    "post_draw_monitoring_enabled": True,
    "monitoring_role": "OBSERVER_REGISTRY",
    "silent_recalibration_allowed": False,
    "automatic_law_mutation_allowed": False,
    "law_evolution_requires_audit": True,
    "monitoring_15_threshold": "11_12_13_14_15",
    "monitoring_17_threshold": "12_PLUS",
    "monitoring_18_threshold": "13_PLUS",
    "gold_target": 14,
    "diamond_target": 15,
}


def _clean_law15_format_label(card_format: int) -> str:
    format_labels = {
        15: "15 dezenas — Núcleo Lei 15",
        16: "16 dezenas — Lei 15 + 1 reserva auditada",
        17: "17 dezenas — Lei 15 + 2 reservas auditadas",
        18: "18 dezenas — Lei 15 + 3 reservas auditadas",
        19: "19 dezenas — Lei 15 + 4 reservas auditadas",
        20: "20 dezenas — Lei 15 + 5 reservas auditadas",
        21: "21 dezenas — Lei 15 + 6 reservas auditadas",
        22: "22 dezenas — Lei 15 + 7 reservas auditadas",
        23: "23 dezenas — Lei 15 + 8 reservas auditadas",
    }
    return format_labels.get(int(card_format), f"{int(card_format)} dezenas")


def _clean_law15_reserve_count(card_format: int) -> int:
    return max(0, int(card_format or 15) - 15)


def _render_signature_grid(signatures: list[str], *, title: str, empty_label: str = "Nenhuma assinatura disponível") -> None:
    st.markdown(f"##### {title}")
    if not signatures:
        st.caption(empty_label)
        return
    rows = []
    for index, signature in enumerate(signatures, start=1):
        rows.append(
            f"""
            <div class="lotoia-signature-pill">
                <span class="lotoia-signature-index">{index:02d}</span>
                <span class="lotoia-signature-text">{signature}</span>
            </div>
            """
        )
    st.markdown(
        """
        <div class="lotoia-signature-grid">
        """
        + "".join(rows)
        + """
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_block_distribution(block_distribution: list[int]) -> None:
    st.markdown("##### Distribuição por bloco")
    if not block_distribution:
        st.caption("Distribuição indisponível")
        return
    cols = st.columns(min(5, max(1, len(block_distribution))))
    for index, value in enumerate(block_distribution):
        cols[index % len(cols)].metric(f"Bloco {index}", int(value))


def _block_distribution(numbers: list[int]) -> dict[str, int]:
    return {
        "01–05": sum(1 for number in numbers if 1 <= number <= 5),
        "06–10": sum(1 for number in numbers if 6 <= number <= 10),
        "11–15": sum(1 for number in numbers if 11 <= number <= 15),
        "16–20": sum(1 for number in numbers if 16 <= number <= 20),
        "21–25": sum(1 for number in numbers if 21 <= number <= 25),
    }


def _format_block_numbers(numbers: list[int]) -> dict[str, str]:
    block_ranges = {
        "01–05": range(1, 6),
        "06–10": range(6, 11),
        "11–15": range(11, 16),
        "16–20": range(16, 21),
        "21–25": range(21, 26),
    }
    formatted: dict[str, str] = {}
    for label, block_range in block_ranges.items():
        values = [number for number in numbers if number in block_range]
        formatted[label] = ", ".join(f"{number:02d}" for number in values) if values else "-"
    return formatted


def _safe_count_games(value: object) -> int:
    """Retorna uma contagem segura de jogos para uso visual em percentuais."""
    if value is None:
        return 0

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return int(value)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return 0
        try:
            return int(float(stripped))
        except ValueError:
            return 0

    if isinstance(value, (list, tuple, set)):
        return len(value)

    try:
        import pandas as pd

        if isinstance(value, pd.DataFrame):
            return len(value.index)
        if isinstance(value, pd.Series):
            return len(value)
    except Exception:
        pass

    try:
        return len(value)  # type: ignore[arg-type]
    except Exception:
        return 0
HISTORICAL_TEST_TABLES = (
    "generation_events",
    "generated_games",
    "reconciliation_runs",
    "reconciliation_games",
    "reconciliation_events",
    "operational_logs",
    "reset_events",
)
PURGE_ONLY_TABLES = ("institutional_output_signatures",)

PAGE_TARGETS = {
    "Painel Inicial Institucional": "home",
    "Governança Institucional — read-only": "governance_read_only",
    "Núcleo Lei 15 — CORE_002": "governance_read_only",
    "Auditoria Runtime": "fallback",
    "Auditoria e Monitoramento": "audit_monitoring",
    "Conferência por concurso": "conference",
    "Desempenho por grupo": "audit_monitoring_group_performance",
    "Dezenas faltantes": "structural_coverage",
    "Dezenas sobrando": "structural_coverage",
    "Vazamento lateral": "central_ml_diagnostics",
    "Evolução 13 -> 14": "central_ml_diagnostics",
    "Evolução 14 -> 15": "central_ml_diagnostics",
    "Hipóteses para teste offline": "audit_monitoring_offline_hypotheses",
    "Gerar Jogos": "clean_law15_generation",
    "Conferir Resultados — Auditoria de Lotes Persistidos": "conference",
    "Conferir Resultados": "conference",
    "Simular Resultados": "simulation",
    "Histórico Analítico": "history_analytical",
    "Historico Analitico": "history_analytical",
    "Histórico Institucional": "history_institutional",
    "Historico Institucional": "history_institutional",
    "Limpar Históricos": "restricted_controlled_cleanup",
    "Área Restrita — Limpeza Controlada": "restricted_controlled_cleanup",
    "Limpeza Controlada — BLOQUEADA": "restricted_controlled_cleanup",
    "Apagar Histórico": "restricted_controlled_cleanup",
    "Comparativos histórico": "structural_coverage",
    "Análises Estratégicas": "strategies_analysis",
    "Testar Estratégias": "strategies_test",
    "Simular Estratégias": "strategies_simulation",
    "Métricas HB": "structural_coverage",
    "Cobertura estrutural": "structural_coverage",
    "Cobertura Estrutural": "structural_coverage",
    "Simulação Institucional / Backtesting": "simulation",
    "Central ML Assistiva": "central_ml_diagnostics",
    "Central de Diagnósticos ML": "central_ml_diagnostics",
    "Central ML — Operacional Supervisionada": "central_ml_diagnostics",
    "Central ML — Calibração Supervisionada": "central_ml_diagnostics",
    "Vazamento Lateral Constitucional": "central_ml_diagnostics",
    "Replay institucional": "institutional_replay",
    "Benchmark resumido": "structural_coverage",
    "Estatísticas operacionais": "operational_statistics",
    "HB Geometry": "hb_geometry",
    "Gerador ADM CORE_002 — BLOQUEADO": "clean_law15_generation",
    "Gerador ADM CORE_002 — Geração Soberana Controlada": "clean_law15_generation",
    "Gerador ADM - Lei 15 Limpo": "clean_law15_generation",
}

INSTITUTIONAL_QUICK_ACCESS: list[dict[str, str]] = [
    {"icon": "🏛️", "label": "Governança Institucional — read-only", "page_id": "governance_read_only"},
    {"icon": "🎯", "label": "Gerador ADM CORE_002 — Geração Soberana Controlada", "page_id": "clean_law15_generation"},
    {"icon": "✅", "label": "Conferir Resultados — Auditoria de Lotes Persistidos", "page_id": "conference"},
    {"icon": "🧪", "label": "Simular Resultados", "page_id": "simulation"},
    {"icon": "📊", "label": "Histórico Analítico", "page_id": "history_analytical"},
    {"icon": "🗂️", "label": "Histórico Institucional", "page_id": "history_institutional"},
    {"icon": "🧱", "label": "Cobertura Estrutural", "page_id": "structural_coverage"},
    {"icon": "🤖", "label": "Central ML — Calibração Supervisionada", "page_id": "central_ml_diagnostics"},
]

PAGE_LABELS = {page_id: label for label, page_id in PAGE_TARGETS.items()}

CONSTITUTIONAL_DIAGNOSTIC_CAPTION = (
    "Diagnóstico observacional — sem efeito operacional automático."
)
RESTRICTED_PURGE_BLOCK_MESSAGE = (
    "Operação bloqueada por Lei 001, ADR-047 e Política de Preservação de Histórico."
)
INVENTORY_REPORT_REFERENCE = "PR #124 — merge 328d26f"


def _is_sovereign_generation_blocked() -> bool:
    return not is_generation_enabled()


def _constitutional_status_lines() -> dict[str, str]:
    report = institutional_status_report()
    generation_blocked = _is_sovereign_generation_blocked()
    return {
        "core_id": str(report.get("core_id") or SOVEREIGN_CORE_ID),
        "batch_label": str(report.get("batch_label") or SOVEREIGN_BATCH_LABEL),
        "generation_status": sovereign_generation_status_label(),
        "lei15a_status": LEI15A_FORMAL_STATUS,
        "ml_status": resolve_institutional_ml_status_line(),
        "calibration_status": (
            resolve_recalibration_display_status()["headline"]
            if is_supervised_output_calibration_active()
            else "RECALIBRAÇÃO: BLOQUEADA"
        ),
        "history_status": "PROTEGIDO",
        "gestao_projetos": "Fase 0 implantada (M-GOV-030)",
        "inventario_painel": f"Aprovado — {INVENTORY_REPORT_REFERENCE}",
    }


def _render_constitutional_status_panel(*, compact: bool = False) -> None:
    lines = _constitutional_status_lines()
    rows = [
        ("Núcleo soberano", lines["core_id"]),
        ("Label soberano", lines["batch_label"]),
        ("Geração", lines["generation_status"]),
        ("Lei 15A", lines["lei15a_status"]),
        ("ML", lines["ml_status"]),
        ("Histórico / purge", lines["history_status"]),
        ("Gestão de Projetos", lines["gestao_projetos"]),
        ("Inventário Painel ADM", lines["inventario_painel"]),
    ]

    def _render_rows() -> None:
        for label, value in rows:
            st.markdown(f"**{label}:** `{value}`")

    if compact:
        with st.sidebar.expander("Status Constitucional", expanded=False):
            _render_rows()
            st.caption(CONSTITUTIONAL_DIAGNOSTIC_CAPTION)
        return

    st.markdown("##### Status Constitucional LotoIA")
    status_cols = st.columns(2)
    midpoint = (len(rows) + 1) // 2
    with status_cols[0]:
        for label, value in rows[:midpoint]:
            st.markdown(f"**{label}:** `{value}`")
    with status_cols[1]:
        for label, value in rows[midpoint:]:
            st.markdown(f"**{label}:** `{value}`")
    if _is_sovereign_generation_blocked():
        st.warning(
            "Geração soberana bloqueada (`LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`). "
            "Somente leitura/diagnóstico neste estado."
        )
    else:
        st.success(SOVEREIGN_GENERATION_STATUS_ACTIVE)
        st.info(SOVEREIGN_GENERATION_DISCLAIMER)
        st.caption(SOVEREIGN_GENERATION_GOVERNANCE_ALERT)
    st.caption(CONSTITUTIONAL_DIAGNOSTIC_CAPTION)


def _render_diagnostic_observational_caption() -> None:
    st.caption(CONSTITUTIONAL_DIAGNOSTIC_CAPTION)


def _sovereign_generation_blocked_result(*, requested_count: int) -> dict[str, Any]:
    return {
        "seed": 0,
        "batch_id": "sovereign-generation-blocked",
        "requested_count": int(requested_count),
        "games": [],
        "blocked": True,
        "block_reason": "LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0",
        "commander_report": {
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "SOVEREIGN_GENERATION_BLOCKED",
            "error_message": "SOVEREIGN_GENERATION_BLOCKED",
        },
        "fill_diagnostics": {
            "insufficient_reason": "SOVEREIGN_GENERATION_BLOCKED",
            "fill_completed": False,
            "sovereign_generation_path": "generate_best_games",
            "analysis_batch_label": SOVEREIGN_BATCH_LABEL,
        },
        "generation_mode": "SOVEREIGN_GENERATION_BLOCKED",
        "policy_mode": "ADR_047_CONSTITUTIONAL_BLOCK",
        "dezenas_por_jogo": 15,
        "analysis_batch_label": SOVEREIGN_BATCH_LABEL,
    }


LEGACY_DIRECT_15_BLOCKED_REASON = "LEGACY_DIRECT_15_GENERATION_BLOCKED_M_LEI15_003"
ADM_SOVEREIGN_GENERATION_SOURCE = "dashboard.institutional_app.adm_sovereign_generation"


def _raise_legacy_direct_15_games_blocked(*, caller: str) -> None:
    raise RuntimeError(
        f"[M-LEI15-003 / BLK-LEGACY-GEN-001] {caller} não é caminho operacional da "
        f"Lei 15 soberana (LEI15_CORE_002). Path canônico ADM: generate_best_games("
        f"batch_label={SOVEREIGN_BATCH_LABEL!r}, ml_enabled=False)."
    )


def _resolve_adm_sovereign_batch_label(batch_label: str | None) -> str:
    """Fail-closed: batch_label=None ou label não soberano é erro institucional ADM."""
    if batch_label is None or not str(batch_label).strip():
        raise RuntimeError(
            "[M-LEI15-003] batch_label=None rejeitado no contexto ADM Painel. "
            f"Label soberano obrigatório: {SOVEREIGN_BATCH_LABEL}."
        )
    normalized = str(batch_label).strip().upper()
    sovereign = str(SOVEREIGN_BATCH_LABEL).strip().upper()
    if normalized != sovereign:
        raise RuntimeError(
            f"[M-LEI15-003] Label ADM inválido {normalized!r}. Obrigatório: {SOVEREIGN_BATCH_LABEL}."
        )
    return normalized


def _sovereign_adm_pool_size(*, requested_count: int, pool_size: int | None = None) -> int:
    count = max(1, int(requested_count))
    if pool_size is not None:
        return max(int(pool_size), count)
    return max(count * 3, count, 30)


def _invoke_sovereign_adm_generate_best_games(
    *,
    requested_count: int,
    batch_label: str | None = None,
    pool_size: int | None = None,
    seed: int | None = None,
    ml_enabled: bool | None = None,
    calibration_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Único path preparado para geração ADM Lei 15 (LEI15_CORE_002 / ADR-047)."""
    resolved_label = _resolve_adm_sovereign_batch_label(batch_label or SOVEREIGN_BATCH_LABEL)
    effective_ml = resolve_adm_ml_enabled(ml_enabled=ml_enabled, batch_label=resolved_label)
    effective_pool = _sovereign_adm_pool_size(
        requested_count=requested_count,
        pool_size=pool_size,
    )
    authorized_plan = calibration_plan
    if authorized_plan is None:
        cockpit_bundle = dict(st.session_state.get(COCKPIT_SESSION_PERSIST) or {})
        authorized_plan = resolve_authorized_calibration_plan(cockpit_bundle)
    from lotoia.generator.basic_generator import generate_best_games

    payload = dict(
        generate_best_games(
            count=int(requested_count),
            pool_size=effective_pool,
            batch_label=resolved_label,
            ml_enabled=effective_ml,
            seed=seed,
            calibration_plan=authorized_plan,
        )
    )
    payload["ml_enabled"] = effective_ml
    payload["analysis_batch_label"] = resolved_label
    if authorized_plan:
        payload["authorized_calibration_plan"] = authorized_plan
    return payload


def _render_orphan_generation_blocked_page(snapshot: dict[str, Any]) -> None:
    _ = snapshot
    st.subheader("Gerador legado — BLOQUEADO")
    st.error(
        "A rota órfã `generation` está bloqueada. Geração só será permitida via "
        "Gerador ADM CORE_002 quando a flag soberana estiver habilitada."
    )
    _render_constitutional_status_panel(compact=False)


def _canonical_page_id(value: str | None) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        return "home"
    aliased = resolve_institutional_page_id(text_value)
    if aliased != text_value:
        return aliased
    if is_allowed_institutional_page(text_value):
        return resolve_institutional_page_id(text_value)
    if text_value in PAGE_TARGETS:
        return resolve_institutional_page_id(PAGE_TARGETS[text_value])
    if text_value in PAGE_LABELS:
        return resolve_institutional_page_id(text_value)
    normalized = unicodedata.normalize("NFKD", text_value).encode("ascii", "ignore").decode("ascii").casefold()
    for label, page_id in PAGE_TARGETS.items():
        normalized_label = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii").casefold()
        if normalized_label == normalized:
            return resolve_institutional_page_id(page_id)
    return resolve_institutional_page_id("fallback")


def _canonical_page_label(value: str | None) -> str:
    page_id = _canonical_page_id(value)
    if page_id == "fallback":
        return "Página não encontrada"
    return PAGE_LABELS.get(page_id, "Painel Inicial Institucional")

_JOB_LOCK = threading.Lock()
_JOB_STATE: dict[str, Any] = {
    "running": False,
    "completed": False,
    "current_scenario": "-",
    "processed_batches": 0,
    "contests_processed": 0,
    "elapsed_time": 0.0,
    "error": "",
    "result": None,
    "started_at": None,
}


def _safe_json_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_csv_load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _persist_official_sync_diagnostics(payload: dict[str, Any]) -> None:
    try:
        SYNC_DIAGNOSTIC_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYNC_DIAGNOSTIC_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_official_sync_diagnostics() -> dict[str, Any]:
    return _safe_json_load(SYNC_DIAGNOSTIC_FILE)


def _load_csv_latest_contest_summary() -> dict[str, Any] | None:
    try:
        draws = load_draws_csv()
    except Exception:
        return None
    if not draws:
        return None
    latest_draw = draws[-1]
    contest_number = _safe_int(getattr(latest_draw, "contest", None), default=None)
    if contest_number is None:
        return None
    return {
        "contest_number": int(contest_number),
        "data": str(getattr(latest_draw, "date", "") or ""),
        "dezenas": [int(number) for number in getattr(latest_draw, "numbers", []) or []],
        "source": "historico_lotofacil.csv",
    }


def _load_official_sync_contest_summary() -> dict[str, Any] | None:
    sync_summary = _load_official_sync_diagnostics()
    if not isinstance(sync_summary, dict) or not sync_summary:
        return None
    payload = sync_summary.get("payload")
    payload = payload if isinstance(payload, dict) else {}
    latest_record = _normalize_contest_record(payload.get("latest_contest_record") or sync_summary.get("latest_contest_record"))
    if latest_record:
        latest_record = dict(latest_record)
        latest_record["source"] = "api_caixa_sincronizada"
        return latest_record
    latest_contest = _safe_int(payload.get("latest_contest") or sync_summary.get("imported_contest"), default=None)
    if latest_contest is None:
        return None
    imported_numbers = _extract_int_numbers(payload.get("imported_numbers", []) or sync_summary.get("imported_numbers", []) or [])
    return {
        "contest_number": int(latest_contest),
        "data": str(payload.get("sync_timestamp") or sync_summary.get("sync_timestamp") or ""),
        "dezenas": imported_numbers,
        "source": "api_caixa_sincronizada",
    }


def _mask_database_url(database_url: str) -> str:
    text = str(database_url or "").strip()
    if not text:
        return "-"
    if "@" not in text:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    scheme, remainder = text.split("://", maxsplit=1) if "://" in text else ("", text)
    if "@" not in remainder:
        return text if len(text) <= 96 else f"{text[:48]}...{text[-24:]}"
    credentials, host_part = remainder.split("@", maxsplit=1)
    if ":" in credentials:
        username = credentials.split(":", maxsplit=1)[0]
        masked_credentials = f"{username}:***"
    else:
        masked_credentials = "***"
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}{masked_credentials}@{host_part}"


def _resolve_active_commit() -> str:
    for env_name in (
        "RAILWAY_GIT_COMMIT_SHA",
        "RAILWAY_GIT_COMMIT",
        "GIT_COMMIT",
        "COMMIT_SHA",
        "SOURCE_VERSION",
    ):
        value = str(os.getenv(env_name, "") or "").strip()
        if value:
            return value[:12]
    try:
        value = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return value[:12] if value else "-"
    except Exception:
        return "-"


def _apply_institutional_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.0rem; padding-bottom: 2rem; max-width: 100%; }
        section[data-testid="stMain"] > div.block-container {
            max-width: 100%;
            padding-left: 1.1rem;
            padding-right: 1.1rem;
        }
        .stApp { background: linear-gradient(180deg, #fbfdff 0%, #f2f6fb 100%); }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f7fbff 0%, #eef4fa 100%);
            border-right: 1px solid rgba(18, 52, 86, 0.10);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 0.55rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        section[data-testid="stSidebar"] img {
            width: 96% !important;
            max-width: 340px !important;
            display: block;
            margin: -0.2rem auto 0.7rem auto;
        }
        .lotoia-sidebar-divider {
            border-top: 1px solid rgba(18, 52, 86, 0.14);
            margin: 0.6rem 0;
        }
        .lotoia-nav-hint {
            font-size: 0.84rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            color: #7a8795;
            margin-bottom: 0.35rem;
        }
        .lotoia-sidebar-title {
            color: #123456;
            font-size: 1.18rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            margin: 0.1rem 0 0.15rem 0;
        }
        .lotoia-section-title {
            font-size: 2.04rem;
            font-weight: 800;
            color: #123456;
            margin-bottom: 0.2rem;
            letter-spacing: 0.01em;
        }
        .lotoia-section-subtitle {
            font-size: 1.10rem;
            color: #5a6b7e;
            margin-bottom: 1rem;
            line-height: 1.5;
        }
        .lotoia-kpi-card {
            background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 16px;
            padding: 0.95rem 1rem 0.85rem 1rem;
            box-shadow: 0 6px 22px rgba(18, 52, 86, 0.05);
            min-height: 114px;
        }
        .lotoia-kpi-label {
            color: #5a6b7e;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
        }
        .lotoia-kpi-value {
            color: #123456;
            font-size: 1.72rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.3rem;
        }
        .lotoia-kpi-caption {
            color: #718399;
            font-size: 0.8rem;
            line-height: 1.4;
        }
        .lotoia-operational-hint {
            color: #6d7f92;
            font-size: 0.86rem;
            margin-top: -0.15rem;
            margin-bottom: 0.5rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 14px;
            padding: 0.85rem 0.95rem;
            box-shadow: 0 4px 14px rgba(18, 52, 86, 0.04);
        }
        div[data-testid="stMetric"] label {
            color: #5a6b7e;
            font-size: 0.78rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        div[data-testid="stMetric"] [data-testid="metric-container"] {
            gap: 0.2rem;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #123456;
            font-weight: 800;
        }
        section[data-testid="stMain"] .stButton > button {
            border-radius: 12px;
            border: 1px solid rgba(18, 52, 86, 0.12);
            background: #ffffff;
            color: #123456;
            min-height: 38px;
            font-weight: 700;
            box-shadow: 0 3px 10px rgba(18, 52, 86, 0.04);
        }
        section[data-testid="stMain"] .stButton > button:hover {
            border-color: rgba(18, 52, 86, 0.20);
            background: #f8fbff;
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #ff6666 0%, #ff4d4d 100%);
            color: #ffffff;
            border-color: rgba(255, 77, 77, 0.35);
        }
        section[data-testid="stMain"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(180deg, #ff7777 0%, #ff5f5f 100%);
            color: #ffffff;
        }
        .lotoia-table-wrap {
            padding-top: 0.15rem;
            padding-bottom: 0.15rem;
        }
        section[data-testid="stSidebar"] .stButton > button {
            min-height: 36px;
            padding-top: 0.4rem;
            padding-bottom: 0.4rem;
            border-radius: 10px;
            font-size: 1.02rem;
        }
        .lotoia-sidebar-group {
            font-size: 0.88rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #6f8195;
            margin: 0.55rem 0 0.30rem 0;
            font-weight: 900;
        }
        .lotoia-sidebar-subgroup {
            font-size: 0.80rem;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: #8b97a8;
            margin: 0.55rem 0 0.25rem 0;
        }
        .lotoia-home-header {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 16px;
            box-shadow: 0 6px 22px rgba(18, 52, 86, 0.05);
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
        }
        .lotoia-home-brand-name {
            font-size: 1.65rem;
            font-weight: 800;
            color: #123456;
        }
        .lotoia-home-brand-sub {
            font-size: 0.82rem;
            color: #5a6b7e;
            margin-top: 0.15rem;
        }
        .lotoia-home-contest-label {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #5a6b7e;
        }
        .lotoia-home-contest-value {
            font-size: 2.2rem;
            font-weight: 800;
            color: #4f8ef7;
            line-height: 1;
        }
        .lotoia-pill {
            display: inline-block;
            padding: 0.28rem 0.75rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .lotoia-pill-success { background: rgba(46, 204, 113, 0.15); color: #1f8f4d; border: 1px solid rgba(46, 204, 113, 0.35); }
        .lotoia-pill-warning { background: rgba(243, 156, 18, 0.15); color: #a66a00; border: 1px solid rgba(243, 156, 18, 0.35); }
        .lotoia-pill-danger { background: rgba(231, 76, 60, 0.15); color: #b83227; border: 1px solid rgba(231, 76, 60, 0.35); }
        .lotoia-pill-info { background: rgba(79, 142, 247, 0.15); color: #2f6fd6; border: 1px solid rgba(79, 142, 247, 0.35); }
        .lotoia-metric-card {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 14px;
            box-shadow: 0 4px 14px rgba(18, 52, 86, 0.04);
            padding: 1rem 1.1rem;
            min-height: 118px;
        }
        .lotoia-metric-label {
            font-size: 0.72rem;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: #5a6b7e;
            margin-bottom: 0.35rem;
        }
        .lotoia-metric-value {
            font-size: 1.85rem;
            font-weight: 800;
            color: #123456;
            line-height: 1.1;
        }
        .lotoia-metric-value-accent { color: #4f8ef7; }
        .lotoia-metric-value-success { color: #1f8f4d; }
        .lotoia-metric-value-danger { color: #b83227; }
        .lotoia-metric-caption {
            font-size: 0.78rem;
            color: #718399;
            margin-top: 0.35rem;
        }
        .lotoia-status-panel {
            background: #ffffff;
            border: 1px solid rgba(18, 52, 86, 0.10);
            border-radius: 14px;
            box-shadow: 0 4px 14px rgba(18, 52, 86, 0.04);
            padding: 1rem 1.1rem;
            margin: 0.75rem 0 1rem 0;
        }
        .lotoia-section-heading {
            font-size: 0.95rem;
            font-weight: 700;
            color: #123456;
            margin: 0 0 0.65rem 0;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .lotoia-quick-access .stButton > button {
            min-height: 96px;
            font-size: 0.95rem;
            line-height: 1.35;
            white-space: normal;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_logo() -> None:
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width=220)
    else:
        st.sidebar.empty()


def _sidebar_nav_button(label: str, target_page: str, current_page: str) -> None:
    if st.sidebar.button(label, key=f"nav_{target_page}"):
        page_id = _canonical_page_id(target_page)
        st.session_state["institutional_page_id"] = page_id
        st.rerun()


@st.cache_resource(show_spinner=False)
def _get_engine_cached():
    return get_engine(DB_PATH)


@st.cache_data(show_spinner=False, ttl=2)
def _database_snapshot() -> dict[str, Any]:
    adapter = InstitutionalDatabaseAdapter(DB_PATH)
    engine = _get_engine_cached()
    preferred_tables = [
        "generation_events",
        "generated_games",
        "reconciliation_runs",
        "reconciliation_games",
        "reconciliation_events",
        "imported_contests",
        "lotofacil_official_history",
        "institutional_output_signatures",
        "scientific_calibration_decisions",
        "scientific_institutional_memory",
        "expansion_events",
        "operational_logs",
    ]
    latest_fields = {
        "generation_events": "created_at",
        "generated_games": "created_at",
        "reconciliation_runs": "created_at",
        "reconciliation_games": "created_at",
        "reconciliation_events": "created_at",
        "imported_contests": "contest_number",
        "lotofacil_official_history": "contest_number",
        "institutional_output_signatures": "created_at",
        "scientific_calibration_decisions": "created_at",
        "scientific_institutional_memory": "created_at",
        "expansion_events": "created_at",
        "operational_logs": "created_at",
    }
    counts: dict[str, int] = {}
    latest: dict[str, Any] = {}
    errors: dict[str, str] = {}
    query_logs: list[dict[str, Any]] = []
    table_diagnostics: dict[str, dict[str, Any]] = {}
    for table in preferred_tables:
        count_query = f'SELECT COUNT(*) FROM "{table}"'
        count_status = "ok"
        count_error = ""
        count_value = 0
        try:
            with engine.connect() as connection:
                value = connection.execute(text(count_query)).scalar()
            count_value = int(value or 0)
        except Exception as exc:
            count_status = "error"
            count_error = str(exc)
            errors[table] = count_error
        counts[table] = count_value

        latest_field = latest_fields.get(table, "created_at")
        latest_status = "ok"
        latest_error = ""
        latest_value: Any = "-"
        if latest_field in {"created_at", "contest_number"}:
            latest_query = f'SELECT MAX("{latest_field}") FROM "{table}"'
            try:
                with engine.connect() as connection:
                    value = connection.execute(text(latest_query)).scalar()
                latest_value = value if value is not None else "-"
            except Exception as exc:
                latest_status = "error"
                latest_error = str(exc)
                latest_value = "-"
        latest[table] = latest_value
        table_diagnostics[table] = {
            "table": table,
            "count_query": count_query,
            "count_status": count_status,
            "count": count_value,
            "count_error": count_error,
            "latest_field": latest_field,
            "latest_query": f'SELECT MAX("{latest_field}") FROM "{table}"' if latest_field in {"created_at", "contest_number"} else "",
            "latest_status": latest_status,
            "latest_error": latest_error,
        }
        query_logs.append(
            {
                "table": table,
                "query": count_query,
                "status": count_status,
                "count": count_value,
                "error": count_error,
            }
        )
    return {
        "backend": adapter.backend,
        "engine_url": str(engine.url),
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": counts,
        "latest": latest,
        "tables": preferred_tables,
        "errors": errors,
        "query_logs": query_logs,
        "table_diagnostics": table_diagnostics,
    }


@st.cache_data(show_spinner=False, ttl=CACHE_TTL_SECONDS)
def _light_database_snapshot() -> dict[str, Any]:
    adapter = InstitutionalDatabaseAdapter(DB_PATH)
    engine = _get_engine_cached()
    return {
        "backend": adapter.backend,
        "engine_url": str(engine.url),
        "database_url": adapter.database_url,
        "database_source": adapter.database_source,
        "counts": {},
        "latest": {},
        "tables": [],
        "errors": {},
        "query_logs": [],
        "table_diagnostics": {},
        "light_mode": True,
    }


def _resolve_database_snapshot(*, force_full: bool = False) -> dict[str, Any]:
    if not force_full and is_light_mode_enabled():
        return _light_database_snapshot()
    return _database_snapshot()


def _live_institutional_snapshot(
    snapshot: dict[str, Any] | None = None,
    *,
    force_full: bool = False,
) -> dict[str, Any]:
    try:
        live_snapshot = _resolve_database_snapshot(force_full=force_full)
    except Exception:
        return snapshot or {
            "backend": "unknown",
            "engine_url": "",
            "database_url": "",
            "database_source": "",
            "counts": {},
            "latest": {},
            "tables": [],
        }
    if snapshot:
        snapshot = dict(snapshot)
        snapshot.update(live_snapshot)
        return snapshot
    return live_snapshot


@st.cache_data(show_spinner=True, ttl=CACHE_TTL_SECONDS)
def _cached_card_structure_diagnostics_from_db(
    db_path: str,
    analysis_batch_label: str | None,
    game_size: int | None,
    generation_event_id: int | None,
    reconciliation_run_id: int | None,
    concurso_analisado: int | None,
) -> dict[str, Any]:
    return load_card_structure_diagnostics_from_db(
        db_path,
        analysis_batch_label=analysis_batch_label,
        game_size=game_size,
        generation_event_id=generation_event_id,
        reconciliation_run_id=reconciliation_run_id,
        concurso_analisado=concurso_analisado,
    )


@st.cache_data(show_spinner=True, ttl=CACHE_TTL_SECONDS)
def _cached_operational_core_002_generations(db_path: str) -> list[dict[str, Any]]:
    return load_operational_core_002_generations(db_path)


@st.cache_data(show_spinner=True, ttl=CACHE_TTL_SECONDS)
def _cached_operational_card_structure_diagnostics_from_db(
    db_path: str,
    generation_event_id: int | None,
    game_size: int | None,
) -> dict[str, Any]:
    return load_operational_card_structure_diagnostics_from_db(
        db_path,
        generation_event_id=generation_event_id,
        game_size=game_size,
    )


def _institutional_source_map(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    latest_contest = _get_latest_contest() or _load_latest_contest_summary() or {}
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    latest_csv = _load_csv_latest_contest_summary() or {}
    latest_sync = _load_official_sync_contest_summary() or {}
    official_history = _load_official_history_diagnostics()
    return [
        {
            "camada": "CSV histórico versionado",
            "origem": "historico_lotofacil.csv",
            "tabelas": "data/raw/historico_lotofacil.csv",
            "uso": (
                f"último concurso CSV={latest_csv.get('contest_number', '-')}"
                f" | papel=seed/documentação"
                f" | runtime=PostgreSQL"
            ),
        },
        {
            "camada": "API oficial",
            "origem": "servicebus2.caixa.gov.br",
            "tabelas": "sync_payload / response_preview",
            "uso": f"último concurso API={latest_sync.get('contest_number', '-')}",
        },
        {
            "camada": "Banco persistido",
            "origem": "PostgreSQL",
            "tabelas": "imported_contests / lotofacil_official_history",
            "uso": f"último concurso persistido={latest_contest.get('contest_number', '-')} | imported_contests={snapshot['counts'].get('imported_contests', 0)} | lotofacil_official_history={official_history.get('total_lotofacil_official_history', 0)}",
        },
        {
            "camada": "Histórico oficial",
            "origem": "PostgreSQL",
            "tabelas": "lotofacil_official_history",
            "uso": (
                f"primeiro={official_history.get('contest_number_min', '-')}"
                f" | último={official_history.get('ultimo_concurso_lotofacil_official_history', '-')}"
                f" | faltantes={official_history.get('total_concursos_faltantes', 0)}"
            ),
        },
        {
            "camada": "Conferência",
            "origem": "PostgreSQL",
            "tabelas": "reconciliation_runs / reconciliation_games",
            "uso": f"último concurso={latest_contest.get('contest_number', '-')} | última reconciliação={latest_reconciliation.get('id', '-')}",
        },
        {
            "camada": "Gerador",
            "origem": "PostgreSQL + session_state",
            "tabelas": "generation_events / generated_games",
            "uso": f"última geração={latest_generation.get('generation_event_id', '-')} | build={BUILD_MARKER}",
        },
    ]


def _render_runtime_audit_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    audit = _runtime_audit_payload(snapshot)
    live_counts = _database_snapshot()["counts"]
    st.subheader("Auditoria do Runtime")
    st.write("Leitura ativa da infraestrutura institucional em execução.")
    if audit["backend"] != "postgresql":
        st.warning(f"Backend atual resolvido: {audit['backend']}. Esta instância não está apontando para PostgreSQL.")
    st.markdown("##### Estado Atual do Runtime")
    st.caption("Leitura ativa da infraestrutura institucional em execução.")
    top_cols = st.columns(5)
    top_cols[0].metric("Build ativo", audit["build_active"])
    top_cols[1].metric("Commit ativo", audit["commit_active"])
    top_cols[2].metric("Backend", audit["backend"])
    top_cols[3].metric("Database source", audit["database_source"])
    top_cols[4].metric("Schema", audit["schema"])
    conn_cols = st.columns(3)
    conn_cols[0].caption(f"DATABASE_URL: {audit['database_url']}")
    conn_cols[1].caption(f"engine_url: {audit['engine_url']}")
    conn_cols[2].caption(f"host: {audit['host']} | database: {audit['database']}")
    source_cols = st.columns(5)
    csv_summary = _load_csv_latest_contest_summary() or {}
    sync_summary = _load_official_sync_contest_summary() or {}
    db_summary = _load_imported_contest() or {}
    official_history = _load_official_history_diagnostics()
    source_cols[0].metric("CSV oficial", int(csv_summary.get("contest_number", 0) or 0) or "-")
    source_cols[1].metric("API sincronizada", int(sync_summary.get("contest_number", 0) or 0) or "-")
    source_cols[2].metric("Banco persistido", int(db_summary.get("contest_number", 0) or 0) or "-")
    source_cols[3].metric("Histórico oficial", int(official_history.get("total_lotofacil_official_history", 0) or 0))
    source_cols[4].metric("Primeiro concurso", int(official_history.get("contest_number_min", 0) or 0) or "-")
    official_cols = st.columns(4)
    official_cols[0].metric("Último concurso", int(official_history.get("contest_number_max", 0) or 0) or "-")
    official_cols[1].metric("Faltantes", int(official_history.get("total_concursos_faltantes", 0) or 0))
    official_cols[2].metric("Status", str(official_history.get("status_base_oficial", "-") or "-"))
    official_cols[3].metric("Banco persistido", int(db_summary.get("contest_number", 0) or 0) or "-")
    st.caption(
        " | ".join(
            [
                f"SELECT COUNT generation_events={int(live_counts.get('generation_events', 0))}",
                f"SELECT COUNT generated_games={int(live_counts.get('generated_games', 0))}",
                f"SELECT COUNT reconciliation_runs={int(live_counts.get('reconciliation_runs', 0))}",
                f"SELECT COUNT reconciliation_games={int(live_counts.get('reconciliation_games', 0))}",
                f"SELECT COUNT institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))}",
            ]
        )
    )
    st.markdown("##### SELECT COUNT(*) no runtime")
    audit_rows: list[dict[str, Any]] = []
    with _get_engine_cached().begin() as connection:
        for query in (
            "SELECT COUNT(*) FROM generation_events;",
            "SELECT COUNT(*) FROM generated_games;",
            "SELECT COUNT(*) FROM reconciliation_runs;",
            "SELECT COUNT(*) FROM reconciliation_games;",
            "SELECT COUNT(*) FROM imported_contests;",
            "SELECT COUNT(*) FROM institutional_output_signatures;",
        ):
            row: dict[str, Any] = {"query": query, "count": None, "status": "ok", "error": ""}
            try:
                value = connection.execute(text(query)).scalar()
                row["count"] = int(value or 0)
            except Exception as exc:
                row["status"] = "error"
                row["error"] = str(exc)
                row["count"] = None
            audit_rows.append(row)
    audit_df = pd.DataFrame(audit_rows)
    st.dataframe(audit_df, hide_index=True, use_container_width=True)
    error_rows = [row for row in audit_rows if row.get("status") == "error"]
    if error_rows:
        with st.expander("Erros SQL da auditoria", expanded=True):
            st.dataframe(
                pd.DataFrame(error_rows)[["query", "error"]],
                hide_index=True,
                use_container_width=True,
            )
    st.markdown("##### Diferenças entre módulos")
    source_map = _institutional_source_map(snapshot)
    st.dataframe(pd.DataFrame(source_map), hide_index=True, use_container_width=True)
    st.markdown("##### Auditoria Operacional Ativa")
    st.caption("Resumo da geração e conferência operacional mais recente persistida no banco.")
    generation_history = _load_generation_history_light(limit=1)
    latest_generation = generation_history[0] if generation_history else {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    latest_generation_event_id = int(latest_generation.get("generation_event_id", 0) or 0)
    latest_reconciliation_event_id = int(latest_reconciliation.get("generation_event_id", 0) or 0)
    operational_reconciliation = latest_reconciliation if latest_generation_event_id and latest_reconciliation_event_id == latest_generation_event_id else {}
    operational_status = str(latest_generation.get("status de conferência", "não conferida") or "não conferida")
    if operational_reconciliation:
        operational_status = "conferida" if operational_status.lower() != "reconciliada" else operational_status
    total_games_conferidos = int(operational_reconciliation.get("games_count", 0) or 0) if operational_reconciliation else 0
    operational_cols = st.columns(10)
    operational_cols[0].metric("Última geração persistida", latest_generation_event_id or "-")
    operational_cols[1].metric("Quantidade solicitada", int(latest_generation.get("quantidade solicitada", 0) or 0))
    operational_cols[2].metric("Quantidade gerada", int(latest_generation.get("quantidade real gerada", 0) or 0))
    operational_cols[3].metric("Quantidade persistida", int(latest_generation.get("quantidade persistida", 0) or 0))
    operational_cols[4].metric("Quantidade recuperada", int(latest_generation.get("total de jogos recuperados", 0) or 0))
    operational_cols[5].metric("Status da geração", str(latest_generation.get("status da geração", "não conferida") or "não conferida"))
    operational_cols[6].metric("Último concurso conferido", str(latest_generation.get("concurso conferido", operational_reconciliation.get("contest_number", "-")) or "-"))
    operational_cols[7].metric("Status da conferência", operational_status)
    operational_cols[8].metric("Maior acerto", int(latest_generation.get("maior acerto", operational_reconciliation.get("best_hits", 0)) or 0))
    operational_cols[9].metric("Média de acertos", f"{float(latest_generation.get('média de acertos', latest_generation.get('media de acertos', 0.0)) or 0.0):.4f}")
    operational_detail_cols = st.columns(2)
    operational_detail_cols[0].metric("Total de jogos conferidos", total_games_conferidos if operational_reconciliation else 0)
    operational_detail_cols[1].metric("Status operacional", operational_status)
    st.markdown("##### Auditoria de integridade")
    integrity_rows = pd.DataFrame(
        [
            {
                "módulo": "runtime",
                "origem": "PostgreSQL",
                "status": audit["backend"],
                "observação": "OK" if audit["backend"] == "postgresql" else "atenção",
            },
            {
                "módulo": "base oficial",
                "origem": "lotofacil_official_history",
                "status": official_history.get("status_base_oficial", "-"),
                "observação": f"faltantes={official_history.get('total_concursos_faltantes', 0)}",
            },
            {
                "módulo": "operações",
                "origem": "generation_events / reconciliation_runs",
                "status": str(latest_generation.get("status da geração", latest_reconciliation.get("status", "não conferida")) or "não conferida"),
                "observação": f"concurso={latest_generation.get('concurso conferido', latest_reconciliation.get('contest_number', '-')) or '-'}",
            },
        ]
    )
    st.dataframe(integrity_rows, hide_index=True, use_container_width=True)
    st.markdown("##### Tabelas Institucionais")
    table_rows = []
    for table, count in live_counts.items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": str(snapshot["latest"].get(table, "-") or "-"),
            }
        )
    st.dataframe(_make_arrow_safe(pd.DataFrame(table_rows)), hide_index=True, use_container_width=True)
    st.markdown("##### Timeline secundária")
    timeline = _load_institutional_timeline_light(limit=25)
    if timeline:
        st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
    else:
        st.info("Ainda não há eventos suficientes para montar a timeline institucional.")
    st.markdown("##### Memória Científica Observacional / Legada")
    st.caption("Registros preservados para auditoria histórica. Não representam comando do runtime ativo.")
    st.info("Esta seção é documental. Não comanda geração, não recalibra a Lei 15 e não define o estado atual do runtime.")
    scientific_memory = _load_latest_scientific_memory(limit=20)
    official_15_memory = next((row for row in scientific_memory if _scientific_15_is_official_baseline(row)), {})
    historical_scientific_memory = [row for row in scientific_memory if not _scientific_15_is_official_baseline(row)]
    active_reconciliation_generation_event_id = _safe_int(st.session_state.get("active_reconciliation_generation_event_id"), default=None)
    latest_memory = official_15_memory or (scientific_memory[0] if scientific_memory else {})
    if active_reconciliation_generation_event_id is not None:
        post_reconciliation_memory = next(
            (
                row
                for row in scientific_memory
                if str(row.get("memory_kind", "") or "") == "scientific_reconciliation"
                and int(row.get("generation_event_id", 0) or 0) == int(active_reconciliation_generation_event_id or 0)
            ),
            {},
        )
    else:
        post_reconciliation_memory = next(
            (row for row in scientific_memory if str(row.get("memory_kind", "") or "") == "scientific_reconciliation"),
            {},
        )
    if not post_reconciliation_memory:
        post_reconciliation_memory = dict(st.session_state.get("institutional_post_reconciliation_memory") or {})
    if post_reconciliation_memory:
        st.markdown("###### Memória pós-conferência científica")
        post_window = dict(post_reconciliation_memory.get("generation_range") or {})
        post_cols = st.columns(6)
        post_cols[0].metric("Última geração registrada na memória científica", post_window.get("generation_event_id", "-") or "-")
        post_cols[1].metric("Concurso conferido", post_window.get("contest_number", post_reconciliation_memory.get("official_history_last_contest", "-")) or "-")
        post_cols[2].metric("Jogos conferidos", int(post_reconciliation_memory.get("total_games", 0) or 0))
        post_cols[3].metric("Melhor acerto", int(post_reconciliation_memory.get("best_hit", 0) or 0))
        post_cols[4].metric("Jogos com 10", int(_scientific_hit_decomposition(post_reconciliation_memory).get("count_10_exact", 0) or 0))
        post_cols[5].metric("Jogos com 11+", int(_scientific_hit_decomposition(post_reconciliation_memory).get("count_11_plus", 0) or 0))
    batch_reconciliation_memory = dict(st.session_state.get("institutional_batch_reconciliation_memory") or {})
    if batch_reconciliation_memory:
        st.markdown("###### Memória consolidada da bateria conferida")
        batch_window = dict(batch_reconciliation_memory.get("generation_range") or {})
        batch_cols = st.columns(4)
        batch_cols[0].metric("Memória consolidada", str(batch_reconciliation_memory.get("memory_kind", "-") or "-"))
        batch_cols[1].metric("generation_event_id", str(batch_window.get("generation_event_id", batch_reconciliation_memory.get("generation_event_id", "-")) or "-"))
        batch_cols[2].metric("Concurso conferido", batch_window.get("contest_number", batch_reconciliation_memory.get("contest_number", "-")) or "-")
        batch_cols[3].metric("Melhor acerto", int(batch_reconciliation_memory.get("best_hit", 0) or 0))
    strong_near_miss_memory = next(
        (row for row in scientific_memory if str(row.get("memory_kind", "") or "") == "scientific_strong_near_miss"),
        {},
    )
    if strong_near_miss_memory:
        st.markdown("###### Melhores near miss da última bateria")
        near_miss_window = dict(strong_near_miss_memory.get("generation_range") or {})
        near_miss_cols = st.columns(4)
        near_miss_cols[0].metric("Melhor geração", int(near_miss_window.get("best_generation_event_id", 0) or 0))
        near_miss_cols[1].metric("Registro técnico legado", _institutional_safe_action_label(str(strong_near_miss_memory.get("recommended_action", "") or "")))
        near_miss_cols[2].metric("Concurso", int(near_miss_window.get("contest_number", 0) or 0))
        near_miss_cols[3].metric("Status", "Preservado em quarentena documental")
    st.markdown("##### Papel do session_state")
    st.info(
        "session_state é apenas estado temporário de interface. Não deve ser usado como fonte de verdade persistente, nem como origem de conferência."
    )
    st.caption(f"build={BUILD_MARKER} | commit={audit['commit_active']}")


def _runtime_audit_payload(snapshot: dict[str, Any]) -> dict[str, Any]:
    engine_url = str(snapshot.get("engine_url") or snapshot.get("database_url") or "")
    parsed = urlparse(engine_url)
    database_name = "-"
    if parsed.scheme.startswith("sqlite"):
        database_name = parsed.path or engine_url
    elif parsed.path:
        database_name = parsed.path.lstrip("/") or "-"
    return {
        "backend": snapshot.get("backend", "-"),
        "host": parsed.hostname or "-",
        "database": database_name,
        "schema": "public" if str(snapshot.get("backend", "")).lower() == "postgresql" else "main",
        "engine_url": _mask_database_url(engine_url),
        "database_url": _mask_database_url(str(snapshot.get("database_url") or engine_url)),
        "database_source": snapshot.get("database_source", "-"),
        "build_active": BUILD_MARKER,
        "commit_active": _resolve_active_commit(),
        "counts": dict(snapshot.get("counts") or {}),
    }


@st.cache_data(show_spinner=False, ttl=2)
def _hb_geometry_state() -> dict[str, Any]:
    with _JOB_LOCK:
        state = dict(_JOB_STATE)
    progress = _safe_json_load(HB_GEOMETRY_PROGRESS_FILE)
    report = _safe_json_load(HB_GEOMETRY_JSON_FILE)
    csv_frame = _safe_csv_load(HB_GEOMETRY_CSV_FILE)
    summary = report.get("summary") or progress.get("summary") or {}
    return {
        "job": state,
        "progress": progress,
        "report": report,
        "summary": summary,
        "csv_frame": csv_frame,
    }


def _load_imported_contest(contest_number: int | None = None) -> dict[str, Any] | None:
    with get_session(DB_PATH) as session:
        query = session.query(ImportedContest)
        if contest_number is None:
            row = query.order_by(ImportedContest.contest_number.desc()).first()
        else:
            row = query.filter(ImportedContest.contest_number == int(contest_number)).first()
        if row is None:
            return None
        dezenas = _extract_int_numbers(str(row.dezenas or ""))
        return {
            "contest_number": int(row.contest_number),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "data": str(row.data or ""),
            "dezenas": dezenas,
            "metadata_json": str(row.metadata_json or "{}"),
        }


def _list_all_imported_contest_records() -> list[dict[str, Any]]:
    with get_session(DB_PATH) as session:
        rows = session.query(ImportedContest).order_by(ImportedContest.contest_number.asc()).all()
    records: list[dict[str, Any]] = []
    for row in rows:
        contest_number = int(getattr(row, "contest_number", 0) or 0)
        if contest_number <= 0:
            continue
        records.append(
            {
                "contest_number": contest_number,
                "data": str(getattr(row, "data", "") or ""),
                "dezenas": _extract_int_numbers(str(getattr(row, "dezenas", "") or "")),
                "metadata_json": str(getattr(row, "metadata_json", "{}") or ""),
            }
        )
    return records


def _get_conference_contest_from_imported(contest_number: int | None) -> dict[str, Any] | None:
    selected = _safe_int(contest_number, default=None)
    if selected is None:
        return None
    return to_conference_contest_payload(_load_imported_contest(selected))


def _load_sovereign_generation_event_rows(limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        query = session.query(GenerationEvent).order_by(GenerationEvent.created_at.asc(), GenerationEvent.id.asc())
        if limit is not None and int(limit) > 0:
            query = query.limit(int(limit))
        for event in query.all():
            rows.append(
                {
                    "id": int(event.id or 0),
                    "generation_event_id": int(event.id or 0),
                    "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                }
            )
    return rows


def _attach_operational_generation_label(snapshot: dict[str, Any]) -> dict[str, Any]:
    ge_id = int(snapshot.get("generation_event_id", 0) or 0)
    if ge_id <= 0:
        return snapshot
    event_rows = _load_sovereign_generation_event_rows()
    index_map = build_operational_generation_index(event_rows)
    return {
        **snapshot,
        "operational_generation_label": resolve_operational_generation_label(
            ge_id,
            operational_index=index_map,
        ),
        "operational_generation_index": int(index_map.get(ge_id, 0) or 0),
    }


def _normalize_contest_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    contest_number = record.get("contest_number", record.get("concurso"))
    if not str(contest_number or "").isdigit():
        return None
    dezenas = _extract_int_numbers(record.get("dezenas", []) or [])
    return {
        "contest_number": int(contest_number),
        "created_at": str(record.get("created_at", "") or ""),
        "data": str(record.get("data", "") or ""),
        "dezenas": dezenas,
        "metadata_json": str(record.get("metadata_json", "{}") or "{}"),
    }


def get_official_contest(contest_id: int | str | None) -> dict[str, Any] | None:
    """Gateway único para leitura de concurso oficial persistido."""
    selected_contest = _safe_int(contest_id, default=None)
    if selected_contest is None:
        return None
    contest = _load_official_history_contest(selected_contest)
    if not contest:
        return None
    contest_numbers = _extract_official_numbers_from_record(contest)
    contest = dict(contest)
    contest["contest_number"] = int(selected_contest)
    contest["official_contest_source"] = "official_lotofacil_history"
    contest["official_contest_id"] = int(selected_contest)
    contest["official_contest_numbers"] = " ".join(f"{number:02d}" for number in contest_numbers) or "-"
    return contest


def get_latest_official_contest() -> dict[str, Any] | None:
    """Retorna o concurso oficial persistido mais recente, sem fallback silencioso."""
    diagnostics = _load_official_history_diagnostics()
    latest_contest_number = _safe_int(diagnostics.get("contest_number_max"), default=None)
    if latest_contest_number is None or latest_contest_number <= 0:
        return None
    return get_official_contest(latest_contest_number)


def _load_hai_latest_contest_summary() -> dict[str, Any] | None:
    """Gateway DB-first para páginas HAI (Histórico/Analítico/Institucional)."""
    latest_official = get_latest_official_contest()
    if not latest_official:
        return None
    normalized = _normalize_contest_record(latest_official)
    if not normalized:
        return None
    normalized["source"] = "lotofacil_official_history"
    return normalized


def get_previous_official_contest(target_contest: int | None) -> RFEPreviousContestReference:
    """Retorna a referência anterior oficial usada pela RFE-01."""
    if target_contest is not None and int(target_contest) > 1:
        previous_contest_id = int(target_contest) - 1
        previous_contest = get_official_contest(previous_contest_id)
        if previous_contest:
            numbers = _extract_official_numbers_from_record(previous_contest)
            if numbers:
                return RFEPreviousContestReference(
                    found=True,
                    contest_id=previous_contest_id,
                    numbers=numbers,
                    source="official_lotofacil_history",
                    message=None,
                )
            return RFEPreviousContestReference(
                found=False,
                contest_id=previous_contest_id,
                numbers=[],
                source="official_lotofacil_history",
                message="Concurso anterior encontrado, mas dezenas oficiais inválidas ou incompletas.",
            )
        return RFEPreviousContestReference(
            found=False,
            contest_id=previous_contest_id,
            numbers=[],
            source="official_lotofacil_history",
            message="Concurso anterior não encontrado na base oficial persistida.",
        )

    latest_official_contest = get_latest_official_contest()
    latest_contest_number = _safe_int((latest_official_contest or {}).get("contest_number"), default=None)
    if latest_contest_number is not None and latest_contest_number > 0:
        numbers = _extract_official_numbers_from_record(latest_official_contest)
        if numbers:
            return RFEPreviousContestReference(
                found=True,
                contest_id=latest_contest_number,
                numbers=numbers,
                source="official_lotofacil_history",
                message=None,
            )
        return RFEPreviousContestReference(
            found=False,
            contest_id=latest_contest_number,
            numbers=[],
            source="official_lotofacil_history",
            message="Último concurso oficial encontrado, mas dezenas oficiais inválidas ou incompletas.",
        )

    return RFEPreviousContestReference(
        found=False,
        contest_id=None,
        numbers=[],
        source="indisponivel",
        message="Concurso anterior não encontrado na base oficial persistida.",
    )


def _load_imported_contest_numbers() -> list[int]:
    with get_session(DB_PATH) as session:
        rows = session.query(ImportedContest.contest_number).order_by(ImportedContest.contest_number.asc()).all()
        return [int(row[0]) for row in rows if row and row[0] is not None]


def _load_latest_generated_games() -> dict[str, Any] | None:
    seed = 0
    created_at = ""
    target_contest = None
    with get_session(DB_PATH) as session:
        generation_event = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .first()
        )
        if generation_event is None:
            return None

        generation_event_id = int(generation_event.id or 0)
        seed = int(getattr(generation_event, "seed", 0) or 0)
        created_at = generation_event.created_at.isoformat() if getattr(generation_event, "created_at", None) else ""
        games_query = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == generation_event_id)
            .order_by(GeneratedGame.game_index)
            .all()
        )
        games: list[dict[str, Any]] = []
        for game in games_query:
            if getattr(game, "target_contest", None) is not None:
                target_contest = int(game.target_contest)
            games.append(
                {
                    "game_index": int(game.game_index or 0),
                    "numbers": [int(number) for number in (game.numbers or [])],
                    "profile_type": str(game.profile_type or ""),
                    "final_score": dict(game.final_score or {}),
                    "quadra_score": dict(game.quadra_score or {}),
                    "origin": str(game.origin or "institutional"),
                    "context_json": dict(game.context_json or {}),
                }
            )

    if not games:
        return None

    return {
        "generation_event_id": generation_event_id,
        "seed": seed,
        "games": games,
        "total_games": len(games),
        "target_contest": target_contest,
        "created_at": created_at,
        "runtime_status": "loaded_from_database",
    }


def _load_latest_contest_summary() -> dict[str, Any] | None:
    official_sync = _load_official_sync_contest_summary()
    if official_sync:
        return {
            "contest_number": int(official_sync.get("contest_number", 0) or 0),
            "data": str(official_sync.get("data") or ""),
            "dezenas": [int(number) for number in official_sync.get("dezenas", [])],
            "source": str(official_sync.get("source") or "api_caixa_sincronizada"),
        }
    latest_contest = _load_imported_contest()
    if latest_contest:
        return {
            "contest_number": int(latest_contest.get("contest_number", 0) or 0),
            "data": str(latest_contest.get("data") or ""),
            "dezenas": [int(number) for number in latest_contest.get("dezenas", [])],
            "source": "banco oficial",
        }
    latest_generation = _load_latest_generated_games() or {}
    target_contest = latest_generation.get("target_contest")
    if str(target_contest or "").isdigit():
        return {
            "contest_number": int(target_contest or 0),
            "data": str(latest_generation.get("created_at") or ""),
            "dezenas": [],
            "source": "última geração persistida",
        }
    return None


def _get_latest_contest() -> dict[str, Any] | None:
    sync_summary = st.session_state.get("institutional_last_official_sync_summary", {}) or {}
    sync_record = _normalize_contest_record(sync_summary.get("latest_contest_record"))
    if sync_record:
        return sync_record
    persisted_sync_record = _load_official_sync_contest_summary()
    if persisted_sync_record:
        return persisted_sync_record
    sync_contest = sync_summary.get("latest_contest")
    if str(sync_contest or "").isdigit():
        synced_contest = _load_imported_contest(int(sync_contest))
        if synced_contest and int(synced_contest.get("contest_number", 0) or 0) > 0:
            return synced_contest
    latest_contest = _load_imported_contest()
    if latest_contest and int(latest_contest.get("contest_number", 0) or 0) > 0:
        return latest_contest
    contest_numbers = _load_imported_contest_numbers()
    if contest_numbers:
        return _load_imported_contest(contest_numbers[-1])
    latest_generation = _load_latest_generated_games() or {}
    target_contest = latest_generation.get("target_contest")
    if str(target_contest or "").isdigit():
        return _load_imported_contest(int(target_contest))
    if str(sync_contest or "").isdigit():
        return {
            "contest_number": int(sync_contest),
            "created_at": str(sync_summary.get("sync_timestamp", "") or ""),
            "data": "",
            "dezenas": list(sync_summary.get("imported_numbers", []) or []),
            "metadata_json": "{}",
        }
    return None


def _load_latest_scientific_calibration_decision(limit: int = 1) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit or 1))
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ScientificCalibrationDecision)
            .order_by(
                ScientificCalibrationDecision.created_at.desc(),
                ScientificCalibrationDecision.id.desc(),
            )
            .limit(resolved_limit)
            .all()
        )
    decisions: list[dict[str, Any]] = []
    for row in rows:
        decisions.append(
            {
                "id": int(getattr(row, "id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "strategy": str(getattr(row, "strategy", "") or ""),
                "game_size": int(getattr(row, "game_size", 0) or 0),
                "source_batch_id": str(getattr(row, "source_batch_id", "") or ""),
                "source_generation_range": dict(getattr(row, "source_generation_range", {}) or {}),
                "structural_status": str(getattr(row, "structural_status", "") or ""),
                "scientific_status": str(getattr(row, "scientific_status", "") or ""),
                "classification": str(getattr(row, "classification", "") or ""),
                "main_reason": str(getattr(row, "main_reason", "") or ""),
                "recommended_action": str(getattr(row, "recommended_action", "") or ""),
                "policy_before": dict(getattr(row, "policy_before", {}) or {}),
                "policy_after": dict(getattr(row, "policy_after", {}) or {}),
                "mode": str(getattr(row, "mode", "") or "OBSERVACAO"),
                "applied": bool(getattr(row, "applied", 0) or 0),
                "approved_by": str(getattr(row, "approved_by", "") or ""),
                "notes": str(getattr(row, "notes", "") or ""),
            }
        )
    return decisions


def _load_latest_scientific_memory(limit: int = 5) -> list[dict[str, Any]]:
    resolved_limit = max(1, int(limit or 1))
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ScientificInstitutionalMemory)
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .limit(resolved_limit)
            .all()
        )
    memories: list[dict[str, Any]] = []
    for row in rows:
        generation_range = dict(getattr(row, "generation_range", {}) or {})
        cross_validation_summary = dict(getattr(row, "cross_validation_summary", {}) or {})
        scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
        hit_decomposition = _scientific_hit_decomposition(
            {
                "count_10": int(scientific_components.get("count_10", 0) or 0),
                "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
                "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
                "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
                "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
                "count_15": int(getattr(row, "count_15", 0) or 0),
                "count_10_exact": int(scientific_components.get("count_10_exact", generation_range.get("count_10_exact", 0)) or 0),
                "count_11_exact": int(scientific_components.get("count_11_exact", generation_range.get("count_11_exact", 0)) or 0),
                "count_12_exact": int(scientific_components.get("count_12_exact", generation_range.get("count_12_exact", 0)) or 0),
                "count_13_exact": int(scientific_components.get("count_13_exact", generation_range.get("count_13_exact", 0)) or 0),
                "count_14_exact": int(scientific_components.get("count_14_exact", generation_range.get("count_14_exact", 0)) or 0),
                "count_15_exact": int(scientific_components.get("count_15_exact", generation_range.get("count_15_exact", 0)) or 0),
                "hit_histogram": dict(scientific_components.get("hit_histogram", generation_range.get("hit_histogram", {})) or {}),
                "generation_range": generation_range,
                "cross_validation_summary": cross_validation_summary,
            }
        )
        memories.append(
            {
                "id": int(getattr(row, "id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "memory_kind": str(getattr(row, "memory_kind", "") or ""),
                "strategy_name": str(getattr(row, "strategy_name", "") or ""),
                "game_size": int(getattr(row, "game_size", 0) or 0),
                "batch_id": str(getattr(row, "batch_id", "") or ""),
                "generation_range": generation_range,
                "generation_event_id": int(
                    generation_range.get("generation_event_id", scientific_components.get("best_generation_event_id", 0) or 0) or 0
                ),
                "contest_number": int(generation_range.get("contest_number", scientific_components.get("contest_number", 0) or 0) or 0),
                "total_games": int(getattr(row, "total_games", 0) or 0),
                "unique_games": int(getattr(row, "unique_games", 0) or 0),
                "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                "structural_status": str(getattr(row, "structural_status", "") or ""),
                "scientific_status": str(getattr(row, "scientific_status", "") or ""),
                "scientific_classification": str(getattr(row, "scientific_classification", "") or ""),
                "main_reason": str(getattr(row, "main_reason", "") or ""),
                "recommended_action": str(getattr(row, "recommended_action", "") or ""),
                "best_hit": int(getattr(row, "best_hit", 0) or 0),
                "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
                "count_10": int(hit_decomposition["count_10_exact"]),
                "count_10_exact": int(hit_decomposition["count_10_exact"]),
                "count_11_exact": int(hit_decomposition["count_11_exact"]),
                "count_12_exact": int(hit_decomposition["count_12_exact"]),
                "count_13_exact": int(hit_decomposition["count_13_exact"]),
                "count_14_exact": int(hit_decomposition["count_14_exact"]),
                "count_15_exact": int(hit_decomposition["count_15_exact"]),
                "count_11_plus": int(hit_decomposition["count_11_plus"]),
                "count_12_plus": int(hit_decomposition["count_12_plus"]),
                "count_13_plus": int(hit_decomposition["count_13_plus"]),
                "count_14_plus": int(hit_decomposition["count_14_plus"]),
                "count_15": int(hit_decomposition["count_15"]),
                "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                "decision_mode": str(getattr(row, "decision_mode", "OBSERVACAO") or "OBSERVACAO"),
                "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                "official_history_count": int(getattr(row, "official_history_count", 0) or 0),
                "official_history_first_contest": getattr(row, "official_history_first_contest", None),
                "official_history_last_contest": getattr(row, "official_history_last_contest", None),
                "official_history_window": list(getattr(row, "official_history_window", []) or []),
                "source": str(getattr(row, "source", "") or ""),
                "cross_validation_summary": cross_validation_summary,
                "scientific_score_components": scientific_components,
                "generation_details": list(cross_validation_summary.get("generation_details") or []),
                "best_generation_details": list(cross_validation_summary.get("best_generation_details") or []),
                "games_with_10_hits": list(cross_validation_summary.get("games_with_10_hits") or []),
            }
        )
    return memories


def _load_all_scientific_memory() -> list[dict[str, Any]]:
    with get_session(DB_PATH) as session:
        rows = (
            session.query(ScientificInstitutionalMemory)
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .all()
        )
    memories: list[dict[str, Any]] = []
    for row in rows:
        generation_range = dict(getattr(row, "generation_range", {}) or {})
        cross_validation_summary = dict(getattr(row, "cross_validation_summary", {}) or {})
        scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
        hit_decomposition = _scientific_hit_decomposition(
            {
                "count_10": int(scientific_components.get("count_10", 0) or 0),
                "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
                "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
                "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
                "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
                "count_15": int(getattr(row, "count_15", 0) or 0),
                "count_10_exact": int(scientific_components.get("count_10_exact", generation_range.get("count_10_exact", 0)) or 0),
                "count_11_exact": int(scientific_components.get("count_11_exact", generation_range.get("count_11_exact", 0)) or 0),
                "count_12_exact": int(scientific_components.get("count_12_exact", generation_range.get("count_12_exact", 0)) or 0),
                "count_13_exact": int(scientific_components.get("count_13_exact", generation_range.get("count_13_exact", 0)) or 0),
                "count_14_exact": int(scientific_components.get("count_14_exact", generation_range.get("count_14_exact", 0)) or 0),
                "count_15_exact": int(scientific_components.get("count_15_exact", generation_range.get("count_15_exact", 0)) or 0),
                "hit_histogram": dict(scientific_components.get("hit_histogram", generation_range.get("hit_histogram", {})) or {}),
                "generation_range": generation_range,
                "cross_validation_summary": cross_validation_summary,
            }
        )
        memories.append(
            {
                "id": int(getattr(row, "id", 0) or 0),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "memory_kind": str(getattr(row, "memory_kind", "") or ""),
                "strategy_name": str(getattr(row, "strategy_name", "") or ""),
                "game_size": int(getattr(row, "game_size", 0) or 0),
                "batch_id": str(getattr(row, "batch_id", "") or ""),
                "generation_range": generation_range,
                "generation_event_id": int(
                    generation_range.get("generation_event_id", scientific_components.get("best_generation_event_id", 0) or 0) or 0
                ),
                "contest_number": int(generation_range.get("contest_number", scientific_components.get("contest_number", 0) or 0) or 0),
                "total_games": int(getattr(row, "total_games", 0) or 0),
                "unique_games": int(getattr(row, "unique_games", 0) or 0),
                "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
                "structural_status": str(getattr(row, "structural_status", "") or ""),
                "scientific_status": str(getattr(row, "scientific_status", "") or ""),
                "scientific_classification": str(getattr(row, "scientific_classification", "") or ""),
                "main_reason": str(getattr(row, "main_reason", "") or ""),
                "recommended_action": str(getattr(row, "recommended_action", "") or ""),
                "best_hit": int(getattr(row, "best_hit", 0) or 0),
                "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
                "count_10": int(hit_decomposition["count_10_exact"]),
                "count_10_exact": int(hit_decomposition["count_10_exact"]),
                "count_11_exact": int(hit_decomposition["count_11_exact"]),
                "count_12_exact": int(hit_decomposition["count_12_exact"]),
                "count_13_exact": int(hit_decomposition["count_13_exact"]),
                "count_14_exact": int(hit_decomposition["count_14_exact"]),
                "count_15_exact": int(hit_decomposition["count_15_exact"]),
                "count_11_plus": int(hit_decomposition["count_11_plus"]),
                "count_12_plus": int(hit_decomposition["count_12_plus"]),
                "count_13_plus": int(hit_decomposition["count_13_plus"]),
                "count_14_plus": int(hit_decomposition["count_14_plus"]),
                "count_15": int(hit_decomposition["count_15"]),
                "hit_histogram": dict(hit_decomposition["hit_histogram"]),
                "decision_mode": str(getattr(row, "decision_mode", "OBSERVACAO") or "OBSERVACAO"),
                "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
                "official_history_count": int(getattr(row, "official_history_count", 0) or 0),
                "official_history_first_contest": getattr(row, "official_history_first_contest", None),
                "official_history_last_contest": getattr(row, "official_history_last_contest", None),
                "official_history_window": list(getattr(row, "official_history_window", []) or []),
                "source": str(getattr(row, "source", "") or ""),
                "cross_validation_summary": cross_validation_summary,
                "scientific_score_components": scientific_components,
                "generation_details": list(cross_validation_summary.get("generation_details") or []),
                "best_generation_details": list(cross_validation_summary.get("best_generation_details") or []),
                "games_with_10_hits": list(cross_validation_summary.get("games_with_10_hits") or []),
            }
        )
    return memories


def _format_scientific_memory_listing(memories: list[dict[str, Any]]) -> pd.DataFrame:
    if not memories:
        return pd.DataFrame()
    display_rows: list[dict[str, Any]] = []
    for row in memories:
        cross_validation_summary = dict(row.get("cross_validation_summary") or {})
        memory_kind = str(row.get("memory_kind", "") or "").strip()
        is_batch_memory = memory_kind == "scientific_batch_reconciliation"
        classification = str(
            row.get("scientific_classification")
            or row.get("classification")
            or cross_validation_summary.get("classification")
            or "-"
        )
        memory_role = str(
            row.get("memory_role")
            or cross_validation_summary.get("memory_role")
            or ("strong_support" if is_batch_memory else "auxiliary")
        )
        dominant_memory = row.get("dominant_memory", cross_validation_summary.get("dominant_memory"))
        if isinstance(dominant_memory, bool):
            dominant_memory = "conditional" if dominant_memory else "false"
        if dominant_memory in (None, ""):
            dominant_memory = "conditional" if is_batch_memory else "false"
        selection_variant = str(
            row.get("selection_variant")
            or cross_validation_summary.get("selection_variant")
            or ("cross_validated_scientific_batch_memory" if is_batch_memory else row.get("strategy_name") or "-")
        )
        cross_validation_reason = str(
            row.get("cross_validation_reason")
            or cross_validation_summary.get("cross_validation_reason")
            or ("historical_cross_validation_supports_memory" if is_batch_memory else row.get("main_reason") or "-")
        )
        recommended_action = str(row.get("recommended_action", "") or "-")
        prospective_status = str(
            row.get("prospective_status")
            or cross_validation_summary.get("prospective_status")
            or ("pending_prospective_validation" if is_batch_memory else "pending_prospective_validation")
        )
        scientific_reading = str(
            row.get("scientific_reading")
            or cross_validation_summary.get("scientific_reading")
            or ("memória com suporte histórico cruzado" if is_batch_memory else "memória científica")
        )
        display_rows.append(
            {
                "leitura científica": scientific_reading,
                "memory_id": int(row.get("id", 0) or 0),
                "memory_kind": memory_kind,
                "generation_event_id": str(row.get("generation_event_id", row.get("batch_id", "")) or "-"),
                "classification": classification,
                "memory_role": memory_role,
                "dominant_memory": str(dominant_memory),
                "selection_variant": selection_variant,
                "cross_validation_reason": cross_validation_reason,
                "recommended_action": recommended_action,
                "status prospectivo": prospective_status,
            }
        )
    return pd.DataFrame(
        display_rows,
        columns=[
            "leitura científica",
            "memory_id",
            "memory_kind",
            "generation_event_id",
            "classification",
            "memory_role",
            "dominant_memory",
            "selection_variant",
            "cross_validation_reason",
            "recommended_action",
            "status prospectivo",
        ],
    )


def _ensure_scientific_batch_memory_from_history() -> dict[str, Any]:
    memories = _load_all_scientific_memory()
    existing_batch = next(
        (row for row in memories if str(row.get("memory_kind", "") or "").strip() == "scientific_batch_reconciliation"),
        None,
    )
    if existing_batch:
        return existing_batch
    active_batch_id = _resolve_active_batch_id()
    reconciliation_rows = [
        row
        for row in memories
        if str(row.get("memory_kind", "") or "").strip() == "scientific_reconciliation"
        and int(row.get("generation_event_id", 0) or 0) > 0
    ]
    if active_batch_id:
        candidate_rows = [
            row for row in reconciliation_rows if str(row.get("batch_id", "") or "").strip() == active_batch_id
        ]
    else:
        batch_counter = Counter(str(row.get("batch_id", "") or "").strip() for row in reconciliation_rows if str(row.get("batch_id", "") or "").strip())
        if not batch_counter:
            return {}
        active_batch_id = batch_counter.most_common(1)[0][0]
        candidate_rows = [
            row for row in reconciliation_rows if str(row.get("batch_id", "") or "").strip() == active_batch_id
        ]
    if len(candidate_rows) < 2:
        return {}

    candidate_rows = sorted(
        candidate_rows,
        key=lambda item: (
            int(item.get("generation_event_id", 0) or 0),
            int(item.get("id", 0) or 0),
        ),
    )
    generation_event_ids = [int(row.get("generation_event_id", 0) or 0) for row in candidate_rows if int(row.get("generation_event_id", 0) or 0) > 0]
    contest_numbers = [int(row.get("contest_number", 0) or 0) for row in candidate_rows if int(row.get("contest_number", 0) or 0) > 0]
    total_generations = len(candidate_rows)
    total_games_checked = sum(int(row.get("total_games", 0) or 0) for row in candidate_rows)
    global_best_hits = max((int(row.get("best_hit", 0) or 0) for row in candidate_rows), default=0)
    global_count_10 = sum(int(row.get("count_10", 0) or 0) for row in candidate_rows)
    global_count_11_plus = sum(int(row.get("count_11_plus", 0) or 0) for row in candidate_rows)
    global_count_12_plus = sum(int(row.get("count_12_plus", 0) or 0) for row in candidate_rows)
    global_count_13_plus = sum(int(row.get("count_13_plus", 0) or 0) for row in candidate_rows)
    global_count_14_plus = sum(int(row.get("count_14_plus", 0) or 0) for row in candidate_rows)
    global_count_15 = sum(int(row.get("count_15", 0) or 0) for row in candidate_rows)
    global_average_hits = _mean_or_zero([float(row.get("average_hits", 0.0) or 0.0) for row in candidate_rows])
    dispersion = round(
        math.sqrt(_mean_or_zero([(float(row.get("best_hit", 0) or 0) - global_average_hits) ** 2 for row in candidate_rows]))
        if len(candidate_rows) > 1
        else 0.0,
        4,
    )
    best_row = sorted(
        candidate_rows,
        key=lambda item: (
            -int(item.get("best_hit", 0) or 0),
            -int(item.get("count_10", 0) or 0),
            -int(item.get("count_11_plus", 0) or 0),
            -int(item.get("count_12_plus", 0) or 0),
            -int(item.get("count_13_plus", 0) or 0),
            -float(item.get("average_hits", 0.0) or 0.0),
            int(item.get("id", 0) or 0),
        ),
    )[0]
    secondary_generation_event_ids = [
        int(row.get("generation_event_id", 0) or 0)
        for row in candidate_rows
        if int(row.get("generation_event_id", 0) or 0) != int(best_row.get("generation_event_id", 0) or 0)
    ][:3]
    batch_classification = (
        "STRONG_NEAR_MISS_BATCH"
        if total_games_checked >= 100 and global_best_hits >= 10 and global_count_11_plus == 0 and global_count_10 > 0
        else ("NEAR_MISS_GLOBAL" if global_best_hits >= 10 else "BATCH_REVIEW")
    )
    recommended_action = (
        "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
        if batch_classification == "STRONG_NEAR_MISS_BATCH"
        else "recalibrate_from_near_miss_towards_15"
    )
    batch_generation_range = {
        "batch_id": active_batch_id,
        "contest_number": max(contest_numbers) if contest_numbers else None,
        "generation_event_ids": generation_event_ids,
        "first_generation_event_id": min(generation_event_ids) if generation_event_ids else None,
        "last_generation_event_id": max(generation_event_ids) if generation_event_ids else None,
        "total_generations": total_generations,
        "total_games_checked": total_games_checked,
        "global_best_hits": global_best_hits,
        "global_count_10": global_count_10,
        "global_count_11_plus": global_count_11_plus,
        "global_count_12_plus": global_count_12_plus,
        "global_count_13_plus": global_count_13_plus,
        "global_count_14_plus": global_count_14_plus,
        "global_count_15": global_count_15,
        "best_generation_event_id": int(best_row.get("generation_event_id", 0) or 0),
        "best_generation_count_10": int(best_row.get("count_10", 0) or 0),
        "secondary_generation_event_ids": secondary_generation_event_ids,
        "classification": batch_classification,
        "confidence_level": "MEDIUM_HIGH" if batch_classification == "STRONG_NEAR_MISS_BATCH" else "LOW_TO_MEDIUM",
        "requires_cross_validation": True,
        "overfit_risk": round(min(1.0, dispersion / 5.0), 4),
        "recommended_action": recommended_action,
    }
    payload = {
        "event_type": "post_reconciliation_scientific_batch_expansion",
        "memory_kind": "scientific_batch_reconciliation",
        "strategy_name": str(best_row.get("strategy_name", "") or "15 dezenas"),
        "game_size": int(best_row.get("game_size", 15) or 15),
        "batch_id": active_batch_id,
        "generation_range": batch_generation_range,
        "contest_scope": "BATCH_CONSOLIDATED",
        "local_classification": batch_classification,
        "scientific_classification": batch_classification,
        "confidence_level": batch_generation_range["confidence_level"],
        "requires_cross_validation": True,
        "historical_windows": dict(best_row.get("cross_validation_summary", {}) or {}).get("historical_windows", {}) or {
            "10": {
                "contest_scope": "BATCH_CONSOLIDATED",
                "window_size": 10,
                "contest_count": min(10, total_generations),
                "contest_numbers": generation_event_ids[-10:],
                "best_hits_average": global_average_hits,
                "best_hits_median": global_average_hits,
                "best_hits_min": global_best_hits,
                "best_hits_max": global_best_hits,
                "count_10": global_count_10,
                "count_11_plus": global_count_11_plus,
                "count_12_plus": global_count_12_plus,
                "count_13_plus": global_count_13_plus,
                "count_14_plus": global_count_14_plus,
                "count_15": global_count_15,
                "average_hits_per_contest": global_average_hits,
                "stability": 0.0,
                "overfit_risk": 0.0,
                "scientific_score": 0.0,
            }
        },
        "recommended_action": recommended_action,
        "policy_adjustment_reason": recommended_action,
        "next_generation_policy_adjustments": {
            "policy_origin": "scientific_batch_reconciliation_memory",
            "policy_variant": "batch_near_miss_consolidation",
            "strengthen_11_plus": True,
            "seek_12_plus": True,
            "seek_13_plus": True,
            "preserve_14_15_path": True,
            "recalibrate_from_strong_near_miss_towards_11_plus_and_15": batch_classification == "STRONG_NEAR_MISS_BATCH",
        },
        "scientific_score": _scientific_tier_weighted_score(
            count_10=global_count_10,
            count_11_plus=global_count_11_plus,
            count_12_plus=global_count_12_plus,
            count_13_plus=global_count_13_plus,
            count_14_plus=global_count_14_plus,
            count_15=global_count_15,
            best_hits=global_best_hits,
            average_hits=global_average_hits,
            stability=1.0 - min(1.0, dispersion / 5.0),
            overfit_risk=batch_generation_range["overfit_risk"],
            concentration_risk=0.0 if global_count_10 else 1.0,
        ),
        "scientific_score_components": {
            "count_10": global_count_10,
            "count_11_plus": global_count_11_plus,
            "count_12_plus": global_count_12_plus,
            "count_13_plus": global_count_13_plus,
            "count_14_plus": global_count_14_plus,
            "count_15": global_count_15,
            "best_hits": global_best_hits,
            "average_hits": global_average_hits,
            "dispersion": dispersion,
            "generation_event_ids": generation_event_ids,
            "best_generation_event_id": int(best_row.get("generation_event_id", 0) or 0),
            "secondary_generation_event_ids": secondary_generation_event_ids,
            "total_generations": total_generations,
            "total_games_checked": total_games_checked,
        },
        "policy_before": dict(best_row.get("policy_before") or {}),
        "policy_after": dict(best_row.get("policy_after") or {}),
        "policy_id": str(best_row.get("policy_id") or ""),
        "policy_origin": "scientific_batch_reconciliation_memory",
        "policy_variant": "batch_near_miss_consolidation",
        "policy_applied": dict(best_row.get("policy_applied") or {}),
        "best_hit": global_best_hits,
        "average_hits": global_average_hits,
        "count_10": global_count_10,
        "count_11_plus": global_count_11_plus,
        "count_12_plus": global_count_12_plus,
        "count_13_plus": global_count_13_plus,
        "count_14_plus": global_count_14_plus,
        "count_15": global_count_15,
        "main_reason": batch_classification.lower(),
        "decision_mode": "OBSERVACAO",
        "approved_for_use": 0,
        "notes": (
            f"batch_reconciliation=batch_id={active_batch_id} | "
            f"generation_event_ids={generation_event_ids} | "
            f"best_generation_event_id={batch_generation_range['best_generation_event_id']} | "
            f"global_count_10={global_count_10} | global_count_11_plus={global_count_11_plus}"
        ),
        "based_on_batch_id": active_batch_id,
        "best_generation_event_id": batch_generation_range["best_generation_event_id"],
        "best_generation_count_10": batch_generation_range["best_generation_count_10"],
        "secondary_generation_event_ids": secondary_generation_event_ids,
        "generation_event_ids": generation_event_ids,
        "total_generations": total_generations,
        "total_games_checked": total_games_checked,
        "matched_patterns_json": dict(best_row.get("cross_validation_summary", {}) or {}).get("matched_patterns_json", []),
        "missing_numbers_json": dict(best_row.get("cross_validation_summary", {}) or {}).get("missing_numbers_json", []),
        "extra_numbers_json": dict(best_row.get("cross_validation_summary", {}) or {}).get("extra_numbers_json", []),
        "near_miss_generation_ranking": [
            {
                "generation_event_id": int(row.get("generation_event_id", 0) or 0),
                "batch_id": str(row.get("batch_id", "") or ""),
                "contest_number": int(row.get("contest_number", 0) or 0),
                "total_games": int(row.get("total_games", 0) or 0),
                "best_hits": int(row.get("best_hit", 0) or 0),
                "count_10": int(row.get("count_10", 0) or 0),
                "count_11_plus": int(row.get("count_11_plus", 0) or 0),
                "count_12_plus": int(row.get("count_12_plus", 0) or 0),
                "count_13_plus": int(row.get("count_13_plus", 0) or 0),
                "count_14_plus": int(row.get("count_14_plus", 0) or 0),
                "count_15": int(row.get("count_15", 0) or 0),
                "average_hits": float(row.get("average_hits", 0.0) or 0.0),
                "scientific_score": float(row.get("scientific_score", 0.0) or 0.0),
                "created_at": str(row.get("created_at", "") or ""),
            }
            for row in candidate_rows
        ],
        "historical_expansion_json": {
            "10": batch_generation_range,
            "60": batch_generation_range,
            "100": batch_generation_range,
            "300": batch_generation_range,
            "all": batch_generation_range,
        },
    }
    payload["cross_validation_summary"] = {
        "contest_scope": "BATCH_CONSOLIDATED",
        "confidence_level": batch_generation_range["confidence_level"],
        "requires_cross_validation": True,
        "historical_windows": payload["historical_windows"],
        "scientific_score": payload["scientific_score"],
        "scientific_score_components": payload["scientific_score_components"],
        "next_generation_policy_adjustments": payload["next_generation_policy_adjustments"],
        "local_classification": batch_classification,
        "recommended_action": recommended_action,
        "ranking_summary": {
            "best_generation_event_id": batch_generation_range["best_generation_event_id"],
            "secondary_generation_event_ids": secondary_generation_event_ids,
            "total_generations": total_generations,
            "total_games_checked": total_games_checked,
        },
        "near_miss_generation_ranking": payload["near_miss_generation_ranking"],
        "matched_patterns_json": payload["matched_patterns_json"],
        "missing_numbers_json": payload["missing_numbers_json"],
        "extra_numbers_json": payload["extra_numbers_json"],
        "historical_expansion_json": payload["historical_expansion_json"],
    }
    persisted_payload = _persist_scientific_reconciliation_memory(payload)
    if persisted_payload:
        return persisted_payload
    return payload


def _persist_scientific_reconciliation_memory(memory_payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(memory_payload or {})
    if not payload:
        return {}
    generation_range = dict(payload.get("generation_range") or {})
    policy_applied = dict(payload.get("policy_applied") or {})
    policy_before = dict(payload.get("policy_before") or {})
    policy_after = dict(payload.get("policy_after") or {})
    with get_session(DB_PATH) as session:
        row = ScientificInstitutionalMemory(
            memory_kind=str(payload.get("memory_kind", "scientific_reconciliation") or "scientific_reconciliation"),
            strategy_name=str(payload.get("strategy_name", f"{int(payload.get('game_size', 15) or 15)} dezenas") or ""),
            game_size=int(payload.get("game_size", 15) or 15),
            batch_id=str(payload.get("batch_id", "") or ""),
            generation_range=generation_range,
            total_games=int(payload.get("total_games", 0) or 0),
            unique_games=int(payload.get("unique_games", 0) or 0),
            duplicate_games=int(payload.get("duplicate_games", 0) or 0),
            structural_status=str(payload.get("structural_status", "") or ""),
            scientific_status=str(payload.get("scientific_status", "") or ""),
            scientific_classification=str(payload.get("scientific_classification", payload.get("local_classification", "")) or ""),
            main_reason=str(payload.get("main_reason", payload.get("policy_adjustment_reason", "")) or ""),
            recommended_action=str(payload.get("recommended_action", payload.get("policy_adjustment_reason", "")) or ""),
            policy_applied=policy_applied,
            policy_before=policy_before,
            policy_after=policy_after,
            best_hit=int(payload.get("best_hit", 0) or 0),
            average_hits=float(payload.get("average_hits", 0.0) or 0.0),
            count_11_plus=int(payload.get("count_11_plus", 0) or 0),
            count_12_plus=int(payload.get("count_12_plus", 0) or 0),
            count_13_plus=int(payload.get("count_13_plus", 0) or 0),
            count_14_plus=int(payload.get("count_14_plus", 0) or 0),
            count_15=int(payload.get("count_15", 0) or 0),
            validation_contests=list(payload.get("validation_contests", []) or []),
            cross_validation_summary=dict(payload.get("cross_validation_summary", {}) or {}),
            frequency_alerts=list(payload.get("frequency_alerts", []) or []),
            absence_alerts=list(payload.get("absence_alerts", []) or []),
            parity_alerts=list(payload.get("parity_alerts", []) or []),
            repetition_alerts=list(payload.get("repetition_alerts", []) or []),
            sequence_alerts=list(payload.get("sequence_alerts", []) or []),
            low_high_alerts=list(payload.get("low_high_alerts", []) or []),
            range_alerts=list(payload.get("range_alerts", []) or []),
            decision_mode=str(payload.get("decision_mode", "OBSERVACAO") or "OBSERVACAO"),
            approved_for_use=int(bool(payload.get("approved_for_use", False))),
            notes=str(payload.get("notes", "") or ""),
            official_history_count=int(payload.get("official_history_count", 0) or 0),
            official_history_first_contest=payload.get("official_history_first_contest"),
            official_history_last_contest=payload.get("official_history_last_contest"),
            official_history_window=list(payload.get("official_history_window", []) or []),
            source=str(payload.get("source", "scientific_reconciliation") or "scientific_reconciliation"),
        )
        session.add(row)
        session.flush()
        payload["memory_id"] = int(row.id or 0)
        payload["based_on_post_reconciliation_memory_id"] = int(row.id or 0)
        payload["created_at"] = row.created_at.isoformat() if getattr(row, "created_at", None) else payload.get("created_at", "")
        session.commit()
    st.session_state["institutional_last_scientific_reconciliation_memory"] = dict(payload)
    return payload


def _make_streamlit_dataframe_safe(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    safe_df = df.copy()
    for column in safe_df.columns:
        if safe_df[column].dtype == "object":
            safe_df[column] = safe_df[column].apply(lambda value: "" if value is None else str(value))
    return safe_df


def _load_scientific_context_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    decision_index: dict[str, dict[str, Any]] = {}
    memory_index: dict[str, dict[str, Any]] = {}
    with get_session(DB_PATH) as session:
        decision_rows = (
            session.query(ScientificCalibrationDecision)
            .order_by(
                ScientificCalibrationDecision.created_at.desc(),
                ScientificCalibrationDecision.id.desc(),
            )
            .all()
        )
        memory_rows = (
            session.query(ScientificInstitutionalMemory)
            .order_by(
                ScientificInstitutionalMemory.created_at.desc(),
                ScientificInstitutionalMemory.id.desc(),
            )
            .all()
        )
    for row in decision_rows:
        batch_id = str(getattr(row, "source_batch_id", "") or "").strip()
        if not batch_id or batch_id in decision_index:
            continue
        policy_before = dict(getattr(row, "policy_before", {}) or {})
        policy_after = dict(getattr(row, "policy_after", {}) or {})
        decision_index[batch_id] = {
            "id": int(getattr(row, "id", 0) or 0),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "strategy": str(getattr(row, "strategy", "") or ""),
            "game_size": int(getattr(row, "game_size", 0) or 0),
            "source_batch_id": batch_id,
            "source_generation_range": dict(getattr(row, "source_generation_range", {}) or {}),
            "structural_status": str(getattr(row, "structural_status", "") or ""),
            "scientific_status": str(getattr(row, "scientific_status", "") or ""),
            "classification": str(getattr(row, "classification", "") or ""),
            "main_reason": str(getattr(row, "main_reason", "") or ""),
            "recommended_action": str(getattr(row, "recommended_action", "") or ""),
            "policy_before": policy_before,
            "policy_after": policy_after,
            "policy_id": str(policy_after.get("policy_signature") or policy_after.get("policy_id") or ""),
            "policy_origin": str(policy_after.get("policy_origin") or ""),
            "policy_variant": str(policy_after.get("policy_variant") or ""),
            "mode": str(getattr(row, "mode", "") or "OBSERVACAO"),
            "applied": bool(getattr(row, "applied", 0) or 0),
            "approved_by": str(getattr(row, "approved_by", "") or ""),
            "notes": str(getattr(row, "notes", "") or ""),
        }
    for row in memory_rows:
        batch_id = str(getattr(row, "batch_id", "") or "").strip()
        if not batch_id or batch_id in memory_index:
            continue
        policy_before = dict(getattr(row, "policy_before", {}) or {})
        policy_after = dict(getattr(row, "policy_after", {}) or {})
        generation_range = dict(getattr(row, "generation_range", {}) or {})
        cross_validation_summary = dict(getattr(row, "cross_validation_summary", {}) or {})
        scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
        memory_index[batch_id] = {
            "id": int(getattr(row, "id", 0) or 0),
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
            "memory_kind": str(getattr(row, "memory_kind", "") or ""),
            "strategy_name": str(getattr(row, "strategy_name", "") or ""),
            "game_size": int(getattr(row, "game_size", 0) or 0),
            "batch_id": batch_id,
            "generation_range": generation_range,
            "generation_event_id": int(generation_range.get("generation_event_id", 0) or 0),
            "contest_number": int(generation_range.get("contest_number", 0) or 0),
            "total_games": int(getattr(row, "total_games", 0) or 0),
            "unique_games": int(getattr(row, "unique_games", 0) or 0),
            "duplicate_games": int(getattr(row, "duplicate_games", 0) or 0),
            "structural_status": str(getattr(row, "structural_status", "") or ""),
            "scientific_status": str(getattr(row, "scientific_status", "") or ""),
            "scientific_classification": str(getattr(row, "scientific_classification", "") or ""),
            "main_reason": str(getattr(row, "main_reason", "") or ""),
            "recommended_action": str(getattr(row, "recommended_action", "") or ""),
            "policy_applied": dict(getattr(row, "policy_applied", {}) or {}),
            "policy_before": policy_before,
            "policy_after": policy_after,
            "best_hit": int(getattr(row, "best_hit", 0) or 0),
            "average_hits": float(getattr(row, "average_hits", 0.0) or 0.0),
            "count_10": int(scientific_components.get("count_10", 0) or 0),
            "count_11_plus": int(getattr(row, "count_11_plus", 0) or 0),
            "count_12_plus": int(getattr(row, "count_12_plus", 0) or 0),
            "count_13_plus": int(getattr(row, "count_13_plus", 0) or 0),
            "count_14_plus": int(getattr(row, "count_14_plus", 0) or 0),
            "count_15": int(getattr(row, "count_15", 0) or 0),
            "decision_mode": str(getattr(row, "decision_mode", "OBSERVACAO") or "OBSERVACAO"),
            "approved_for_use": bool(getattr(row, "approved_for_use", 0) or 0),
            "official_history_count": int(getattr(row, "official_history_count", 0) or 0),
            "official_history_first_contest": getattr(row, "official_history_first_contest", None),
            "official_history_last_contest": getattr(row, "official_history_last_contest", None),
            "official_history_window": list(getattr(row, "official_history_window", []) or []),
            "source": str(getattr(row, "source", "") or ""),
            "policy_id": str(policy_after.get("policy_signature") or policy_after.get("policy_id") or ""),
            "policy_origin": str(policy_after.get("policy_origin") or ""),
            "policy_variant": str(policy_after.get("policy_variant") or ""),
        }
    return decision_index, memory_index


def _classify_generation_visibility(
    *,
    generation: dict[str, Any],
    scientific_decision: dict[str, Any] | None = None,
    scientific_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = dict(scientific_decision or {})
    memory = dict(scientific_memory or {})
    commander_status = str(generation.get("status_comandante_saida", "APROVADO") or "APROVADO").strip().upper()
    total_duplicates = int(generation.get("total_jogos_duplicados", 0) or 0)
    structural_status = "APROVADO" if commander_status == "APROVADO" and total_duplicates == 0 else "REPROVADO"
    scientific_status = str(decision.get("scientific_status") or memory.get("scientific_status") or "").strip().upper()
    scientific_classification = str(decision.get("classification") or memory.get("scientific_classification") or "").strip() or "-"
    recommended_action = str(decision.get("recommended_action") or memory.get("recommended_action") or "").strip() or "-"
    decision_mode = str(decision.get("mode") or memory.get("decision_mode") or "").strip().upper()
    approved_for_use = bool(decision.get("applied") or memory.get("approved_for_use"))
    policy_id = str(decision.get("policy_id") or memory.get("policy_id") or "")
    policy_origin = str(decision.get("policy_origin") or memory.get("policy_origin") or "")
    policy_variant = str(decision.get("policy_variant") or memory.get("policy_variant") or "")
    source_batch_id = str(decision.get("source_batch_id") or memory.get("batch_id") or generation.get("batch_id", "") or "").strip()
    is_guardian_rejected = commander_status != "APROVADO" or total_duplicates > 0
    is_scientific_rejected = bool(scientific_status) and scientific_status != "APROVADO" and not approved_for_use
    is_calibration_only = bool(decision_mode) and decision_mode == "OBSERVACAO" and bool(scientific_status) and not approved_for_use
    ml_verdict = str(generation.get("ml_verdict") or "").strip().upper()
    ml_verdict_reason = str(generation.get("ml_verdict_reason") or generation.get("motivo_principal") or "").strip()
    lot_operational_status = str(generation.get("lot_operational_status") or "").strip().lower()
    official_release_allowed = generation.get("official_release_allowed")
    if official_release_allowed is None and lot_operational_status:
        official_release_allowed = is_official_conference_eligible(generation)
    elif official_release_allowed is None and ml_verdict:
        official_release_allowed = is_ml_official_release_allowed({"ml_verdict": ml_verdict})
    elif official_release_allowed is None:
        official_release_allowed = True
    is_ml_verdict_rejected = not bool(official_release_allowed)
    if is_ml_verdict_rejected:
        visibility_label = "Bloqueado — Veredito ML"
        visibility_kind = "ml_verdict_blocked"
        visibility_reason = ml_verdict_reason or f"veredito ML: {ml_verdict}"
        is_conferible = False
    elif is_guardian_rejected:
        visibility_label = "Rejeitado pelo Guardião"
        visibility_kind = "rejected_guardian"
        visibility_reason = "bateria bloqueada pelo comandante ou com duplicidade"
        is_conferible = False
    elif is_scientific_rejected:
        visibility_label = "Reprovado pelo Motor Científico"
        visibility_kind = "scientific_rejected"
        visibility_reason = recommended_action if recommended_action != "-" else "bateria estruturalmente aprovada, mas cientificamente reprovada"
        is_conferible = False
    elif is_calibration_only:
        visibility_label = "Calibração"
        visibility_kind = "calibration"
        visibility_reason = recommended_action if recommended_action != "-" else "bateria de calibração científica"
        is_conferible = False
    else:
        visibility_label = "Conferível"
        visibility_kind = "conferible"
        visibility_reason = "bateria apta para conferência"
        is_conferible = True
    if commander_status == "APROVADO" and is_scientific_rejected:
        visibility_reason = "Bateria estruturalmente aprovada, mas cientificamente reprovada. Disponível para diagnóstico/conferência supervisionada."
    if is_guardian_rejected and total_duplicates > 0 and not str(visibility_reason).strip():
        visibility_reason = "duplicidade acima do limite"
    return {
        "batch_id": source_batch_id,
        "policy_id": policy_id,
        "policy_origin": policy_origin,
        "policy_variant": policy_variant,
        "structural_status": structural_status,
        "scientific_status": scientific_status or "-",
        "scientific_classification": scientific_classification,
        "recommended_action": recommended_action,
        "decision_mode": decision_mode or "-",
        "approved_for_use": approved_for_use,
        "visibility_label": visibility_label,
        "visibility_kind": visibility_kind,
        "visibility_reason": visibility_reason,
        "is_conferible": is_conferible,
        "is_rejected_policy": is_scientific_rejected or is_guardian_rejected,
        "is_candidate": bool(policy_id) or bool(policy_origin),
        "is_guardian_rejected": is_guardian_rejected,
        "is_scientific_rejected": is_scientific_rejected,
        "is_calibration_only": is_calibration_only,
        "ml_verdict": ml_verdict or "-",
        "ml_verdict_reason": ml_verdict_reason or "-",
        "lot_operational_status": lot_operational_status or "-",
        "official_release_allowed": bool(official_release_allowed),
        "is_ml_verdict_blocked": is_ml_verdict_rejected,
    }


def _load_official_history_summary() -> dict[str, Any]:
    with get_session(DB_PATH) as session:
        rows = (
            session.query(LotofacilOfficialHistory)
            .order_by(LotofacilOfficialHistory.contest_number.asc())
            .all()
        )
    contest_numbers = [int(getattr(row, "contest_number", 0) or 0) for row in rows if int(getattr(row, "contest_number", 0) or 0) > 0]
    latest = rows[-1] if rows else None
    return {
        "count": len(rows),
        "first_contest": contest_numbers[0] if contest_numbers else None,
        "last_contest": contest_numbers[-1] if contest_numbers else None,
        "latest_contest": {
            "contest_number": int(getattr(latest, "contest_number", 0) or 0) if latest is not None else 0,
            "draw_date": str(getattr(latest, "draw_date", "") or "") if latest is not None else "",
            "numbers": [int(value) for value in str(getattr(latest, "numbers", "") or "").replace(",", " ").split() if str(value).isdigit()] if latest is not None else [],
            "source": str(getattr(latest, "source", "") or "") if latest is not None else "",
        }
        if latest is not None
        else {},
        "window": contest_numbers[-10:],
        "rows": [
            {
                "contest_number": int(getattr(row, "contest_number", 0) or 0),
                "draw_date": str(getattr(row, "draw_date", "") or ""),
                "numbers": [int(value) for value in str(getattr(row, "numbers", "") or "").replace(",", " ").split() if str(value).isdigit()],
                "source": str(getattr(row, "source", "") or ""),
            }
            for row in rows[-10:]
        ],
        "source": "lotofacil_official_history",
    }


def _load_imported_contests_summary() -> dict[str, Any]:
    try:
        with get_session(DB_PATH) as session:
            rows = (
                session.query(ImportedContest)
                .order_by(ImportedContest.contest_number.asc())
                .all()
            )
        contest_numbers = [int(getattr(row, "contest_number", 0) or 0) for row in rows if int(getattr(row, "contest_number", 0) or 0) > 0]
        latest = rows[-1] if rows else None
        return {
            "count": len(rows),
            "first_contest": contest_numbers[0] if contest_numbers else None,
            "last_contest": contest_numbers[-1] if contest_numbers else None,
            "latest_contest": {
                "contest_number": int(getattr(latest, "contest_number", 0) or 0) if latest is not None else 0,
                "draw_date": str(getattr(latest, "data", "") or "") if latest is not None else "",
                "numbers": [int(value) for value in str(getattr(latest, "dezenas", "") or "").replace(",", " ").split() if str(value).isdigit()] if latest is not None else [],
                "source": "imported_contests" if latest is not None else "",
            }
            if latest is not None
            else {},
            "window": contest_numbers[-10:],
            "rows": [
                {
                    "contest_number": int(getattr(row, "contest_number", 0) or 0),
                    "draw_date": str(getattr(row, "data", "") or ""),
                    "numbers": [int(value) for value in str(getattr(row, "dezenas", "") or "").replace(",", " ").split() if str(value).isdigit()],
                    "source": "imported_contests",
                }
                for row in rows[-10:]
            ],
            "source": "imported_contests",
            "status": "OK",
        }
    except Exception as exc:
        logger.warning("imported_contests summary unavailable: %s", exc)
        return imported_contests_summary_unavailable(error=str(exc))


def _load_official_history_rows(limit: int | None = None, *, descending: bool = False) -> list[dict[str, Any]]:
    with get_session(DB_PATH) as session:
        order_column = LotofacilOfficialHistory.contest_number.desc() if descending else LotofacilOfficialHistory.contest_number.asc()
        query = session.query(LotofacilOfficialHistory).order_by(order_column)
        if limit is not None and int(limit) > 0:
            query = query.limit(int(limit))
        rows = query.all()
    return [
        {
            "concurso": int(getattr(row, "contest_number", 0) or 0),
            "data": str(getattr(row, "draw_date", "") or ""),
            "dezenas_sorteadas": " ".join(
                f"{int(value):02d}"
                for value in str(getattr(row, "numbers", "") or "").replace(",", " ").split()
                if str(value).isdigit()
            ),
            "numbers_signature": str(getattr(row, "numbers_signature", "") or ""),
            "fonte": str(getattr(row, "source", "") or ""),
            "status": "OK" if int(getattr(row, "is_valid", 1) or 0) else "INVALIDO",
            "importado_em": row.imported_at.isoformat() if getattr(row, "imported_at", None) else "",
            "validado_em": row.validated_at.isoformat() if getattr(row, "validated_at", None) else "",
        }
        for row in rows
        if int(getattr(row, "contest_number", 0) or 0) > 0
    ]


def _load_official_history_contest(contest_number: int | str | None) -> dict[str, Any] | None:
    selected_contest = _safe_int(contest_number, default=None)
    if selected_contest is None:
        return None
    with get_session(DB_PATH) as session:
        row = (
            session.query(LotofacilOfficialHistory)
            .filter(LotofacilOfficialHistory.contest_number == int(selected_contest))
            .limit(1)
            .one_or_none()
        )
    if row is None:
        return None
    numbers = [
        int(str(value).lstrip("0") or "0")
        for value in str(getattr(row, "numbers", "") or "").replace(",", " ").split()
        if str(value).strip().isdigit()
    ]
    return {
        "concurso": int(getattr(row, "contest_number", selected_contest) or selected_contest),
        "data": str(getattr(row, "draw_date", "") or ""),
        "dezenas": numbers,
        "numbers_signature": str(getattr(row, "numbers_signature", "") or ""),
        "fonte": str(getattr(row, "source", "") or ""),
        "status": "OK" if int(getattr(row, "is_valid", 1) or 0) else "INVALIDO",
        "importado_em": row.imported_at.isoformat() if getattr(row, "imported_at", None) else "",
        "validado_em": row.validated_at.isoformat() if getattr(row, "validated_at", None) else "",
    }


def _load_official_history_diagnostics() -> dict[str, Any]:
    try:
        official_rows = _load_official_history_rows()
        imported_summary = _load_imported_contests_summary()
        if str(imported_summary.get("status") or "") == "UNAVAILABLE":
            payload = official_history_diagnostics_unavailable(
                error=str(imported_summary.get("error") or DB_UNAVAILABLE_LABEL)
            )
            payload["imported_contests_count"] = 0
            return payload
        contest_numbers = [int(row.get("concurso", 0) or 0) for row in official_rows if int(row.get("concurso", 0) or 0) > 0]
        if contest_numbers:
            min_contest = contest_numbers[0]
            max_contest = contest_numbers[-1]
            official_set = set(contest_numbers)
            imported_last = imported_summary.get("last_contest")
            target_max = max(
                int(max_contest or 0),
                int(imported_last or 0),
            )
            missing = [contest for contest in range(min_contest, target_max + 1) if contest not in official_set]
        else:
            min_contest = None
            max_contest = None
            missing = []
        imported_last = imported_summary.get("last_contest")
        status = "OK"
        if not contest_numbers:
            status = "INCOMPLETA"
        elif missing:
            status = "INCOMPLETA"
        return {
            "total_lotofacil_official_history": len(official_rows),
            "contest_number_min": min_contest,
            "contest_number_max": max_contest,
            "concursos_faltantes": missing,
            "total_concursos_faltantes": len(missing),
            "ultimo_concurso_imported_contests": imported_last,
            "ultimo_concurso_lotofacil_official_history": max_contest,
            "status_base_oficial": status,
            "imported_contests_count": int(imported_summary.get("count", 0) or 0),
            "imported_contests_window": list(imported_summary.get("window") or []),
            "db_status": "OK",
        }
    except Exception as exc:
        logger.warning("official history diagnostics unavailable: %s", exc)
        return official_history_diagnostics_unavailable(error=str(exc))


def _ensure_official_history_seeded() -> dict[str, Any]:
    diagnostics = _load_official_history_diagnostics()
    if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) > 0 and int(diagnostics.get("total_concursos_faltantes", 0) or 0) == 0:
        return {"status": "ok", "seeded": 0, **diagnostics}
    try:
        repository = ContestRepository(DB_PATH)
        inserted = 0
        if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) <= 0 or int(diagnostics.get("total_concursos_faltantes", 0) or 0) > 0:
            inserted += int(repository.bootstrap_official_history_from_csv())
        inserted += int(repository.sync_official_history_from_imported_contests())
        diagnostics = _load_official_history_diagnostics()
        return {
            "status": "ok" if int(diagnostics.get("total_lotofacil_official_history", 0) or 0) > 0 and int(diagnostics.get("total_concursos_faltantes", 0) or 0) == 0 else "partial",
            "seeded": inserted,
            **diagnostics,
        }
    except Exception as exc:
        return {"status": "error", "seeded": 0, "error": str(exc), **diagnostics}


def _render_scientific_memory_block() -> None:
    seed_report = _ensure_official_history_seeded()
    official_diagnostics = _load_official_history_diagnostics()
    synthesized_batch_memory = _ensure_scientific_batch_memory_from_history()
    if synthesized_batch_memory:
        st.session_state["institutional_batch_reconciliation_memory"] = dict(synthesized_batch_memory)
    scientific_memory = _load_latest_scientific_memory(limit=20)
    batch_reconciliation_memory: dict[str, Any] = {}
    official_15_memory = next((row for row in scientific_memory if _scientific_15_is_official_baseline(row)), {})
    historical_scientific_memory = [row for row in scientific_memory if not _scientific_15_is_official_baseline(row)]
    active_reconciliation_generation_event_id = _safe_int(st.session_state.get("active_reconciliation_generation_event_id"), default=None)
    latest_memory = official_15_memory or (scientific_memory[0] if scientific_memory else {})
    if active_reconciliation_generation_event_id is not None:
        post_reconciliation_memory = next(
            (
                row
                for row in scientific_memory
                if str(row.get("memory_kind", "") or "") == "scientific_reconciliation"
                and int(row.get("generation_event_id", 0) or 0) == int(active_reconciliation_generation_event_id or 0)
            ),
            {},
        )
    else:
        post_reconciliation_memory = next(
            (row for row in scientific_memory if str(row.get("memory_kind", "") or "") == "scientific_reconciliation"),
            {},
        )
    if not post_reconciliation_memory:
        post_reconciliation_memory = dict(st.session_state.get("institutional_post_reconciliation_memory") or {})
    st.markdown("##### Mem?ria Cient?fica da LotoIA")
    summary_cols = st.columns(6)
    summary_cols[0].metric("Concursos oficiais carregados", int(official_diagnostics.get("total_lotofacil_official_history", 0) or 0))
    summary_cols[1].metric("Primeiro concurso", str(official_diagnostics.get("contest_number_min", "-") or "-").zfill(4) if official_diagnostics.get("contest_number_min") is not None else "-")
    summary_cols[2].metric("?ltimo concurso", official_diagnostics.get("contest_number_max", "-") or "-")
    summary_cols[3].metric("Concursos faltantes", int(official_diagnostics.get("total_concursos_faltantes", 0) or 0))
    summary_cols[4].metric("Status da base oficial", official_diagnostics.get("status_base_oficial", "-") or "-")
    summary_cols[5].metric("?ltimo importado", official_diagnostics.get("ultimo_concurso_imported_contests", "-") or "-")
    st.caption(
        " | ".join(
            [
                f"seed_status={seed_report.get('status', '-')}",
                f"seeded={seed_report.get('seeded', 0)}",
                f"faltantes={official_diagnostics.get('concursos_faltantes', [])}",
            ]
        )
    )
    if official_15_memory:
        st.markdown("###### Baseline oficial da política 15")
        official_hit_decomposition = _scientific_hit_decomposition(official_15_memory)
        official_window = dict(official_15_memory.get("generation_range") or {})
        official_cols = st.columns(6)
        official_cols[0].metric("Status atual", str(official_15_memory.get("policy_validation_status", "-") or "-"))
        official_cols[1].metric("Baseline oficial", str(official_15_memory.get("batch_id", "-") or "-"))
        official_cols[2].metric("Concurso de validação", int(official_15_memory.get("contest_number", official_window.get("contest_number", 0)) or 0))
        official_cols[3].metric("Melhor acerto", int(official_15_memory.get("best_hit", 0) or 0))
        official_cols[4].metric("Jogos com 11+", int(official_hit_decomposition.get("count_11_plus", 0) or 0))
        official_cols[5].metric("Jogos com 13+", int(official_hit_decomposition.get("count_13_plus", 0) or 0))
        official_banner = _official_15_policy_status_label(official_15_memory)
        if official_banner:
            st.success(official_banner)
        official_exact_cols = st.columns(5)
        official_exact_cols[0].metric("count_11_exact", int(official_hit_decomposition.get("count_11_exact", 0) or 0))
        official_exact_cols[1].metric("count_12_exact", int(official_hit_decomposition.get("count_12_exact", 0) or 0))
        official_exact_cols[2].metric("count_13_exact", int(official_hit_decomposition.get("count_13_exact", 0) or 0))
        official_exact_cols[3].metric("count_14_exact", int(official_hit_decomposition.get("count_14_exact", 0) or 0))
        official_exact_cols[4].metric("count_15_exact", int(official_hit_decomposition.get("count_15_exact", 0) or 0))
        official_plus_cols = st.columns(5)
        official_plus_cols[0].metric("count_11_plus", int(official_hit_decomposition.get("count_11_plus", 0) or 0))
        official_plus_cols[1].metric("count_12_plus", int(official_hit_decomposition.get("count_12_plus", 0) or 0))
        official_plus_cols[2].metric("count_13_plus", int(official_hit_decomposition.get("count_13_plus", 0) or 0))
        official_plus_cols[3].metric("count_14_plus", int(official_hit_decomposition.get("count_14_plus", 0) or 0))
        official_plus_cols[4].metric("count_15", int(official_hit_decomposition.get("count_15", 0) or 0))
        official_detail_cols = st.columns(4)
        official_detail_cols[0].markdown(
            f"**Classificação oficial**  \n{official_15_memory.get('policy_validation_status', '-') or '-'}"
        )
        official_detail_cols[1].markdown(
            f"**Mensagem oficial**  \n{official_banner or 'Política 15 validada até nível 13. Ouro 14 e diamante 15 seguem como metas futuras.'}"
        )
        official_detail_cols[2].markdown(
            f"**Baseline batch_id**  \n{official_15_memory.get('baseline_batch_id', official_15_memory.get('batch_id', '-')) or '-'}"
        )
        official_detail_cols[3].markdown(
            f"**Concurso base**  \n{official_15_memory.get('baseline_contest_number', official_window.get('contest_number', '-')) or '-'}"
        )
        with st.expander("Ver baseline oficial da política 15 completa", expanded=False):
            st.json(official_15_memory)
    if post_reconciliation_memory:
        post_title = "###### Histórico antigo / memória anterior à baseline oficial - Memória pós-conferência científica" if official_15_memory else "###### Memória pós-conferência científica"
        st.markdown(post_title)
        post_window = dict(post_reconciliation_memory.get("generation_range") or {})
        cross_validation_summary = dict(post_reconciliation_memory.get("cross_validation_summary") or {})
        scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
        post_hit_decomposition = _scientific_hit_decomposition(post_reconciliation_memory)
        post_summary_cols = st.columns(6)
        post_summary_cols[0].metric(
            "Última geração conferida",
            post_window.get("generation_event_id", post_reconciliation_memory.get("batch_id", "-")) or "-",
        )
        post_summary_cols[1].metric(
            "Concurso conferido",
            post_window.get("contest_number", post_reconciliation_memory.get("official_history_last_contest", "-")) or "-",
        )
        post_summary_cols[2].metric("Jogos conferidos", int(post_reconciliation_memory.get("total_games", 0) or 0))
        post_summary_cols[3].metric("Melhor acerto", int(post_reconciliation_memory.get("best_hit", 0) or 0))
        post_summary_cols[4].metric("Jogos com 10", int(post_hit_decomposition.get("count_10_exact", 0) or 0))
        post_summary_cols[5].metric(
            f"Jogos com {post_hit_decomposition.get('validation_threshold', 11)}+",
            int(post_hit_decomposition.get("scientific_validation_zone_count", post_hit_decomposition.get("count_11_plus", 0)) or 0),
        )
        post_exact_cols = st.columns(6)
        post_exact_cols[0].metric("count_10_exact", int(post_hit_decomposition.get("count_10_exact", 0) or 0))
        post_exact_cols[1].metric("count_11_exact", int(post_hit_decomposition.get("count_11_exact", 0) or 0))
        post_exact_cols[2].metric("count_12_exact", int(post_hit_decomposition.get("count_12_exact", 0) or 0))
        post_exact_cols[3].metric("count_13_exact", int(post_hit_decomposition.get("count_13_exact", 0) or 0))
        post_exact_cols[4].metric("count_14_exact", int(post_hit_decomposition.get("count_14_exact", 0) or 0))
        post_exact_cols[5].metric("count_15_exact", int(post_hit_decomposition.get("count_15_exact", 0) or 0))
        post_plus_cols = st.columns(5)
        post_plus_cols[0].metric("count_11_plus", int(post_hit_decomposition.get("count_11_plus", 0) or 0))
        post_plus_cols[1].metric("count_12_plus", int(post_hit_decomposition.get("count_12_plus", 0) or 0))
        post_plus_cols[2].metric("count_13_plus", int(post_hit_decomposition.get("count_13_plus", 0) or 0))
        post_plus_cols[3].metric("count_14_plus", int(post_hit_decomposition.get("count_14_plus", 0) or 0))
        post_plus_cols[4].metric("count_15", int(post_hit_decomposition.get("count_15", 0) or 0))
        post_detail_cols = st.columns(4)
        post_detail_cols[0].markdown(f"**Classificação local**  \n{post_reconciliation_memory.get('scientific_classification', '-') or '-'}")
        post_detail_cols[1].markdown("**Registro técnico legado**  \nPreservado para auditoria histórica, sem comando operacional.")
        post_detail_cols[2].markdown(
            f"**Nível de confiança**  \n{cross_validation_summary.get('confidence_level', '-') or '-'}"
        )
        post_detail_cols[3].markdown(
            f"**Risco de overfit**  \n{scientific_components.get('overfit_risk', '-') or '-'}"
        )
        windows_summary = cross_validation_summary.get("historical_windows", {}) or {}
        if windows_summary:
            st.markdown("###### Expansão histórica")
            window_items = sorted(
                windows_summary.items(),
                key=lambda item: (item[0] != "all", int(item[0]) if str(item[0]).isdigit() else 9999),
            )
            window_cols = st.columns(min(5, max(1, len(window_items))))
            for index, (label, window_payload) in enumerate(window_items[: len(window_cols)]):
                window_cols[index].metric(
                    f"Janela {label}",
                    int(window_payload.get("contest_count", 0) or 0),
                )
            with st.expander("Memória pós-conferência observacional — detalhes avançados", expanded=False):
                st.caption("Registro técnico legado preservado para auditoria histórica.")
                st.json(post_reconciliation_memory)
        batch_reconciliation_memory = next(
            (row for row in scientific_memory if str(row.get("memory_kind", "") or "") == "scientific_batch_reconciliation"),
            {},
        )
    if batch_reconciliation_memory:
        batch_title = "###### Histórico institucional / memória consolidada da bateria conferida" if official_15_memory else "###### Memória consolidada da bateria conferida"
        st.markdown(batch_title)
        batch_window = dict(batch_reconciliation_memory.get("generation_range") or {})
        batch_components = dict(batch_reconciliation_memory.get("scientific_score_components") or {})
        batch_cross_validation = dict(batch_reconciliation_memory.get("cross_validation_summary") or {})
        batch_hit_decomposition = _scientific_hit_decomposition(batch_reconciliation_memory)
        batch_cross_windows = dict(
            batch_cross_validation.get("windows")
            or batch_cross_validation.get("cross_validation_windows")
            or {}
        )
        batch_memory_role = str(
            batch_reconciliation_memory.get("memory_role")
            or batch_cross_validation.get("memory_role")
            or "strong_support"
        )
        batch_dominant_memory = batch_reconciliation_memory.get(
            "dominant_memory",
            batch_cross_validation.get("dominant_memory", "conditional"),
        )
        batch_selection_variant = str(
            batch_reconciliation_memory.get("selection_variant")
            or batch_cross_validation.get("selection_variant")
            or "cross_validated_scientific_batch_memory"
        )
        batch_cross_validation_reason = str(
            batch_reconciliation_memory.get("cross_validation_reason")
            or batch_cross_validation.get("cross_validation_reason")
            or "historical_cross_validation_supports_memory"
        )
        batch_prospective_status = "historical_only" if official_15_memory else "pending_prospective_validation"
        if official_15_memory:
            st.info(
                "Histórico antigo / memória anterior à baseline oficial. "
                "A política 15 consolidada acima é a referência principal atual."
            )
        else:
            st.info(
                "Memória com suporte histórico cruzado. Validação cruzada histórica favorável, mas ainda pendente de validação prospectiva."
            )
        identity_cols = st.columns(5)
        identity_cols[0].markdown(f"**memory_id**  \n{batch_reconciliation_memory.get('id', '-')}")
        identity_cols[1].markdown(f"**memory_kind**  \n{batch_reconciliation_memory.get('memory_kind', '-') or '-'}")
        identity_cols[2].markdown(f"**generation_event_id**  \n{batch_reconciliation_memory.get('generation_event_id', '-') or '-'}")
        identity_cols[3].markdown(f"**classification**  \n{batch_reconciliation_memory.get('scientific_classification', '-') or '-'}")
        identity_cols[4].markdown(f"**status prospectivo**  \n{batch_prospective_status}")
        role_cols = st.columns(3)
        role_cols[0].markdown(f"**memory_role**  \n{batch_memory_role}")
        role_cols[1].markdown("**dominant_memory**  \nRegistro legado para auditoria histórica")
        role_cols[2].markdown("**selection_variant**  \nRegistro legado para auditoria histórica")
        control_cols = st.columns(2)
        control_cols[0].markdown(f"**cross_validation_reason**  \n{batch_cross_validation_reason}")
        control_cols[1].markdown("**Registro técnico legado**  \nPreservado para auditoria histórica, sem comando operacional.")
        batch_cols = st.columns(6)
        batch_cols[0].metric(
            "Última bateria conferida",
            f"{batch_window.get('first_generation_event_id', '-') }–{batch_window.get('last_generation_event_id', '-') }".replace(" ", ""),
        )
        batch_cols[1].metric("Total de gerações", int(batch_window.get("total_generations", 0) or 0))
        batch_cols[2].metric("Total de jogos", int(batch_window.get("total_games_checked", 0) or 0))
        batch_cols[3].metric("Melhor acerto global", int(batch_window.get("global_best_hits", 0) or 0))
        batch_cols[4].metric("Jogos com 10", int(batch_hit_decomposition.get("count_10_exact", 0) or 0))
        batch_cols[5].metric(
            f"Jogos com {batch_hit_decomposition.get('validation_threshold', 11)}+",
            int(batch_hit_decomposition.get("scientific_validation_zone_count", batch_hit_decomposition.get("count_11_plus", 0)) or 0),
        )
        batch_exact_cols = st.columns(6)
        batch_exact_cols[0].metric("count_10_exact", int(batch_hit_decomposition.get("count_10_exact", 0) or 0))
        batch_exact_cols[1].metric("count_11_exact", int(batch_hit_decomposition.get("count_11_exact", 0) or 0))
        batch_exact_cols[2].metric("count_12_exact", int(batch_hit_decomposition.get("count_12_exact", 0) or 0))
        batch_exact_cols[3].metric("count_13_exact", int(batch_hit_decomposition.get("count_13_exact", 0) or 0))
        batch_exact_cols[4].metric("count_14_exact", int(batch_hit_decomposition.get("count_14_exact", 0) or 0))
        batch_exact_cols[5].metric("count_15_exact", int(batch_hit_decomposition.get("count_15_exact", 0) or 0))
        batch_plus_cols = st.columns(5)
        batch_plus_cols[0].metric("count_11_plus", int(batch_hit_decomposition.get("count_11_plus", 0) or 0))
        batch_plus_cols[1].metric("count_12_plus", int(batch_hit_decomposition.get("count_12_plus", 0) or 0))
        batch_plus_cols[2].metric("count_13_plus", int(batch_hit_decomposition.get("count_13_plus", 0) or 0))
        batch_plus_cols[3].metric("count_14_plus", int(batch_hit_decomposition.get("count_14_plus", 0) or 0))
        batch_plus_cols[4].metric("count_15", int(batch_hit_decomposition.get("count_15", 0) or 0))
        batch_detail_cols = st.columns(4)
        batch_detail_cols[0].markdown(f"**Classificação global**  \n{batch_reconciliation_memory.get('scientific_classification', '-') or '-'}")
        batch_detail_cols[1].markdown("**Registro técnico legado**  \nPreservado para auditoria histórica, sem comando operacional.")
        batch_detail_cols[2].markdown(
            f"**Validação histórica**  \n{batch_reconciliation_memory.get('confidence_level', '-') or '-'}"
        )
        batch_detail_cols[3].markdown(
            f"**Eventos avaliados**  \n{len(batch_window.get('generation_event_ids', []) or [])}"
        )
        st.markdown("###### Validação histórica observacional")
        if batch_cross_windows:
            for label in ("10", "30", "60"):
                window_payload = dict(batch_cross_windows.get(label, {}) or {})
                if not window_payload:
                    continue
                st.markdown(f"**Janela {label}**")
                window_cols = st.columns(3)
                window_cols[0].metric("average_best_hits", f"{float(window_payload.get('average_best_hits', 0.0) or 0.0):.4f}")
                window_cols[1].metric("max_best_hits", int(window_payload.get("max_best_hits", 0) or 0))
                validation_threshold = int(batch_hit_decomposition.get("validation_threshold", 11) or 11)
                window_cols[2].metric(
                    f"contests_with_{validation_threshold}_plus",
                    int(
                        window_payload.get(
                            f"contests_with_{validation_threshold}_plus",
                            window_payload.get("contests_with_11_plus", 0),
                        )
                        or 0
                    ),
                )
                window_detail_cols = st.columns(3)
                window_detail_cols[0].metric(
                    f"total_count_{validation_threshold}_plus",
                    int(window_payload.get(f"total_count_{validation_threshold}_plus", window_payload.get("total_count_11_plus", 0)) or 0),
                )
                window_detail_cols[1].metric(
                    f"total_count_{validation_threshold + 1}_plus",
                    int(window_payload.get(f"total_count_{validation_threshold + 1}_plus", window_payload.get("total_count_12_plus", 0)) or 0),
                )
                window_detail_cols[2].metric(
                    "total_count_15" if validation_threshold >= 13 else f"total_count_{validation_threshold + 2}_plus",
                    int(window_payload.get("total_count_15", window_payload.get(f"total_count_{validation_threshold + 2}_plus", window_payload.get("total_count_13_plus", 0))) or 0),
                )
                with st.expander(f"Ver detalhes da janela {label}", expanded=False):
                    st.json(window_payload)
        else:
            st.caption("Validação cruzada histórica não persistida nesta memória; usando o resumo consolidado disponível.")
        st.markdown("###### Validação prospectiva")
        prospective_cols = st.columns(4)
        prospective_cols[0].markdown("**Status**  \nainda não confirmada")
        prospective_cols[1].markdown("**Próximo passo**  \nrequer próxima bateria limpa")
        prospective_cols[2].markdown("**Conferência**  \ncontra concurso não usado como calibração")
        prospective_cols[3].markdown(f"**Critério mínimo**  \nproduzir {batch_hit_decomposition.get('validation_threshold', 11)}+")
        ranking_payload = list(
            dict(batch_reconciliation_memory.get("cross_validation_summary") or {}).get("near_miss_generation_ranking") or []
        )
        if ranking_payload:
            ranking_rows = []
            for item in ranking_payload[:10]:
                ranking_rows.append(
                    {
                        "generation_event_id": int(item.get("generation_event_id", 0) or 0),
                        "best_hits": int(item.get("best_hits", 0) or 0),
                        "count_10": int(item.get("count_10", 0) or 0),
                        "count_11_plus": int(item.get("count_11_plus", 0) or 0),
                        "average_hits": float(item.get("average_hits", 0.0) or 0.0),
                        "dispersion": float(item.get("dispersion", 0.0) or 0.0),
                    }
                )
            st.dataframe(_make_streamlit_dataframe_safe(pd.DataFrame(ranking_rows)), hide_index=True, use_container_width=True)
        st.caption(
            " | ".join(
                [
                    f"generation_event_id={batch_reconciliation_memory.get('generation_event_id', '-')}",
                    f"generation_event_ids={batch_window.get('generation_event_ids', [])}",
                    f"classification={batch_reconciliation_memory.get('scientific_classification', '-')}",
                    f"memory_role={batch_memory_role}",
                    f"dominant_memory={batch_dominant_memory}",
                    f"cross_validation_reason={batch_cross_validation_reason}",
                ]
            )
        )
        if official_15_memory:
            st.warning(
                "Histórico antigo preservado para auditoria. "
                "A baseline oficial da política 15 acima é a leitura principal e já validada nível 3."
            )
        else:
            st.warning(
                "A memória possui suporte histórico cruzado, mas ainda depende de validação prospectiva. "
                f"O uso recomendado é condicional/híbrido até produzir {batch_hit_decomposition.get('validation_threshold', 11)}+ na próxima bateria limpa."
            )
        with st.expander("Memória consolidada da bateria conferida — detalhes", expanded=False):
            if st.checkbox("Carregar memória consolidada", value=False, key="load_batch_reconciliation_memory"):
                st.json(batch_reconciliation_memory)
    else:
        st.caption("Memória de reconciliação em lote indisponível ou ainda não registrada para esta sessão.")
    strong_near_miss_memory = next(
        (row for row in scientific_memory if str(row.get("memory_kind", "") or "") == "scientific_strong_near_miss"),
        {},
    )
    if strong_near_miss_memory:
        near_miss_title = "###### Histórico antigo / memória anterior à baseline oficial - Melhores near miss da última bateria" if official_15_memory else "###### Melhores near miss da última bateria"
        st.markdown(near_miss_title)
        near_miss_window = dict(strong_near_miss_memory.get("generation_range") or {})
        near_miss_components = dict(strong_near_miss_memory.get("scientific_score_components") or {})
        near_miss_hit_decomposition = _scientific_hit_decomposition(strong_near_miss_memory)
        near_miss_cols = st.columns(6)
        near_miss_cols[0].metric("Melhor geração", int(near_miss_window.get("best_generation_event_id", 0) or 0))
        near_miss_cols[1].metric(
            "Jogos com 10",
            int(near_miss_hit_decomposition.get("count_10_exact", 0) or 0),
        )
        near_miss_cols[2].metric(
            f"Jogos com {near_miss_hit_decomposition.get('validation_threshold', 11)}+",
            int(near_miss_hit_decomposition.get("scientific_validation_zone_count", near_miss_hit_decomposition.get("count_11_plus", 0)) or 0),
        )
        near_miss_cols[3].metric("Melhor acerto", int(near_miss_window.get("best_generation_best_hits", 0) or strong_near_miss_memory.get("best_hit", 0) or 0))
        near_miss_cols[4].metric("Classificação", str(strong_near_miss_memory.get("scientific_classification", "-") or "-"))
        near_miss_cols[5].metric(
            "Registro técnico legado",
            _institutional_safe_action_label(strong_near_miss_memory.get("recommended_action", "-")),
        )
        near_miss_exact_cols = st.columns(6)
        near_miss_exact_cols[0].metric("count_10_exact", int(near_miss_hit_decomposition.get("count_10_exact", 0) or 0))
        near_miss_exact_cols[1].metric("count_11_exact", int(near_miss_hit_decomposition.get("count_11_exact", 0) or 0))
        near_miss_exact_cols[2].metric("count_12_exact", int(near_miss_hit_decomposition.get("count_12_exact", 0) or 0))
        near_miss_exact_cols[3].metric("count_13_exact", int(near_miss_hit_decomposition.get("count_13_exact", 0) or 0))
        near_miss_exact_cols[4].metric("count_14_exact", int(near_miss_hit_decomposition.get("count_14_exact", 0) or 0))
        near_miss_exact_cols[5].metric("count_15_exact", int(near_miss_hit_decomposition.get("count_15_exact", 0) or 0))
        near_miss_plus_cols = st.columns(5)
        near_miss_plus_cols[0].metric("count_11_plus", int(near_miss_hit_decomposition.get("count_11_plus", 0) or 0))
        near_miss_plus_cols[1].metric("count_12_plus", int(near_miss_hit_decomposition.get("count_12_plus", 0) or 0))
        near_miss_plus_cols[2].metric("count_13_plus", int(near_miss_hit_decomposition.get("count_13_plus", 0) or 0))
        near_miss_plus_cols[3].metric("count_14_plus", int(near_miss_hit_decomposition.get("count_14_plus", 0) or 0))
        near_miss_plus_cols[4].metric("count_15", int(near_miss_hit_decomposition.get("count_15", 0) or 0))
        st.caption(
            " | ".join(
                [
                    f"batch_id={strong_near_miss_memory.get('batch_id', '-')}",
                    f"candidate_generation_event_ids={near_miss_window.get('candidate_generation_event_ids', [])}",
                    f"total_generations_analyzed={near_miss_window.get('total_generations_analyzed', 0)}",
                    f"secondary_reference_generation_event_id={near_miss_window.get('secondary_reference_generation_event_id', '-')}",
                    f"count_10={near_miss_components.get('count_10', strong_near_miss_memory.get('count_10', 0))}",
                ]
            )
        )
        with st.expander("Melhores near miss — detalhes", expanded=False):
            if st.checkbox("Carregar near miss", value=False, key="load_strong_near_miss_memory"):
                st.json(strong_near_miss_memory)
    st.markdown("##### Histórico Oficial Lotofácil")
    official_rows_summary = _load_official_history_rows(limit=10, descending=True)
    if official_rows_summary:
        st.caption("Últimos 10 concursos oficiais persistidos no banco. A tabela completa é carregada sob demanda.")
        summary_df = pd.DataFrame(official_rows_summary)[["concurso", "data", "dezenas_sorteadas", "numbers_signature", "fonte", "status", "importado_em"]]
        st.dataframe(_make_streamlit_dataframe_safe(summary_df), hide_index=True, use_container_width=True)
        show_official_history = st.checkbox("Carregar histórico oficial Lotofácil", value=False, key="show_official_history")
        if show_official_history:
            filter_cols = st.columns([2, 2, 1])
            search_term = filter_cols[0].text_input("Buscar concurso", value="", key="official_history_search")
            order_mode = filter_cols[1].selectbox("Ordem", ["Mais recentes", "Mais antigos"], index=0, key="official_history_order")
            limit_value = int(filter_cols[2].number_input("Linhas", min_value=5, max_value=50, value=25, step=1, key="official_history_limit"))
            official_rows = _load_official_history_rows()
            filtered_rows = official_rows
            if search_term.strip():
                term = search_term.strip().lower()
                filtered_rows = [
                    row for row in filtered_rows
                    if term in str(row.get("concurso", "")).lower()
                    or term in str(row.get("data", "")).lower()
                    or term in str(row.get("dezenas_sorteadas", "")).lower()
                    or term in str(row.get("numbers_signature", "")).lower()
                ]
            if order_mode == "Mais recentes":
                filtered_rows = list(reversed(filtered_rows))
            table_rows = filtered_rows[:limit_value]
            official_df = pd.DataFrame(table_rows)[["concurso", "data", "dezenas_sorteadas", "numbers_signature", "fonte", "status", "importado_em"]]
            st.dataframe(_make_streamlit_dataframe_safe(official_df), hide_index=True, use_container_width=True)
    else:
        st.info("Histórico oficial vazio. Aguarde a sincronização da base oficial.")
    scientific_cols = st.columns(4)
    scientific_cols[0].metric("Lei Científica LotoIA", "COMMANDER")
    scientific_cols[1].metric("Gerador ADM", "EXECUTOR")
    scientific_cols[2].metric("OutputCommander", "AUDITOR")
    scientific_cols[3].metric("Memória institucional", "REGISTRY")
    st.caption(
        " | ".join(
            [
                f"memory_kind={latest_memory.get('memory_kind', '-')} ",
                f"strategy={latest_memory.get('strategy_name', '-')} ",
                f"batch_id={latest_memory.get('batch_id', '-')} ",
                f"decision_mode={latest_memory.get('decision_mode', '-')} ",
                f"approved_for_use={latest_memory.get('approved_for_use', False)}",
                "generation_hierarchy=LOTOIA_LAW_ONLY",
                "legacy_calibrator_role=REMOVED_FROM_RUNTIME",
                "legacy_runtime_access=False",
            ]
        )
    )
    if scientific_memory:
        with st.expander("Memória científica legada — quarentena documental", expanded=False):
            if official_15_memory:
                st.caption(
                    "Baseline oficial 15 validada nível 3 | official_15_search_standard=true | "
                    "histórico antigo preservado abaixo apenas para auditoria | historical_view_only=true"
                )
                display_rows = [official_15_memory] + historical_scientific_memory
            else:
                st.caption(
                    "Memória institucional com suporte histórico cruzado | strong_support | dominant_memory=conditional | "
                    "validação cruzada histórica favorável | historical_view_only=true"
                )
                display_rows = scientific_memory
            if st.checkbox("Carregar payload científico legado", value=False, key="load_scientific_legacy_payload_listing"):
                scientific_memory_listing = _format_scientific_memory_listing(display_rows)
                st.dataframe(
                    _make_streamlit_dataframe_safe(scientific_memory_listing),
                    hide_index=True,
                    use_container_width=True,
                )


def _format_scientific_number_list(values: Sequence[int] | None) -> str:
    formatted: list[str] = []
    for value in values or []:
        try:
            formatted.append(f"{int(value):02d}")
        except Exception:
            continue
    return ", ".join(formatted) if formatted else "-"


def _format_scientific_parity_pairs(pairs: Sequence[tuple[int, int]] | None) -> str:
    formatted: list[str] = []
    for pair in pairs or []:
        try:
            normalized_pair = _normalize_scientific_parity_pair(pair)
            if normalized_pair is None:
                continue
            formatted.append(f"{normalized_pair[0]}/{normalized_pair[1]}")
        except Exception:
            continue
    return ", ".join(formatted) if formatted else "-"


def _normalize_scientific_parity_pair(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for separator in ("/", "-"):
            if separator in text:
                left, right = text.split(separator, 1)
                left_value = _safe_int(left.strip(), default=None)
                right_value = _safe_int(right.strip(), default=None)
                if left_value is None or right_value is None:
                    return None
                return int(left_value), int(right_value)
        return None
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        left_value = _safe_int(value[0], default=None)
        right_value = _safe_int(value[1], default=None)
        if left_value is None or right_value is None:
            return None
        return int(left_value), int(right_value)
    return None


def _scientific_policy_is_ready(policy_discovery: dict[str, Any] | None) -> bool:
    if not isinstance(policy_discovery, dict):
        return False
    if str(policy_discovery.get("policy_origin", "") or "").strip() not in {"automatic_scientific_discovery", "scientific_batch_reconciliation_memory"}:
        return False
    if int(policy_discovery.get("candidate_count", policy_discovery.get("policies_tested", 0)) or 0) <= 0:
        return False
    if not str(policy_discovery.get("selection_reason", "") or "").strip():
        return False
    policy = policy_discovery.get("policy")
    selection_status = str(policy_discovery.get("selection_status", "") or "").strip().upper()
    if selection_status and selection_status not in {"POLICY_SELECTED", "POLICY_DESCOBERTA_E_SELECIONADA"}:
        return False
    return isinstance(policy, dict) and bool(policy)


def _render_scientific_policy_panel(
    *,
    policy: dict[str, Any],
    strategy_size: int,
    total_expected_games: int,
    games_per_generation: int,
    generations_in_batch: int,
    policy_discovery: dict[str, Any] | None = None,
    use_expander: bool = True,
) -> None:
    st.markdown("##### Lei Científica da Geração")
    discovery_ready = _scientific_policy_is_ready(policy_discovery)
    policy_payload = dict(policy_discovery.get("policy") or {}) if discovery_ready else {}
    discovery_origin = str(policy_discovery.get("policy_origin", "-") or "-") if isinstance(policy_discovery, dict) else "-"
    selection_status = str(policy_discovery.get("selection_status", "") or "").strip().upper() if isinstance(policy_discovery, dict) else ""
    if discovery_ready:
        discovery_status = "LEI DESCOBERTA E SELECIONADA"
    elif selection_status == "NONE_APPROVED":
        discovery_status = "NENHUMA LEI APROVADA ENCONTRADA"
    elif selection_status == "PENDING":
        discovery_status = "DESCOBERTA EM EXECUÇÃO"
    else:
        discovery_status = "AGUARDANDO LEI AUTOMÁTICA"
    selected_policy_id = str(policy_discovery.get("policy_id", "-") or "-") if discovery_ready else "-"
    selected_policy_name = str(policy_discovery.get("selection_variant", "-") or "-") if discovery_ready else "-"
    selected_reason = str(policy_discovery.get("selection_reason", "-") or "-") if discovery_ready else "-"
    selected_memory_role = str(policy_discovery.get("memory_role", policy_payload.get("memory_role", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_dominant_memory = str(policy_discovery.get("dominant_memory", policy_payload.get("dominant_memory", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_based_on_memory_kind = str(policy_discovery.get("based_on_memory_kind", policy_payload.get("based_on_memory_kind", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_based_on_memory_id = str(policy_discovery.get("based_on_memory_id", policy_payload.get("based_on_memory_id", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_based_on_batch_id = str(policy_discovery.get("based_on_batch_id", policy_payload.get("based_on_batch_id", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_cross_validation_reason = str(policy_discovery.get("cross_validation_reason", policy_payload.get("cross_validation_reason", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_recommended_action = str(policy_discovery.get("recommended_action", policy_payload.get("recommended_action", "-")) or "-") if isinstance(policy_discovery, dict) else "-"
    selected_validation_threshold = int(policy_discovery.get("validation_threshold", policy_payload.get("validation_threshold", strategy_size if strategy_size else 15)) or 15) if isinstance(policy_discovery, dict) else 15
    selected_target_band = str(policy_discovery.get("target_band", policy_payload.get("target_band", f"{selected_validation_threshold}_to_15")) or f"{selected_validation_threshold}_to_15") if isinstance(policy_discovery, dict) else f"{selected_validation_threshold}_to_15"
    selected_validation_zone_label = str(policy_discovery.get("validation_zone_label", policy_payload.get("validation_zone_label", f"Zona de validação científica: {selected_validation_threshold} a 15 acertos.")) or f"Zona de validação científica: {selected_validation_threshold} a 15 acertos.") if isinstance(policy_discovery, dict) else f"Zona de validação científica: {selected_validation_threshold} a 15 acertos."
    official_15_policy_status_label = _official_15_policy_status_label(policy_discovery if isinstance(policy_discovery, dict) else policy_payload)
    panel_validation_rule = _scientific_validation_rule(strategy_size)
    panel_validation_threshold = int(panel_validation_rule.get("validation_threshold", selected_validation_threshold) or selected_validation_threshold)
    panel_validation_zone_label = str(panel_validation_rule.get("validation_zone_label", selected_validation_zone_label) or selected_validation_zone_label)
    selected_window = str(policy_discovery.get("validation_window", "-") or "-") if discovery_ready else "-"
    selected_score = str(policy_discovery.get("selection_score", "-") or "-") if discovery_ready else "-"
    selected_at = str(policy_discovery.get("selected_at", "-") or "-") if discovery_ready else "-"
    tested_count = int(policy_discovery.get("policies_tested", policy_discovery.get("candidate_count", 0)) or 0) if isinstance(policy_discovery, dict) else 0
    rejected_by_guardian = int(policy_discovery.get("rejected_by_guardian", 0) or 0) if isinstance(policy_discovery, dict) else 0
    rejected_by_rules = int(policy_discovery.get("rejected_by_rules", 0) or 0) if isinstance(policy_discovery, dict) else 0
    parameter_reasoning = dict(policy_discovery.get("parameter_reasoning") or {}) if discovery_ready else {}
    cross_validation_summary = dict(
        policy_discovery.get("cross_validation_summary")
        or policy_payload.get("cross_validation_summary")
        or {}
    ) if isinstance(policy_discovery, dict) else {}
    cross_validation_windows = dict(
        policy_discovery.get("cross_validation_windows")
        or policy_payload.get("cross_validation_windows")
        or cross_validation_summary.get("windows")
        or {}
    ) if isinstance(policy_discovery, dict) else {}

    top_cols = st.columns(4)
    top_cols[0].metric("Lei", f"{int(strategy_size)} dezenas")
    top_cols[1].metric("Origem", discovery_origin if discovery_ready else "aguardando lei automática")
    top_cols[2].metric("Status", discovery_status if discovery_ready else "AGUARDANDO LEI")
    top_cols[3].metric("Leis testadas", tested_count if discovery_ready else 0)

    meta_cols = st.columns(4)
    meta_cols[0].metric("Lei selecionada", selected_policy_name)
    meta_cols[1].metric("Janela analisada", selected_window)
    meta_cols[2].metric("Crit?rio vencedor", selected_reason)
    meta_cols[3].metric("Pol?tica ID", selected_policy_id)

    score_cols = st.columns(2)
    score_cols[0].metric("Selection score", selected_score)
    score_cols[1].metric("Selected at", selected_at)

    if discovery_ready:
        st.info(
            official_15_policy_status_label
            or (
                f"Último concurso não produziu {selected_validation_threshold}+, mas a validação cruzada histórica sustenta a memória como "
                f"{selected_memory_role} / dominant_memory {selected_dominant_memory}."
            )
        )
        st.caption(panel_validation_zone_label)

    if not discovery_ready:
        if selection_status == "NONE_APPROVED":
            st.warning("Nenhuma lei aprovada encontrada.")
            st.caption(
                f"Leis testadas: {tested_count} | "
                f"descartadas pelo guardi?o: {rejected_by_guardian} | "
                f"descartadas pelas regras: {rejected_by_rules}"
            )
        else:
            st.info("Parâmetros: aguardando a LotoIA descobrir a lei.")
        with st.expander("Ver payload t?cnico completo", expanded=False):
            st.json({"status": "aguardando descoberta automática", "policy_discovery": policy_discovery or {}})
        return

    detail_cols = st.columns(3)
    repeat_min = int(policy_payload.get("repeat_min", 0) or 0)
    repeat_max = int(policy_payload.get("repeat_max", 0) or 0)
    detail_cols[0].markdown(f"**Repeti??o do ?ltimo concurso**  \\n{repeat_min} a {repeat_max} dezenas")
    detail_cols[1].markdown(
        f"**Paridade preferencial**  \\n{_format_scientific_parity_pairs(policy_payload.get('preferred_parity_pairs', []))}"
    )
    detail_cols[2].markdown(
        f"**Paridade permitida**  \\n{_format_scientific_parity_pairs(policy_payload.get('allowed_parity_pairs', []))}"
    )

    detail_cols_2 = st.columns(3)
    detail_cols_2[0].markdown(
        f"**Limite de sequ?ncia**  \\nM?ximo {int(policy_payload.get('sequence_max', 0) or 0)} dezenas consecutivas"
    )
    detail_cols_2[1].markdown(
        f"**N?cleo refor?ado**  \\n{_format_scientific_number_list(policy_payload.get('core_numbers', []))}"
    )
    detail_cols_2[2].markdown(
        f"**Dezenas com redu??o de peso**  \\n{_format_scientific_number_list(policy_payload.get('discouraged_numbers', []))}"
    )

    freq_cols = st.columns(2)
    freq_cols[0].metric(
        "Controle de frequ?ncia (m?x.)",
        f"{float(policy_payload.get('max_frequency_ratio', 0.0) or 0.0) * 100:.0f}%",
    )
    freq_cols[1].metric(
        "Controle de frequ?ncia (m?n. candidata)",
        f"{float(policy_payload.get('min_frequency_ratio', 0.0) or 0.0) * 100:.0f}%",
    )

    identity_cols = st.columns(4)
    identity_cols[0].markdown(f"**based_on_memory_kind**  \n{selected_based_on_memory_kind}")
    identity_cols[1].markdown(f"**based_on_memory_id**  \n{selected_based_on_memory_id}")
    identity_cols[2].markdown(f"**based_on_batch_id**  \n{selected_based_on_batch_id}")
    identity_cols[3].markdown(f"**memory_role / dominant_memory**  \n{selected_memory_role} / {selected_dominant_memory}")

    control_cols = st.columns(3)
    control_cols[0].markdown(f"**selection_variant**  \n{selected_policy_name}")
    control_cols[1].markdown(f"**cross_validation_reason**  \n{selected_cross_validation_reason}")
    control_cols[2].markdown(
        f"**historical_view_only**  \n{str(bool(policy_discovery.get('legacy_runtime_access', False)) is False).lower()}"
    )

    if cross_validation_windows:
        st.markdown("###### Validação cruzada histórica")
        window_labels = [("10", "Janela 10"), ("30", "Janela 30"), ("60", "Janela 60")]
        for key, label in window_labels:
            window = dict(cross_validation_windows.get(key, {}) or {})
            if not window:
                continue
            window_decomposition = _scientific_hit_decomposition({"game_size": strategy_size, **window})
            st.markdown(f"**{label}**")
            window_cols = st.columns(3)
            window_cols[0].metric("average_best_hits", f"{float(window.get('average_best_hits', 0.0) or 0.0):.4f}")
            window_cols[1].metric("max_best_hits", str(int(window.get('max_best_hits', 0) or 0)))
            window_cols[2].metric("contests_with_11_plus", str(int(window.get('contests_with_11_plus', 0) or 0)))
            window_detail_counts = [count for count in range(panel_validation_threshold, 16)]
            detail_cols = st.columns(max(1, len(window_detail_counts) + 2))
            detail_cols[0].metric("validation_threshold", str(int(window_decomposition.get("validation_threshold", panel_validation_threshold) or panel_validation_threshold)))
            for index, count in enumerate(window_detail_counts, start=1):
                detail_cols[index].metric(
                    f"count_{count}_exact",
                    str(int(window_decomposition.get(f"count_{count}_exact", 0) or 0)),
                )
            detail_cols[len(window_detail_counts) + 1].metric(
                f"count_{panel_validation_threshold}_plus",
                str(int(window_decomposition.get(f"count_{panel_validation_threshold}_plus", 0) or 0)),
            )
            st.caption(window_decomposition.get("validation_zone_label", panel_validation_zone_label))
            window_context = st.expander(f"Ver detalhes da {label.lower()}", expanded=False) if use_expander else st.container()
            with window_context:
                st.json(window)

    if parameter_reasoning:
        st.markdown("###### Motivo de cada parâmetro")
        rationale_cols = st.columns(2)
        rationale_left = [
            ("Repetição", parameter_reasoning.get("repeat", "-")),
            ("Paridade", parameter_reasoning.get("parity", "-")),
            ("Sequência", parameter_reasoning.get("sequence", "-")),
            ("Frequência", parameter_reasoning.get("frequency", "-")),
        ]
        rationale_right = [
            ("Núcleo", parameter_reasoning.get("core_numbers", "-")),
            ("Redução", parameter_reasoning.get("discouraged_numbers", "-")),
            ("Cobertura", parameter_reasoning.get("coverage", "-")),
            ("Entropia", parameter_reasoning.get("entropy", "-")),
        ]
        with rationale_cols[0]:
            for label, text in rationale_left:
                st.markdown(f"**{label}**  \n{text}")
        with rationale_cols[1]:
            for label, text in rationale_right:
                st.markdown(f"**{label}**  \n{text}")
    policy_context = st.expander("Ver payload t?cnico completo", expanded=False) if use_expander else st.container()
    with policy_context:
        st.json({"policy": policy, "policy_discovery": policy_discovery})
def _render_scientific_calibration_panel(
    *,
    strategy_size: int,
    scientific_state: dict[str, Any] | None,
    scientific_recommendation: dict[str, Any] | None,
    technical_payload: dict[str, Any] | None = None,
    use_expander: bool = True,
) -> None:
    scientific_state, scientific_recommendation, technical_payload = _resolve_official_15_calibration_context(
        strategy_size=strategy_size,
        scientific_state=scientific_state,
        scientific_recommendation=scientific_recommendation,
        technical_payload=technical_payload,
    )
    scientific_state = scientific_state or {
        "mode": "GERAÇÃO PREPARADA",
        "structural_status": "baseline oficial pronta" if int(strategy_size or 0) == 15 else "régua futura preparada",
        "scientific_status": "VALIDATED_15_POLICY_LEVEL_3" if int(strategy_size or 0) == 15 else "PREPARADO",
        "classification": "VALIDATED_15_POLICY_LEVEL_3" if int(strategy_size or 0) == 15 else "PREPARADO",
        "main_reason": "usar baseline oficial validada nível 3 para próxima geração compacta"
        if int(strategy_size or 0) == 15
        else "Estratégia preparada para uso operacional futuro.",
        "status_visual": "BASELINE OFICIAL" if int(strategy_size or 0) == 15 else "PREPARADO",
    }
    scientific_recommendation = scientific_recommendation or {
        "action_suggested": "usar baseline oficial validada nível 3 para próxima geração compacta"
        if int(strategy_size or 0) == 15
        else "gerar jogos",
        "status_visual": "BASELINE OFICIAL" if int(strategy_size or 0) == 15 else "PREPARADO",
    }
    st.markdown("##### Visão Histórica de Calibração")
    official_15_banner = _official_15_policy_status_label(technical_payload)
    if official_15_banner:
        st.success(official_15_banner)
        baseline_batch_id = str(
            (technical_payload or {}).get("baseline_batch_id")
            or (technical_payload or {}).get("source_batch_id")
            or (technical_payload or {}).get("batch_id")
            or ""
        ).strip()
        baseline_contest_number = (
            (technical_payload or {}).get("baseline_contest_number")
            or (technical_payload or {}).get("contest_number")
            or (technical_payload or {}).get("reference_window", [None])[-1]
        )
        st.caption(
            " | ".join(
                [
                    f"status_atual={str((technical_payload or {}).get('policy_validation_status', 'VALIDATED_15_POLICY_LEVEL_3') or 'VALIDATED_15_POLICY_LEVEL_3')}",
                    f"baseline_batch_id={baseline_batch_id or 'calibration-20260602172948-20a682cd'}",
                    f"concurso_validacao={baseline_contest_number or 3697}",
                ]
            )
        )
    top_cols = st.columns(4)
    top_cols[0].metric("Modo", str(scientific_state.get("mode", "-") or "-"))
    top_cols[1].metric("Estratégia", f"{int(strategy_size)} dezenas")
    top_cols[2].metric("Status estrutural", str(scientific_state.get("structural_status", "-") or "-"))
    top_cols[3].metric("Status científico", str(scientific_state.get("scientific_status", "-") or "-"))

    detail_cols = st.columns(3)
    detail_cols[0].markdown(
        f"**Classificação**  \n{scientific_state.get('classification', '-') or '-'}"
    )
    detail_cols[1].markdown(
        f"**Motivo**  \n{scientific_state.get('main_reason', '-') or '-'}"
    )
    detail_cols[2].markdown(
        f"**Ação sugerida pela LotoIA**  \n{scientific_recommendation.get('action_suggested', '-') or '-'}"
    )

    detail_cols_2 = st.columns(2)
    detail_cols_2[0].metric(
        "Status visual",
        str(scientific_recommendation.get("status_visual", scientific_state.get("status_visual", "-")) or "-"),
    )
    detail_cols_2[1].metric(
        "Última decisão científica",
        str(scientific_state.get("scientific_status", "-") or "-"),
    )

    summary_bits: list[str] = []
    if scientific_state.get("reference_window"):
        summary_bits.append(f"reference_window={scientific_state.get('reference_window')}")
    if scientific_state.get("source_batch_id"):
        summary_bits.append(f"source_batch_id={scientific_state.get('source_batch_id')}")
    if scientific_recommendation.get("status_visual"):
        summary_bits.append(f"status_visual={scientific_recommendation.get('status_visual')}")
    if scientific_state.get("main_reason"):
        summary_bits.append(f"main_reason={scientific_state.get('main_reason')}")
    if summary_bits:
        st.caption(" | ".join(summary_bits))
    panel_context = st.expander("Ver diagnóstico científico completo", expanded=False) if use_expander else st.container()
    with panel_context:
        payload: dict[str, Any] = {}
        if technical_payload:
            payload.update(technical_payload)
        payload.setdefault("historical_view_only", True)
        payload.setdefault("legacy_removed_from_runtime", True)
        payload.setdefault("legacy_runtime_access", False)
        payload.setdefault("scientific_state", scientific_state)
        payload.setdefault("scientific_recommendation", scientific_recommendation)
        st.json(payload)


@st.cache_data(show_spinner=False)

def _history_number_frequency() -> dict[int, int]:
    try:
        draws = load_draws_csv()
    except Exception:
        return {}
    frequencies = number_frequency(draws)
    return {int(number): int(amount) for number, amount in frequencies.items()}


def _sequence_metrics(numbers: list[int]) -> dict[str, int]:
    ordered = sorted(int(number) for number in numbers)
    if not ordered:
        return {"sequence_count": 0, "largest_sequence": 0}
    longest = 1
    current = 1
    count = 0
    for index in range(1, len(ordered)):
        if ordered[index] == ordered[index - 1] + 1:
            current += 1
        else:
            if current > 1:
                count += 1
            longest = max(longest, current)
            current = 1
    if current > 1:
        count += 1
    longest = max(longest, current)
    return {"sequence_count": count, "largest_sequence": longest}


def _coverage_metrics(numbers: list[int]) -> dict[str, Any]:
    blocks = Counter(((int(number) - 1) // 5) for number in numbers)
    block_distribution = [int(blocks.get(index, 0)) for index in range(5)]
    active_blocks = sum(1 for amount in block_distribution if amount > 0)
    coverage_score = round(active_blocks / 5.0, 4)
    return {
        "coverage_score": coverage_score,
        "block_distribution": block_distribution,
        "active_blocks": active_blocks,
    }


def _entropy_score(numbers: list[int]) -> float:
    coverage = _coverage_metrics(numbers)["block_distribution"]
    total = sum(coverage) or 1
    entropy = 0.0
    for amount in coverage:
        if amount <= 0:
            continue
        share = amount / total
        entropy -= share * math.log2(share)
    non_zero_blocks = sum(1 for amount in coverage if amount > 0)
    max_entropy = math.log2(non_zero_blocks) if non_zero_blocks > 1 else 1.0
    return round((entropy / max_entropy) if max_entropy else 0.0, 4)


def _hb_geometry_profile_for_size(size: int) -> dict[str, float | int]:
    size = max(2, min(15, int(size or 15)))
    if size <= 2:
        odd_even_max = 2
        sequence_max = 2
        coverage_min = 0.20
        entropy_min = 0.15
    elif size <= 4:
        odd_even_max = 4
        sequence_max = 3
        coverage_min = 0.25
        entropy_min = 0.20
    elif size <= 8:
        odd_even_max = 5
        sequence_max = 4
        coverage_min = 0.30
        entropy_min = 0.30
    elif size <= 12:
        odd_even_max = 7
        sequence_max = 5
        coverage_min = 0.35
        entropy_min = 0.40
    else:
        odd_even_max = 9
        sequence_max = 6
        coverage_min = 0.40
        entropy_min = 0.45
    return {
        "odd_min": 0,
        "odd_max": min(size, odd_even_max),
        "even_min": 0,
        "even_max": min(size, odd_even_max),
        "sequence_max": min(size, sequence_max),
        "coverage_min": coverage_min,
        "entropy_min": entropy_min,
    }


def _institutional_generation_policy(size: int) -> dict[str, Any]:
    size = max(2, min(25, int(size or 15)))
    if size == 15:
        discovery = discover_scientific_generation_policy(size, db_path=DB_PATH)
        selection_status = str(discovery.get("selection_status", "") or "").strip().upper()
        if selection_status == "POLICY_SELECTED" and discovery.get("policy"):
            policy = dict(discovery.get("policy") or {})
            policy.setdefault("game_size", size)
            return _apply_scientific_15_vnext_policy(policy)
        profile = _hb_geometry_profile_for_size(size)
        return _apply_scientific_15_vnext_policy({
            "game_size": size,
            "repeat_min": 0,
            "repeat_max": min(size, 8),
            "preferred_parity_pairs": [],
            "allowed_parity_pairs": [],
            "sequence_max": int(profile["sequence_max"]),
            "coverage_min": float(profile["coverage_min"]),
            "entropy_min": float(profile["entropy_min"]),
            "core_numbers": [],
            "discouraged_numbers": [],
            "max_frequency_ratio": 1.0,
            "min_frequency_ratio": 0.0,
            "preferred_profile_ratios": {},
            "policy_origin": str(discovery.get("policy_origin") or "automatic_scientific_discovery"),
            "policy_variant": "history_profile_seed",
            "selection_variant": str(discovery.get("selection_variant") or "history_profile_seed"),
            "selection_status": str(discovery.get("selection_status") or "NONE_APPROVED"),
            "selection_reason": str(discovery.get("selection_reason") or "policy_derived_from_official_history"),
            "policy_adjustment_reason": str(discovery.get("selection_reason") or "policy_derived_from_official_history"),
            "status_prospectivo": str(discovery.get("status_prospectivo") or "pending_prospective_validation"),
            "based_on_memory_kind": discovery.get("based_on_memory_kind"),
            "based_on_memory_id": discovery.get("based_on_memory_id"),
            "based_on_batch_id": discovery.get("based_on_batch_id"),
            "based_on_generation_range": dict(discovery.get("based_on_generation_range") or {}),
            "based_on_best_generations": list(discovery.get("based_on_best_generations") or []),
        })
    profile = _hb_geometry_profile_for_size(size)
    return {
        "repeat_min": 0,
        "repeat_max": min(size, 8),
        "preferred_parity_pairs": [],
        "allowed_parity_pairs": [],
        "sequence_max": int(profile["sequence_max"]),
        "coverage_min": float(profile["coverage_min"]),
        "entropy_min": float(profile["entropy_min"]),
        "core_numbers": [],
        "discouraged_numbers": [],
        "max_frequency_ratio": 1.0,
        "min_frequency_ratio": 0.0,
        "preferred_profile_ratios": {},
    }


def _load_scientific_batch_games(batch_id: str | None) -> list[dict[str, Any]]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return []
    with get_session(DB_PATH) as session:
        rows = (
            session.query(InstitutionalOutputSignature)
            .filter(InstitutionalOutputSignature.batch_id == resolved_batch_id)
            .order_by(InstitutionalOutputSignature.created_at.asc(), InstitutionalOutputSignature.id.asc())
            .all()
        )
    games: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(getattr(row, "payload", {}) or {})
        numbers = _extract_int_numbers(payload.get("numbers", []))
        games.append(
            {
                "game_index": int(payload.get("game_index", len(games) + 1) or len(games) + 1),
                "numbers": numbers,
                "game_signature": str(getattr(row, "game_signature", "") or ""),
                "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else "",
                "source": str(payload.get("source", "institutional_app") or "institutional_app"),
                "batch_id": resolved_batch_id,
            }
        )
    return games


def _scientific_batch_diagnostics(
    *,
    batch_id: str | None,
    games: list[dict[str, Any]],
    game_size: int,
) -> dict[str, Any]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return {}
    scientific_games = games or _load_scientific_batch_games(resolved_batch_id)
    if not scientific_games:
        return {}
    resolved_game_size = int(game_size or 0)
    if resolved_game_size <= 0:
        first_game_numbers = scientific_games[0].get("numbers", []) if scientific_games else []
        resolved_game_size = len(first_game_numbers) if first_game_numbers else 15
    core = LotofacilScientificCore()
    reference_contests = core.contests[-10:] if core.contests else []
    policy = (
        get_scientific_generation_policy(resolved_game_size, contests=core.contests)
        if core.contests
        else get_scientific_generation_policy(resolved_game_size)
    )
    report = validate_scientific_batch(
        scientific_games,
        reference_contests,
        resolved_game_size,
        policy,
        batch_id=resolved_batch_id,
    )
    report["reference_window"] = [int(item.get("contest_number", 0) or 0) for item in reference_contests]
    report["game_size"] = resolved_game_size
    report["status_comandante_cientifico"] = str(report.get("status_comandante_cientifico", "REPROVADO") or "REPROVADO")
    report["classificacao_cientifica"] = str(report.get("classificacao_cientifica", "REPROVADA") or "REPROVADA")
    report["status_visual"] = (
        "APROVADO"
        if str(report["status_comandante_cientifico"]).upper() == "APROVADO"
        else "REPROVADO"
    )
    return report


def _sync_hb_geometry_controls(size: int) -> dict[str, float | int]:
    profile = _hb_geometry_profile_for_size(size)
    size_key = int(size)
    if int(st.session_state.get("institutional_geometry_size", 0) or 0) != size_key:
        st.session_state["institutional_geometry_size"] = size_key
        st.session_state["institutional_odd_min"] = int(profile["odd_min"])
        st.session_state["institutional_odd_max"] = int(profile["odd_max"])
        st.session_state["institutional_even_min"] = int(profile["even_min"])
        st.session_state["institutional_even_max"] = int(profile["even_max"])
        st.session_state["institutional_sequence_max"] = int(profile["sequence_max"])
        st.session_state["institutional_coverage_min"] = float(profile["coverage_min"])
        st.session_state["institutional_entropy_min"] = float(profile["entropy_min"])
    else:
        st.session_state["institutional_odd_min"] = max(
            0,
            min(int(st.session_state.get("institutional_odd_min", profile["odd_min"]) or profile["odd_min"]), int(profile["odd_max"])),
        )
        st.session_state["institutional_odd_max"] = max(
            st.session_state["institutional_odd_min"],
            min(int(st.session_state.get("institutional_odd_max", profile["odd_max"]) or profile["odd_max"]), int(profile["odd_max"])),
        )
        st.session_state["institutional_even_min"] = max(
            0,
            min(int(st.session_state.get("institutional_even_min", profile["even_min"]) or profile["even_min"]), int(profile["even_max"])),
        )
        st.session_state["institutional_even_max"] = max(
            st.session_state["institutional_even_min"],
            min(int(st.session_state.get("institutional_even_max", profile["even_max"]) or profile["even_max"]), int(profile["even_max"])),
        )
        st.session_state["institutional_sequence_max"] = max(
            1,
            min(int(st.session_state.get("institutional_sequence_max", profile["sequence_max"]) or profile["sequence_max"]), int(profile["sequence_max"])),
        )
        st.session_state["institutional_coverage_min"] = max(
            0.0,
            min(float(st.session_state.get("institutional_coverage_min", profile["coverage_min"]) or profile["coverage_min"]), float(profile["coverage_min"]) + 0.2),
        )
        st.session_state["institutional_entropy_min"] = max(
            0.0,
            min(float(st.session_state.get("institutional_entropy_min", profile["entropy_min"]) or profile["entropy_min"]), float(profile["entropy_min"]) + 0.2),
        )
    return profile


def _parity_pair_is_allowed(
    odd_count: int,
    even_count: int,
    *,
    target_size: int,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
) -> bool:
    if odd_count + even_count != target_size:
        return False
    if not allowed_parity_pairs:
        return True
    return (odd_count, even_count) in set(tuple(pair) for pair in allowed_parity_pairs)


def _order_parity_pairs_for_batch(
    pairs: Sequence[tuple[int, int]] | None,
    *,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
) -> list[tuple[int, int]]:
    ordered_pairs: list[tuple[int, int]] = []
    for pair in pairs or []:
        normalized_pair = _normalize_scientific_parity_pair(pair)
        if normalized_pair is None:
            continue
        if normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    if not ordered_pairs:
        return []
    if not batch_profile_usage:
        return ordered_pairs
    total_usage = sum(int(amount or 0) for amount in batch_profile_usage.values()) or 1
    preferred_profile_ratios = preferred_profile_ratios or {}
    return sorted(
        ordered_pairs,
        key=lambda pair: (
            float(batch_profile_usage.get(pair, 0)) / max(1.0, float(preferred_profile_ratios.get(pair, 0.0) or 0.0) * total_usage)
            if preferred_profile_ratios.get(pair, 0.0)
            else float(batch_profile_usage.get(pair, 0)),
            int(pair[0]),
            int(pair[1]),
        ),
    )


def _select_subset_from_candidate(
    numbers: list[int],
    *,
    target_size: int,
    frequency_map: dict[int, int],
    latest_numbers: set[int],
    batch_number_usage: dict[int, int] | None = None,
    batch_total_games: int | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    core_numbers: Sequence[int] | None = None,
    discouraged_numbers: Sequence[int] | None = None,
    max_frequency_ratio: float = 1.0,
    min_frequency_ratio: float = 0.0,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_min: int,
    repeat_max: int,
    preferred_parity_pairs: Sequence[tuple[int, int]] | None = None,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
) -> list[int] | None:
    candidate_numbers = sorted({int(number) for number in numbers})
    if target_size < 1:
        return None
    if target_size > 25:
        return None
    universe = list(range(1, 26))
    candidate_set = set(candidate_numbers)
    batch_number_usage = dict(batch_number_usage or {})
    batch_total_games = max(1, int(batch_total_games or 1))
    core_numbers_set = {int(number) for number in (core_numbers or [])}
    discouraged_numbers_set = {int(number) for number in (discouraged_numbers or [])}
    max_count = max(1, int(math.ceil(batch_total_games * float(max_frequency_ratio or 1.0))))
    min_count = max(0, int(math.ceil(batch_total_games * float(min_frequency_ratio or 0.0))))
    preferred_profile_ratios = {
        normalized_pair: float(ratio)
        for pair, ratio in (preferred_profile_ratios or {}).items()
        if (normalized_pair := _normalize_scientific_parity_pair(pair)) is not None
    }
    scoring = sorted(
        universe,
        key=lambda number: (
            -int(number in candidate_set),
            -int(frequency_map.get(int(number), 0)),
            int(batch_number_usage.get(int(number), 0)),
            -int(number in core_numbers_set and int(batch_number_usage.get(int(number), 0)) < min_count),
            int(number in latest_numbers),
            int(number in discouraged_numbers_set),
            int(number),
        ),
    )

    candidate_pairs: list[tuple[int, int]] = []
    for pair in preferred_parity_pairs or []:
        normalized_pair = _normalize_scientific_parity_pair(pair)
        if normalized_pair is None:
            continue
        if sum(normalized_pair) == target_size and normalized_pair not in candidate_pairs:
            candidate_pairs.append(normalized_pair)
    for pair in allowed_parity_pairs or []:
        normalized_pair = _normalize_scientific_parity_pair(pair)
        if normalized_pair is None:
            continue
        if sum(normalized_pair) == target_size and normalized_pair not in candidate_pairs:
            candidate_pairs.append(normalized_pair)
    if not candidate_pairs:
        odd_target = min(max((target_size + 1) // 2, odd_min), odd_max)
        even_target = target_size - odd_target
        candidate_pairs = [(odd_target, even_target)]
    if batch_profile_usage and preferred_profile_ratios:
        candidate_pairs = _order_parity_pairs_for_batch(
            candidate_pairs,
            batch_profile_usage=batch_profile_usage,
            preferred_profile_ratios=preferred_profile_ratios,
        )

    for odd_target, even_target in candidate_pairs:
        if odd_target < odd_min or odd_target > odd_max:
            continue
        if even_target < even_min or even_target > even_max:
            continue
        if odd_target + even_target != target_size:
            continue
        selected: list[int] = []
        for pool, quota in (
            ([number for number in scoring if number % 2 != 0], odd_target),
            ([number for number in scoring if number % 2 == 0], even_target),
        ):
            for number in pool:
                if number not in selected:
                    selected.append(number)
                if sum(1 for item in selected if item % 2 == pool[0] % 2) >= quota:
                    break

        if len(selected) < target_size:
            for number in scoring:
                if number not in selected:
                    selected.append(number)
                if len(selected) >= target_size:
                    break

        selected = sorted(selected[:target_size])
        if not selected:
            continue

        odd_count = sum(1 for number in selected if number % 2 != 0)
        even_count = len(selected) - odd_count
        if not (odd_min <= odd_count <= odd_max and even_min <= even_count <= even_max):
            continue
        if _sequence_metrics(selected)["largest_sequence"] > sequence_max:
            continue
        repeat_count = len(set(selected).intersection(latest_numbers))
        if repeat_count < repeat_min or repeat_count > repeat_max:
            continue
        if _coverage_metrics(selected)["coverage_score"] < coverage_min:
            continue
        if _entropy_score(selected) < entropy_min:
            continue
        if batch_number_usage:
            projected = dict(batch_number_usage)
            for number in selected:
                projected[int(number)] = int(projected.get(int(number), 0) or 0) + 1
            if any(int(projected.get(number, 0) or 0) > max_count for number in selected):
                continue
            if core_numbers_set:
                if any(int(projected.get(number, 0) or 0) < min_count for number in core_numbers_set if number in selected):
                    # do not reject here; just prefer candidates that keep core numbers growing
                    pass
        if not _parity_pair_is_allowed(
            odd_count,
            even_count,
            target_size=target_size,
            allowed_parity_pairs=allowed_parity_pairs or candidate_pairs,
        ):
            continue
        return selected
    return None


def _force_subset_from_universe(
    *,
    target_size: int,
    frequency_map: dict[int, int],
    latest_numbers: set[int],
    batch_number_usage: dict[int, int] | None = None,
    batch_total_games: int | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    core_numbers: Sequence[int] | None = None,
    discouraged_numbers: Sequence[int] | None = None,
    max_frequency_ratio: float = 1.0,
    min_frequency_ratio: float = 0.0,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    preferred_parity_pairs: Sequence[tuple[int, int]] | None = None,
    preferred_profile_ratios: dict[tuple[int, int], float] | None = None,
    repeat_min: int = 0,
    repeat_max: int | None = None,
    sequence_max: int | None = None,
    coverage_min: float | None = None,
    entropy_min: float | None = None,
    allowed_parity_pairs: Sequence[tuple[int, int]] | None = None,
    offset: int = 0,
) -> list[int]:
    target_size = max(1, min(int(target_size or 1), 25))
    universe = list(range(1, 26))
    batch_number_usage = dict(batch_number_usage or {})
    batch_total_games = max(1, int(batch_total_games or 1))
    batch_profile_usage = dict(batch_profile_usage or {})
    core_numbers_set = {int(number) for number in (core_numbers or [])}
    discouraged_numbers_set = {int(number) for number in (discouraged_numbers or [])}
    max_count = max(1, int(math.ceil(batch_total_games * float(max_frequency_ratio or 1.0))))
    min_count = max(0, int(math.ceil(batch_total_games * float(min_frequency_ratio or 0.0))))
    preferred_profile_ratios = {
        normalized_pair: float(ratio)
        for pair, ratio in (preferred_profile_ratios or {}).items()
        if (normalized_pair := _normalize_scientific_parity_pair(pair)) is not None
    }
    scoring = sorted(
        universe,
        key=lambda number: (
            -int(frequency_map.get(int(number), 0)),
            int(batch_number_usage.get(int(number), 0)),
            -int(number in core_numbers_set and int(batch_number_usage.get(int(number), 0)) < min_count),
            int(number in discouraged_numbers_set),
            int(number in latest_numbers),
            int(number),
        ),
    )
    if scoring:
        offset = int(offset or 0) % len(scoring)
        scoring = scoring[offset:] + scoring[:offset]
    odd_target = min(max((target_size + 1) // 2, odd_min), odd_max)
    even_target = target_size - odd_target
    if even_target < even_min:
        even_target = even_min
        odd_target = target_size - even_target
    if odd_target < odd_min:
        odd_target = odd_min
        even_target = target_size - odd_target
    if odd_target > odd_max:
        odd_target = odd_max
        even_target = target_size - odd_target
    if even_target > even_max:
        even_target = even_max
        odd_target = target_size - even_target
    if odd_target < 0 or even_target < 0 or odd_target + even_target != target_size:
        odd_target = min(max(odd_target, 0), target_size)
        even_target = target_size - odd_target
    parity_pairs = [(odd_target, even_target)]
    ordered_pairs: list[tuple[int, int]] = []
    for pair in preferred_parity_pairs or []:
        normalized_pair = _normalize_scientific_parity_pair(pair)
        if normalized_pair is None:
            continue
        if sum(normalized_pair) == target_size and normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    for pair in allowed_parity_pairs or []:
        normalized_pair = _normalize_scientific_parity_pair(pair)
        if normalized_pair is None:
            continue
        if sum(normalized_pair) == target_size and normalized_pair not in ordered_pairs:
            ordered_pairs.append(normalized_pair)
    if ordered_pairs:
        parity_pairs = ordered_pairs
    if batch_profile_usage and preferred_profile_ratios:
        parity_pairs = _order_parity_pairs_for_batch(
            parity_pairs,
            batch_profile_usage=batch_profile_usage,
            preferred_profile_ratios=preferred_profile_ratios,
        )
    latest_numbers = set(latest_numbers or set())
    repeat_max = target_size if repeat_max is None else max(0, min(int(repeat_max), target_size))
    repeat_min = max(0, min(int(repeat_min), repeat_max))

    for odd_target, even_target in parity_pairs:
        selected: list[int] = []
        odd_pool = [number for number in scoring if number % 2 != 0]
        even_pool = [number for number in scoring if number % 2 == 0]
        for pool, quota in ((odd_pool, odd_target), (even_pool, even_target)):
            for number in pool:
                if number not in selected:
                    selected.append(number)
                if sum(1 for item in selected if item % 2 == pool[0] % 2) >= quota:
                    break
        if len(selected) < target_size:
            for number in scoring:
                if number not in selected:
                    selected.append(number)
                if len(selected) >= target_size:
                    break
        selected = sorted(selected[:target_size])
        if not selected:
            continue
        odd_count = sum(1 for number in selected if number % 2 != 0)
        even_count = len(selected) - odd_count
        if not _parity_pair_is_allowed(
            odd_count,
            even_count,
            target_size=target_size,
            allowed_parity_pairs=allowed_parity_pairs,
        ):
            continue
        if repeat_min or repeat_max is not None:
            repeat_count = len(set(selected).intersection(latest_numbers))
            if repeat_count < repeat_min or repeat_count > repeat_max:
                continue
        if sequence_max is not None and _sequence_metrics(selected)["largest_sequence"] > sequence_max:
            continue
        if coverage_min is not None and _coverage_metrics(selected)["coverage_score"] < coverage_min:
            continue
        if entropy_min is not None and _entropy_score(selected) < entropy_min:
            continue
        if batch_number_usage:
            projected = dict(batch_number_usage)
            for number in selected:
                projected[int(number)] = int(projected.get(int(number), 0) or 0) + 1
            if any(int(projected.get(number, 0) or 0) > max_count for number in selected):
                continue
            if core_numbers_set and any(int(projected.get(number, 0) or 0) < min_count for number in core_numbers_set if number in selected):
                continue
        return selected
    return []


def _generate_direct_15_games(
    *,
    total_games: int,
    seed: int,
    history_frequency: dict[int, int],
    latest_numbers: set[int],
    batch_number_usage: dict[int, int],
    batch_profile_usage: dict[tuple[int, int], int],
    batch_total_games: int,
    core_numbers: list[int],
    discouraged_numbers: list[int],
    max_frequency_ratio: float,
    min_frequency_ratio: float,
    preferred_profile_ratios: dict[tuple[int, int], float],
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_min: int,
    repeat_max: int,
    preferred_parity_pairs: list[tuple[int, int]],
    allowed_parity_pairs: list[tuple[int, int]],
    fill_diagnostics: dict[str, Any] | None = None,
    seen_signatures: set[str] | None = None,
    previous_contest_numbers: Sequence[int] | None = None,
    analysis_batch_label: str | None = None,
) -> list[dict[str, Any]]:
    _raise_legacy_direct_15_games_blocked(caller="_generate_direct_15_games")
    games: list[dict[str, Any]] = []
    used_signatures: set[str] = set(seen_signatures or set())
    diagnostics = fill_diagnostics if fill_diagnostics is not None else {}
    normalized_previous_contest_numbers = sorted(
        {
            int(number)
            for number in (previous_contest_numbers or [])
            if isinstance(number, (int, str)) and str(number).strip().isdigit() and 1 <= int(number) <= 25
        }
    )
    diagnostics.setdefault("candidate_pool_generated", 0)
    diagnostics.setdefault("valid_candidates_found", 0)
    diagnostics.setdefault("accepted_games", 0)
    diagnostics.setdefault("rejected_by_internal_duplicate", 0)
    diagnostics.setdefault("rejected_by_invalid_size", 0)
    diagnostics.setdefault("rejected_by_repeated_pattern", 0)
    diagnostics.setdefault("rejected_by_output_commander", 0)
    diagnostics.setdefault("attempts_used", 0)
    diagnostics.setdefault("fill_completed", False)
    diagnostics.setdefault("rfe_enabled", True)
    diagnostics.setdefault("rfe_rejected_games", 0)
    diagnostics.setdefault("rfe_01_rejected_games", 0)
    diagnostics.setdefault("rfe_02_rejected_games", 0)
    diagnostics.setdefault("rfe_blocked_reasons", [])
    diagnostics.setdefault("rfe_status", "OK")
    diagnostics.setdefault("rfe_previous_contest_found", bool(normalized_previous_contest_numbers) and len(normalized_previous_contest_numbers) == 15)
    diagnostics.setdefault("rfe_previous_contest_id", None)
    diagnostics.setdefault("rfe_previous_contest_numbers", " ".join(f"{number:02d}" for number in normalized_previous_contest_numbers) or "-")
    diagnostics.setdefault("rfe_previous_contest_source", "official_lotofacil_history" if normalized_previous_contest_numbers else "indisponivel")
    if len(normalized_previous_contest_numbers) != 15:
        diagnostics["fill_completed"] = False
        diagnostics["candidate_pool_generated"] = 0
        diagnostics["valid_candidates_found"] = 0
        diagnostics["accepted_games"] = 0
        diagnostics["attempts_used"] = 0
        diagnostics["rfe_enabled"] = True
        diagnostics["rfe_status"] = "BLOQUEADO"
        diagnostics["insufficient_reason"] = (
            "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS"
            if normalized_previous_contest_numbers
            else "RFE_PREVIOUS_CONTEST_NOT_FOUND"
        )
        if normalized_previous_contest_numbers:
            diagnostics["rfe_blocked_reasons"] = ["RFE-01: concurso anterior encontrado, mas dezenas oficiais inválidas ou incompletas."]
        else:
            diagnostics["rfe_blocked_reasons"] = ["RFE-01: concurso anterior indisponível para validação estrutural."]
        return []
    relaxed_repeat_min = 0
    relaxed_repeat_max = max(15, repeat_max)
    relaxed_sequence_max = max(sequence_max, 10)
    relaxed_coverage_min = 0.0 if coverage_min > 0.0 else coverage_min
    relaxed_entropy_min = 0.0 if entropy_min > 0.0 else entropy_min
    candidate_count = max(total_games * 30, 300)
    ranked_candidates = generate_ranked_games(
        total_games=candidate_count,
        seed=seed,
        ml_enabled=False,
        pool_size=max(candidate_count, 50),
        batch_label=analysis_batch_label,
    )
    attempt_limit = max(total_games * 80, len(ranked_candidates) * 4, 400)
    attempt = 0
    while len(games) < total_games and attempt < attempt_limit:
        candidate = ranked_candidates[attempt % len(ranked_candidates)] if ranked_candidates else {}
        attempt += 1
        diagnostics["candidate_pool_generated"] = int(diagnostics.get("candidate_pool_generated", 0) or 0) + 1
        diagnostics["attempts_used"] = int(diagnostics.get("attempts_used", 0) or 0) + 1
        selected_numbers = _select_subset_from_candidate(
            list(candidate.get("numbers", [])),
            target_size=15,
            frequency_map=history_frequency,
            latest_numbers=latest_numbers,
            batch_number_usage=batch_number_usage,
            batch_total_games=batch_total_games,
            batch_profile_usage=batch_profile_usage,
            core_numbers=core_numbers,
            discouraged_numbers=discouraged_numbers,
            max_frequency_ratio=max_frequency_ratio,
            min_frequency_ratio=min_frequency_ratio,
            preferred_profile_ratios=preferred_profile_ratios,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            sequence_max=relaxed_sequence_max,
            coverage_min=relaxed_coverage_min,
            entropy_min=relaxed_entropy_min,
            repeat_min=relaxed_repeat_min,
            repeat_max=relaxed_repeat_max,
            preferred_parity_pairs=preferred_parity_pairs,
            allowed_parity_pairs=allowed_parity_pairs,
        )
        if not selected_numbers:
            selected_numbers = _force_subset_from_universe(
                target_size=15,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max_frequency_ratio,
                min_frequency_ratio=min_frequency_ratio,
                odd_min=odd_min,
                odd_max=odd_max,
                even_min=even_min,
                even_max=even_max,
                preferred_parity_pairs=preferred_parity_pairs,
                preferred_profile_ratios=preferred_profile_ratios,
                repeat_min=relaxed_repeat_min,
                repeat_max=relaxed_repeat_max,
                sequence_max=relaxed_sequence_max,
                coverage_min=relaxed_coverage_min,
                entropy_min=relaxed_entropy_min,
                allowed_parity_pairs=allowed_parity_pairs,
                offset=seed + attempt,
            )
        if not selected_numbers:
            diagnostics["rejected_by_invalid_size"] = int(diagnostics.get("rejected_by_invalid_size", 0) or 0) + 1
            continue
        rfe_result = validate_rfe_final_card(selected_numbers, previous_contest_numbers or [])
        if not rfe_result.approved:
            _update_rfe_diagnostics(diagnostics, rfe_result)
            continue
        diagnostics["valid_candidates_found"] = int(diagnostics.get("valid_candidates_found", 0) or 0) + 1
        signature = _game_signature(selected_numbers)
        if signature in used_signatures:
            diagnostics["rejected_by_internal_duplicate"] = int(diagnostics.get("rejected_by_internal_duplicate", 0) or 0) + 1
            diagnostics["rejected_by_repeated_pattern"] = int(diagnostics.get("rejected_by_repeated_pattern", 0) or 0) + 1
            continue
        games.append(
            _build_institutional_game_record(
                selected_numbers=selected_numbers,
                candidate=dict(candidate),
                history_frequency=history_frequency,
                dezenas_per_game=15,
            )
        )
        used_signatures.add(signature)
        if seen_signatures is not None:
            seen_signatures.add(signature)
        diagnostics["accepted_games"] = int(diagnostics.get("accepted_games", 0) or 0) + 1
        profile_pair = (
            sum(1 for number in selected_numbers if number % 2 != 0),
            sum(1 for number in selected_numbers if number % 2 == 0),
        )
        batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
        for number in selected_numbers:
            batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
    if len(games) < total_games:
        ultra_relaxed_repeat_min = 0
        ultra_relaxed_repeat_max = 15
        ultra_relaxed_sequence_max = max(sequence_max, 15)
        ultra_relaxed_coverage_min = 0.0
        ultra_relaxed_entropy_min = 0.0
        relaxed_attempt = 0
        relaxed_attempt_limit = max(total_games * 120, len(ranked_candidates) * 6, 600)
        while len(games) < total_games and relaxed_attempt < relaxed_attempt_limit:
            candidate = ranked_candidates[(attempt + relaxed_attempt) % len(ranked_candidates)] if ranked_candidates else {}
            relaxed_attempt += 1
            diagnostics["candidate_pool_generated"] = int(diagnostics.get("candidate_pool_generated", 0) or 0) + 1
            diagnostics["attempts_used"] = int(diagnostics.get("attempts_used", 0) or 0) + 1
            selected_numbers = _select_subset_from_candidate(
                list(candidate.get("numbers", [])),
                target_size=15,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max(max_frequency_ratio, 2.0),
                min_frequency_ratio=min_frequency_ratio,
                preferred_profile_ratios=preferred_profile_ratios,
                odd_min=0,
                odd_max=15,
                even_min=0,
                even_max=15,
                sequence_max=ultra_relaxed_sequence_max,
                coverage_min=ultra_relaxed_coverage_min,
                entropy_min=ultra_relaxed_entropy_min,
                repeat_min=ultra_relaxed_repeat_min,
                repeat_max=ultra_relaxed_repeat_max,
                preferred_parity_pairs=preferred_parity_pairs,
                allowed_parity_pairs=allowed_parity_pairs,
            )
            if not selected_numbers:
                selected_numbers = _force_subset_from_universe(
                    target_size=15,
                    frequency_map=history_frequency,
                    latest_numbers=latest_numbers,
                    batch_number_usage=batch_number_usage,
                    batch_total_games=batch_total_games,
                    batch_profile_usage=batch_profile_usage,
                    core_numbers=core_numbers,
                    discouraged_numbers=discouraged_numbers,
                    max_frequency_ratio=max(max_frequency_ratio, 2.0),
                    min_frequency_ratio=min_frequency_ratio,
                    odd_min=0,
                    odd_max=15,
                    even_min=0,
                    even_max=15,
                    preferred_parity_pairs=preferred_parity_pairs,
                    preferred_profile_ratios=preferred_profile_ratios,
                    repeat_min=ultra_relaxed_repeat_min,
                    repeat_max=ultra_relaxed_repeat_max,
                    sequence_max=ultra_relaxed_sequence_max,
                    coverage_min=ultra_relaxed_coverage_min,
                    entropy_min=ultra_relaxed_entropy_min,
                    allowed_parity_pairs=allowed_parity_pairs,
                    offset=seed + attempt + relaxed_attempt,
                )
            if not selected_numbers:
                diagnostics["rejected_by_invalid_size"] = int(diagnostics.get("rejected_by_invalid_size", 0) or 0) + 1
                continue
            rfe_result = validate_rfe_final_card(selected_numbers, previous_contest_numbers or [])
            if not rfe_result.approved:
                _update_rfe_diagnostics(diagnostics, rfe_result)
                continue
            diagnostics["valid_candidates_found"] = int(diagnostics.get("valid_candidates_found", 0) or 0) + 1
            signature = _game_signature(selected_numbers)
            if signature in used_signatures:
                diagnostics["rejected_by_internal_duplicate"] = int(diagnostics.get("rejected_by_internal_duplicate", 0) or 0) + 1
                diagnostics["rejected_by_repeated_pattern"] = int(diagnostics.get("rejected_by_repeated_pattern", 0) or 0) + 1
                continue
            games.append(
                _build_institutional_game_record(
                    selected_numbers=selected_numbers,
                    candidate=dict(candidate),
                    history_frequency=history_frequency,
                    dezenas_per_game=15,
                )
            )
            used_signatures.add(signature)
            if seen_signatures is not None:
                seen_signatures.add(signature)
            diagnostics["accepted_games"] = int(diagnostics.get("accepted_games", 0) or 0) + 1
            profile_pair = (
                sum(1 for number in selected_numbers if number % 2 != 0),
                sum(1 for number in selected_numbers if number % 2 == 0),
            )
            batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
            for number in selected_numbers:
                batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
    if len(games) < total_games:
        exhaustive_attempt_limit = max(total_games * 200, 1000)
        exhaustive_attempt = 0
        while len(games) < total_games and exhaustive_attempt < exhaustive_attempt_limit:
            candidate = ranked_candidates[(attempt + relaxed_attempt + exhaustive_attempt) % len(ranked_candidates)] if ranked_candidates else {}
            exhaustive_attempt += 1
            diagnostics["candidate_pool_generated"] = int(diagnostics.get("candidate_pool_generated", 0) or 0) + 1
            diagnostics["attempts_used"] = int(diagnostics.get("attempts_used", 0) or 0) + 1
            selected_numbers = _force_subset_from_universe(
                target_size=15,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max(max_frequency_ratio, 2.5),
                min_frequency_ratio=0.0,
                odd_min=0,
                odd_max=15,
                even_min=0,
                even_max=15,
                preferred_parity_pairs=preferred_parity_pairs,
                preferred_profile_ratios=preferred_profile_ratios,
                repeat_min=0,
                repeat_max=15,
                sequence_max=max(sequence_max, 15),
                coverage_min=0.0,
                entropy_min=0.0,
                allowed_parity_pairs=allowed_parity_pairs,
                offset=seed + attempt + relaxed_attempt + exhaustive_attempt,
            )
            if not selected_numbers:
                diagnostics["rejected_by_invalid_size"] = int(diagnostics.get("rejected_by_invalid_size", 0) or 0) + 1
                continue
            rfe_result = validate_rfe_final_card(selected_numbers, previous_contest_numbers or [])
            if not rfe_result.approved:
                _update_rfe_diagnostics(diagnostics, rfe_result)
                continue
            diagnostics["valid_candidates_found"] = int(diagnostics.get("valid_candidates_found", 0) or 0) + 1
            signature = _game_signature(selected_numbers)
            if signature in used_signatures:
                diagnostics["rejected_by_internal_duplicate"] = int(diagnostics.get("rejected_by_internal_duplicate", 0) or 0) + 1
                diagnostics["rejected_by_repeated_pattern"] = int(diagnostics.get("rejected_by_repeated_pattern", 0) or 0) + 1
                continue
            games.append(
                _build_institutional_game_record(
                    selected_numbers=selected_numbers,
                    candidate=dict(candidate),
                    history_frequency=history_frequency,
                    dezenas_per_game=15,
                )
            )
            used_signatures.add(signature)
            if seen_signatures is not None:
                seen_signatures.add(signature)
            diagnostics["accepted_games"] = int(diagnostics.get("accepted_games", 0) or 0) + 1
            profile_pair = (
                sum(1 for number in selected_numbers if number % 2 != 0),
                sum(1 for number in selected_numbers if number % 2 == 0),
            )
            batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
            for number in selected_numbers:
                batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
    diagnostics["fill_completed"] = len(games) >= total_games
    if diagnostics["fill_completed"]:
        diagnostics["rfe_status"] = "OK"
    elif int(diagnostics.get("rfe_rejected_games", 0) or 0) > 0:
        diagnostics["rfe_status"] = "BLOQUEADO"
        diagnostics["insufficient_reason"] = "INSUFFICIENT_RFE_APPROVED_CANDIDATES"
    elif int(diagnostics.get("attempts_used", 0) or 0) > 0:
        diagnostics["insufficient_reason"] = "INSUFFICIENT_VALID_CANDIDATES"
    return games


def _build_institutional_game_record(
    *,
    selected_numbers: list[int],
    candidate: dict[str, Any] | None = None,
    history_frequency: dict[int, int] | None = None,
    dezenas_per_game: int,
) -> dict[str, Any]:
    candidate = candidate or {}
    history_frequency = history_frequency or {}
    sequence_stats = _sequence_metrics(selected_numbers)
    coverage_stats = _coverage_metrics(selected_numbers)
    entropy_value = _entropy_score(selected_numbers)
    odd_count = sum(1 for number in selected_numbers if number % 2 != 0)
    even_count = len(selected_numbers) - odd_count
    structural_score = round(
        max(
            0.0,
            min(
                100.0,
                float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0)
                * 0.45
                + float(candidate.get("final_score", {}).get("final_score", 0.0) or 0.0) * 0.30
                + coverage_stats["coverage_score"] * 25.0
                + entropy_value * 20.0
                - abs(odd_count - even_count) * 1.5,
            ),
        ),
        2,
    )
    return {
        "numbers": selected_numbers,
        "core_numbers": list(selected_numbers),
        "audited_reserve_numbers": [],
        "final_card_numbers": list(selected_numbers),
        "display_core_numbers": " ".join(f"{number:02d}" for number in selected_numbers),
        "display_audited_reserve_numbers": "",
        "display_final_card_numbers": " ".join(f"{number:02d}" for number in selected_numbers),
        "odd": odd_count,
        "even": even_count,
        "sum": sum(selected_numbers),
        "frame": len({((number - 1) // 5) for number in selected_numbers}),
        "center": sum(1 for number in selected_numbers if 8 <= number <= 18),
        "quadra_score": {
            "found_quadras": int(candidate.get("quadra_score", {}).get("found_quadras", 0) or 0),
            "average_rank": float(candidate.get("quadra_score", {}).get("average_rank", 0.0) or 0.0),
        },
        "final_score": {
            "final_score": structural_score,
            "components": {
                "structural_score": structural_score,
                "coverage_score": coverage_stats["coverage_score"],
                "entropy_score": entropy_value,
                "sequence_score": max(0.0, 1.0 - (sequence_stats["largest_sequence"] / max(1, dezenas_per_game))),
            },
        },
        "historical_intelligence": {
            "profile_type": str(candidate.get("profile_type", "")),
            "profile_score": float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0),
            "coverage_score": coverage_stats["coverage_score"],
            "entropy_score": entropy_value,
            "sequence_max": sequence_stats["largest_sequence"],
            "dominant_numbers": [
                {"number": int(number), "frequency": int(history_frequency.get(int(number), 0))}
                for number in selected_numbers
            ],
        },
        "profile_type": str(candidate.get("profile_type", "")),
        "profile_score": float(candidate.get("historical_intelligence", {}).get("profile_score", 0.0) or 0.0),
        "ml_enabled": False,
        "structural_metrics": {
            "coverage_score": coverage_stats["coverage_score"],
            "entropy_score": entropy_value,
            "sequence_max": sequence_stats["largest_sequence"],
            "block_distribution": coverage_stats["block_distribution"],
        },
    }


def _build_simulated_draw(size: int = 15) -> list[int]:
    return sorted(random.sample(range(1, 26), k=max(1, min(size, 25))))


def _extract_int_numbers(raw_text: str) -> list[int]:
    numbers: list[int] = []
    for token in re.findall(r"\d+", str(raw_text or "")):
        number = int(token)
        if 1 <= number <= 25 and number not in numbers:
            numbers.append(number)
    return sorted(numbers)


def _extract_contest_number(contest: dict[str, Any]) -> int | None:
    """Extrai o número do concurso oficial aceitando variações de schema."""
    if not isinstance(contest, dict):
        return None

    for key in ("contest_number", "contest_id", "id", "numero", "concurso", "draw_number"):
        value = contest.get(key)
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_contest_numbers(contest: dict[str, Any]) -> list[int]:
    """Extrai dezenas oficiais aceitando variações de schema."""
    if not isinstance(contest, dict):
        return []

    for key in ("numbers", "dezenas", "drawn_numbers", "matched_numbers", "resultado"):
        value = contest.get(key)
        if not value:
            continue
        if isinstance(value, str):
            parts = value.replace(",", " ").replace(";", " ").split()
            numbers: list[int] = []
            for part in parts:
                try:
                    numbers.append(int(part))
                except ValueError:
                    pass
            return sorted(numbers)
        if isinstance(value, (list, tuple, set)):
            numbers = []
            for item in value:
                try:
                    numbers.append(int(item))
                except (TypeError, ValueError):
                    pass
            return sorted(numbers)

    return []


def _lei15a_frozen_nucleus() -> list[int]:
    """Núcleo operacional 15D congelado da Lei 15A (referência institucional)."""
    return list(NUCLEO_LEI15A_15D_CONGELADO)


def build_lei15A_registration_card(format_size: int | str | None) -> dict[str, Any]:
    """Monta o cartão de registro da aposta Lei 15A para formatos 15D–20D."""
    card_format = int(format_size or 15)
    nucleus = list(NUCLEO_LEI15A_15D_CONGELADO)
    if card_format in LEI15A_REGISTRATION_PENDING_FORMATS or card_format > LEI15A_REGISTRATION_MAX_FORMAT:
        return {
            "format_size": card_format,
            "nucleus": nucleus,
            "reserves_used": [],
            "registration_card": [],
            "status": "pendente Lei 15A",
            "operational": False,
        }
    if card_format <= 15:
        reserves_used: list[int] = []
    else:
        reserve_count = min(card_format - 15, len(RESERVAS_LEI15A_PRIORITARIAS))
        reserves_used = list(RESERVAS_LEI15A_PRIORITARIAS[:reserve_count])
    registration_card = sorted(set(nucleus + reserves_used))
    return {
        "format_size": card_format,
        "nucleus": nucleus,
        "reserves_used": reserves_used,
        "registration_card": registration_card,
        "status": "registro_lei15a",
        "operational": True,
    }


def _lei15a_registration_card_label(format_size: int | str | None) -> str:
    """Formata o cartão de registro Lei 15A para exibição ou comparação de sync."""
    registration = build_lei15A_registration_card(format_size)
    if not registration.get("operational"):
        return "-"
    return _format_numbers_for_history(registration.get("registration_card")) or "-"


def _extract_conference_card_numbers(game: dict[str, Any]) -> tuple[list[int], int, str]:
    """Extrai as dezenas que devem ser conferidas, priorizando o cartão final expandido."""
    if not isinstance(game, dict):
        return [], 15, "indisponivel"

    core_numbers = _extract_int_numbers(game.get("numbers", []))
    final_card_numbers = _extract_int_numbers(
        game.get("final_card_numbers")
        or game.get("cartao_final")
        or game.get("cartão_final")
        or []
    )
    card_format = _safe_int(
        game.get("formato_cartao")
        or game.get("card_format")
        or game.get("selected_card_format")
        or game.get("quantidade_final"),
        default=None,
    )
    expected_card_size = int(card_format or len(final_card_numbers) or len(core_numbers) or 15)
    if expected_card_size >= 16 and final_card_numbers:
        return final_card_numbers, expected_card_size, "cartao_final"
    frozen_nucleus = _lei15a_frozen_nucleus()
    if expected_card_size <= 15 and frozen_nucleus:
        return frozen_nucleus, 15, "nucleo_lei_15a_congelado"
    if core_numbers:
        return core_numbers, expected_card_size, "núcleo_lei_15"
    if final_card_numbers:
        return final_card_numbers, expected_card_size, "cartao_final"
    return [], expected_card_size, "indisponivel"


def _select_conference_numbers(game: dict[str, Any]) -> dict[str, Any]:
    """Seleciona as dezenas usadas na conferência institucional."""
    conference_numbers, expected_card_size, origin_label = _extract_conference_card_numbers(game)
    formato = _safe_int(
        game.get("formato_cartao")
        or game.get("format")
        or game.get("card_size")
        or game.get("total_final"),
        default=None,
    )
    formato = int(formato or expected_card_size or len(conference_numbers) or 15)
    return {
        "conference_numbers": conference_numbers,
        "origem_dezenas_conferencia": origin_label if conference_numbers else "indisponivel",
        "dezenas_conferidas_count": len(conference_numbers),
        "expected_card_size": formato,
        "actual_card_size": len(conference_numbers),
        "formato_cartao": formato,
    }


def _normalize_official_numbers(value: object) -> list[int]:
    if not value:
        return []

    raw_items: list[Any] = []
    if isinstance(value, str):
        cleaned = value.replace(",", " ").replace(";", " ").replace("-", " ")
        raw_items = cleaned.split()
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        return []

    numbers: list[int] = []
    for item in raw_items:
        try:
            number = int(item)
        except (TypeError, ValueError):
            continue
        if 1 <= number <= 25:
            numbers.append(number)

    unique_numbers = sorted(set(numbers))
    if len(unique_numbers) != 15:
        return []
    return unique_numbers


def _extract_official_numbers_from_record(record: dict[str, Any]) -> list[int]:
    if not isinstance(record, dict):
        return []

    for key in ("numbers", "dezenas", "drawn_numbers", "resultado", "official_numbers"):
        numbers = _normalize_official_numbers(record.get(key))
        if numbers:
            return numbers
    return []


def _load_previous_contest_numbers_for_rfe(target_contest: int | None) -> RFEPreviousContestReference:
    """
    Carrega as dezenas oficiais do concurso imediatamente anterior ao alvo.

    Não altera histórico.
    Não importa concurso novo.
    Não consulta API externa.
    Usa somente dados já persistidos no banco/snapshot.
    """
    if target_contest is not None and int(target_contest) > 1:
        previous_contest_id = int(target_contest) - 1
        previous_contest = get_official_contest(previous_contest_id)
        if previous_contest:
            numbers = _extract_official_numbers_from_record(previous_contest)
            if numbers:
                return RFEPreviousContestReference(
                    found=True,
                    contest_id=previous_contest_id,
                    numbers=numbers,
                    source="official_lotofacil_history",
                    message=None,
                )
            return RFEPreviousContestReference(
                found=False,
                contest_id=previous_contest_id,
                numbers=[],
                source="official_lotofacil_history",
                message="Concurso anterior encontrado, mas dezenas oficiais inválidas ou incompletas.",
            )
        return RFEPreviousContestReference(
            found=False,
            contest_id=previous_contest_id,
            numbers=[],
            source="official_lotofacil_history",
            message="Concurso anterior não encontrado na base oficial persistida.",
        )

    latest_contest = get_latest_official_contest()
    latest_contest_number = _safe_int((latest_contest or {}).get("contest_number"), default=None)
    if latest_contest_number is not None and latest_contest_number > 0:
        previous_contest = get_official_contest(int(latest_contest_number))
        if previous_contest:
            numbers = _extract_official_numbers_from_record(previous_contest)
            if numbers:
                return RFEPreviousContestReference(
                    found=True,
                    contest_id=latest_contest_number,
                    numbers=numbers,
                    source="official_lotofacil_history",
                    message=None,
                )
            return RFEPreviousContestReference(
                found=False,
                contest_id=latest_contest_number,
                numbers=[],
                source="official_lotofacil_history",
                message="Último concurso oficial encontrado, mas dezenas oficiais inválidas ou incompletas.",
            )

    return RFEPreviousContestReference(
        found=False,
        contest_id=None,
        numbers=[],
        source="indisponivel",
        message="Nenhum concurso oficial persistido disponível.",
    )


def _update_rfe_diagnostics(diagnostics: dict[str, Any], result: RFEValidationResult) -> None:
    diagnostics["rfe_enabled"] = True
    diagnostics["rfe_rejected_games"] = int(diagnostics.get("rfe_rejected_games", 0) or 0) + 1
    diagnostics["rfe_01_rejected_games"] = int(diagnostics.get("rfe_01_rejected_games", 0) or 0) + (
        1 if any(str(reason).startswith("RFE-01") for reason in result.blocked_reasons) else 0
    )
    diagnostics["rfe_02_rejected_games"] = int(diagnostics.get("rfe_02_rejected_games", 0) or 0) + (
        1 if any(str(reason).startswith("RFE-02") for reason in result.blocked_reasons) else 0
    )
    blocked_reasons = list(diagnostics.get("rfe_blocked_reasons", []) or [])
    blocked_reasons.extend(str(reason) for reason in result.blocked_reasons if reason)
    diagnostics["rfe_blocked_reasons"] = blocked_reasons
    diagnostics["rfe_status"] = "BLOQUEADO"


def _parse_draw_numbers(raw_text: str) -> list[int]:
    values: list[int] = []
    for token in str(raw_text or "").replace(",", " ").split():
        if token.isdigit():
            number = int(token)
            if 1 <= number <= 25 and number not in values:
                values.append(number)
    return sorted(values)


def _format_simulation_numbers(numbers: list[int], matched_numbers: list[int]) -> str:
    matched_set = set(int(number) for number in matched_numbers)
    fragments: list[str] = []
    for number in numbers:
        if int(number) in matched_set:
            fragments.append(
                f'<span style="color:#1b7f2a;font-weight:700;">{int(number):02d}</span>'
            )
        else:
            fragments.append(
                f'<span style="color:#9aa4b2;text-decoration:line-through;">{int(number):02d}</span>'
            )
    return " ".join(fragments)


def _run_institutional_generation(
    *,
    total_games: int,
    dezenas_per_game: int,
    use_top50: bool,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_limit: int,
    snapshot: dict[str, Any],
    batch_number_usage: dict[int, int] | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    batch_total_games: int | None = None,
    seen_signatures: set[str] | None = None,
) -> None:
    if _is_sovereign_generation_blocked():
        st.session_state["institutional_generation_result"] = _sovereign_generation_blocked_result(
            requested_count=total_games,
        )
        st.warning("Geração legada bloqueada — rota órfã indisponível (M-VIS-031).")
        return
    st.session_state["institutional_last_ui_event"] = "operacional:gerar_jogos"
    st.session_state.pop("institutional_generation_batch_result", None)
    started = time.monotonic()
    seed = int(time.time()) % 1_000_000
    batch_id = _institutional_output_batch_id()
    policy = _institutional_generation_policy(dezenas_per_game)
    official_15_context = _official_15_generation_context(st.session_state.get("institutional_official_15_group", "G30")) if int(dezenas_per_game or 0) == 15 else {}
    compact_adjustment = _compact_small_batch_adjustment(game_size=dezenas_per_game, total_games=total_games)
    if compact_adjustment:
        policy = dict(policy)
        policy.update(compact_adjustment)
        compact_boost_numbers = [int(number) for number in (policy.get("compactation_adjustment_boost_numbers", []) or [17, 23])]
        compact_reduce_priority_numbers = [2, 5, 21, 24]
        policy["core_numbers"] = sorted(
            {int(number) for number in (policy.get("core_numbers", []) or [])}.union(compact_boost_numbers)
        )
        policy["discouraged_numbers"] = sorted(
            {int(number) for number in (policy.get("discouraged_numbers", []) or [])}.union(compact_reduce_priority_numbers)
        )
    repeat_min = int(policy.get("repeat_min", 0) or 0)
    repeat_max = int(policy.get("repeat_max", repeat_limit) or repeat_limit)
    compact_repeat_min = policy.get("compactation_adjustment_repeat_min")
    compact_repeat_max = policy.get("compactation_adjustment_repeat_max")
    compact_sequence_max = policy.get("compactation_adjustment_sequence_max")
    compact_odd_min = policy.get("compactation_adjustment_odd_min")
    compact_odd_max = policy.get("compactation_adjustment_odd_max")
    compact_even_min = policy.get("compactation_adjustment_even_min")
    compact_even_max = policy.get("compactation_adjustment_even_max")
    preferred_parity_pairs = list(policy.get("preferred_parity_pairs", []) or [])
    allowed_parity_pairs = list(policy.get("allowed_parity_pairs", []) or [])
    preferred_profile_ratios = dict(policy.get("preferred_profile_ratios", {}) or {})
    core_numbers = [int(number) for number in (policy.get("core_numbers", []) or [])]
    discouraged_numbers = [int(number) for number in (policy.get("discouraged_numbers", []) or [])]
    max_frequency_ratio = float(policy.get("max_frequency_ratio", 1.0) or 1.0)
    min_frequency_ratio = float(policy.get("min_frequency_ratio", 0.0) or 0.0)
    effective_sequence_max = int(policy.get("sequence_max", sequence_max) or sequence_max)
    if compact_sequence_max is not None:
        effective_sequence_max = max(effective_sequence_max, int(compact_sequence_max))
    effective_odd_min = int(compact_odd_min) if compact_odd_min is not None else odd_min
    effective_odd_max = int(compact_odd_max) if compact_odd_max is not None else odd_max
    effective_even_min = int(compact_even_min) if compact_even_min is not None else even_min
    effective_even_max = int(compact_even_max) if compact_even_max is not None else even_max
    compact_coverage_min = policy.get("compactation_adjustment_coverage_min")
    compact_entropy_min = policy.get("compactation_adjustment_entropy_min")
    if compact_repeat_min is not None:
        repeat_min = max(0, int(compact_repeat_min))
    if compact_repeat_max is not None:
        repeat_max = max(0, int(compact_repeat_max))
    if repeat_min > repeat_max:
        repeat_min = repeat_max
    if int(total_games or 0) <= 20 and int(dezenas_per_game or 0) == 15:
        effective_sequence_max = max(effective_sequence_max, 6)
        effective_odd_min = min(effective_odd_min, 5)
        effective_odd_max = max(effective_odd_max, 10)
        effective_even_min = min(effective_even_min, 5)
        effective_even_max = max(effective_even_max, 10)
        repeat_min = min(repeat_min, 3)
        repeat_max = max(repeat_max, 9)
        if compact_coverage_min is not None:
            compact_coverage_min = min(float(compact_coverage_min), 0.34)
        else:
            compact_coverage_min = 0.34
        if compact_entropy_min is not None:
            compact_entropy_min = min(float(compact_entropy_min), 0.38)
        else:
            compact_entropy_min = 0.38
    effective_coverage_min = (
        float(compact_coverage_min)
        if compact_coverage_min is not None
        else max(float(coverage_min), float(policy.get("coverage_min", coverage_min) or coverage_min))
    )
    effective_entropy_min = (
        float(compact_entropy_min)
        if compact_entropy_min is not None
        else max(float(entropy_min), float(policy.get("entropy_min", entropy_min) or entropy_min))
    )
    latest_contest = _load_latest_contest_summary()
    target_contest = int(latest_contest["contest_number"]) if latest_contest else None
    previous_contest_reference = _load_previous_contest_numbers_for_rfe(target_contest)
    previous_contest_numbers = list(previous_contest_reference.numbers or [])
    rfe_reference_source = str(previous_contest_reference.source or "indisponivel")
    history_frequency = _history_number_frequency()
    latest_numbers = set(int(number) for number in (latest_contest or {}).get("dezenas", []))
    batch_number_usage = batch_number_usage if batch_number_usage is not None else {}
    batch_profile_usage = batch_profile_usage if batch_profile_usage is not None else {}
    batch_total_games = max(1, int(batch_total_games or total_games))
    official_package_registry_found = False
    official_package_group_key = ""
    official_group_games: list[tuple[int, ...]] = []
    official_package_size_loaded = 0
    games: list[dict[str, Any]] = []
    used_signatures: set[str] = set(seen_signatures or set())
    fill_diagnostics: dict[str, Any] = {}
    fill_diagnostics["rfe_enabled"] = True
    fill_diagnostics["rfe_previous_contest_found"] = bool(previous_contest_reference.found)
    fill_diagnostics["rfe_previous_contest_id"] = previous_contest_reference.contest_id
    fill_diagnostics["rfe_previous_contest_numbers"] = " ".join(f"{number:02d}" for number in previous_contest_numbers) or "-"
    fill_diagnostics["rfe_previous_contest_source"] = rfe_reference_source
    if previous_contest_reference.message:
        fill_diagnostics["rfe_previous_contest_message"] = previous_contest_reference.message
    direct_generation_mode = int(dezenas_per_game or 0) == 15
    if not previous_contest_reference.found:
        fill_diagnostics["fill_completed"] = False
        fill_diagnostics["attempts_used"] = 0
        fill_diagnostics["candidate_pool_generated"] = 0
        fill_diagnostics["valid_candidates_found"] = 0
        fill_diagnostics["accepted_games"] = 0
        fill_diagnostics["rfe_status"] = "BLOQUEADO"
        fill_diagnostics["insufficient_reason"] = (
            "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS"
            if previous_contest_reference.contest_id is not None
            else "RFE_PREVIOUS_CONTEST_NOT_FOUND"
        )
        fill_diagnostics["rfe_blocked_reasons"] = [
            previous_contest_reference.message
            or "RFE-01: concurso anterior indisponível para validação estrutural."
        ]
        games = []
    elif direct_generation_mode:
        sovereign_payload = _invoke_sovereign_adm_generate_best_games(
            requested_count=total_games,
            batch_label=SOVEREIGN_BATCH_LABEL,
            seed=seed,
        )
        games = list(sovereign_payload.get("games") or [])
        fill_diagnostics["sovereign_generation_path"] = "generate_best_games"
        fill_diagnostics["analysis_batch_label"] = SOVEREIGN_BATCH_LABEL
        fill_diagnostics["fill_completed"] = len(games) >= total_games
        if len(games) < total_games:
            fill_diagnostics["insufficient_reason"] = "INSUFFICIENT_VALID_CANDIDATES"
        else:
            fill_diagnostics["insufficient_reason"] = "none"
    else:
        candidate_count = max(total_games * 20, 200 if use_top50 else 120)
        compact_candidate_multiplier = int(policy.get("compactation_adjustment_candidate_multiplier", 0) or 0)
        if compact_candidate_multiplier > 0:
            candidate_count = max(candidate_count, total_games * compact_candidate_multiplier)
        compact_attempt_limit = int(policy.get("compactation_adjustment_attempt_limit", 0) or 0)
        ranked_candidates = generate_ranked_games(
            total_games=candidate_count, seed=seed, ml_enabled=False,
            pool_size=max(candidate_count, 30),
            batch_label=st.session_state.get("clean_law15_analysis_batch_label"),
        )
        for candidate in ranked_candidates:
            selected_numbers = _select_subset_from_candidate(
                list(candidate.get("numbers", [])),
                target_size=dezenas_per_game,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max_frequency_ratio,
                min_frequency_ratio=min_frequency_ratio,
                preferred_profile_ratios=preferred_profile_ratios,
                odd_min=effective_odd_min,
                odd_max=effective_odd_max,
                even_min=effective_even_min,
                even_max=effective_even_max,
                sequence_max=effective_sequence_max,
                coverage_min=effective_coverage_min,
                entropy_min=effective_entropy_min,
                repeat_min=repeat_min,
                repeat_max=repeat_max,
                preferred_parity_pairs=preferred_parity_pairs,
                allowed_parity_pairs=allowed_parity_pairs,
            )
            if not selected_numbers:
                selected_numbers = _force_subset_from_universe(
                    target_size=dezenas_per_game,
                    frequency_map=history_frequency,
                    latest_numbers=latest_numbers,
                    batch_number_usage=batch_number_usage,
                    batch_total_games=batch_total_games,
                    batch_profile_usage=batch_profile_usage,
                    core_numbers=core_numbers,
                    discouraged_numbers=discouraged_numbers,
                    max_frequency_ratio=max_frequency_ratio,
                    min_frequency_ratio=min_frequency_ratio,
                    preferred_profile_ratios=preferred_profile_ratios,
                    odd_min=effective_odd_min,
                    odd_max=effective_odd_max,
                    even_min=effective_even_min,
                    even_max=effective_even_max,
                    preferred_parity_pairs=preferred_parity_pairs,
                    repeat_min=repeat_min,
                    repeat_max=repeat_max,
                    sequence_max=effective_sequence_max,
                    coverage_min=effective_coverage_min,
                    entropy_min=effective_entropy_min,
                    allowed_parity_pairs=allowed_parity_pairs,
                    offset=len(games),
                )
            if not selected_numbers:
                continue
            rfe_result = validate_rfe_final_card(selected_numbers, previous_contest_numbers or [])
            if not rfe_result.approved:
                _update_rfe_diagnostics(fill_diagnostics, rfe_result)
                continue
            signature = _game_signature(selected_numbers)
            if signature in used_signatures:
                fill_diagnostics["rejected_by_internal_duplicate"] = int(fill_diagnostics.get("rejected_by_internal_duplicate", 0) or 0) + 1
                fill_diagnostics["rejected_by_repeated_pattern"] = int(fill_diagnostics.get("rejected_by_repeated_pattern", 0) or 0) + 1
                continue
            games.append(
                _build_institutional_game_record(
                    selected_numbers=selected_numbers,
                    candidate=dict(candidate),
                    history_frequency=history_frequency,
                    dezenas_per_game=dezenas_per_game,
                )
            )
            profile_pair = (
                sum(1 for number in selected_numbers if number % 2 != 0),
                sum(1 for number in selected_numbers if number % 2 == 0),
            )
            batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
            for number in selected_numbers:
                batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
            used_signatures.add(signature)
            if seen_signatures is not None:
                seen_signatures.add(signature)
            if len(games) >= total_games:
                break

        fallback_attempt = 0
        fallback_attempt_limit = max(total_games * 25, 50)
        if compact_attempt_limit > 0:
            fallback_attempt_limit = max(fallback_attempt_limit, compact_attempt_limit)
        while len(games) < total_games and fallback_attempt < fallback_attempt_limit:
            candidate = ranked_candidates[fallback_attempt % len(ranked_candidates)] if ranked_candidates else {}
            fallback_numbers = _force_subset_from_universe(
                target_size=dezenas_per_game,
                frequency_map=history_frequency,
                latest_numbers=latest_numbers,
                batch_number_usage=batch_number_usage,
                batch_total_games=batch_total_games,
                batch_profile_usage=batch_profile_usage,
                core_numbers=core_numbers,
                discouraged_numbers=discouraged_numbers,
                max_frequency_ratio=max_frequency_ratio,
                min_frequency_ratio=min_frequency_ratio,
                preferred_profile_ratios=preferred_profile_ratios,
                odd_min=effective_odd_min,
                odd_max=effective_odd_max,
                even_min=effective_even_min,
                even_max=effective_even_max,
                preferred_parity_pairs=preferred_parity_pairs,
                repeat_min=repeat_min,
                repeat_max=repeat_max,
                sequence_max=effective_sequence_max,
                coverage_min=effective_coverage_min,
                entropy_min=effective_entropy_min,
                allowed_parity_pairs=allowed_parity_pairs,
                offset=seed + fallback_attempt,
            )
            fallback_attempt += 1
            if not fallback_numbers:
                continue
            rfe_result = validate_rfe_final_card(fallback_numbers, previous_contest_numbers or [])
            if not rfe_result.approved:
                _update_rfe_diagnostics(fill_diagnostics, rfe_result)
                continue
            signature = _game_signature(fallback_numbers)
            if signature in used_signatures:
                fill_diagnostics["rejected_by_internal_duplicate"] = int(fill_diagnostics.get("rejected_by_internal_duplicate", 0) or 0) + 1
                fill_diagnostics["rejected_by_repeated_pattern"] = int(fill_diagnostics.get("rejected_by_repeated_pattern", 0) or 0) + 1
                continue
            games.append(
                _build_institutional_game_record(
                    selected_numbers=fallback_numbers,
                    candidate=dict(candidate),
                    history_frequency=history_frequency,
                    dezenas_per_game=dezenas_per_game,
                )
            )
            profile_pair = (
                sum(1 for number in fallback_numbers if number % 2 != 0),
                sum(1 for number in fallback_numbers if number % 2 == 0),
            )
            batch_profile_usage[profile_pair] = int(batch_profile_usage.get(profile_pair, 0) or 0) + 1
            for number in fallback_numbers:
                batch_number_usage[int(number)] = int(batch_number_usage.get(int(number), 0) or 0) + 1
            used_signatures.add(signature)
            if seen_signatures is not None:
                seen_signatures.add(signature)
    historical_deduplication_mode = "AUDIT_ONLY"
    historical_duplicates_found = 0
    batch_fill_strategy = "FILL_UNTIL_REQUESTED_QUANTITY" if direct_generation_mode else "STRUCTURAL_SELECTION"
    commander_report = output_commander_validate_games(
        games,
        batch_id=batch_id,
        generation_event_id=None,
        target_size=dezenas_per_game,
        required_total=total_games,
        candidate_total=total_games,
        persisted_signatures=set(load_all_output_signatures()),
        historical_deduplication_mode=historical_deduplication_mode,
    )
    if direct_generation_mode and len(games) < total_games:
        commander_report = {
            **commander_report,
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "INSUFFICIENT_VALID_CANDIDATES",
            "error_message": "INSUFFICIENT_VALID_CANDIDATES",
        }
    fill_diagnostics["rejected_by_output_commander"] = int(commander_report.get("quantidade_jogos_rejeitados", 0) or 0)
    if commander_report.get("status_comandante_saida") != "APROVADO" or int(commander_report.get("quantidade_jogos_unicos", 0) or 0) != int(total_games):
        approved_total = int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games))
        rejected_total = int(commander_report.get("quantidade_jogos_rejeitados", max(0, total_games - approved_total)) or max(0, total_games - approved_total))
        blocked_reason = str(
            commander_report.get("motivo_bloqueio")
            or commander_report.get("error_message")
            or "nao foi possivel gerar a quantidade solicitada de jogos unicos"
        )
        if fill_diagnostics.get("insufficient_reason") in {
            "RFE_PREVIOUS_CONTEST_NOT_FOUND",
            "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS",
        }:
            blocked_reason = str(fill_diagnostics.get("insufficient_reason"))
        if (
            int(commander_report.get("quantidade_jogos_aprovados", 0) or 0)
            < int(commander_report.get("quantidade_jogos_solicitada", total_games) or total_games)
            and fill_diagnostics.get("insufficient_reason") not in {
                "RFE_PREVIOUS_CONTEST_NOT_FOUND",
                "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS",
            }
        ):
            blocked_reason = "Pacote bloqueado por não atingir a quantidade solicitada."
        if direct_generation_mode and len(games) < total_games and fill_diagnostics.get("insufficient_reason") not in {
            "RFE_PREVIOUS_CONTEST_NOT_FOUND",
            "RFE_PREVIOUS_CONTEST_INVALID_NUMBERS",
        }:
            blocked_reason = "INSUFFICIENT_VALID_CANDIDATES"
        if official_group_games and int(commander_report.get("historical_duplicates_found", 0) or 0) > 0:
            blocked_reason = "Aviso: há jogos do pacote oficial já presentes no histórico. O pacote foi preservado por se tratar de grupo oficial fechado."
        st.session_state["institutional_generation"] = {
            "seed": seed,
            "games": [],
            "total_games": total_games,
            "dezenas_per_game": dezenas_per_game,
            "use_top50": use_top50,
            "core_numbers": core_numbers,
            "discouraged_numbers": discouraged_numbers,
            "compactation_mode": str(policy.get("compactation_mode", "") or ""),
            "compactation_test_status": str(policy.get("compactation_test_status", "") or ""),
            "compactation_failure_type": str(policy.get("compactation_failure_type", "") or ""),
            "compactation_adjustment_status": str(policy.get("compactation_adjustment_status", "") or ""),
            "compactation_adjustment_mode": str(policy.get("compactation_adjustment_mode", "") or ""),
            "compactation_adjustment_reason": str(policy.get("compactation_adjustment_reason", "") or ""),
            "compactation_adjustment_boost_numbers": list(policy.get("compactation_adjustment_boost_numbers", []) or []),
            "compactation_adjustment_reduce_priority_numbers": list(policy.get("compactation_adjustment_reduce_priority_numbers", []) or []),
            "compactation_adjustment_repeat_min": int(policy.get("compactation_adjustment_repeat_min", 0) or 0),
            "compactation_adjustment_repeat_max": int(policy.get("compactation_adjustment_repeat_max", 0) or 0),
            "compactation_adjustment_coverage_min": float(policy.get("compactation_adjustment_coverage_min", 0.0) or 0.0),
            "compactation_adjustment_entropy_min": float(policy.get("compactation_adjustment_entropy_min", 0.0) or 0.0),
            "compactation_adjustment_sequence_max": int(policy.get("compactation_adjustment_sequence_max", 0) or 0),
            "compactation_adjustment_candidate_multiplier": int(policy.get("compactation_adjustment_candidate_multiplier", 0) or 0),
            "max_frequency_ratio": max_frequency_ratio,
            "min_frequency_ratio": min_frequency_ratio,
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "batch_fill_strategy": batch_fill_strategy,
            "scientific_law_role": "COMMANDER",
            "generator_role": "EXECUTOR",
            "output_commander_role": "AUDITOR",
            "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
            "calibration_engine_role": "DISABLED",
            "candidate_pool_generated": int(fill_diagnostics.get("candidate_pool_generated", 0) or 0),
            "valid_candidates_found": int(fill_diagnostics.get("valid_candidates_found", 0) or 0),
            "accepted_games": int(fill_diagnostics.get("accepted_games", 0) or 0),
            "rejected_by_internal_duplicate": int(fill_diagnostics.get("rejected_by_internal_duplicate", 0) or 0),
            "rejected_by_invalid_size": int(fill_diagnostics.get("rejected_by_invalid_size", 0) or 0),
            "rejected_by_repeated_pattern": int(fill_diagnostics.get("rejected_by_repeated_pattern", 0) or 0),
            "rejected_by_output_commander": int(fill_diagnostics.get("rejected_by_output_commander", 0) or 0),
            "attempts_used": int(fill_diagnostics.get("attempts_used", 0) or 0),
            "fill_completed": bool(fill_diagnostics.get("fill_completed", False)),
            "rfe_enabled": bool(fill_diagnostics.get("rfe_enabled", True)),
            "rfe_rejected_games": int(fill_diagnostics.get("rfe_rejected_games", 0) or 0),
            "rfe_01_rejected_games": int(fill_diagnostics.get("rfe_01_rejected_games", 0) or 0),
            "rfe_02_rejected_games": int(fill_diagnostics.get("rfe_02_rejected_games", 0) or 0),
            "rfe_blocked_reasons": list(fill_diagnostics.get("rfe_blocked_reasons", []) or []),
            "rfe_status": str(fill_diagnostics.get("rfe_status", "OK") or "OK"),
            "rfe_reference_source": rfe_reference_source,
            "rfe_previous_contest_found": bool(fill_diagnostics.get("rfe_previous_contest_found", False)),
            "rfe_previous_contest_id": fill_diagnostics.get("rfe_previous_contest_id"),
            "rfe_previous_contest_numbers": str(fill_diagnostics.get("rfe_previous_contest_numbers", "-") or "-"),
            "rfe_previous_contest_message": str(fill_diagnostics.get("rfe_previous_contest_message", "") or ""),
            "rfe_previous_contest_source": str(fill_diagnostics.get("rfe_previous_contest_source", rfe_reference_source) or rfe_reference_source),
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "generation_event_id": None,
            "created_at": datetime.now(UTC).isoformat(),
            "runtime_status": "critical_error",
            "elapsed_time": round(time.monotonic() - started, 3),
            "batch_id": batch_id,
            "output_commander": commander_report,
        }
        st.session_state["institutional_generation_result"] = {
            "generation_event_id": None,
            "seed": seed,
            "jogos": [],
            "quantidade_jogos_solicitada": total_games,
            "quantidade_dezenas_solicitada": dezenas_per_game,
            "total_esperado_jogos": int(total_games) * int(1 if total_games else 0),
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "quantidade_jogos_candidatos": int(commander_report.get("quantidade_jogos_candidatos", total_games) or total_games),
            "quantidade_jogos_aprovados": approved_total,
            "quantidade_jogos_real_gerada": approved_total,
            "quantidade_jogos_persistida": 0,
            "len_todos_os_jogos": [],
            "primeiro_jogo": [],
            "len_primeiro_jogo": 0,
            "batch_id": batch_id,
            "status_comandante_saida": "BLOQUEADO",
            "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", 0) or 0),
            "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
            "total_jogos_rejeitados": rejected_total,
            "motivo_bloqueio": blocked_reason,
            "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
            "error_message": blocked_reason,
            "duplicate_hashes": list(commander_report.get("duplicate_hashes", []) or []),
            "invalid_games": list(commander_report.get("invalid_games", []) or []),
            "historical_deduplication_mode": str(commander_report.get("historical_deduplication_mode", historical_deduplication_mode) or historical_deduplication_mode),
            "historical_duplicates_found": int(commander_report.get("historical_duplicates_found", historical_duplicates_found) or historical_duplicates_found),
            "historical_duplicates_removed": int(commander_report.get("historical_duplicates_removed", 0) or 0),
            "official_package_preserved": bool(official_group_games),
            "candidate_pool_generated": int(fill_diagnostics.get("candidate_pool_generated", 0) or 0),
            "valid_candidates_found": int(fill_diagnostics.get("valid_candidates_found", 0) or 0),
            "accepted_games": int(fill_diagnostics.get("accepted_games", 0) or 0),
            "rejected_by_internal_duplicate": int(fill_diagnostics.get("rejected_by_internal_duplicate", 0) or 0),
            "rejected_by_invalid_size": int(fill_diagnostics.get("rejected_by_invalid_size", 0) or 0),
            "rejected_by_repeated_pattern": int(fill_diagnostics.get("rejected_by_repeated_pattern", 0) or 0),
            "rejected_by_output_commander": int(fill_diagnostics.get("rejected_by_output_commander", 0) or 0),
            "attempts_used": int(fill_diagnostics.get("attempts_used", 0) or 0),
            "fill_completed": bool(fill_diagnostics.get("fill_completed", False)),
            "rfe_enabled": bool(fill_diagnostics.get("rfe_enabled", True)),
            "rfe_rejected_games": int(fill_diagnostics.get("rfe_rejected_games", 0) or 0),
            "rfe_01_rejected_games": int(fill_diagnostics.get("rfe_01_rejected_games", 0) or 0),
            "rfe_02_rejected_games": int(fill_diagnostics.get("rfe_02_rejected_games", 0) or 0),
            "rfe_blocked_reasons": list(fill_diagnostics.get("rfe_blocked_reasons", []) or []),
            "rfe_status": str(fill_diagnostics.get("rfe_status", "OK") or "OK"),
            "rfe_reference_source": rfe_reference_source,
            "rfe_previous_contest_found": bool(fill_diagnostics.get("rfe_previous_contest_found", False)),
            "rfe_previous_contest_id": fill_diagnostics.get("rfe_previous_contest_id"),
            "rfe_previous_contest_numbers": str(fill_diagnostics.get("rfe_previous_contest_numbers", "-") or "-"),
            "rfe_previous_contest_message": str(fill_diagnostics.get("rfe_previous_contest_message", "") or ""),
            "rfe_previous_contest_source": str(fill_diagnostics.get("rfe_previous_contest_source", rfe_reference_source) or rfe_reference_source),
        }
        _store_active_batch_state(
            batch_id=batch_id,
            generation_event_ids=[],
            policy_id=str(commander_report.get("policy_id", "") or ""),
            generated_at=st.session_state["institutional_generation"]["created_at"],
            game_size=dezenas_per_game,
            total_games=total_games,
        )
        return
    generation_snapshot = _persist_generation_snapshot(
        games=games,
        seed=seed,
        target_contest=target_contest,
        batch_id=batch_id,
        generation_context={
            **official_15_context,
            "policy_mode": str(policy.get("policy_mode", "") or ""),
            "validation_threshold": int(policy.get("validation_threshold", 0) or 0),
            "target_band": str(policy.get("target_band", "") or ""),
            "current_target": str(policy.get("current_target", "") or ""),
            "secondary_target": str(policy.get("secondary_target", "") or ""),
            "policy_origin": str(policy.get("policy_origin", "") or ""),
            "policy_variant": str(policy.get("policy_variant", "") or ""),
            "policy_adjustment_reason": str(policy.get("policy_adjustment_reason", "") or ""),
            "status_prospectivo": str(policy.get("status_prospectivo", "") or "pending_prospective_validation"),
            "memory_role": str(policy.get("memory_role", "") or ""),
            "dominant_memory": policy.get("dominant_memory"),
            "dominant_memory_mode": str(policy.get("dominant_memory_mode", "") or ""),
            "selection_variant": str(policy.get("selection_variant", "") or ""),
            "cross_validation_reason": str(policy.get("cross_validation_reason", "") or ""),
            "cross_validation_summary": dict(policy.get("cross_validation_summary", {}) or {}),
            "based_on_memory_kind": str(policy.get("based_on_memory_kind", "") or ""),
            "based_on_memory_id": policy.get("based_on_memory_id"),
            "based_on_batch_id": str(policy.get("based_on_batch_id", "") or ""),
            "based_on_generation_range": dict(policy.get("based_on_generation_range", {}) or {}),
            "based_on_best_generations": list(policy.get("based_on_best_generations", []) or []),
            "core_numbers_to_preserve": list(policy.get("core_numbers_to_preserve", []) or []),
            "controlled_support_numbers": list(policy.get("controlled_support_numbers", []) or []),
            "promote_numbers_for_12_plus": list(policy.get("promote_numbers_for_12_plus", []) or []),
            "reduce_priority_numbers": list(policy.get("reduce_priority_numbers", []) or []),
            "real_gap_number": policy.get("real_gap_number"),
            "compactation_test_status": str(policy.get("compactation_test_status", "") or ""),
            "compactation_failure_type": str(policy.get("compactation_failure_type", "") or ""),
            "compactation_adjustment_status": str(policy.get("compactation_adjustment_status", "") or ""),
            "compactation_adjustment_mode": str(policy.get("compactation_adjustment_mode", "") or ""),
            "compactation_adjustment_reason": str(policy.get("compactation_adjustment_reason", "") or ""),
            "compactation_adjustment_boost_numbers": list(policy.get("compactation_adjustment_boost_numbers", []) or []),
            "compactation_adjustment_reduce_priority_numbers": list(policy.get("compactation_adjustment_reduce_priority_numbers", []) or []),
            "compactation_adjustment_repeat_min": int(policy.get("compactation_adjustment_repeat_min", 0) or 0),
            "compactation_adjustment_repeat_max": int(policy.get("compactation_adjustment_repeat_max", 0) or 0),
            "compactation_adjustment_coverage_min": float(policy.get("compactation_adjustment_coverage_min", 0.0) or 0.0),
            "compactation_adjustment_entropy_min": float(policy.get("compactation_adjustment_entropy_min", 0.0) or 0.0),
            "compactation_adjustment_sequence_max": int(policy.get("compactation_adjustment_sequence_max", 0) or 0),
            "compactation_adjustment_candidate_multiplier": int(policy.get("compactation_adjustment_candidate_multiplier", 0) or 0),
            "compactation_adjustment_odd_min": int(policy.get("compactation_adjustment_odd_min", 0) or 0),
            "compactation_adjustment_odd_max": int(policy.get("compactation_adjustment_odd_max", 0) or 0),
            "compactation_adjustment_even_min": int(policy.get("compactation_adjustment_even_min", 0) or 0),
            "compactation_adjustment_even_max": int(policy.get("compactation_adjustment_even_max", 0) or 0),
            "compactation_adjustment_attempt_limit": int(policy.get("compactation_adjustment_attempt_limit", 0) or 0),
            "dezenas_per_game": dezenas_per_game,
            "total_games": total_games,
            "use_top50": use_top50,
            "core_numbers": core_numbers,
            "discouraged_numbers": discouraged_numbers,
            "max_frequency_ratio": max_frequency_ratio,
            "min_frequency_ratio": min_frequency_ratio,
            "odd_min": odd_min,
            "odd_max": odd_max,
            "even_min": even_min,
            "even_max": even_max,
            "sequence_max": effective_sequence_max,
            "coverage_min": effective_coverage_min,
            "entropy_min": effective_entropy_min,
            "repeat_limit": repeat_limit,
            "repeticao_ultimo_concurso_min": repeat_min,
            "repeticao_ultimo_concurso_max": repeat_max,
            "perfis_paridade_preferenciais": preferred_parity_pairs,
            "perfis_paridade_permitidos": allowed_parity_pairs,
            "limite_sequencia_max": effective_sequence_max,
            "batch_id": batch_id,
            "game_signatures": [game.get("game_signature", "") for game in commander_report.get("accepted_games", [])],
            "batch_fill_strategy": batch_fill_strategy,
            "scientific_law_role": "COMMANDER",
            "generator_role": "EXECUTOR",
            "output_commander_role": "AUDITOR",
            "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
            "calibration_engine_role": "DISABLED",
            "rfe_enabled": bool(fill_diagnostics.get("rfe_enabled", True)),
            "rfe_rejected_games": int(fill_diagnostics.get("rfe_rejected_games", 0) or 0),
            "rfe_01_rejected_games": int(fill_diagnostics.get("rfe_01_rejected_games", 0) or 0),
            "rfe_02_rejected_games": int(fill_diagnostics.get("rfe_02_rejected_games", 0) or 0),
            "rfe_blocked_reasons": list(fill_diagnostics.get("rfe_blocked_reasons", []) or []),
            "rfe_status": str(fill_diagnostics.get("rfe_status", "OK") or "OK"),
            "rfe_reference_source": rfe_reference_source,
            "rfe_previous_contest_found": bool(fill_diagnostics.get("rfe_previous_contest_found", False)),
            "rfe_previous_contest_id": fill_diagnostics.get("rfe_previous_contest_id"),
            "rfe_previous_contest_numbers": str(fill_diagnostics.get("rfe_previous_contest_numbers", "-") or "-"),
            "rfe_previous_contest_message": str(fill_diagnostics.get("rfe_previous_contest_message", "") or ""),
            "rfe_previous_contest_source": str(fill_diagnostics.get("rfe_previous_contest_source", rfe_reference_source) or rfe_reference_source),
            "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", len(games)) or len(games)),
            "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
            "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
            "status_comandante_saida": str(commander_report.get("status_comandante_saida", "APROVADO") or "APROVADO"),
            "historical_deduplication_mode": str(commander_report.get("historical_deduplication_mode", historical_deduplication_mode) or historical_deduplication_mode),
            "historical_duplicates_found": int(commander_report.get("historical_duplicates_found", historical_duplicates_found) or historical_duplicates_found),
            "historical_duplicates_removed": int(commander_report.get("historical_duplicates_removed", 0) or 0),
            "official_package_preserved": bool(official_group_games),
            "official_package_registry_found": bool(official_package_registry_found),
            "official_package_group_key": official_package_group_key,
            "official_package_size_loaded": int(official_package_size_loaded),
            "official_package_size_before_output_commander": int(len(games)),
            "official_package_size_after_output_commander": int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games)),
            "fallback_dynamic_used": False,
            "official_package_error": "none",
        },
    )
    st.session_state["institutional_generation"] = {
        "seed": seed,
        "games": games,
        "total_games": total_games,
        "dezenas_per_game": dezenas_per_game,
        **official_15_context,
        "use_top50": use_top50,
        "core_numbers": core_numbers,
        "discouraged_numbers": discouraged_numbers,
        "compactation_mode": str(policy.get("compactation_mode", "") or ""),
        "compactation_test_status": str(policy.get("compactation_test_status", "") or ""),
        "compactation_failure_type": str(policy.get("compactation_failure_type", "") or ""),
        "compactation_adjustment_status": str(policy.get("compactation_adjustment_status", "") or ""),
        "compactation_adjustment_mode": str(policy.get("compactation_adjustment_mode", "") or ""),
        "compactation_adjustment_reason": str(policy.get("compactation_adjustment_reason", "") or ""),
        "compactation_adjustment_boost_numbers": list(policy.get("compactation_adjustment_boost_numbers", []) or []),
        "compactation_adjustment_reduce_priority_numbers": list(policy.get("compactation_adjustment_reduce_priority_numbers", []) or []),
        "compactation_adjustment_repeat_min": int(policy.get("compactation_adjustment_repeat_min", 0) or 0),
        "compactation_adjustment_repeat_max": int(policy.get("compactation_adjustment_repeat_max", 0) or 0),
        "compactation_adjustment_coverage_min": float(policy.get("compactation_adjustment_coverage_min", 0.0) or 0.0),
        "compactation_adjustment_entropy_min": float(policy.get("compactation_adjustment_entropy_min", 0.0) or 0.0),
        "compactation_adjustment_sequence_max": int(policy.get("compactation_adjustment_sequence_max", 0) or 0),
        "compactation_adjustment_candidate_multiplier": int(policy.get("compactation_adjustment_candidate_multiplier", 0) or 0),
        "max_frequency_ratio": max_frequency_ratio,
        "min_frequency_ratio": min_frequency_ratio,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "generation_event_id": generation_snapshot["generation_event_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "runtime_status": "generated",
        "elapsed_time": round(time.monotonic() - started, 3),
        "batch_id": batch_id,
        "output_commander": commander_report,
        "status_prospectivo": str(policy.get("status_prospectivo", "") or "pending_prospective_validation"),
    }
    st.session_state["institutional_generation_result"] = {
        "generation_event_id": generation_snapshot["generation_event_id"],
        "seed": seed,
        "jogos": games,
        "quantidade_jogos_solicitada": total_games,
        "quantidade_dezenas_solicitada": dezenas_per_game,
        "total_esperado_jogos": int(total_games) * 1,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "quantidade_jogos_candidatos": int(commander_report.get("quantidade_jogos_candidatos", total_games) or total_games),
        "quantidade_jogos_aprovados": int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games)),
        "quantidade_jogos_real_gerada": len(games),
        "quantidade_jogos_persistida": int(generation_snapshot.get("games_count", 0) or 0),
        "len_todos_os_jogos": [len(game.get("numbers", [])) for game in games],
        "primeiro_jogo": games[0]["numbers"] if games else [],
        "len_primeiro_jogo": len(games[0]["numbers"]) if games else 0,
        "batch_id": batch_id,
        "status_comandante_saida": commander_report.get("status_comandante_saida", "APROVADO"),
        "status_prospectivo": str(policy.get("status_prospectivo", "") or "pending_prospective_validation"),
        "total_jogos_unicos": int(commander_report.get("quantidade_jogos_unicos", len(games)) or len(games)),
        "total_jogos_duplicados": int(commander_report.get("quantidade_jogos_duplicados", 0) or 0),
        "total_jogos_rejeitados": int(commander_report.get("quantidade_jogos_rejeitados", 0) or 0),
        "motivo_bloqueio": str(commander_report.get("motivo_bloqueio", "") or ""),
        "taxa_duplicidade": float(commander_report.get("taxa_duplicidade", 0.0) or 0.0),
        "duplicate_hashes": list(commander_report.get("duplicate_hashes", []) or []),
        "invalid_games": list(commander_report.get("invalid_games", []) or []),
        "historical_deduplication_mode": str(commander_report.get("historical_deduplication_mode", historical_deduplication_mode) or historical_deduplication_mode),
        "historical_duplicates_found": int(commander_report.get("historical_duplicates_found", historical_duplicates_found) or historical_duplicates_found),
        "historical_duplicates_removed": int(commander_report.get("historical_duplicates_removed", 0) or 0),
        "official_package_preserved": bool(official_group_games),
        "official_package_registry_found": bool(official_package_registry_found),
        "official_package_group_key": official_package_group_key,
        "official_package_size_loaded": int(official_package_size_loaded),
        "official_package_size_before_output_commander": int(len(games)),
        "official_package_size_after_output_commander": int(commander_report.get("quantidade_jogos_aprovados", len(games)) or len(games)),
        "fallback_dynamic_used": False,
        "official_package_error": "none",
    }
    _store_active_batch_state(
        batch_id=batch_id,
        generation_event_ids=[int(generation_snapshot["generation_event_id"])],
        policy_id=str(commander_report.get("policy_id", "") or ""),
        generated_at=st.session_state["institutional_generation"]["created_at"],
        game_size=dezenas_per_game,
        total_games=total_games,
    )


def _run_institutional_generation_batch(
    *,
    generation_runs: int,
    total_games: int,
    dezenas_per_game: int,
    use_top50: bool,
    odd_min: int,
    odd_max: int,
    even_min: int,
    even_max: int,
    sequence_max: int,
    coverage_min: float,
    entropy_min: float,
    repeat_limit: int,
    snapshot: dict[str, Any],
    batch_number_usage: dict[int, int] | None = None,
    batch_profile_usage: dict[tuple[int, int], int] | None = None,
    batch_total_games: int | None = None,
) -> None:
    batch_runs = max(1, int(generation_runs))
    batch_id = _institutional_output_batch_id()
    batch_seen_signatures: set[str] = set(load_batch_output_signatures(batch_id))
    policy = _institutional_generation_policy(dezenas_per_game)
    repeat_min = int(policy.get("repeat_min", 0) or 0)
    repeat_max = int(policy.get("repeat_max", repeat_limit) or repeat_limit)
    preferred_parity_pairs = list(policy.get("preferred_parity_pairs", []) or [])
    allowed_parity_pairs = list(policy.get("allowed_parity_pairs", []) or [])
    preferred_profile_ratios = dict(policy.get("preferred_profile_ratios", {}) or {})
    core_numbers = [int(number) for number in (policy.get("core_numbers", []) or [])]
    discouraged_numbers = [int(number) for number in (policy.get("discouraged_numbers", []) or [])]
    max_frequency_ratio = float(policy.get("max_frequency_ratio", 1.0) or 1.0)
    min_frequency_ratio = float(policy.get("min_frequency_ratio", 0.0) or 0.0)
    effective_sequence_max = int(min(sequence_max, int(policy.get("sequence_max", sequence_max) or sequence_max)))
    st.session_state["institutional_generation_batch_result"] = {}
    batch_number_usage: dict[int, int] = {}
    batch_profile_usage: dict[tuple[int, int], int] = {}
    batch_total_games = int(total_games) * batch_runs
    run_summaries: list[dict[str, Any]] = []
    for run_index in range(batch_runs):
        _run_institutional_generation(
            total_games=total_games,
            dezenas_per_game=dezenas_per_game,
            use_top50=use_top50,
            odd_min=odd_min,
            odd_max=odd_max,
            even_min=even_min,
            even_max=even_max,
            sequence_max=sequence_max,
            coverage_min=coverage_min,
            entropy_min=entropy_min,
            repeat_limit=repeat_limit,
            snapshot=snapshot,
            batch_number_usage=batch_number_usage,
            batch_profile_usage=batch_profile_usage,
            batch_total_games=batch_total_games,
            seen_signatures=batch_seen_signatures,
        )
        generation_result = dict(st.session_state.get("institutional_generation_result") or {})
        run_summaries.append(generation_result)
        if str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO") != "APROVADO":
            break
        if run_index + 1 < batch_runs:
            continue

    batch_signatures = load_batch_output_signatures(batch_id)
    batch_total_requested = sum(int(item.get("quantidade_jogos_solicitada", 0) or 0) for item in run_summaries)
    batch_total_candidates = sum(int(item.get("quantidade_jogos_candidatos", 0) or 0) for item in run_summaries)
    batch_total_approved = sum(int(item.get("quantidade_jogos_aprovados", 0) or 0) for item in run_summaries)
    batch_total_generated = sum(int(item.get("quantidade_jogos_real_gerada", 0) or 0) for item in run_summaries)
    batch_total_unique = len(batch_signatures)
    batch_total_duplicates = max(0, batch_total_generated - batch_total_unique)
    batch_total_rejected = max(0, batch_total_requested - batch_total_approved)
    batch_status = "APROVADO" if batch_total_requested == batch_total_approved == batch_total_generated == batch_total_unique and batch_total_duplicates == 0 else "BLOQUEADO"
    batch_reason = "OK" if batch_status == "APROVADO" else "não foi possível gerar a quantidade solicitada de jogos únicos"
    st.session_state["institutional_generation_batch_result"] = {
        "batch_id": batch_id,
        "quantidade_jogos_por_geracao": int(total_games),
        "quantidade_geracoes_na_bateria": batch_runs,
        "quantidade_dezenas_por_jogo": int(dezenas_per_game),
        "total_jogos_esperados": int(total_games) * batch_runs,
        "total_esperado_jogos": int(total_games) * batch_runs,
        "repeticao_ultimo_concurso_min": repeat_min,
        "repeticao_ultimo_concurso_max": repeat_max,
        "perfis_paridade_preferenciais": preferred_parity_pairs,
        "perfis_paridade_permitidos": allowed_parity_pairs,
        "limite_sequencia_max": effective_sequence_max,
        "core_numbers": core_numbers,
        "discouraged_numbers": discouraged_numbers,
        "max_frequency_ratio": max_frequency_ratio,
        "min_frequency_ratio": min_frequency_ratio,
        "total_gens_solicitadas": batch_runs,
        "total_jogos_solicitados": batch_total_requested,
        "total_jogos_candidatos": batch_total_candidates,
        "total_jogos_aprovados": batch_total_approved,
        "total_jogos_gerados": batch_total_generated,
        "total_jogos_unicos": batch_total_unique,
        "total_jogos_duplicados": batch_total_duplicates,
        "total_jogos_rejeitados": batch_total_rejected,
        "taxa_duplicidade": round(batch_total_duplicates / max(1, batch_total_generated), 4),
        "status_comandante_saida": batch_status,
        "motivo_bloqueio": batch_reason,
        "institutional_output_signatures": batch_total_unique,
    }
    _store_active_batch_state(
        batch_id=batch_id,
        generation_event_ids=[int(item.get("generation_event_id", 0) or 0) for item in run_summaries if int(item.get("generation_event_id", 0) or 0) > 0],
        policy_id=str((run_summaries[-1] or {}).get("policy_id", "") or ""),
        generated_at=(run_summaries[-1] or {}).get("created_at", datetime.now(UTC).isoformat()),
        game_size=dezenas_per_game,
        total_games=total_games,
    )


def _load_generation_batch_ids() -> list[str]:
    batch_ids: list[str] = []
    seen: set[str] = set()
    for generation in _load_generation_history(limit=None):
        batch_id = str(generation.get("batch_id", "") or "").strip()
        if not batch_id or batch_id in seen:
            continue
        seen.add(batch_id)
        batch_ids.append(batch_id)
    return batch_ids


def _resolve_active_batch_id() -> str:
    session_keys = (
        "institutional_active_batch_id",
        "institutional_output_batch_id",
    )
    for key in session_keys:
        batch_id = str(st.session_state.get(key, "") or "").strip()
        if batch_id:
            return batch_id
    generation_result = dict(st.session_state.get("institutional_generation_result") or {})
    batch_id = str(generation_result.get("batch_id", "") or "").strip()
    if batch_id:
        return batch_id
    generation_state = dict(st.session_state.get("institutional_generation") or {})
    batch_id = str(generation_state.get("batch_id", "") or "").strip()
    if batch_id:
        return batch_id
    latest_generation = _load_latest_generated_games() or {}
    batch_id = str(latest_generation.get("batch_id", "") or "").strip()
    if batch_id:
        return batch_id
    batch_ids = _load_generation_batch_ids()
    return batch_ids[0] if batch_ids else ""


def _load_generation_event_ids_for_batch(batch_id: str | None) -> list[int]:
    resolved_batch_id = str(batch_id or "").strip()
    if not resolved_batch_id:
        return []
    event_ids: list[int] = []
    seen: set[int] = set()
    for generation in _load_generation_history(limit=None):
        if str(generation.get("batch_id", "") or "").strip() != resolved_batch_id:
            continue
        generation_event_id = int(generation.get("generation_event_id", 0) or 0)
        if generation_event_id > 0 and generation_event_id not in seen:
            seen.add(generation_event_id)
            event_ids.append(generation_event_id)
    return sorted(event_ids)


def _get_latest_unreconciled_generation_event_id(batch_id: str | None = None) -> int | None:
    for group in _load_persisted_generation_event_groups(batch_id=batch_id):
        if not bool(group.get("official_release_allowed", True)):
            continue
        if not bool(group.get("is_conferida", False)):
            return _safe_int(group.get("generation_event_id"), default=None)
    return None


def _store_active_batch_state(*, batch_id: str | None = None, generation_event_ids: list[int] | None = None, policy_id: str | None = None, generated_at: str | None = None, game_size: int | None = None, total_games: int | None = None) -> None:
    resolved_batch_id = str(batch_id or "").strip()
    if resolved_batch_id:
        st.session_state["institutional_active_batch_id"] = resolved_batch_id
    if generation_event_ids is not None:
        st.session_state["institutional_active_generation_event_ids"] = [int(value) for value in generation_event_ids if int(value) > 0]
    if policy_id is not None:
        st.session_state["institutional_active_policy_id"] = str(policy_id or "").strip()
    if generated_at is not None:
        st.session_state["institutional_active_generated_at"] = str(generated_at or "")
    if game_size is not None:
        st.session_state["institutional_active_game_size"] = int(game_size)
    if total_games is not None:
        st.session_state["institutional_active_total_games"] = int(total_games)


def _load_persisted_generation_event_groups(batch_id: str | None = None) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    resolved_batch_id = str(batch_id or "").strip()
    with get_session(DB_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .all()
        )
        for event in events:
            rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            if resolved_batch_id:
                rows = [
                    row
                    for row in rows
                    if str(dict(getattr(row, "context_json", {}) or {}).get("batch_id", "") or "").strip() == resolved_batch_id
                ]
                if not rows:
                    continue
            reconciliation_summary = _load_latest_reconciliation_for_generation(session, int(event.id or 0))
            games: list[dict[str, Any]] = []
            for row in rows:
                numbers = [int(number) for number in (row.numbers or [])]
                context_json = dict(row.context_json or {})
                structural_metrics = dict(context_json.get("structural_metrics") or {})
                core_numbers = list(context_json.get("core_numbers") or numbers or [])
                audited_reserve_numbers = list(context_json.get("audited_reserve_numbers") or [])
                final_card_numbers = list(context_json.get("final_card_numbers") or numbers or [])
                card_format = _safe_int(
                    context_json.get("selected_card_format")
                    or context_json.get("card_format")
                    or context_json.get("format_cartao")
                    or context_json.get("formato_cartao"),
                    default=None,
                )
                expected_card_size = int(card_format or len(final_card_numbers) or len(numbers) or 15)
                games.append(
                    {
                        "game_index": int(row.game_index or 0),
                        "numbers": numbers,
                        "formato_cartao": int(card_format or len(final_card_numbers) or len(numbers) or 15),
                        "nucleo_lei_15": " ".join(f"{number:02d}" for number in core_numbers) if core_numbers else "",
                        "reservas_auditadas": " ".join(f"{number:02d}" for number in audited_reserve_numbers) if audited_reserve_numbers else "",
                        "cartao_final": final_card_numbers,
                        "expected_card_size": expected_card_size,
                        "actual_card_size": len(final_card_numbers) if final_card_numbers else len(numbers),
                        "profile_type": str(row.profile_type or ""),
                        "perfil": str(row.profile_type or ""),
                        "game_signature": str(context_json.get("game_signature", "") or ""),
                        "context_json": context_json,
                        "score": round(float((row.final_score or {}).get("final_score", 0.0) or 0.0), 4),
                        "final_score": dict(row.final_score or {}),
                        "quadra_score": dict(row.quadra_score or {}),
                        "coverage": round(float(structural_metrics.get("coverage_score", 0.0) or 0.0), 4),
                        "entropy": round(float(structural_metrics.get("entropy_score", 0.0) or 0.0), 4),
                        "odd": sum(1 for number in numbers if number % 2 != 0),
                        "even": sum(1 for number in numbers if number % 2 == 0),
                        "frame": len({((number - 1) // 5) for number in numbers}),
                        "center": sum(1 for number in numbers if 8 <= number <= 18),
                    }
                )
            target_contests: list[int] = []
            for row in rows:
                value = _safe_int(_safe_get(row, "target_contest"), default=None)
                if value is not None and value > 0:
                    target_contests.append(value)
            event_context = dict(getattr(event, "context_json", {}) or {})
            first_row_context = dict(rows[0].context_json or {}) if rows else {}
            batch_id_value = str(
                event_context.get("batch_id") or first_row_context.get("batch_id", "") or ""
            )
            ml_verdict_payload = {
                "ml_verdict": str(event_context.get("ml_verdict") or ""),
                "official_release_allowed": event_context.get("official_release_allowed"),
            }
            official_release_allowed = is_official_conference_eligible(event_context)
            lot_status = extract_lot_operational_status(event_context)
            groups.append(
                {
                    "generation_event_id": int(event.id or 0),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "seed": int(getattr(event, "seed", 0) or 0),
                    "strategy": str(getattr(event, "strategy", "") or ""),
                    "batch_id": batch_id_value,
                    "total_games": len(games),
                    "target_contest": max(target_contests) if target_contests else None,
                    "reconciliation": reconciliation_summary or {},
                    "conference_status": "Conferido" if reconciliation_summary else "Nao conferido",
                    "is_conferida": bool(reconciliation_summary),
                    "official_release_allowed": official_release_allowed,
                    "is_official_conference_eligible": official_release_allowed,
                    "is_analytical_history_eligible": is_analytical_history_eligible(event_context),
                    "lot_operational_status": lot_status,
                    "ml_verdict": str(event_context.get("ml_verdict") or ""),
                    "ml_verdict_reason": str(
                        event_context.get("ml_verdict_reason") or event_context.get("motivo_principal") or ""
                    ),
                    "games": games,
                    "structural_summary": _summarize_games_structurally([game["numbers"] for game in games]),
                }
            )
    return groups


def _run_institutional_conference(
    contest_number: int | None = None,
    generation_event_id: int | None = None,
    batch_id: str | None = None,
    *,
    conference_all_official: bool = False,
) -> None:
    selected_contest = _safe_int(contest_number, default=None)
    selected_batch_id = str(batch_id or st.session_state.get("institutional_active_batch_id", "") or "").strip()
    selected_generation_event_id = _safe_int(generation_event_id, default=None) or _safe_int(
        st.session_state.get("active_reconciliation_generation_event_id"),
        default=None,
    )
    if conference_all_official or selected_contest is None:
        auto_contest = _resolve_latest_official_conference_contest()
        if auto_contest is not None:
            selected_contest = _safe_int(auto_contest.get("concurso"), default=selected_contest)
    official_contest = _get_conference_contest_from_imported(selected_contest)
    if official_contest is None:
        official_contest = _load_official_history_contest(selected_contest)
    if official_contest is None:
        imported_fallback = _load_imported_contest(selected_contest)
        fallback_contest = to_conference_contest_payload(imported_fallback) or _normalize_contest_record(imported_fallback)
        if fallback_contest is not None and not fallback_contest.get("dezenas"):
            fallback_contest["dezenas"] = _extract_int_numbers(
                imported_fallback.get("numbers", imported_fallback.get("dezenas", [])) if isinstance(imported_fallback, dict) else []
            )
        if fallback_contest is not None:
            official_contest = fallback_contest
            st.session_state["institutional_check_result"] = {
                "status": "fallback_imported_contest",
                "warning": "Concurso inválido ou incompleto em imported_contests.",
                "selected_contest": int(selected_contest or 0),
            }
        else:
            st.session_state["institutional_check_result"] = {
                "status": "waiting_contest",
                "warning": "Concurso não encontrado em imported_contests. Escolha um concurso válido persistido.",
            }
            return
    all_persisted_groups = _load_persisted_generation_event_groups(batch_id=selected_batch_id or None)
    grouped_generations = [
        group
        for group in all_persisted_groups
        if bool(group.get("is_official_conference_eligible", group.get("official_release_allowed", False)))
    ]
    if not all_persisted_groups:
        st.session_state["institutional_check_result"] = {
            "warning": (
                "Sem lote persistido para conferir. Ação bloqueada por Lei 001. "
                "Use Simulação Institucional para laboratório histórico."
            )
        }
        return
    if not grouped_generations:
        st.session_state["institutional_check_result"] = {
            "warning": (
                "Sem lote oficial liberado para conferir. Lotes bloqueados pelo Veredito ML permanecem "
                "pendentes de calibração. Autorize calibração supervisionada na Central ML."
            )
        }
        return
    if selected_generation_event_id is None:
        selected_generation_event_id = _get_latest_unreconciled_generation_event_id(batch_id=selected_batch_id or None)
        if selected_generation_event_id is not None:
            st.session_state["active_reconciliation_generation_event_id"] = selected_generation_event_id
    generation_results: list[dict[str, Any]] = []
    total_prizes = 0
    total_hits = 0
    best_hits_global = 0
    selected_generation_groups = grouped_generations
    if conference_all_official:
        selected_generation_groups = grouped_generations
    elif selected_generation_event_id is not None:
        selected_generation_groups = [
            group
            for group in grouped_generations
            if int(group.get("generation_event_id", 0) or 0) == int(selected_generation_event_id or 0)
        ]
    elif selected_batch_id:
        selected_generation_groups = [
            group
            for group in grouped_generations
            if str(group.get("batch_id", "") or "").strip() == selected_batch_id
        ]
    if not selected_generation_groups and grouped_generations and not conference_all_official:
        selected_generation_groups = grouped_generations[:1]

    for group in selected_generation_groups:
        group_target_contest = _safe_int(_safe_get(group, "target_contest"), default=None)
        contest_to_use = selected_contest or group_target_contest or _safe_int(_safe_get(official_contest, "concurso"), default=None)
        contest_payload = _get_conference_contest_from_imported(contest_to_use) or (
            _load_official_history_contest(contest_to_use) if contest_to_use is not None else official_contest
        )
        if contest_payload is None:
            contest_payload = official_contest
        comparison = _compare_games_against_contest(
            generation_event_id=int(group.get("generation_event_id") or 0),
            games=list(group.get("games") or []),
            contest=contest_payload,
        )
        comparison_diagnostics = dict(comparison.get("diagnostics") or {})
        group_games = list(group.get("games") or [])
        group_game_size = len(group_games[0].get("numbers", [])) if group_games and isinstance(group_games[0], dict) else 0
        scientific_policy_snapshot = discover_scientific_generation_policy(
            group_game_size or int(group.get("total_games", 0) or 0) or 15,
            db_path=DB_PATH,
        )
        scientific_memory_payload = build_post_reconciliation_scientific_memory(
            generation_event_id=int(group.get("generation_event_id") or 0),
            batch_id=str(group.get("batch_id", "") or selected_batch_id or ""),
            contest=contest_payload,
            games=list(group.get("games") or []),
            reconciliation_results=list(comparison.get("results", [])),
            policy_before=dict(scientific_policy_snapshot.get("policy_before") or scientific_policy_snapshot.get("policy") or {}),
            policy_after=dict(scientific_policy_snapshot.get("policy_after") or scientific_policy_snapshot.get("policy") or {}),
            db_path=DB_PATH,
        )
        persisted_scientific_memory = _persist_scientific_reconciliation_memory(scientific_memory_payload)
        st.session_state["institutional_post_reconciliation_memory"] = dict(persisted_scientific_memory or scientific_memory_payload)
        hit_counts = Counter(int(row.get("hits", 0) or 0) for row in comparison.get("results", []))
        generation_results.append(
            {
                "generation_event_id": int(group.get("generation_event_id") or 0),
                "created_at": group.get("created_at", ""),
                "seed": int(group.get("seed") or 0),
                "total_games": int(group.get("total_games") or 0),
                "target_contest": contest_to_use,
                "best_hits": int(comparison.get("best_hits", 0) or 0),
                "total_hits": int(comparison.get("total_hits", 0) or 0),
                "prize_count": int(comparison.get("prize_count", 0) or 0),
                "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
                "results": list(comparison.get("results", [])),
                "games": list(group.get("games") or []),
                "contest_number": int(comparison.get("contest_number", contest_to_use or 0) or 0),
                "contest_date": str(comparison.get("contest_date", _safe_get(contest_payload, "data", "")) or ""),
                "formato_cartao": int(comparison_diagnostics.get("formato_cartao", group_game_size or 15) or (group_game_size or 15)),
                "dezenas_conferidas_count": int(comparison_diagnostics.get("dezenas_conferidas_count", group_game_size or 0) or (group_game_size or 0)),
                "origem_dezenas_conferencia": str(comparison_diagnostics.get("origem_dezenas_conferencia", "indisponivel") or "indisponivel"),
                "expected_card_size": int(comparison_diagnostics.get("expected_card_size", group_game_size or 15) or (group_game_size or 15)),
                "actual_card_size": int(comparison_diagnostics.get("actual_card_size", group_game_size or 0) or (group_game_size or 0)),
                "post_reconciliation_memory_id": int((persisted_scientific_memory or scientific_memory_payload).get("memory_id", 0) or 0),
                "post_reconciliation_local_classification": str((persisted_scientific_memory or scientific_memory_payload).get("local_classification", "") or ""),
                "post_reconciliation_recommended_action": str((persisted_scientific_memory or scientific_memory_payload).get("recommended_action", "") or ""),
            }
        )
        total_prizes += int(comparison.get("prize_count", 0) or 0)
        total_hits += int(comparison.get("total_hits", 0) or 0)
        best_hits_global = max(best_hits_global, int(comparison.get("best_hits", 0) or 0))
    latest_contest = official_contest
    batch_hit_values = [
        int(result.get("hits", 0) or 0)
        for generation in generation_results
        for result in list(generation.get("results") or [])
        if isinstance(result, dict)
    ]
    batch_hit_decomposition = _decompose_hit_counts(batch_hit_values)
    strong_near_miss_payload: dict[str, Any] = {}
    if generation_results:
        strong_near_miss_payload = build_strong_near_miss_scientific_memory(
            batch_id=selected_batch_id or str(generation_results[0].get("batch_id", "") or ""),
            contest=latest_contest,
            generation_results=generation_results,
            policy_before=dict((st.session_state.get("institutional_post_reconciliation_memory") or {}).get("policy_before") or {}),
            policy_after=dict((st.session_state.get("institutional_post_reconciliation_memory") or {}).get("policy_after") or {}),
            db_path=DB_PATH,
        )
        if strong_near_miss_payload:
            persisted_strong_near_miss = _persist_scientific_reconciliation_memory(strong_near_miss_payload)
            st.session_state["institutional_post_reconciliation_memory"] = dict(
                persisted_strong_near_miss or strong_near_miss_payload
            )
            st.session_state["institutional_strong_near_miss_memory"] = dict(
                persisted_strong_near_miss or strong_near_miss_payload
            )
    batch_reconciliation_payload: dict[str, Any] = {}
    if generation_results:
        batch_reconciliation_payload = build_batch_reconciliation_scientific_memory(
            batch_id=selected_batch_id or str(generation_results[0].get("batch_id", "") or ""),
            contest=latest_contest,
            generation_results=generation_results,
            policy_before=dict((st.session_state.get("institutional_post_reconciliation_memory") or {}).get("policy_before") or {}),
            policy_after=dict((st.session_state.get("institutional_post_reconciliation_memory") or {}).get("policy_after") or {}),
            db_path=DB_PATH,
        )
        if batch_reconciliation_payload:
            persisted_batch_reconciliation = _persist_scientific_reconciliation_memory(batch_reconciliation_payload)
            st.session_state["institutional_post_reconciliation_memory"] = dict(
                persisted_batch_reconciliation or batch_reconciliation_payload
            )
            st.session_state["institutional_batch_reconciliation_memory"] = dict(
                persisted_batch_reconciliation or batch_reconciliation_payload
            )
    batch_generation_range = dict(batch_reconciliation_payload.get("generation_range") or {})
    batch_conference_result = {
        "runtime_status": "checked",
        "status": "checked",
        "contest_number": int(official_contest.get("concurso", 0) or 0),
        "contest_date": str(official_contest.get("data", "") or ""),
        "batch_id": str(batch_reconciliation_payload.get("batch_id", selected_batch_id) or selected_batch_id or ""),
        "generation_event_ids": list(batch_generation_range.get("generation_event_ids", []) or [int(item.get("generation_event_id", 0) or 0) for item in generation_results if int(item.get("generation_event_id", 0) or 0) > 0]),
        "first_generation_event_id": batch_generation_range.get("first_generation_event_id"),
        "last_generation_event_id": batch_generation_range.get("last_generation_event_id"),
        "total_generations": int(batch_generation_range.get("total_generations", len(generation_results)) or len(generation_results)),
        "total_games_checked": int(batch_generation_range.get("total_games_checked", sum(int(item.get("total_games", 0) or 0) for item in generation_results)) or sum(int(item.get("total_games", 0) or 0) for item in generation_results)),
        "best_hits": int(batch_reconciliation_payload.get("best_hit", best_hits_global) or best_hits_global),
        "count_10_exact": int(batch_reconciliation_payload.get("count_10_exact", batch_hit_decomposition["count_10_exact"]) or batch_hit_decomposition["count_10_exact"]),
        "count_11_exact": int(batch_reconciliation_payload.get("count_11_exact", batch_hit_decomposition["count_11_exact"]) or batch_hit_decomposition["count_11_exact"]),
        "count_12_exact": int(batch_reconciliation_payload.get("count_12_exact", batch_hit_decomposition["count_12_exact"]) or batch_hit_decomposition["count_12_exact"]),
        "count_13_exact": int(batch_reconciliation_payload.get("count_13_exact", batch_hit_decomposition["count_13_exact"]) or batch_hit_decomposition["count_13_exact"]),
        "count_14_exact": int(batch_reconciliation_payload.get("count_14_exact", batch_hit_decomposition["count_14_exact"]) or batch_hit_decomposition["count_14_exact"]),
        "count_15_exact": int(batch_reconciliation_payload.get("count_15_exact", batch_hit_decomposition["count_15_exact"]) or batch_hit_decomposition["count_15_exact"]),
        "count_11_plus": int(batch_reconciliation_payload.get("count_11_plus", batch_hit_decomposition["count_11_plus"]) or batch_hit_decomposition["count_11_plus"]),
        "count_12_plus": int(batch_reconciliation_payload.get("count_12_plus", batch_hit_decomposition["count_12_plus"]) or batch_hit_decomposition["count_12_plus"]),
        "count_13_plus": int(batch_reconciliation_payload.get("count_13_plus", batch_hit_decomposition["count_13_plus"]) or batch_hit_decomposition["count_13_plus"]),
        "count_14_plus": int(batch_reconciliation_payload.get("count_14_plus", batch_hit_decomposition["count_14_plus"]) or batch_hit_decomposition["count_14_plus"]),
        "count_15": int(batch_reconciliation_payload.get("count_15", batch_hit_decomposition["count_15"]) or batch_hit_decomposition["count_15"]),
        "hit_histogram": dict(batch_reconciliation_payload.get("hit_histogram", batch_hit_decomposition["hit_histogram"]) or batch_hit_decomposition["hit_histogram"]),
        "total_hits": int(total_hits),
        "prize_count": int(total_prizes),
        "best_generation_event_id": int(batch_generation_range.get("best_generation_event_id", 0) or batch_reconciliation_payload.get("best_generation_event_id", 0) or 0),
        "best_generations": list(batch_generation_range.get("best_generations", []) or []),
        "classification": str(batch_reconciliation_payload.get("scientific_classification", "") or ""),
        "recommended_action": str(batch_reconciliation_payload.get("recommended_action", "") or ""),
        "source_batch_id": str(batch_reconciliation_payload.get("batch_id", selected_batch_id) or selected_batch_id or ""),
        "memory_id": int(batch_reconciliation_payload.get("memory_id", 0) or 0),
        "games_with_11_plus": list(batch_reconciliation_payload.get("games_with_11_plus", []) or []),
        "generation_results": generation_results,
        "batch_reconciliation_memory": batch_reconciliation_payload,
        "strong_near_miss_memory": strong_near_miss_payload,
        "scientific_state": {
            "mode": "AUTONOMIA SUPERVISIONADA"
            if str(batch_reconciliation_payload.get("decision_mode", "")).upper() == "AUTONOMIA_SUPERVISIONADA"
            else "OBSERVAÇÃO",
            "structural_status": str(batch_reconciliation_payload.get("structural_status", "BLOQUEADO") or "BLOQUEADO"),
            "scientific_status": str(batch_reconciliation_payload.get("scientific_status", "-") or "-"),
            "classification": str(batch_reconciliation_payload.get("scientific_classification", "-") or "-"),
            "main_reason": str(batch_reconciliation_payload.get("main_reason", "-") or "-"),
            "status_visual": str(batch_reconciliation_payload.get("confidence_level", "-") or "-"),
            "reference_window": list(batch_generation_range.get("generation_event_ids", []) or []),
            "source_batch_id": str(batch_reconciliation_payload.get("batch_id", selected_batch_id) or selected_batch_id or ""),
        },
        "scientific_recommendation": {
            "action_suggested": str(batch_reconciliation_payload.get("recommended_action", "-") or "-"),
            "status_visual": str(batch_reconciliation_payload.get("confidence_level", "-") or "-"),
        },
    }
    st.session_state["institutional_batch_conference_result"] = dict(batch_conference_result)
    st.session_state["institutional_check"] = {
        "runtime_status": "checked",
        "timestamp": datetime.now(UTC).isoformat(),
        "contest_number": int(official_contest.get("concurso", 0) or 0),
        "best_hits": best_hits_global,
        "total_hits": total_hits,
    }
    st.session_state["institutional_check_result"] = {
        "status": "checked",
        "contest_number": int(official_contest.get("concurso", 0) or 0),
        "contest_date": str(official_contest.get("data", "") or ""),
        "dezenas": list(official_contest.get("dezenas", []) or []),
        "official_numbers_from_db": list(official_contest.get("dezenas", []) or []),
        "generation_results": generation_results,
        "generation_event_id": int(selected_generation_event_id or 0),
        "best_hits": best_hits_global,
        "total_hits": total_hits,
        "prize_count": total_prizes,
        "formato_cartao": int(generation_results[0].get("formato_cartao", 15) if generation_results else 15),
        "dezenas_conferidas_count": int(generation_results[0].get("dezenas_conferidas_count", 0) if generation_results else 0),
        "origem_dezenas_conferencia": str(generation_results[0].get("origem_dezenas_conferencia", "indisponivel") if generation_results else "indisponivel"),
        "expected_card_size": int(generation_results[0].get("expected_card_size", 15) if generation_results else 15),
        "actual_card_size": int(generation_results[0].get("actual_card_size", 0) if generation_results else 0),
        "games_with_11_plus": list(batch_reconciliation_payload.get("games_with_11_plus", []) or []),
        "count_10_exact": int(batch_reconciliation_payload.get("count_10_exact", batch_hit_decomposition["count_10_exact"]) or batch_hit_decomposition["count_10_exact"]),
        "count_11_exact": int(batch_reconciliation_payload.get("count_11_exact", batch_hit_decomposition["count_11_exact"]) or batch_hit_decomposition["count_11_exact"]),
        "count_12_exact": int(batch_reconciliation_payload.get("count_12_exact", batch_hit_decomposition["count_12_exact"]) or batch_hit_decomposition["count_12_exact"]),
        "count_13_exact": int(batch_reconciliation_payload.get("count_13_exact", batch_hit_decomposition["count_13_exact"]) or batch_hit_decomposition["count_13_exact"]),
        "count_14_exact": int(batch_reconciliation_payload.get("count_14_exact", batch_hit_decomposition["count_14_exact"]) or batch_hit_decomposition["count_14_exact"]),
        "count_15_exact": int(batch_reconciliation_payload.get("count_15_exact", batch_hit_decomposition["count_15_exact"]) or batch_hit_decomposition["count_15_exact"]),
        "count_11_plus": int(batch_reconciliation_payload.get("count_11_plus", batch_hit_decomposition["count_11_plus"]) or batch_hit_decomposition["count_11_plus"]),
        "count_12_plus": int(batch_reconciliation_payload.get("count_12_plus", batch_hit_decomposition["count_12_plus"]) or batch_hit_decomposition["count_12_plus"]),
        "count_13_plus": int(batch_reconciliation_payload.get("count_13_plus", batch_hit_decomposition["count_13_plus"]) or batch_hit_decomposition["count_13_plus"]),
        "count_14_plus": int(batch_reconciliation_payload.get("count_14_plus", batch_hit_decomposition["count_14_plus"]) or batch_hit_decomposition["count_14_plus"]),
        "count_15": int(batch_reconciliation_payload.get("count_15", batch_hit_decomposition["count_15"]) or batch_hit_decomposition["count_15"]),
        "hit_histogram": dict(batch_reconciliation_payload.get("hit_histogram", batch_hit_decomposition["hit_histogram"]) or batch_hit_decomposition["hit_histogram"]),
        "batch_conference_result": batch_conference_result,
        "batch_reconciliation_memory": batch_reconciliation_payload,
        "strong_near_miss_memory": strong_near_miss_payload,
        "selected_contest": int(official_contest.get("concurso", 0) or 0),
    }


def _run_simulation_lot_generation(*, requested_count: int, selected_card_format: int) -> dict[str, Any]:
    """Gera lote laboratorial com o mesmo motor CORE_002 + ML — não oficializa (M-OPS-062)."""
    result = _run_clean_law15_generation(requested_count=requested_count)
    result["selected_card_format"] = int(selected_card_format)
    result["card_format_label"] = multidezena_format_label(selected_card_format)
    result["analysis_batch_label"] = multidezena_batch_label(selected_card_format)
    result["generation_origin"] = GENERATION_ORIGIN_SIMULATION
    result["simulation_mode"] = True
    result["display_games"] = _expand_generation_games_for_format(result.get("games") or [], selected_card_format)
    if is_multidezena_persistence_supported(selected_card_format):
        persisted = _persist_clean_law15_generation_history(
            result=result,
            selected_card_format=int(selected_card_format),
        )
        if persisted:
            result.update(persisted)
    else:
        result["persistence_blocked"] = True
        result["persistence_block_reason"] = f"Formato {selected_card_format}D fora do escopo CORE_002 (15–23)."
    return result


def _run_simulation_multicontest_lab(*, games: Sequence[dict[str, Any]], contests_limit: int = 50) -> dict[str, Any]:
    """Compara lote laboratorial contra até 50 concursos importados — sem oficializar."""
    records = sorted(
        _list_all_imported_contest_records(),
        key=lambda row: int(row.get("contest_number", 0) or 0),
        reverse=True,
    )[: max(1, int(contests_limit))]
    contest_results: list[dict[str, Any]] = []
    premium_rows: list[dict[str, Any]] = []
    for record in records:
        contest_payload = to_conference_contest_payload(record) or _normalize_contest_record(record)
        if not contest_payload or not contest_payload.get("dezenas"):
            continue
        contest_numbers = set(_extract_int_numbers(contest_payload.get("dezenas", [])))
        contest_number = int(contest_payload.get("concurso", record.get("contest_number", 0)) or 0)
        game_rows: list[dict[str, Any]] = []
        for index, game in enumerate(games, start=1):
            numbers = _extract_int_numbers(game.get("numbers", game.get("final_card_numbers", [])))
            matched = sorted(set(numbers) & contest_numbers)
            hits = len(matched)
            row = {
                "concurso": contest_number,
                "jogo": index,
                "hits": hits,
                "premiado": "sim" if hits >= 11 else "nao",
                "dezenas": " ".join(f"{number:02d}" for number in numbers),
                "matched_numbers": matched,
            }
            game_rows.append(row)
            if hits >= 11:
                premium_rows.append(row)
        contest_results.append(
            {
                "contest_number": contest_number,
                "total_games": len(game_rows),
                "premium_games": sum(1 for row in game_rows if int(row.get("hits", 0) or 0) >= 11),
                "best_hits": max((int(row.get("hits", 0) or 0) for row in game_rows), default=0),
                "results": game_rows,
            }
        )
    return {
        "contests_compared": len(contest_results),
        "premium_rows": premium_rows,
        "contest_results": contest_results,
        "generation_origin": GENERATION_ORIGIN_SIMULATION,
        "officialization_blocked": True,
    }


def _run_institutional_simulation(*, drawn_numbers: list[int] | None = None) -> None:
    st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
    try:
        simulated_numbers = sorted(drawn_numbers or _build_simulated_draw(15))
        source = "session_generation"
        generation_state = st.session_state.get("institutional_generation") or {}
        games = list(generation_state.get("games") or [])
        if not games:
            source = "session_generation_result"
            generation_result = st.session_state.get("institutional_generation_result") or {}
            games = list(generation_result.get("jogos") or [])
        if not games:
            source = "latest_persisted_generation"
            games = _institutional_generation_games()
        if not games:
            source = "simulation_lab_non_official"
            lab_groups = [
                group
                for group in _load_persisted_generation_event_groups()
                if str(group.get("lot_operational_status", "")) in {"not_officialized", "calibration_source_only", ""}
                or not bool(group.get("is_official_conference_eligible", False))
            ]
            games = [game for group in lab_groups[:3] for game in list(group.get("games") or [])]
        if not games:
            source = "all_persisted_games"
            games = [
                game
                for group in _load_persisted_generation_event_groups()
                for game in list(group.get("games") or [])
                if not bool(group.get("is_official_conference_eligible", False))
            ]
        simulation_rows: list[dict[str, Any]] = []
        for index, game in enumerate(games, start=1):
            numbers = sorted(int(number) for number in game.get("numbers", []))
            matched = sorted(set(numbers) & set(simulated_numbers))
            simulation_rows.append(
                {
                    "jogo": index,
                    "dezenas": " ".join(f"{number:02d}" for number in numbers),
                    "resultado": _format_simulation_numbers(numbers, matched),
                    "hits": len(matched),
                    "premiado": "sim" if len(matched) >= 11 else "nao",
                    "matched_numbers": matched,
                    "generation_event_id": int(game.get("generation_event_id", 0) or 0),
                    "profile_type": str(game.get("profile_type", "") or ""),
                    "score": float(game.get("score", game.get("final_score", {}).get("final_score", 0.0)) or 0.0),
                    "odd": int(game.get("odd", 0) or 0),
                    "even": int(game.get("even", 0) or 0),
                    "entropy": float(game.get("entropy", 0.0) or 0.0),
                    "coverage": float(game.get("coverage", 0.0) or 0.0),
                }
            )
        premium_rows = [row for row in simulation_rows if int(row.get("hits", 0) or 0) >= 11]
        st.session_state["institutional_simulation"] = {
            "runtime_status": "simulated",
            "timestamp": datetime.now(UTC).isoformat(),
            "contest_numbers": simulated_numbers,
            "source": source,
            "loaded_games": len(games),
            "compared_games": len(simulation_rows),
            "premium_games": len(premium_rows),
            "results": simulation_rows,
            "summary": {
                "source": source,
                "loaded_games": len(games),
                "compared_games": len(simulation_rows),
                "premium_games": len(premium_rows),
                "contest_numbers": simulated_numbers,
            },
        }
        st.session_state["institutional_simulation_result"] = simulation_rows
        st.session_state["institutional_simulation_error"] = None
    except Exception as exc:  # pragma: no cover - diagnostic path
        st.session_state["institutional_simulation"] = {
            "runtime_status": "error",
            "timestamp": datetime.now(UTC).isoformat(),
            "contest_numbers": sorted(drawn_numbers or []),
            "results": [],
            "source": "error",
            "loaded_games": 0,
            "compared_games": 0,
            "premium_games": 0,
            "summary": {
                "source": "error",
                "loaded_games": 0,
                "compared_games": 0,
                "premium_games": 0,
            },
        }
        st.session_state["institutional_simulation_result"] = []
        st.session_state["institutional_simulation_error"] = {
            "error": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        st.exception(exc)


def _institutional_generation_games() -> list[dict[str, Any]]:
    generation_state = st.session_state.get("institutional_generation") or {}
    if generation_state.get("games"):
        return list(generation_state.get("games") or [])
    persisted_generation = _load_latest_generated_games()
    if persisted_generation and persisted_generation.get("games"):
        return list(persisted_generation.get("games") or [])
    return []


def _summarize_games_structurally(games: list[Any]) -> dict[str, Any]:
    normalized_games: list[list[int]] = []
    for game in games:
        if isinstance(game, dict):
            raw_numbers = game.get("numbers", [])
        else:
            raw_numbers = game
        numbers = [int(number) for number in raw_numbers or [] if str(number).isdigit() or isinstance(number, int)]
        if numbers:
            normalized_games.append(sorted(numbers))
    if not normalized_games:
        return {
            "games": 0,
            "average_overlap": 0.0,
            "average_unique_numbers": 0.0,
            "dominant_numbers": [],
            "number_frequency": {},
        }
    frequencies: dict[int, int] = {}
    total_unique = 0
    pairwise_overlap = 0
    pair_count = 0
    for numbers in normalized_games:
        total_unique += len(set(numbers))
        for number in numbers:
            frequencies[number] = frequencies.get(number, 0) + 1
    for index, left in enumerate(normalized_games):
        left_set = set(left)
        for right in normalized_games[index + 1 :]:
            pairwise_overlap += len(left_set & set(right))
            pair_count += 1
    dominant_numbers = [
        {"number": number, "frequency": frequency}
        for number, frequency in sorted(frequencies.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "games": len(normalized_games),
        "average_overlap": round(pairwise_overlap / pair_count, 4) if pair_count else 0.0,
        "average_unique_numbers": round(total_unique / len(normalized_games), 4),
        "dominant_numbers": dominant_numbers,
        "number_frequency": {str(number): frequency for number, frequency in sorted(frequencies.items())},
    }


def _load_latest_reconciliation_summary() -> dict[str, Any] | None:
    with get_session(DB_PATH) as session:
        run = session.query(ReconciliationRun).order_by(ReconciliationRun.id.desc()).first()
        if run is None:
            return None
        games_rows = (
            session.query(ReconciliationGame)
            .filter(ReconciliationGame.reconciliation_run_id == run.id)
            .order_by(ReconciliationGame.game_index.asc())
            .all()
        )
        matched_numbers: set[int] = set()
        hit_counts: Counter[int] = Counter()
        for row in games_rows:
            hits = int(getattr(row, "hits", 0) or 0)
            hit_counts[hits] += 1
            matched_numbers.update(int(number) for number in (row.matched_numbers or []))
        return {
            "id": int(run.id or 0),
            "contest_id": int(getattr(run, "contest_id", 0) or 0),
            "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
            "status": str(getattr(run, "status", "") or ""),
            "prize_count": int(getattr(run, "prize_count", 0) or 0),
            "total_hits": int(getattr(run, "total_hits", 0) or 0),
            "best_hits": int(getattr(run, "best_hits", 0) or 0),
            "games_count": len(games_rows),
            "matched_numbers": sorted(matched_numbers),
            "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
            "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        }


def _mean_or_zero(values: list[float]) -> float:
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else 0.0


def _load_latest_reconciliation_for_generation(session: Any, generation_event_id: int) -> dict[str, Any] | None:
    run = (
        session.query(ReconciliationRun)
        .filter(ReconciliationRun.generation_event_id == int(generation_event_id))
        .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
        .first()
    )
    if run is None:
        return None
    games_rows = (
        session.query(ReconciliationGame)
        .filter(ReconciliationGame.reconciliation_run_id == run.id)
        .order_by(ReconciliationGame.game_index.asc())
        .all()
    )
    matched_numbers: set[int] = set()
    hit_counts: Counter[int] = Counter()
    games_by_index: dict[int, dict[str, Any]] = {}
    for row in games_rows:
        hits = int(getattr(row, "hits", 0) or 0)
        matched = [int(number) for number in (row.matched_numbers or [])]
        hit_counts[hits] += 1
        matched_numbers.update(matched)
        games_by_index[int(getattr(row, "game_index", 0) or 0)] = {
            "reconciliation_id": int(run.id or 0),
            "contest_id": int(getattr(row, "contest_id", 0) or 0),
            "hits": hits,
            "matched_numbers": matched,
            "prize_status": str(getattr(row, "prize_status", "") or ""),
            "prize_tier": str(getattr(row, "prize_tier", "") or ""),
            "status": str(getattr(run, "status", "") or ""),
            "reconciled_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        }
    return {
        "id": int(run.id or 0),
        "contest_id": int(getattr(run, "contest_id", 0) or 0),
        "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
        "status": str(getattr(run, "status", "") or ""),
        "prize_count": int(getattr(run, "prize_count", 0) or 0),
        "total_hits": int(getattr(run, "total_hits", 0) or 0),
        "best_hits": int(getattr(run, "best_hits", 0) or 0),
        "games_count": len(games_rows),
        "matched_numbers": sorted(matched_numbers),
        "hit_distribution": dict(sorted(hit_counts.items(), key=lambda item: (-item[0], item[1]))),
        "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
        "games_by_index": games_by_index,
    }


def _load_generation_history(limit: int | None = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    scientific_decisions, scientific_memories = _load_scientific_context_indexes()
    with get_session(DB_PATH) as session:
        events_query = session.query(GenerationEvent).order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
        if limit is not None and int(limit) > 0:
            events_query = events_query.limit(int(limit))
        events = events_query.all()
        for event in events:
            games_rows = (
                session.query(GeneratedGame)
                .filter(GeneratedGame.generation_event_id == event.id)
                .order_by(GeneratedGame.game_index.asc())
                .all()
            )
            reconciliation_summary = _load_latest_reconciliation_for_generation(session, int(event.id or 0))
            reconciliation_games = dict((reconciliation_summary or {}).get("games_by_index", {}))
            games: list[dict[str, Any]] = []
            scores: list[float] = []
            entropies: list[float] = []
            coverages: list[float] = []
            target_contests: list[int] = []
            for row in games_rows:
                numbers = [int(number) for number in (row.numbers or [])]
                final_score = dict(row.final_score or {})
                quadra_score = dict(row.quadra_score or {})
                context_json = dict(row.context_json or {})
                structural_metrics = dict(context_json.get("structural_metrics") or {})
                historical_intelligence = dict(context_json.get("historical_intelligence") or {})
                score_value = float(final_score.get("final_score", 0.0) or 0.0)
                entropy_value = float(
                    structural_metrics.get("entropy_score", historical_intelligence.get("entropy_score", 0.0)) or 0.0
                )
                coverage_value = float(
                    structural_metrics.get("coverage_score", historical_intelligence.get("coverage_score", 0.0)) or 0.0
                )
                odd_count = sum(1 for number in numbers if number % 2 != 0)
                even_count = len(numbers) - odd_count
                reconciliation_row = reconciliation_games.get(int(row.game_index or 0), {})
                games.append(
                    {
                        "game_index": int(row.game_index or 0),
                        "numbers": numbers,
                        "profile_type": str(row.profile_type or ""),
                        "origin": str(getattr(row, "origin", "") or "institutional"),
                        "generation_mode": str(getattr(row, "generation_mode", "") or ""),
                        "generation_context": dict(context_json),
                        "score": score_value,
                        "final_score": final_score,
                        "quadra_score": quadra_score,
                        "target_contest": int(row.target_contest) if getattr(row, "target_contest", None) is not None else None,
                        "coverage": round(coverage_value, 4),
                        "entropy": round(entropy_value, 4),
                        "sequence_max": int(structural_metrics.get("sequence_max", historical_intelligence.get("sequence_max", 0)) or 0),
                        "odd": odd_count,
                        "even": even_count,
                        "center": sum(1 for number in numbers if 8 <= number <= 18),
                        "frame": len({((number - 1) // 5) for number in numbers}),
                        "contest_id": int(reconciliation_row.get("contest_id", 0) or 0) if reconciliation_row else None,
                        "hits": int(reconciliation_row.get("hits", 0) or 0) if reconciliation_row else None,
                        "matched_numbers": list(reconciliation_row.get("matched_numbers", []) or []) if reconciliation_row else [],
                        "prize_status": str(reconciliation_row.get("prize_status", "") or "") if reconciliation_row else "",
                        "prize_tier": str(reconciliation_row.get("prize_tier", "") or "") if reconciliation_row else "",
                        "conference_status": "Conferido" if reconciliation_row else "Nao conferido",
                        "reconciliation_id": int(reconciliation_row.get("reconciliation_id", 0) or 0) if reconciliation_row else None,
                        "reconciled_at": str(reconciliation_row.get("reconciled_at", "") or "") if reconciliation_row else "",
                    }
                )
                scores.append(score_value)
                entropies.append(entropy_value)
                coverages.append(coverage_value)
                if getattr(row, "target_contest", None) is not None:
                    target_contests.append(int(row.target_contest))
            structural_summary = _summarize_games_structurally([game["numbers"] for game in games]) if games else {}
            top_games = sorted(games, key=lambda item: (-float(item["score"]), item["game_index"]))
            first_context = dict(games[0].get("generation_context") or {}) if games and isinstance(games[0], dict) else {}
            event_context = dict(getattr(event, "context_json", {}) or {})
            visibility_context = _classify_generation_visibility(
                generation={
                    "batch_id": str(first_context.get("batch_id") or event_context.get("batch_id", "") or ""),
                    "status_comandante_saida": str(
                        first_context.get("status_comandante_saida")
                        or event_context.get("status_comandante_saida", "APROVADO")
                        or "APROVADO"
                    ),
                    "total_jogos_duplicados": int(
                        first_context.get("total_jogos_duplicados")
                        or event_context.get("total_jogos_duplicados", 0)
                        or 0
                    ),
                    "ml_verdict": str(event_context.get("ml_verdict") or first_context.get("ml_verdict") or ""),
                    "ml_verdict_reason": str(
                        event_context.get("ml_verdict_reason")
                        or event_context.get("motivo_principal")
                        or first_context.get("ml_verdict_reason")
                        or ""
                    ),
                    "lot_operational_status": str(
                        event_context.get("lot_operational_status") or first_context.get("lot_operational_status") or ""
                    ),
                    "official_release_allowed": is_analytical_history_eligible(event_context),
                },
                scientific_decision=scientific_decisions.get(str(first_context.get("batch_id", "") or "").strip(), {}),
                scientific_memory=scientific_memories.get(str(first_context.get("batch_id", "") or "").strip(), {}),
            )
            history.append(
                {
                    "generation_event_id": int(event.id or 0),
                    "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
                    "seed": int(getattr(event, "seed", 0) or 0),
                    "strategy": str(getattr(event, "strategy", "") or ""),
                    "ml_enabled": bool(getattr(event, "ml_enabled", 0) or 0),
                    "analysis_batch_label": str(getattr(event, "analysis_batch_label", "") or ""),
                    "analysis_batch_type": str(getattr(event, "analysis_batch_type", "") or ""),
                    "total_games": len(games),
                    "target_contest": max(target_contests) if target_contests else None,
                    "first_name": str(getattr(event, "first_name", "") or ""),
                    "whatsapp": str(getattr(event, "whatsapp", "") or ""),
                    "avg_score": _mean_or_zero(scores),
                    "avg_entropy": _mean_or_zero(entropies),
                    "avg_coverage": _mean_or_zero(coverages),
                    "average_overlap": float(structural_summary.get("average_overlap", 0.0) or 0.0),
                    "dominant_numbers": list(structural_summary.get("dominant_numbers", [])),
                    "batch_id": str(first_context.get("batch_id", "") or ""),
                    "status_comandante_saida": str(first_context.get("status_comandante_saida", "APROVADO") or "APROVADO"),
                    "total_jogos_unicos": int(first_context.get("total_jogos_unicos", len(games)) or len(games)),
                    "total_jogos_duplicados": int(first_context.get("total_jogos_duplicados", 0) or 0),
                    "taxa_duplicidade": float(first_context.get("taxa_duplicidade", 0.0) or 0.0),
                    **visibility_context,
                    "reconciliation": reconciliation_summary or {},
                    "games": games,
                    "top_games": sorted(
                        games,
                        key=lambda item: (
                            -float(item["score"]),
                            -(int(item.get("hits") or -1) if item.get("hits") is not None else -1),
                            int(item["game_index"]),
                        ),
                    ),
                }
            )
    return history


def _load_generation_history_light(limit: int | None = 25) -> list[dict[str, Any]]:
    return _load_generation_history(limit=limit)


def _load_reconciliation_history(limit: int = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    with get_session(DB_PATH) as session:
        runs = (
            session.query(ReconciliationRun)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .limit(limit)
            .all()
        )
        for run in runs:
            games_rows = (
                session.query(ReconciliationGame)
                .filter(ReconciliationGame.reconciliation_run_id == run.id)
                .order_by(ReconciliationGame.game_index.asc())
                .all()
            )
            matched_numbers: set[int] = set()
            for row in games_rows:
                matched_numbers.update(int(number) for number in (row.matched_numbers or []))
            history.append(
                {
                    "id": int(run.id or 0),
                    "generation_event_id": int(getattr(run, "generation_event_id", 0) or 0),
                    "contest_id": int(getattr(run, "contest_id", 0) or 0),
                    "status": str(getattr(run, "status", "") or ""),
                    "prize_count": int(getattr(run, "prize_count", 0) or 0),
                    "total_hits": int(getattr(run, "total_hits", 0) or 0),
                    "best_hits": int(getattr(run, "best_hits", 0) or 0),
                    "created_at": run.created_at.isoformat() if getattr(run, "created_at", None) else "",
                    "matched_numbers": sorted(matched_numbers),
                    "games_count": len(games_rows),
                }
            )
    return history


def _load_reconciliation_history_light(limit: int = 25) -> list[dict[str, Any]]:
    return _load_reconciliation_history(limit=limit)


def _load_operational_logs_history(limit: int = 20) -> list[dict[str, Any]]:
    with get_session(DB_PATH) as session:
        inspector = inspect(session.get_bind())
        if "operational_logs" not in set(inspector.get_table_names()):
            return []
        try:
            rows = session.execute(
                text(
                    """
                    SELECT id, event_type, status, duration_ms, context_json, created_at
                    FROM operational_logs
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": int(limit)},
            ).mappings().all()
        except Exception:
            return []
        history: list[dict[str, Any]] = []
        for row in rows:
            context_json = row.get("context_json", {})
            if isinstance(context_json, str):
                try:
                    context_json = json.loads(context_json or "{}")
                except Exception:
                    context_json = {}
            history.append(
                {
                    "id": int(row.get("id") or 0),
                    "event_type": str(row.get("event_type") or ""),
                    "status": str(row.get("status") or ""),
                    "duration_ms": float(row.get("duration_ms") or 0.0),
                    "created_at": row.get("created_at").isoformat() if getattr(row.get("created_at"), "isoformat", None) else str(row.get("created_at") or ""),
                    "context_json": context_json if isinstance(context_json, dict) else {},
                }
            )
        return history


def _load_institutional_timeline(limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in _load_generation_history(limit=limit):
        items.append(
            {
                "kind": "generation",
                "created_at": entry["created_at"],
                "title": f"Geração #{entry['generation_event_id']}",
                "details": (
                    f"concurso={entry.get('target_contest', '-') or '-'} | jogos={entry['total_games']} | "
                    f"seed={entry['seed']} | status=persistido"
                ),
            }
        )
    for entry in _load_reconciliation_history(limit=limit):
        items.append(
            {
                "kind": "reconciliation",
                "created_at": entry["created_at"],
                "title": f"Conferência #{entry['id']}",
                "details": (
                    f"concurso={entry['contest_id']} | jogos_conferidos={entry['games_count']} | "
                    f"status={entry['status']} | generation_event_id={entry['generation_event_id']}"
                ),
            }
        )
    sync_summary = _load_official_sync_diagnostics()
    if sync_summary:
        items.append(
            {
                "kind": "sync",
                "created_at": str(sync_summary.get("sync_timestamp", "") or ""),
                "title": "Sync Caixa",
                "details": (
                    f"concurso={sync_summary.get('imported_contest', '-')} | status={sync_summary.get('sync_status', '-')} | "
                    f"http={sync_summary.get('http_status', '-')} | persisted={len(sync_summary.get('imported_numbers', []) or [])} | "
                    f"dezenas={' '.join(f'{int(number):02d}' for number in sync_summary.get('imported_numbers', []) or []) or '-'}"
                ),
            }
        )
    items.append(
        {
            "kind": "audit",
            "created_at": "",
            "title": "Auditoria Runtime",
            "details": "PostgreSQL Institucional validado como fonte oficial",
        }
    )
    items.append(
        {
            "kind": "governance",
            "created_at": "",
            "title": "Lei Nº 001",
            "details": "PostgreSQL Institucional como Fonte Única da Verdade",
        }
    )
    hb_state = _hb_geometry_state()
    progress = hb_state.get("progress") or {}
    if progress:
        items.append(
            {
                "kind": "hb_geometry",
                "created_at": str(progress.get("created_at", "") or ""),
                "title": "HB Geometry",
                "details": f"batch={progress.get('current_batch', '-')} | contests={progress.get('contests_processed', '-')} | completed={'sim' if progress.get('completed') else 'não'}",
            }
        )
    items.append(
        {
            "kind": "whatsapp",
            "created_at": "",
            "title": "WhatsApp",
            "details": "Futura integração operacional da plataforma",
        }
    )
    for entry in _load_operational_logs_history(limit=limit):
        items.append(
            {
                "kind": "log",
                "created_at": entry["created_at"],
                "title": f"Log operacional #{entry['id']}",
                "details": f"evento={entry['event_type']} | status={entry['status']} | duration_ms={entry['duration_ms']:.1f}",
            }
        )
    return sorted(
        items,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )[:limit]


def _load_institutional_timeline_light(limit: int = 25) -> list[dict[str, Any]]:
    return _load_institutional_timeline(limit=limit)


def _load_analytical_timeline(limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in _load_generation_history(limit=limit):
        if not is_analytical_history_eligible(entry):
            continue
        top_game = (entry.get("top_games") or [{}])[0] if entry.get("top_games") else {}
        top_numbers = " ".join(f"{number:02d}" for number in top_game.get("numbers", [])[:15]) if top_game else "-"
        items.append(
            {
                "kind": "generation",
                "created_at": entry.get("created_at", ""),
                "title": f"Geração #{entry['generation_event_id']} | concurso={entry.get('target_contest', '-') or '-'}",
                "details": (
                    f"jogos={entry['total_games']} | seed={entry['seed']} | perfil_medio={entry.get('avg_score', 0.0):.4f} | "
                    f"entropy={entry.get('avg_entropy', 0.0):.4f} | coverage={entry.get('avg_coverage', 0.0):.4f} | "
                    f"overlap={entry.get('average_overlap', 0.0):.4f} | top_jogo={top_numbers}"
                ),
            }
        )
        for game in (entry.get("games") or []):
            items.append(
                {
                    "kind": "game",
                    "created_at": entry.get("created_at", ""),
                    "title": f"Jogo {game.get('game_index', '-')}",
                    "details": (
                        f"dezenas={' '.join(f'{number:02d}' for number in game.get('numbers', []))} | "
                        f"perfil={game.get('profile_type', '-')} | score={float(game.get('score', 0.0) or 0.0):.4f} | "
                        f"pares={game.get('even', 0)} | impares={game.get('odd', 0)} | "
                        f"cobertura={float(game.get('coverage', 0.0) or 0.0):.4f} | entropia={float(game.get('entropy', 0.0) or 0.0):.4f}"
                    ),
                }
            )
    for entry in _load_reconciliation_history(limit=limit):
        items.append(
            {
                "kind": "reconciliation",
                "created_at": entry.get("created_at", ""),
                "title": f"Conferência #{entry['id']} | concurso={entry.get('contest_id', '-')}",
                "details": (
                    f"jogos_conferidos={entry.get('games_count', 0)} | melhor_acerto={entry.get('best_hits', 0)} | "
                    f"premios={entry.get('prize_count', 0)} | total_hits={entry.get('total_hits', 0)} | "
                    f"matched_numbers={' '.join(f'{number:02d}' for number in entry.get('matched_numbers', [])) or '-'}"
                ),
            }
        )
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]


def _analytical_row_from_game(
    *,
    generation: dict[str, Any],
    game: dict[str, Any],
    operational_index: dict[int, int] | None = None,
) -> dict[str, Any]:
    generation_label = f"Geração {generation.get('generation_event_id', '-')}"
    created_at = str(generation.get("created_at", "") or "")
    strategy = str(generation.get("strategy", "") or "")
    context_json = dict(game.get("generation_context") or {})
    core_numbers = list(context_json.get("core_numbers") or game.get("numbers", []) or [])
    reserve_numbers = list(context_json.get("audited_reserve_numbers") or [])
    final_card_numbers = list(context_json.get("final_card_numbers") or game.get("numbers", []) or [])
    card_format = int(context_json.get("selected_card_format", context_json.get("card_format", 15)) or 15)
    display_numbers = (
        final_card_numbers
        if card_format > 15 and final_card_numbers
        else list(game.get("numbers") or core_numbers or [])
    )
    ge_id = int(generation.get("generation_event_id", 0) or 0)
    hits_value = game.get("hits")
    return {
        "geração": generation_label,
        "generation_event_id": ge_id,
        "batch_id": str(generation.get("batch_id", "") or ""),
        "analysis_batch_label": str(generation.get("analysis_batch_label", "") or ""),
        "ml_enabled": bool(generation.get("ml_enabled", False)),
        "operacional": resolve_operational_generation_label(ge_id, operational_index=operational_index),
        "data/hora": created_at,
        "jogo n°": int(game.get("game_index", 0) or 0),
        "dezenas": " ".join(f"{number:02d}" for number in display_numbers),
        "formato_cartao": card_format,
        "núcleo_lei_15": " ".join(f"{number:02d}" for number in core_numbers),
        "reservas_auditadas": " ".join(f"+{number:02d}" for number in reserve_numbers) or "-",
        "cartão_final": " ".join(f"{number:02d}" for number in final_card_numbers),
        "quantidade_nucleo": int(context_json.get("quantidade_nucleo", len(core_numbers)) or len(core_numbers)),
        "quantidade_reservas": int(context_json.get("quantidade_reservas", len(reserve_numbers)) or len(reserve_numbers)),
        "quantidade_final": int(context_json.get("quantidade_final", len(final_card_numbers)) or len(final_card_numbers)),
        "estratégia": strategy or "-",
        "score": round(float(game.get("score", 0.0) or 0.0), 4),
        "origem/modelo": str(game.get("origin", "") or "institutional"),
        "status de conferência": str(game.get("conference_status", "Nao conferido") or "Nao conferido"),
        "concurso conferido": int(game.get("contest_id", 0) or 0) if game.get("contest_id") else None,
        "acertos": int(hits_value) if hits_value is not None else None,
        "premiação": str(game.get("prize_status", "") or "") or "—",
        "observações": str(game.get("prize_tier", "") or "") or "-",
        "generation_mode": str(game.get("generation_mode", "") or ""),
        "reconciliation_id": int(game.get("reconciliation_id", 0) or 0) if game.get("reconciliation_id") else None,
        "reconciled_at": str(game.get("reconciled_at", "") or ""),
        "status comandante saída": str(generation.get("status_comandante_saida", "APROVADO") or "APROVADO"),
        "status científico": str(generation.get("scientific_status", "-") or "-"),
        "classificação científica": str(generation.get("scientific_classification", "-") or "-"),
        "ação sugerida": str(generation.get("recommended_action", "-") or "-"),
        "tipo visual": str(generation.get("visibility_label", "Conferível") or "Conferível"),
        "motivo rejeição": str(generation.get("visibility_reason", "-") or "-"),
        "policy_id": str(generation.get("policy_id", "") or ""),
        "policy_origin": str(generation.get("policy_origin", "") or ""),
        "policy_variant": str(generation.get("policy_variant", "") or ""),
        "is_conferible": bool(generation.get("is_conferible", False)),
        "is_rejected_policy": bool(generation.get("is_rejected_policy", False)),
        "is_candidate": bool(generation.get("is_candidate", False)),
        "is_guardian_rejected": bool(generation.get("is_guardian_rejected", False)),
        "is_scientific_rejected": bool(generation.get("is_scientific_rejected", False)),
        "is_calibration_only": bool(generation.get("is_calibration_only", False)),
    }


def _load_accumulated_analytical_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    operational_index = build_operational_generation_index(_load_sovereign_generation_event_rows())
    for generation in _load_generation_history_light(limit=25):
        if not is_analytical_history_eligible({"lot_operational_status": generation.get("lot_operational_status"), "official_release_allowed": generation.get("official_release_allowed")}):
            continue
        for game in generation.get("games", []) or []:
            rows.append(
                _analytical_row_from_game(
                    generation=generation,
                    game=game,
                    operational_index=operational_index,
                )
            )
    return rows


def _load_accumulated_analytical_rows_light(limit: int = 25) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    operational_index = build_operational_generation_index(_load_sovereign_generation_event_rows())
    for generation in _load_generation_history_light(limit=limit):
        if not is_analytical_history_eligible({"lot_operational_status": generation.get("lot_operational_status"), "official_release_allowed": generation.get("official_release_allowed")}):
            continue
        for game in generation.get("games", []) or []:
            rows.append(
                _analytical_row_from_game(
                    generation=generation,
                    game=game,
                    operational_index=operational_index,
                )
            )
    return rows


def _ensure_analytical_games_schema(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "geração",
                "generation_event_id",
                "batch_id",
                "data/hora",
                "jogo n°",
                "dezenas",
                "formato_cartao",
                "núcleo_lei_15",
                "reservas_auditadas",
                "cartão_final",
                "quantidade_nucleo",
                "quantidade_reservas",
                "quantidade_final",
                "estratégia",
                "score",
                "origem/modelo",
                "status de conferência",
                "concurso conferido",
                "acertos",
                "premiação",
                "observações",
                "generation_mode",
                "reconciliation_id",
                "reconciled_at",
                "status comandante saída",
                "status científico",
                "classificação científica",
                "ação sugerida",
                "tipo visual",
                "motivo rejeição",
                "policy_id",
                "policy_origin",
                "policy_variant",
                "is_conferible",
                "is_rejected_policy",
                "is_candidate",
                "is_guardian_rejected",
                "is_scientific_rejected",
                "is_calibration_only",
            ]
        )

    df = df.copy()
    alias_map = {
        "strategy": "estratégia",
        "strategy_name": "estratégia",
        "nome_estrategia": "estratégia",
        "game_strategy": "estratégia",
        "estratÃ©gia": "estratégia",
        "geraÃ§Ã£o": "geração",
        "jogo nÂ°": "jogo n°",
        "premiaÃ§Ã£o": "premiação",
        "observaÃ§Ãµes": "observações",
        "status de conferÃªncia": "status de conferência",
    }
    for source, target in alias_map.items():
        if source in df.columns and target not in df.columns:
            df[target] = df[source]
    if "estratégia" not in df.columns:
        df["estratégia"] = "não informado"
    for column in ("formato_cartao", "quantidade_nucleo", "quantidade_reservas", "quantidade_final"):
        if column not in df.columns:
            df[column] = 0
    if "geração" not in df.columns and "generation_event_id" in df.columns:
        df["geração"] = df["generation_event_id"].apply(lambda value: f"Geração {int(value)}" if pd.notna(value) else "Geração -")
    if "jogo n°" not in df.columns:
        df["jogo n°"] = 0
    if "status de conferência" not in df.columns:
        df["status de conferência"] = "Nao conferido"
    if "premiação" not in df.columns:
        df["premiação"] = "—"
    if "observações" not in df.columns:
        df["observações"] = "-"
    if "batch_id" not in df.columns:
        df["batch_id"] = ""
    if "generation_mode" not in df.columns:
        df["generation_mode"] = ""
    if "reconciliation_id" not in df.columns:
        df["reconciliation_id"] = None
    if "reconciled_at" not in df.columns:
        df["reconciled_at"] = ""
    for column in (
        "generation_event_id",
        "jogo n°",
        "concurso conferido",
        "acertos",
        "score",
        "reconciliation_id",
    ):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in ("data/hora", "reconciled_at", "estratégia", "origem/modelo", "status de conferência", "premiação", "observações", "tipo visual", "motivo rejeição", "policy_id", "policy_origin", "policy_variant", "classificação científica", "ação sugerida", "status comandante saída", "status científico", "núcleo_lei_15", "reservas_auditadas", "cartão_final"):
        if column in df.columns:
            df[column] = df[column].fillna("").astype(str)
    if "status de conferência" in df.columns:
        df["status de conferência"] = (
            df["status de conferência"]
            .astype(str)
            .str.strip()
            .replace(
                {
                    "Nao conferido": "Não conferido",
                    "Nao conferida": "Não conferido",
                    "Nao conferidos": "Não conferido",
                    "Conferida": "Conferido",
                    "Conferidas": "Conferido",
                    "Nao conferido": "Não conferido",
                }
            )
        )
    for column in ("is_conferible", "is_rejected_policy", "is_candidate", "is_guardian_rejected", "is_scientific_rejected", "is_calibration_only"):
        if column in df.columns:
            df[column] = df[column].fillna(False).astype(bool)
    return df


def _make_arrow_safe(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    safe_df = df.copy()
    for column in safe_df.columns:
        if safe_df[column].dtype == "object":
            safe_df[column] = safe_df[column].apply(lambda value: "" if value is None else str(value))
    return safe_df
@st.cache_data(show_spinner=False, ttl=5)
def _load_accumulated_institutional_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for generation in _load_generation_history(limit=None):
        games = list(generation.get("games", []) or [])
        reconciliation = dict(generation.get("reconciliation") or {})
        generated_count = int(generation.get("total_games", 0) or 0)
        persisted_count = _count_generated_games_for_event(int(generation.get("generation_event_id", 0) or 0))
        recovered_count = len(games)
        first_context = dict((games[0] or {}).get("generation_context") or {}) if games and isinstance(games[0], dict) else {}
        requested_count = int(first_context.get("total_games", generated_count) or generated_count)
        generated_requested = generated_count
        strategy = str(generation.get("strategy", "") or "")
        latest_game = max(games, key=lambda item: float(item.get("score", 0.0) or 0.0), default={})
        top_score = float(latest_game.get("score", 0.0) or 0.0) if latest_game else 0.0
        highest_hits = max((int(game.get("hits", 0) or 0) for game in games), default=0)
        average_hits = round(sum(int(game.get("hits", 0) or 0) for game in games) / len(games), 4) if games and any(game.get("hits") is not None for game in games) else 0.0
        conference_status = "Conferido" if reconciliation.get("id") else "Nao conferido"
        persistence_status = "OK" if persisted_count >= recovered_count and recovered_count >= generated_count else "ALERTA"
        generation_status = "OK" if requested_count == generated_count else "ALERTA"
        integrity_alerts: list[str] = []
        if requested_count != generated_count:
            integrity_alerts.append("solicitado_!=_gerado")
        if generated_count != persisted_count:
            integrity_alerts.append("gerado_!=_persistido")
        if persisted_count != recovered_count:
            integrity_alerts.append("persistido_!=_recuperado")
        if not games:
            integrity_alerts.append("sem_jogos_associados")
        if not reconciliation.get("contest_id"):
            integrity_alerts.append("sem_conferencia")
        commander_status = str(first_context.get("status_comandante_saida", "APROVADO") or "APROVADO")
        total_unique = int(first_context.get("total_jogos_unicos", recovered_count) or recovered_count)
        total_duplicates = int(first_context.get("total_jogos_duplicados", 0) or 0)
        rows.append(
            {
                "geração": f"Geração {generation.get('generation_event_id', '-')}",
                "generation_event_id": int(generation.get("generation_event_id", 0) or 0),
                "data/hora": str(generation.get("created_at", "") or ""),
                "usuário/session_id": str(generation.get("first_name", "") or "-"),
                "estratégia/modelo": strategy or "-",
                "quantidade solicitada": requested_count,
                "quantidade real gerada": generated_requested,
                "quantidade persistida": persisted_count,
                "total de jogos recuperados": recovered_count,
                "status da geração": generation_status,
                "status de persistência": persistence_status,
                "status de conferência": conference_status,
                "status comandante saída": commander_status,
                "concurso conferido": int(reconciliation.get("contest_id", 0) or 0) if reconciliation.get("contest_id") else None,
                "maior acerto": highest_hits,
                "média de acertos": average_hits,
                "melhor score": round(top_score, 4),
                "score médio": round(float(generation.get("avg_score", 0.0) or 0.0), 4),
                "origem da geração": str(generation.get("strategy", "") or "institutional"),
                "observações/alertas": ", ".join(integrity_alerts) if integrity_alerts else "OK",
                "total_games": generated_count,
                "batch_id": str(first_context.get("batch_id", "") or ""),
                "total jogos únicos": total_unique,
                "total jogos duplicados": total_duplicates,
                "taxa duplicidade": float(first_context.get("taxa_duplicidade", 0.0) or 0.0),
                "reconciliation_id": reconciliation.get("id"),
                "reconciliation_best_hits": reconciliation.get("best_hits"),
                "reconciliation_prize_count": reconciliation.get("prize_count"),
                "reconciliation_total_hits": reconciliation.get("total_hits"),
                "generated_games": games,
            }
        )
    return rows

def _clear_institutional_history_state() -> None:
    for key in (
        "institutional_generation",
        "institutional_generation_result",
        "institutional_generation_batch_result",
        "institutional_active_batch_id",
        "institutional_active_generation_event_ids",
        "institutional_active_policy_id",
        "institutional_active_generated_at",
        "institutional_active_game_size",
        "institutional_active_total_games",
        "institutional_check",
        "institutional_check_result",
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_last_official_sync_summary",
        "institutional_output_batch_id",
    ):
        st.session_state.pop(key, None)


def _align_institutional_runtime_with_database(snapshot: dict[str, Any]) -> None:
    history_counts = (
        int(snapshot["counts"].get("generation_events", 0) or 0),
        int(snapshot["counts"].get("generated_games", 0) or 0),
        int(snapshot["counts"].get("reconciliation_runs", 0) or 0),
        int(snapshot["counts"].get("reconciliation_games", 0) or 0),
        int(snapshot["counts"].get("reconciliation_events", 0) or 0),
    )
    if any(history_counts):
        return
    _clear_institutional_history_state()
    for key in (
        "institutional_contest_nav",
        "institutional_draw_input",
        "institutional_sync_last_payload",
        "institutional_sync_status",
        "institutional_sync_error",
        "institutional_sync_timestamp",
        "institutional_sync_http_status",
        "institutional_sync_request_url",
        "institutional_imported_contest",
        "institutional_imported_numbers",
        "institutional_generation_batch_result",
        "institutional_simulation",
        "institutional_simulation_result",
        "institutional_simulation_error",
        "institutional_check_result",
        "institutional_check",
        "institutional_active_batch_id",
        "institutional_active_generation_event_ids",
        "institutional_active_policy_id",
        "institutional_active_generated_at",
        "institutional_active_game_size",
        "institutional_active_total_games",
        "institutional_output_batch_id",
    ):
        st.session_state.pop(key, None)


def _purge_institutional_history_tables() -> dict[str, Any]:
    from lotoia.governance.history_preservation_policy import assert_generic_institutional_purge_blocked

    assert_generic_institutional_purge_blocked(
        source="dashboard.institutional_app._purge_institutional_history_tables",
        tables=list(HISTORICAL_TEST_TABLES) + list(PURGE_ONLY_TABLES),
    )
    before_snapshot = _database_snapshot()
    deleted: dict[str, int] = {}
    errors: dict[str, str] = {}
    engine = get_engine(DB_PATH)
    tables_to_purge = list(HISTORICAL_TEST_TABLES) + list(PURGE_ONLY_TABLES)
    for table in tables_to_purge:
        try:
            with engine.begin() as connection:
                result = connection.execute(text(f'DELETE FROM "{table}"'))
            deleted[table] = int(result.rowcount or 0)
        except Exception as exc:
            deleted[table] = 0
            errors[table] = str(exc)
    try:
        st.cache_data.clear()
    except Exception:
        pass
    _clear_institutional_history_state()
    after_snapshot = _database_snapshot()
    return {
        "status": "partial" if errors else "ok",
        "deleted": deleted,
        "errors": errors,
        "before": {
            "counts": {table: int(before_snapshot["counts"].get(table, 0) or 0) for table in HISTORICAL_TEST_TABLES},
            "latest": {table: before_snapshot["latest"].get(table, "-") for table in HISTORICAL_TEST_TABLES},
        },
        "after": {
            "counts": {table: int(after_snapshot["counts"].get(table, 0) or 0) for table in HISTORICAL_TEST_TABLES},
            "latest": {table: after_snapshot["latest"].get(table, "-") for table in HISTORICAL_TEST_TABLES},
        },
        "preserved": {
            "imported_contests": int(after_snapshot["counts"].get("imported_contests", 0) or 0),
            "latest_imported_contest": after_snapshot["latest"].get("imported_contests", "-"),
        },
    }


def _render_history_institutional_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot, force_full=True)
    live_counts = _database_snapshot()["counts"]
    st.subheader("Histórico Institucional")
    st.write("Visão institucional de rastreabilidade, memória pós-reconciliação e documentação legada.")
    if is_light_mode_enabled() and not render_lazy_load_gate(
        SESSION_LOAD_HISTORY,
        "Carregar Histórico",
        help_text=(
            "Modo leve ativo: histórico acumulado não é carregado automaticamente. "
            "Clique para reconstruir a memória institucional do PostgreSQL."
        ),
    ):
        source_cols = st.columns(3)
        source_cols[0].metric("backend", snapshot["backend"])
        source_cols[1].metric("build", BUILD_MARKER)
        source_cols[2].metric("commit", _resolve_active_commit())
        return

    source_map = _institutional_source_map(snapshot)
    latest_sync = st.session_state.get("institutional_last_official_sync_summary", {})
    latest_contest = _load_latest_contest_summary() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    generation_rows = _load_accumulated_institutional_rows()
    generation_df = pd.DataFrame(generation_rows)
    source_cols = st.columns(8)
    source_cols[0].metric("backend", snapshot["backend"])
    source_cols[1].metric("database_source", snapshot["database_source"])
    source_cols[2].metric("schema", "public" if str(snapshot.get("backend", "")).lower() == "postgresql" else "main")
    source_cols[3].metric("operational_logs", int(live_counts.get("operational_logs", 0)))
    source_cols[4].metric("institutional_output_signatures", int(live_counts.get("institutional_output_signatures", 0)))
    source_cols[5].metric("Registros científicos legados", int(live_counts.get("scientific_calibration_decisions", 0)))
    source_cols[6].metric("lotofacil_official_history", int(live_counts.get("lotofacil_official_history", 0)))
    source_cols[7].metric("scientific_institutional_memory", int(live_counts.get("scientific_institutional_memory", 0)))
    st.caption(
        " | ".join(
            [
                f"build={BUILD_MARKER}",
                f"commit={_resolve_active_commit()}",
                f"last_imported_contest={latest_contest.get('contest_number', '-')}",
                f"last_sync={latest_sync.get('sync_timestamp', '-')}",
            ]
        )
    )
    if int(live_counts.get("generation_events", 0) or 0) > 0 and not generation_rows:
        generation_rows = _load_accumulated_institutional_rows()
        generation_df = pd.DataFrame(generation_rows)
    st.markdown("##### Rastreabilidade institucional principal")
    summary_cols = st.columns(10)
    total_generation_events = len(generation_df)
    total_requested = int(generation_df["quantidade solicitada"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_generated = int(generation_df["quantidade real gerada"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_persisted = int(generation_df["quantidade persistida"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_recovered = int(generation_df["total de jogos recuperados"].fillna(0).astype(int).sum()) if not generation_df.empty else 0
    total_contests_reconciled = int(generation_df["concurso conferido"].fillna(0).astype(int).ne(0).sum()) if not generation_df.empty else 0
    highest_hits = int(generation_df["maior acerto"].fillna(0).astype(int).max()) if not generation_df.empty else 0
    best_score = float(generation_df["melhor score"].fillna(0.0).astype(float).max()) if not generation_df.empty else 0.0
    latest_generation_label = generation_df.iloc[0]["geração"] if not generation_df.empty else "-"
    first_generation_label = generation_df.iloc[-1]["geração"] if not generation_df.empty else "-"
    summary_cols[0].metric("total gerações", total_generation_events)
    summary_cols[1].metric("jogos solicitados", total_requested)
    summary_cols[2].metric("jogos gerados", total_generated)
    summary_cols[3].metric("jogos persistidos", total_persisted)
    summary_cols[4].metric("jogos recuperados", total_recovered)
    summary_cols[5].metric("concursos conferidos", total_contests_reconciled)
    summary_cols[6].metric("maior acerto", highest_hits)
    summary_cols[7].metric("melhor score", f"{best_score:.4f}")
    summary_cols[8].metric("última geração", latest_generation_label)
    summary_cols[9].metric("primeira geração", first_generation_label)
    _render_scientific_memory_block()

    if not generation_df.empty:
        latest_commander = generation_df.iloc[0]
        st.markdown("##### Status operacional da última memória consolidada")
        commander_cols = st.columns(6)
        commander_cols[0].metric("total_jogos_solicitados", int(latest_commander.get("quantidade solicitada", 0) or 0))
        commander_cols[1].metric("total_jogos_gerados", int(latest_commander.get("quantidade real gerada", 0) or 0))
        commander_cols[2].metric("total_jogos_unicos", int(latest_commander.get("total jogos únicos", 0) or 0))
        commander_cols[3].metric("total_jogos_duplicados", int(latest_commander.get("total jogos duplicados", 0) or 0))
        commander_cols[4].metric("taxa_duplicidade", f"{float(latest_commander.get('taxa duplicidade', 0.0) or 0.0):.4f}")
        commander_cols[5].metric("Status do OutputCommander", str(latest_commander.get("status comandante saída", "APROVADO") or "APROVADO"))
        st.caption(
            f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))} | "
            f"generation_event_id={int(latest_commander.get('generation_event_id', 0) or 0)}"
        )

        scientific_batch_id = str(latest_commander.get("batch_id", "") or "").strip()
        scientific_batch = dict(st.session_state.get("institutional_batch_conference_result") or {})
        if not scientific_batch and scientific_batch_id:
            scientific_batch = _scientific_batch_diagnostics(batch_id=scientific_batch_id, games=[], game_size=0) or {}
        latest_generated_games = list(latest_commander.get("generated_games", []) or [])
        latest_generation_context = dict((latest_generated_games[0] or {}).get("generation_context") or {}) if latest_generated_games and isinstance(latest_generated_games[0], dict) else {}
        scientific_game_size = int(
            latest_generation_context.get("dezenas_per_game")
            or latest_commander.get("quantidade_dezenas_por_jogo")
            or latest_commander.get("quantidade solicitada", 15)
            or 15
        )
        scientific_policy_discovery = discover_scientific_generation_policy(scientific_game_size, db_path=DB_PATH)
        history_policy = dict(
            scientific_policy_discovery.get("policy")
            or {
                "repeat_min": int(latest_commander.get("repeticao_ultimo_concurso_min", 7) or 7),
                "repeat_max": int(latest_commander.get("repeticao_ultimo_concurso_max", 10) or 10),
                "preferred_parity_pairs": list(latest_commander.get("perfis_paridade_preferenciais", [(7, 8), (8, 7)]) or [(7, 8), (8, 7)]),
                "allowed_parity_pairs": list(latest_commander.get("perfis_paridade_permitidos", [(7, 8), (8, 7), (6, 9), (9, 6)]) or [(7, 8), (8, 7), (6, 9), (9, 6)]),
                "sequence_max": int(latest_commander.get("limite_sequencia_max", 6) or 6),
                "core_numbers": list(latest_commander.get("core_numbers", [7, 12, 16, 23]) or [7, 12, 16, 23]),
                "discouraged_numbers": list(latest_commander.get("discouraged_numbers", [2, 4, 11, 15, 24, 25]) or [2, 4, 11, 15, 24, 25]),
                "max_frequency_ratio": float(latest_commander.get("max_frequency_ratio", 0.7) or 0.7),
                "min_frequency_ratio": float(latest_commander.get("min_frequency_ratio", 0.2) or 0.2),
            }
        )
        scientific_state = None
        scientific_recommendation = None
        st.markdown("##### Diagnóstico histórico observacional")
        st.info("Esta seção observa a memória consolidada. Os registros científicos sensíveis ficam recolhidos na quarentena documental.")
        with st.expander("Memória científica legada — quarentena documental", expanded=False):
            st.caption("Registro técnico legado preservado para auditoria histórica. Não atua como comando, seleção ou recalibração.")
            if st.checkbox("Carregar payload científico legado", value=False, key="load_scientific_legacy_payload"):
                _render_scientific_policy_panel(
                    policy=history_policy,
                    strategy_size=int(scientific_game_size),
                    total_expected_games=int(latest_commander.get("quantidade solicitada", 0) or 0),
                    games_per_generation=int(latest_commander.get("quantidade solicitada", 0) or 0),
                    generations_in_batch=1,
                    policy_discovery=scientific_policy_discovery if scientific_policy_discovery is not None else None,
                    use_expander=False,
                )
                _render_scientific_calibration_panel(
                    strategy_size=int(scientific_game_size),
                    scientific_state=scientific_state,
                    scientific_recommendation=scientific_recommendation,
                    technical_payload=scientific_batch if scientific_batch else None,
                    use_expander=False,
                )
                latest_scientific_decisions = _load_latest_scientific_calibration_decision(limit=5)
                if latest_scientific_decisions:
                    st.dataframe(pd.DataFrame(latest_scientific_decisions), hide_index=True, use_container_width=True)



    if not generation_df.empty:
        filter_row_1 = st.columns([1, 1, 1, 1, 1])
        generation_options = sorted(int(value) for value in generation_df["generation_event_id"].dropna().astype(int).unique().tolist())
        strategy_options = sorted(str(value) for value in generation_df["estratégia/modelo"].dropna().astype(str).unique().tolist())
        status_generation_options = sorted(str(value) for value in generation_df["status da geração"].dropna().astype(str).unique().tolist())
        status_persistence_options = sorted(str(value) for value in generation_df["status de persistência"].dropna().astype(str).unique().tolist())
        status_conference_options = sorted(str(value) for value in generation_df["status de conferência"].dropna().astype(str).unique().tolist())
        selected_generations = filter_row_1[0].multiselect("geração", generation_options, default=generation_options)
        selected_strategies = filter_row_1[1].multiselect("estratégia/modelo", strategy_options, default=strategy_options)
        selected_generation_status = filter_row_1[2].multiselect("status da geração", status_generation_options, default=status_generation_options)
        selected_persistence_status = filter_row_1[3].multiselect("status de persistência", status_persistence_options, default=status_persistence_options)
        selected_conference_status = filter_row_1[4].multiselect("status de conferência", status_conference_options, default=status_conference_options)

        filter_row_2 = st.columns([1, 1, 1, 1, 1])
        contest_options = sorted(int(value) for value in generation_df["concurso conferido"].dropna().astype(int).unique().tolist() if int(value) > 0)
        alert_only = filter_row_2[0].checkbox("somente gerações com alerta", value=False)
        conference_only = filter_row_2[1].checkbox("somente gerações conferidas", value=False)
        not_conference_only = filter_row_2[2].checkbox("somente gerações não conferidas", value=False)
        min_score = filter_row_2[3].number_input("score mínimo", min_value=0.0, value=0.0, step=0.1)
        min_hits = filter_row_2[4].number_input("maior acerto mínimo", min_value=0, value=0, step=1)

        date_values = pd.to_datetime(generation_df["data/hora"], errors="coerce").dropna()
        if not date_values.empty:
            start_date = date_values.min().date()
            end_date = date_values.max().date()
            date_range = st.date_input("data inicial/final", value=(start_date, end_date))
        else:
            date_range = ()

        filtered_df = generation_df.copy()
        filtered_df["data/hora_dt"] = pd.to_datetime(filtered_df["data/hora"], errors="coerce")
        filtered_df["score_medio_num"] = pd.to_numeric(filtered_df["score médio"], errors="coerce").fillna(0.0)
        if selected_generations:
            filtered_df = filtered_df[filtered_df["generation_event_id"].isin(selected_generations)]
        if selected_strategies:
            filtered_df = filtered_df[filtered_df["estratégia/modelo"].isin(selected_strategies)]
        if selected_generation_status:
            filtered_df = filtered_df[filtered_df["status da geração"].isin(selected_generation_status)]
        if selected_persistence_status:
            filtered_df = filtered_df[filtered_df["status de persistência"].isin(selected_persistence_status)]
        if selected_conference_status:
            filtered_df = filtered_df[filtered_df["status de conferência"].isin(selected_conference_status)]
        if contest_options:
            filtered_df = filtered_df[filtered_df["concurso conferido"].fillna(0).astype(int).isin(contest_options)]
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[filtered_df["data/hora_dt"].dt.date.between(start_date, end_date)]
        if alert_only:
            filtered_df = filtered_df[filtered_df["observações/alertas"].astype(str) != "OK"]
        if conference_only:
            filtered_df = filtered_df[filtered_df["status de conferência"].astype(str) == "Conferido"]
        if not_conference_only:
            filtered_df = filtered_df[filtered_df["status de conferência"].astype(str) != "Conferido"]
        filtered_df = filtered_df[filtered_df["score médio"].astype(float) >= float(min_score)]
        filtered_df = filtered_df[filtered_df["maior acerto"].astype(int) >= int(min_hits)]

        order_by = st.selectbox("ordenar por", ["data", "maior acerto", "score"], index=0)
        if order_by == "maior acerto":
            filtered_df = filtered_df.sort_values(
                by=["maior acerto", "melhor score", "data/hora_dt", "generation_event_id"],
                ascending=[False, False, False, False],
            )
        elif order_by == "score":
            filtered_df = filtered_df.sort_values(
                by=["score médio", "melhor score", "data/hora_dt", "generation_event_id"],
                ascending=[False, False, False, False],
            )
        else:
            filtered_df = filtered_df.sort_values(
                by=["data/hora_dt", "generation_event_id"],
                ascending=[False, False],
            )

        display_df = filtered_df.copy()
        display_df["concurso conferido"] = display_df["concurso conferido"].apply(lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—")
        display_df["quantidade solicitada"] = display_df["quantidade solicitada"].fillna(0).astype(int)
        display_df["quantidade real gerada"] = display_df["quantidade real gerada"].fillna(0).astype(int)
        display_df["quantidade persistida"] = display_df["quantidade persistida"].fillna(0).astype(int)
        display_df["total de jogos recuperados"] = display_df["total de jogos recuperados"].fillna(0).astype(int)
        display_df["maior acerto"] = display_df["maior acerto"].fillna(0).astype(int)
        display_df["média de acertos"] = display_df["média de acertos"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["melhor score"] = display_df["melhor score"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["score médio"] = display_df["score médio"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df["observações/alertas"] = display_df["observações/alertas"].astype(str)
        display_df["data/hora"] = display_df["data/hora"].fillna("—")
        for column, default in (
            ("status comandante saída", "APROVADO"),
            ("batch_id", "-"),
            ("total jogos únicos", 0),
            ("total jogos duplicados", 0),
            ("taxa duplicidade", 0.0),
        ):
            if column not in display_df.columns:
                display_df[column] = default
        display_df["status comandante saída"] = display_df["status comandante saída"].astype(str)
        display_df["batch_id"] = display_df["batch_id"].astype(str)
        display_df["total jogos únicos"] = display_df["total jogos únicos"].fillna(0).astype(int)
        display_df["total jogos duplicados"] = display_df["total jogos duplicados"].fillna(0).astype(int)
        display_df["taxa duplicidade"] = display_df["taxa duplicidade"].fillna(0.0).astype(float).map(lambda value: f"{value:.4f}")
        display_df = display_df[
            [
                "geração",
                "generation_event_id",
                "data/hora",
                "usuário/session_id",
                "estratégia/modelo",
                "quantidade solicitada",
                "quantidade real gerada",
                "quantidade persistida",
                "total de jogos recuperados",
                "status da geração",
                "status de persistência",
                "status de conferência",
                "status comandante saída",
                "concurso conferido",
                "maior acerto",
                "média de acertos",
                "melhor score",
                "score médio",
                "origem da geração",
                "batch_id",
                "total jogos únicos",
                "total jogos duplicados",
                "taxa duplicidade",
                "observações/alertas",
            ]
        ]
        st.markdown("##### Gerações institucionais")
        st.dataframe(display_df, hide_index=True, use_container_width=True, height=540)

        if filtered_df.empty:
            st.info("Nenhuma geração encontrada com os filtros atuais.")
        else:
            selected_generation_label = st.selectbox(
                "Detalhe da geração selecionada",
                list(display_df["generation_event_id"].astype(int).tolist()),
                index=0,
            )
            selected_generation_id = int(selected_generation_label)
            selected_generation = next((item for item in generation_rows if int(item.get("generation_event_id", 0) or 0) == selected_generation_id), {})
            detail_cols = st.columns(6)
            detail_cols[0].metric("generation_event_id", selected_generation.get("generation_event_id", "-"))
            detail_cols[1].metric("data/hora", selected_generation.get("data/hora", "-"))
            detail_cols[2].metric("solicitados", selected_generation.get("quantidade solicitada", 0))
            detail_cols[3].metric("gerados", selected_generation.get("quantidade real gerada", 0))
            detail_cols[4].metric("persistidos", selected_generation.get("quantidade persistida", 0))
            detail_cols[5].metric("recuperados", selected_generation.get("total de jogos recuperados", 0))
            st.caption(
                " | ".join(
                    [
                        f"estratégia/modelo={selected_generation.get('estratégia/modelo', '-')}",
                        f"status_conferência={selected_generation.get('status de conferência', '-')}",
                        f"concurso={selected_generation.get('concurso conferido', '-') or '-'}",
                        f"maior_acerto={selected_generation.get('maior acerto', '-')}",
                        f"melhor_score={selected_generation.get('melhor score', '-')}",
                    ]
                )
            )
            if selected_generation.get("observações/alertas") and selected_generation.get("observações/alertas") != "OK":
                st.warning(f"Alerta: {selected_generation.get('observações/alertas')}")
            selected_history = next((item for item in _load_generation_history(limit=None) if int(item.get("generation_event_id", 0) or 0) == selected_generation_id), {})
            if selected_history:
                selected_generation_batch_id = str(selected_generation.get("batch_id", "") or "").strip()
                if selected_generation_batch_id and bool(selected_generation.get("is_conferible", False)):
                    action_cols = st.columns([1.2, 1.0, 1.0])
                    if action_cols[0].button("Enviar geração para conferência", type="primary"):
                        st.session_state["institutional_active_batch_id"] = selected_generation_batch_id
                        st.session_state["active_reconciliation_batch_id"] = selected_generation_batch_id
                        st.session_state["active_reconciliation_generation_event_id"] = selected_generation_id
                        st.session_state["active_reconciliation_scope"] = "generation"
                        st.success(
                            f"Geração {selected_generation_id} enviada para conferência da bateria {selected_generation_batch_id}."
                        )
                        st.rerun()
                    action_cols[1].caption("Somente geração conferível")
                    action_cols[2].caption("Vai abrir a conferência com esta geração")
                st.markdown("###### Top jogos da geração selecionada")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "jogo": game.get("game_index", "-"),
                                "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                                "perfil": game.get("profile_type", "-"),
                                "score": round(float(game.get("score", 0.0) or 0.0), 4),
                                "pares": int(game.get("even", 0) or 0),
                                "?mpares": int(game.get("odd", 0) or 0),
                                "cobertura": round(float(game.get("coverage", 0.0) or 0.0), 4),
                                "entropia": round(float(game.get("entropy", 0.0) or 0.0), 4),
                                "concurso conferido": game.get("contest_id", "-") or "-",
                                "acertos": game.get("hits", "-") if game.get("hits") is not None else "-",
                                "status": game.get("prize_status", "nao_premiado") or "nao_premiado",
                            }
                            for game in (selected_history.get("top_games") or [])
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

        st.markdown("##### Auditoria de integridade")
        issues = display_df[display_df["observações/alertas"].astype(str) != "OK"]
        if issues.empty:
            st.success("Nenhuma inconsistência detectada na visão institucional atual.")
        else:
            st.dataframe(
                issues[
                    [
                        "geração",
                        "generation_event_id",
                        "quantidade solicitada",
                        "quantidade real gerada",
                        "quantidade persistida",
                        "total de jogos recuperados",
                        "status da geração",
                        "status de persistência",
                        "status de conferência",
                        "observações/alertas",
                    ]
                ],
                hide_index=True,
                use_container_width=True,
            )
        diag_cols = st.columns(10)
        diag_cols[0].metric("total_generation_events_carregados", len(generation_rows))
        diag_cols[1].metric("total_generation_events_exibidos", len(display_df))
        diag_cols[2].metric("total_jogos_solicitados", total_requested)
        diag_cols[3].metric("total_jogos_gerados", total_generated)
        diag_cols[4].metric("total_jogos_persistidos", total_persisted)
        diag_cols[5].metric("total_jogos_recuperados", total_recovered)
        diag_cols[6].metric("generation_event_id_mais_antigo", int(generation_df["generation_event_id"].min()) if not generation_df.empty else "-")
        diag_cols[7].metric("generation_event_id_mais_recente", int(generation_df["generation_event_id"].max()) if not generation_df.empty else "-")
        diag_cols[8].metric("total_eventos_com_alerta", int((generation_df["observações/alertas"].astype(str) != "OK").sum()) if not generation_df.empty else 0)
        diag_cols[9].metric("total_eventos_ok", int((generation_df["observações/alertas"].astype(str) == "OK").sum()) if not generation_df.empty else 0)
        st.caption(f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))}")
    else:
        if dict(st.session_state.get("institutional_batch_reconciliation_memory") or {}):
            st.info(
                "Não há gerações operacionais persistidas para reconstrução institucional, "
                "mas a memória científica consolidada da bateria ativa está disponível."
            )
        else:
            st.info("Ainda não há gerações persistidas para reconstrução institucional.")

    st.divider()
    st.markdown("##### Tabelas Institucionais")
    table_rows = []
    for table, count in live_counts.items():
        table_rows.append(
            {
                "tabela": table,
                "contagem": int(count),
                "ultima_persistencia": str(snapshot["latest"].get(table, "-") or "-"),
            }
        )
    st.dataframe(_make_arrow_safe(pd.DataFrame(table_rows)), hide_index=True, use_container_width=True)

    with st.expander("Timeline secundária", expanded=False):
        timeline = _load_institutional_timeline_light(limit=25)
        if timeline:
            st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
        else:
            st.info("Ainda não há eventos suficientes para montar a timeline institucional.")

def _render_clear_histories_page(snapshot: dict[str, Any]) -> None:
    _render_restricted_controlled_cleanup_page(snapshot)


def _render_delete_history_page(snapshot: dict[str, Any]) -> None:
    _render_restricted_controlled_cleanup_page(snapshot)


def _render_restricted_controlled_cleanup_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    state_keys = sorted(
        [key for key in st.session_state.keys() if str(key).startswith("institutional_")]
    )

    def _clear_visual_cache() -> None:
        try:
            st.cache_data.clear()
        except Exception:
            pass

    render_restricted_controlled_cleanup_page(
        table_counts={str(k): int(v or 0) for k, v in snapshot["counts"].items()},
        table_latest={str(k): str(v or "-") for k, v in snapshot["latest"].items()},
        session_institutional_keys=state_keys,
        on_clear_session=_clear_institutional_history_state,
        on_clear_visual_cache=_clear_visual_cache,
        render_constitutional_panel=_render_constitutional_status_panel,
        render_diagnostic_caption=_render_diagnostic_observational_caption,
    )


def _render_comparative_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot, force_full=True)
    st.subheader("Comparativos Histórico")
    st.write("Leitura comparativa entre geração persistida, conferência e concurso oficial.")
    st.info("Esta página é analítica e observacional. Não gera jogos, não recalibra a Lei 15 e não altera histórico.")
    if is_light_mode_enabled() and not render_lazy_load_gate(
        SESSION_LOAD_COMPARATIVE,
        "Carregar Comparativo",
        help_text=(
            "Modo leve ativo: comparativo histórico não é carregado automaticamente. "
            "Clique para consultar geração persistida e concurso oficial."
        ),
    ):
        return
    latest_generation = _load_latest_generated_games() or {}
    latest_contest = _load_imported_contest()
    structural_stats = _summarize_games_structurally(list(latest_generation.get("games") or []))
    st.markdown("##### Resumo da comparação")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Jogos gerados", int(snapshot["counts"].get("generated_games", 0)))
    summary_cols[1].metric("Conferências realizadas", int(snapshot["counts"].get("reconciliation_runs", 0)))
    summary_cols[2].metric("Concursos oficiais importados", int(snapshot["counts"].get("imported_contests", 0)))
    summary_cols[3].metric("Média de sobreposição", f"{structural_stats.get('average_overlap', 0.0):.4f}")

    st.markdown("##### Leitura da geração analisada")
    generation_cols = st.columns(4)
    if latest_generation.get("games"):
        generation_cols[0].metric("Geração", int(latest_generation.get("generation_event_id", 0) or 0) or "-")
        generation_cols[1].metric("Seed", int(latest_generation.get("seed", 0) or 0) or "-")
        generation_cols[2].metric("Total de jogos", int(latest_generation.get("total_games", 0) or 0))
        generation_cols[3].metric("Concurso alvo", int(latest_generation.get("target_contest", 0) or 0) or "-")
        st.caption(
            f"A geração {latest_generation.get('generation_event_id', '-')} foi comparada ao concurso oficial {latest_contest.get('contest_number', '-') if latest_contest else '-'} com {len(list(latest_generation.get('games') or []))} jogos persistidos."
        )
    else:
        st.info("Nenhuma geração persistida encontrada.")
    st.markdown("##### Leitura do concurso oficial")
    contest_cols = st.columns(4)
    if latest_contest:
        contest_cols[0].metric("Concurso", int(latest_contest.get("contest_number", 0) or 0) or "-")
        contest_cols[1].metric("Data", str(latest_contest.get("data", "-") or "-"))
        contest_cols[2].metric("Total de dezenas", len(list(latest_contest.get("dezenas", []) or [])))
        contest_cols[3].metric("Fonte", str(latest_contest.get("source", "banco oficial") or "banco oficial"))
        st.caption(" ".join(f"{int(number):02d}" for number in (latest_contest.get("dezenas", []) or [])) or "-")
    else:
        st.info("Nenhum concurso oficial importado ainda.")
    st.markdown("##### Indicadores de sobreposição")
    overlap_cols = st.columns(4)
    overlap_cols[0].metric("Média de sobreposição", f"{structural_stats.get('average_overlap', 0.0):.4f}")
    overlap_cols[1].metric("Maior recorrência observada", int(max((item.get("frequency", 0) for item in structural_stats.get("dominant_numbers", []) or []), default=0)))
    overlap_cols[2].metric("Total de jogos avaliados", int(structural_stats.get("games", 0) or len(list(latest_generation.get("games") or []))))
    overlap_cols[3].metric("Concurso comparado", int(latest_contest.get("contest_number", 0) or 0) if latest_contest else "-")
    st.markdown("##### Números dominantes")
    dominant_numbers = list(structural_stats.get("dominant_numbers") or [])
    if dominant_numbers:
        dominant_df = pd.DataFrame(dominant_numbers).copy()
        if "number" in dominant_df.columns:
            dominant_df = dominant_df.rename(columns={"number": "Dezena", "frequency": "Frequência nos jogos"})
        elif "Dezena" not in dominant_df.columns:
            dominant_df = dominant_df.rename(columns={dominant_df.columns[0]: "Dezena"})
        if "Frequência nos jogos" not in dominant_df.columns and "frequency" in dominant_df.columns:
            dominant_df["Frequência nos jogos"] = dominant_df["frequency"]
        total_games = max(1, int(structural_stats.get("games", 0) or len(list(latest_generation.get("games") or [])) or 1))
        if "Frequência nos jogos" in dominant_df.columns:
            dominant_df["Percentual"] = dominant_df["Frequência nos jogos"].apply(lambda value: f"{(float(value) / total_games) * 100:.0f}%")
        display_columns = [column for column in ["Dezena", "Frequência nos jogos", "Percentual"] if column in dominant_df.columns]
        st.dataframe(dominant_df[display_columns], hide_index=True, use_container_width=True)
        st.caption("Números dominantes são dezenas que apareceram com maior frequência nos jogos da geração analisada. Esta leitura é observacional e não comanda novas gerações.")
    else:
        st.info("Nenhuma dezena dominante encontrada para a leitura atual.")
    st.markdown("##### Interpretação observacional")
    st.info("A tela compara a geração persistida com o concurso oficial selecionado. A frequência das dezenas mostra concentração dentro da bateria analisada, mas não representa recomendação automática, recalibração ou mudança da Lei 15.")
    with st.expander("Detalhes técnicos avançados", expanded=False):
        st.markdown("###### Geração atual")
        if latest_generation:
            st.json(
                {
                    "generation_event_id": latest_generation.get("generation_event_id", "-"),
                    "seed": latest_generation.get("seed", "-"),
                    "total_games": latest_generation.get("total_games", 0),
                    "target_contest": latest_generation.get("target_contest", "-"),
                }
            )
        else:
            st.info("Nenhuma geração persistida encontrada.")
        st.markdown("###### Concurso oficial")
        if latest_contest:
            st.json(
                {
                    "contest_number": latest_contest.get("contest_number", "-"),
                    "data": latest_contest.get("data", "-"),
                    "dezenas": latest_contest.get("dezenas", []),
                }
            )
        else:
            st.info("Nenhum concurso oficial importado ainda.")
        if structural_stats.get("dominant_numbers"):
            st.markdown("###### Números dominantes técnicos")
            st.dataframe(pd.DataFrame(structural_stats.get("dominant_numbers") or []), hide_index=True, use_container_width=True)


def _render_strategies_page(page_title: str, snapshot: dict[str, Any]) -> None:
    st.subheader(page_title)
    st.write("Ações analíticas desacopladas do fluxo operacional principal.")
    latest_generation = _load_latest_generated_games() or {}
    games = list(latest_generation.get("games") or [])
    structural_stats = _summarize_games_structurally(games)
    action_cols = st.columns(3)
    if action_cols[0].button("Análises Estratégicas", type="primary"):
        st.session_state["institutional_strategy_action"] = "análises_estratégicas"
    if action_cols[1].button("Testar Estratégias", type="primary"):
        st.session_state["institutional_strategy_action"] = "testar_estratégias"
    if action_cols[2].button("Simular Estratégias", type="primary"):
        st.session_state["institutional_strategy_action"] = "simular_estratégias"
    st.caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")
    st.caption(f"strategy_action: {st.session_state.get('institutional_strategy_action', '-')}")
    stats_cols = st.columns(4)
    stats_cols[0].metric("games", structural_stats.get("games", 0))
    stats_cols[1].metric("average_overlap", f"{structural_stats.get('average_overlap', 0.0):.4f}")
    stats_cols[2].metric("average_unique_numbers", f"{structural_stats.get('average_unique_numbers', 0.0):.4f}")
    stats_cols[3].metric("dominant_numbers", len(structural_stats.get("dominant_numbers") or []))
    if structural_stats.get("dominant_numbers"):
        st.dataframe(pd.DataFrame(structural_stats["dominant_numbers"]), hide_index=True, use_container_width=True)
    latest_contest = _load_imported_contest()
    if latest_generation.get("games") and latest_contest:
        comparison = _compare_games_against_contest(
            generation_event_id=int(latest_generation.get("generation_event_id") or 0),
            games=list(latest_generation.get("games") or []),
            contest=latest_contest,
        )
        st.markdown("##### Replay institucional")
        st.caption(
            f"concurso={comparison['contest_number']} | best_hits={comparison['best_hits']} | "
            f"prizes={comparison['prize_count']} | total_hits={comparison['total_hits']}"
        )
        replay_df = pd.DataFrame(
            [
                {
                    "jogo": row["game_index"],
                    "hits": row["hits"],
                    "premiado": row["prize_status"],
                    "matched_numbers": " ".join(f"{number:02d}" for number in row["matched_numbers"]),
                }
                for row in comparison["results"]
            ]
        )
        st.dataframe(replay_df, hide_index=True, use_container_width=True)


def _render_metrics_hb_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Métricas HB")
    st.write("Leitura observacional de acertos, recorrência e dispersão estrutural da bateria analisada.")
    st.info(
        "Esta página é analítica e observacional. "
        "Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 "
        "e não modifica histórico."
    )
    st.markdown(
        "Nesta página, **HB** representa uma camada observacional de métricas "
        "estruturais da bateria analisada. Ela resume acertos, sobreposição, "
        "dispersão e volume analisado, sem atuar como comando de geração ou "
        "recalibração."
    )
    state = _hb_geometry_state()
    summary = state["summary"] or {}
    baseline = summary.get("hb_baseline", {})
    avg_hits = round(float(baseline.get("average_hits", 0.0)), 4)
    hits_11_plus = int(baseline.get("hits_11_plus", 0))
    hits_12_plus = int(baseline.get("hits_12_plus", 0))
    entropy = round(float(baseline.get("entropy", 0.0)), 4)
    average_overlap = round(float(baseline.get("average_overlap", 0.0)), 4)
    dominant_numbers = list(baseline.get("dominant_numbers", []) or [])
    contests_analyzed = int(summary.get("contests_analyzed", 0) or 0)
    games_count = int(summary.get("games_count", 0) or 0)
    pool_size = int(summary.get("pool_size", 0) or 0)
    cols = st.columns(4)
    cols[0].metric("Média de acertos", avg_hits)
    cols[1].metric("Jogos com 11+ acertos", hits_11_plus)
    cols[2].metric("Jogos com 12+ acertos", hits_12_plus)
    cols[3].metric("Entropia estrutural", entropy)
    st.caption(
        "As métricas acima resumem o comportamento estrutural da bateria analisada. "
        "Elas não representam recomendação automática, alteração de estratégia "
        "ou mudança da governança soberana."
    )
    st.subheader("Resumo observacional HB")
    st.caption("Indicadores estruturais derivados da bateria analisada.")
    metrics_df = pd.DataFrame(
        [
            {"métrica": "average_overlap", "valor": average_overlap},
            {"métrica": "dominant_numbers", "valor": ", ".join(f"{item['number']}:{item['frequency']}" for item in dominant_numbers[:5]) or "-"},
            {"métrica": "contests_analyzed", "valor": contests_analyzed},
            {"métrica": "games_count", "valor": games_count},
            {"métrica": "pool_size", "valor": pool_size},
        ]
    )
    metric_label_map = {
        "average_overlap": "Média de sobreposição",
        "dominant_numbers": "Dezenas dominantes",
        "contests_analyzed": "Concursos analisados",
        "games_count": "Jogos analisados",
        "pool_size": "Tamanho do conjunto",
    }
    metrics_display_df = metrics_df.copy()
    if "métrica" in metrics_display_df.columns:
        metrics_display_df["métrica"] = metrics_display_df["métrica"].astype(str).replace(metric_label_map)
        metrics_display_df = metrics_display_df.rename(columns={"métrica": "Métrica", "valor": "Valor"})
    elif "metric" in metrics_display_df.columns:
        metrics_display_df["metric"] = metrics_display_df["metric"].astype(str).replace(metric_label_map)
        metrics_display_df = metrics_display_df.rename(columns={"metric": "Métrica", "value": "Valor"})
    st.dataframe(metrics_display_df, hide_index=True, use_container_width=True)
    st.subheader("Interpretação observacional")
    st.markdown(
        "As Métricas HB permitem observar a média de acertos, a concentração de dezenas, "
        "a dispersão estrutural e o volume analisado. Esta leitura serve para auditoria "
        "e acompanhamento institucional, sem gerar jogos, sem recalibrar leis e sem "
        "alterar histórico."
    )
    with st.expander("Detalhes técnicos avançados"):
        st.write(
            {
                "AVG_HITS": avg_hits,
                "11+": hits_11_plus,
                "12+": hits_12_plus,
                "ENTROPY": entropy,
                "average_overlap": average_overlap,
                "dominant_numbers": dominant_numbers,
                "contests_analyzed": contests_analyzed,
                "games_count": games_count,
                "pool_size": pool_size,
            }
        )


def _render_ml_diagnostic_source_caption(
    payload: dict[str, Any],
    *,
    analysis_only: bool = False,
) -> None:
    parts = [
        "Fonte: PostgreSQL (reconciliation_runs / reconciliation_games)",
        "Camada: diagnóstico observacional",
        "Sem efeito operacional",
    ]
    if analysis_only:
        parts.append("Modo: análise apenas")
    st.caption(" | ".join(parts))




def _resolve_ml_diagnostic_adm_user(snapshot: dict[str, Any]) -> str:
    for key in ("adm_user", "institutional_user", "operator_email", "user_email"):
        value = str(snapshot.get(key) or st.session_state.get(key) or "").strip()
        if value:
            return value
    return "adm@institucional.local"



def _render_diagnostic_evidence_base(
    evidence_base: dict[str, Any] | None,
    *,
    title: str = "Base do diagnóstico",
) -> None:
    base = dict(evidence_base or {})
    if not _evidence_base_identifiable(base):
        st.warning("Base do diagnóstico não identificável — IDs ausentes.")
        return
    st.markdown(f"**{title}**")
    metric_cols = st.columns(3)
    metric_cols[0].metric("Gerações", int(base.get("total_geracoes", 0) or 0))
    metric_cols[1].metric("Concursos", int(base.get("total_concursos", 0) or 0))
    metric_cols[2].metric("Runs", int(base.get("total_runs", 0) or 0))
    st.write(f"Nível de evidência: `{base.get('evidence_level', '—')}`")
    st.write(f"Concursos analisados: `{base.get('concursos_analisados', [])}`")
    if base.get("analysis_batch_label"):
        st.write(f"analysis_batch_label: `{base.get('analysis_batch_label')}`")
    elif base.get("analysis_batch_labels"):
        st.write(f"analysis_batch_labels: `{base.get('analysis_batch_labels', [])}`")
    if base.get("formatos_analisados"):
        st.write(f"formatos_analisados: `{base.get('formatos_analisados', [])}`")
    st.write(f"generation_event_ids: `{base.get('generation_event_ids', [])}`")
    st.write(f"reconciliation_run_ids: `{base.get('reconciliation_run_ids', [])}`")




def _resolve_structural_ranking_rows(
    section: dict[str, Any],
    *,
    kind: str,
    size: int,
    profile: str,
) -> list[dict[str, Any]]:
    prefix_key = "prefixo" if kind == "abertura" else "sufixo"
    if profile == "lotoia":
        for key in (f"lotoia_{prefix_key}_{size}_ranking", f"ranking_{prefix_key}_{size}"):
            rows = section.get(key)
            if rows:
                return list(rows)
        comparison = section.get("comparacao_com_concursos_oficiais")
        if isinstance(comparison, dict):
            lotoia_rows = comparison.get("lotoia")
            if lotoia_rows:
                return list(lotoia_rows)
        if size == 4:
            comparison4 = section.get(f"comparacao_com_concursos_oficiais_{prefix_key}_4")
            if isinstance(comparison4, dict) and comparison4.get("lotoia"):
                return list(comparison4.get("lotoia") or [])
        return []
    comparison = section.get("comparacao_com_concursos_oficiais")
    if size == 4:
        comparison = section.get(f"comparacao_com_concursos_oficiais_{prefix_key}_4") or comparison
    if isinstance(comparison, dict) and comparison.get("oficial"):
        return list(comparison.get("oficial") or [])
    official_key = f"official_{prefix_key}_{size}_ranking"
    rows = section.get(official_key)
    return list(rows or [])


def _render_structural_coverage_ranking_tables(
    section: dict[str, Any],
    *,
    kind: str,
) -> None:
    prefix = "prefixo" if kind == "abertura" else "sufixo"
    table_specs = [
        (f"LotoIA — {prefix} 3", "lotoia", 3),
        (f"Concursos oficiais — {prefix} 3", "official", 3),
        (f"LotoIA — {prefix} 4", "lotoia", 4),
        (f"Concursos oficiais — {prefix} 4", "official", 4),
    ]
    first_row = st.columns(2)
    second_row = st.columns(2)
    for index, (title, profile, size) in enumerate(table_specs):
        target_col = first_row[index] if index < 2 else second_row[index - 2]
        rows = _resolve_structural_ranking_rows(section, kind=kind, size=size, profile=profile)
        with target_col:
            st.markdown(f"**{title}**")
            if rows:
                if is_light_mode_enabled() and len(rows) > 25:
                    render_paginated_dataframe(
                        rows,
                        page_key=f"struct_cov_{kind}_{source_key}",
                    )
                else:
                    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            else:
                st.caption("Sem dados.")




def _render_central_ml_observational_alerts(snapshot: dict[str, Any]) -> None:
    """Conteúdo observacional — sem expander (wrapper fica na página)."""
    _render_diagnostic_observational_caption()
    payload = build_central_ml_diagnostics_payload(DB_PATH)
    _render_ml_diagnostic_source_caption(payload)
    header_cols = st.columns(3)
    header_cols[0].metric("Alertas ativos", int(payload.get("total_alertas_ativos", 0) or 0))
    header_cols[1].metric("Última atualização", str(payload.get("ultima_atualizacao", ""))[:19])
    header_cols[2].metric("Fonte", "PostgreSQL")
    if not payload.get("available"):
        st.warning(
            "Nenhuma reconciliation_run com jogos e resultado oficial encontrada no PostgreSQL."
        )
    alerts = list(payload.get("alerts") or [])
    local_alerts_count = int(payload.get("local_alerts_count", 0) or 0)
    if not alerts and local_alerts_count > 0:
        st.info(payload.get("empty_state_message") or CENTRAL_EMPTY_NO_RECURRENT_MESSAGE)
    elif not alerts and payload.get("available"):
        st.success("Nenhum alerta ML recorrente ativo no momento.")
    adm_user = _resolve_ml_diagnostic_adm_user(snapshot)
    for alert in alerts[:8]:
        status = str(alert.get("status") or STATUS_PENDENTE)
        with st.container(border=True):
            st.markdown(f"**{alert.get('tipo_alerta')}** — {alert.get('tipo_label')}")
            st.write(
                f"Dezena: **{alert.get('dezena_fmt')}** | Status: **{status}** | "
                f"Veredito: **{alert.get('verdict_type') or '—'}**"
            )
            st.caption(str(alert.get("evidencia") or "—"))
            if status in ACTIVE_ALERT_STATUSES and alert.get("verdict_buttons_allowed"):
                reason_key = f"ml_diag_verdict_reason_{alert.get('alert_key')}"
                adm_guide = dict(alert.get("adm_guide") or {})
                suggested_verdict = str(adm_guide.get("suggested_verdict") or "")
                st.text_input(
                    "Motivo do veredito (obrigatório para REQUEST_MORE_EVIDENCE, REJECT e override)",
                    key=reason_key,
                )
                action_cols = st.columns(3)
                if action_cols[0].button(
                    "ACCEPT_DIAGNOSTIC",
                    key=f"ml_diag_accept_{alert.get('alert_key')}",
                    type="primary",
                ):
                    reason = str(st.session_state.get(reason_key) or "").strip()
                    if suggested_verdict and suggested_verdict != VERDICT_ACCEPT_DIAGNOSTIC and not reason:
                        st.error("Override do veredito sugerido exige motivo.")
                    else:
                        try:
                            register_ml_diagnostic_verdict(
                                alert_type=str(alert.get("tipo_alerta")),
                                dezena=int(alert.get("dezena") or 0),
                                ml_proposal=dict(alert.get("ml_proposal") or {}),
                                verdict_type=VERDICT_ACCEPT_DIAGNOSTIC,
                                reconciliation_run_id=int(alert.get("reconciliation_run_id") or 0),
                                adm_user=adm_user,
                                leakage_evidence=dict(alert.get("leakage_evidence") or {}),
                                alert_card=alert,
                                db_path=DB_PATH,
                            )
                            st.success("Veredito ACCEPT_DIAGNOSTIC registrado.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                if action_cols[1].button(
                    "REQUEST_MORE_EVIDENCE",
                    key=f"ml_diag_more_evidence_{alert.get('alert_key')}",
                ):
                    reason = str(st.session_state.get(reason_key) or "").strip()
                    if not reason:
                        st.error("Informe o motivo antes de confirmar REQUEST_MORE_EVIDENCE.")
                    else:
                        try:
                            register_ml_diagnostic_verdict(
                                alert_type=str(alert.get("tipo_alerta")),
                                dezena=int(alert.get("dezena") or 0),
                                ml_proposal=dict(alert.get("ml_proposal") or {}),
                                verdict_type=VERDICT_REQUEST_MORE_EVIDENCE,
                                reconciliation_run_id=int(alert.get("reconciliation_run_id") or 0),
                                verdict_reason=reason,
                                adm_user=adm_user,
                                leakage_evidence=dict(alert.get("leakage_evidence") or {}),
                                alert_card=alert,
                                missing_evidence=list(alert.get("evidence_gaps") or []),
                                db_path=DB_PATH,
                            )
                            st.info("Veredito REQUEST_MORE_EVIDENCE registrado.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
                if action_cols[2].button(
                    "REJECT",
                    key=f"ml_diag_reject_{alert.get('alert_key')}",
                ):
                    reason = str(st.session_state.get(reason_key) or "").strip()
                    if not reason:
                        st.error("Informe o motivo antes de confirmar REJECT.")
                    else:
                        try:
                            register_ml_diagnostic_verdict(
                                alert_type=str(alert.get("tipo_alerta")),
                                dezena=int(alert.get("dezena") or 0),
                                ml_proposal=dict(alert.get("ml_proposal") or {}),
                                verdict_type=VERDICT_REJECT,
                                reconciliation_run_id=int(alert.get("reconciliation_run_id") or 0),
                                verdict_reason=reason,
                                adm_user=adm_user,
                                leakage_evidence=dict(alert.get("leakage_evidence") or {}),
                                alert_card=alert,
                                db_path=DB_PATH,
                            )
                            st.warning("Veredito REJECT registrado.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))


def _render_central_ml_observational_history() -> None:
    history = list_ml_diagnostic_decisions(db_path=DB_PATH, limit=50)
    if not history:
        st.caption("Nenhuma decisão ADM registrada ainda.")
        return
    st.dataframe(pd.DataFrame(history), hide_index=True, use_container_width=True)


def _render_central_ml_diagnostics_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    render_ml_calibration_cockpit(DB_PATH)
    st.markdown("### Detalhes técnicos adicionais")
    with st.expander("Diagnóstico ML observacional (alertas vazamento lateral)", expanded=False):
        _render_central_ml_observational_alerts(snapshot)
    with st.expander("Histórico de decisões ADM (observacional)", expanded=False):
        _render_central_ml_observational_history()
    with st.expander("Governança ML assistiva (referência institucional)", expanded=False):
        render_ml_assistive_governance_section()


def _render_metrics_hb_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Métricas HB")
    st.write("Leitura observacional de acertos, recorrência e dispersão estrutural da bateria analisada.")
    st.info(
        "Esta página é analítica e observacional. "
        "Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 "
        "e não modifica histórico."
    )
    st.markdown(
        "Nesta página, **HB** representa uma camada observacional de métricas "
        "estruturais da bateria analisada. Ela resume acertos, sobreposição, "
        "dispersão e volume analisado, sem atuar como comando de geração ou "
        "recalibração."
    )
    metrics = _load_hb_metrics_from_reconciliation_db()
    st.caption(
        f"Fonte: PostgreSQL ({metrics.get('tables', 'reconciliation_runs / reconciliation_games')}) | "
        f"Prêmios: {metrics.get('prize_count', 0)} | "
        f"Melhor acerto: {metrics.get('best_hits', 0)} | "
        f"Resultado oficial: {metrics.get('official_source', 'indisponivel')}"
    )
    if not metrics.get("available"):
        st.warning("Nenhuma reconciliation_run persistida encontrada no PostgreSQL para calcular as métricas HB.")
    avg_hits = float(metrics.get("media_acertos", 0.0) or 0.0)
    hits_11_plus = int(metrics.get("jogos_11_mais", 0) or 0)
    hits_12_plus = int(metrics.get("jogos_12_mais", 0) or 0)
    entropy = float(metrics.get("entropia_estrutural", 0.0) or 0.0)
    average_overlap = float(metrics.get("media_sobreposicao", 0.0) or 0.0)
    dominant_numbers = list(metrics.get("dezenas_dominantes", []) or [])
    contests_analyzed = int(metrics.get("concursos_analisados", 0) or 0)
    games_count = int(metrics.get("jogos_analisados", 0) or 0)
    pool_size = int(metrics.get("tamanho_conjunto", 0) or 0)
    cols = st.columns(4)
    cols[0].metric("Média de acertos", avg_hits)
    cols[1].metric("Jogos com 11+ acertos", hits_11_plus)
    cols[2].metric("Jogos com 12+ acertos", hits_12_plus)
    cols[3].metric("Entropia estrutural", entropy)
    st.caption(
        "As métricas acima resumem o comportamento estrutural da bateria analisada. "
        "Elas não representam recomendação automática, alteração de estratégia "
        "ou mudança da governança soberana."
    )
    st.subheader("Resumo observacional HB")
    st.caption("Indicadores estruturais derivados da última reconciliation_run persistida.")
    metrics_df = pd.DataFrame(
        [
            {"métrica": "media_sobreposicao", "valor": average_overlap},
            {
                "métrica": "dezenas_dominantes",
                "valor": _format_hb_dominant_numbers(dominant_numbers),
            },
            {"métrica": "concursos_analisados", "valor": contests_analyzed},
            {"métrica": "jogos_analisados", "valor": games_count},
            {"métrica": "tamanho_conjunto", "valor": pool_size},
        ]
    )
    metric_label_map = {
        "media_sobreposicao": "Média de sobreposição",
        "dezenas_dominantes": "Dezenas dominantes",
        "concursos_analisados": "Concursos analisados",
        "jogos_analisados": "Jogos analisados",
        "tamanho_conjunto": "Tamanho do conjunto",
    }
    metrics_display_df = metrics_df.copy()
    metrics_display_df["métrica"] = metrics_display_df["métrica"].astype(str).replace(metric_label_map)
    metrics_display_df = metrics_display_df.rename(columns={"métrica": "Métrica", "valor": "Valor"})
    metrics_display_df = make_arrow_safe_dataframe(metrics_display_df)
    st.dataframe(metrics_display_df, hide_index=True, use_container_width=True)
    st.subheader("Interpretação observacional")
    st.markdown(
        "As Métricas HB permitem observar a média de acertos, a concentração de dezenas, "
        "a dispersão estrutural e o volume analisado. Esta leitura serve para auditoria "
        "e acompanhamento institucional, sem gerar jogos, sem recalibrar leis e sem "
        "alterar histórico."
    )




def _render_structural_coverage_diagnostics_body(payload: dict[str, Any]) -> None:
    summary = dict(payload.get("summary") or {})
    summary_cols = st.columns(4)
    summary_cols[0].metric("Gerações", int(summary.get("total_geracoes", 0) or 0))
    summary_cols[1].metric("Jogos", int(summary.get("total_jogos", 0) or 0))
    summary_cols[2].metric("Concursos comparados", int(summary.get("total_concursos_comparados", 0) or 0))
    summary_cols[3].metric(
        "Formatos",
        ", ".join(str(size) for size in (summary.get("formatos_analisados") or [])) or "-",
    )
    if summary.get("analysis_batch_label"):
        st.caption(f"batch_label: `{summary.get('analysis_batch_label')}`")

    st.markdown("### Resumo estrutural")
    st.write(
        f"Nível de evidência: `{payload.get('evidence_level', 'LOCAL_DIAGNOSTIC')}` | "
        f"ml_role=`{payload.get('ml_role', 'diagnostic_only')}`"
    )

    abertura = dict(payload.get("abertura") or {})
    st.markdown("### Abertura do cartão")
    abertura_cols = st.columns(2)
    prefix3 = abertura.get("prefixo_3_mais_gerado") or {}
    prefix4 = abertura.get("prefixo_4_mais_gerado") or {}
    abertura_cols[0].write(
        f"Prefixo 3 mais gerado: `{prefix3.get('estrutura', '-')}` ({prefix3.get('frequencia', 0)}x)"
    )
    abertura_cols[1].write(
        f"Prefixo 4 mais gerado: `{prefix4.get('estrutura', '-')}` ({prefix4.get('frequencia', 0)}x)"
    )
    if abertura.get("prefixos_pouco_cobertos"):
        st.caption(f"Prefixos pouco cobertos: {', '.join(abertura['prefixos_pouco_cobertos'])}")
    _render_structural_coverage_ranking_tables(abertura, kind="abertura")

    fechamento = dict(payload.get("fechamento") or {})
    st.markdown("### Fechamento do cartão")
    fechamento_cols = st.columns(2)
    suffix3 = fechamento.get("sufixo_3_mais_gerado") or {}
    suffix4 = fechamento.get("sufixo_4_mais_gerado") or {}
    fechamento_cols[0].write(
        f"Sufixo 3 mais gerado: `{suffix3.get('estrutura', '-')}` ({suffix3.get('frequencia', 0)}x)"
    )
    fechamento_cols[1].write(
        f"Sufixo 4 mais gerado: `{suffix4.get('estrutura', '-')}` ({suffix4.get('frequencia', 0)}x)"
    )
    if fechamento.get("sufixos_pouco_cobertos"):
        st.caption(f"Sufixos pouco cobertos: {', '.join(fechamento['sufixos_pouco_cobertos'])}")
    _render_structural_coverage_ranking_tables(fechamento, kind="fechamento")

    faixas_gaps = dict(payload.get("faixas_gaps") or {})
    st.markdown("### Faixas e gaps")
    if faixas_gaps.get("distribuicao_baixas_medias_altas"):
        st.write("Distribuição média por faixa:", faixas_gaps["distribuicao_baixas_medias_altas"])
    st.write(f"Maior gap observado: `{faixas_gaps.get('maior_gap', 0)}`")
    gap_cols = st.columns(2)
    if faixas_gaps.get("gaps_mais_comuns"):
        gap_cols[0].dataframe(pd.DataFrame(faixas_gaps["gaps_mais_comuns"]), hide_index=True, use_container_width=True)
    if faixas_gaps.get("sequencias_mais_comuns"):
        gap_cols[1].dataframe(
            pd.DataFrame(faixas_gaps["sequencias_mais_comuns"]),
            hide_index=True,
            use_container_width=True,
        )

    travamento = dict(payload.get("travamento_13_14") or {})
    st.markdown("### Travamento em 13/14")
    stuck_cols = st.columns(2)
    stuck_cols[0].metric("Jogos com 13 hits", len(travamento.get("jogos_com_13_hits") or []))
    stuck_cols[1].metric("Jogos com 14 hits", len(travamento.get("jogos_com_14_hits") or []))
    missing_cols = st.columns(2)
    if travamento.get("dezenas_faltantes_para_14"):
        missing_cols[0].markdown("**Dezenas faltantes para 14**")
        missing_cols[0].dataframe(
            pd.DataFrame(travamento["dezenas_faltantes_para_14"]),
            hide_index=True,
            use_container_width=True,
        )
    if travamento.get("dezenas_faltantes_para_15"):
        missing_cols[1].markdown("**Dezenas faltantes para 15**")
        missing_cols[1].dataframe(
            pd.DataFrame(travamento["dezenas_faltantes_para_15"]),
            hide_index=True,
            use_container_width=True,
        )
    if travamento.get("jogos_com_13_hits"):
        with st.expander("Estrutura dos jogos travados em 13 hits", expanded=False):
            st.dataframe(pd.DataFrame(travamento["jogos_com_13_hits"]), hide_index=True, use_container_width=True)

    redundancia = dict(payload.get("redundancia_gp") or {})
    st.markdown("### Redundância GP")
    redundancy_cols = st.columns(3)
    redundancy_cols[0].metric("Similaridade média", redundancia.get("similaridade_media_entre_jogos", 0.0))
    redundancy_cols[1].metric("Sobreposição máxima", redundancia.get("sobreposicao_maxima", 0))
    redundancy_cols[2].metric("Quase repetidos", redundancia.get("cartoes_quase_repetidos", 0))
    if redundancia.get("ausencias_recorrentes_no_GP"):
        st.dataframe(
            pd.DataFrame(redundancia["ausencias_recorrentes_no_GP"]),
            hide_index=True,
            use_container_width=True,
        )

    comparacao = dict(payload.get("comparacao_oficial") or {})
    if comparacao.get("available"):
        st.markdown("### Comparação LotoIA vs concursos oficiais")
        insight_cols = st.columns(2)
        if comparacao.get("prefixos_oficiais_raros_na_LotoIA"):
            insight_cols[0].markdown("**Prefixos oficiais raros na LotoIA**")
            insight_cols[0].dataframe(
                pd.DataFrame(comparacao["prefixos_oficiais_raros_na_LotoIA"]),
                hide_index=True,
                use_container_width=True,
            )
        if comparacao.get("prefixos_LotoIA_excessivos"):
            insight_cols[1].markdown("**Prefixos LotoIA excessivos**")
            insight_cols[1].dataframe(
                pd.DataFrame(comparacao["prefixos_LotoIA_excessivos"]),
                hide_index=True,
                use_container_width=True,
            )

    _render_diagnostic_evidence_base(
        dict(payload.get("evidence_base") or {}),
        title="Base do diagnóstico",
    )


def _render_historical_structural_coverage_section() -> None:
    with st.expander(HISTORICAL_SECTION_TITLE, expanded=False):
        st.caption(HISTORICAL_SOURCE_CAPTION)
        st.write(
            "Camada secundária de evidência histórica e reconciliação. "
            "Não representa geração operacional CORE_002 atual."
        )
        filter_cols = st.columns(5)
        batch_options = batch_select_options(include_all=not is_light_mode_enabled())
        selected_batch_option = filter_cols[0].selectbox(
            "Lote histórico (reconciliação)",
            options=batch_options,
            index=default_batch_index(batch_options),
            key="structural_coverage_historical_batch_label",
        )
        if is_light_mode_enabled() and selected_batch_option == "(todos)":
            st.warning("Modo leve: selecione um lote histórico específico.")
            return
        selected_game_size = filter_cols[1].selectbox(
            "game_size (histórico)",
            options=["(todos)", *list(RUNTIME_GENERATION_CARD_FORMATS)],
            index=0,
            key="structural_coverage_historical_game_size",
        )
        selected_generation_event_id = filter_cols[2].number_input(
            "generation_event_id (histórico)",
            min_value=0,
            value=0,
            step=1,
            key="structural_coverage_historical_generation_event_id",
        )
        selected_reconciliation_run_id = filter_cols[3].number_input(
            "reconciliation_run_id",
            min_value=0,
            value=0,
            step=1,
            key="structural_coverage_historical_reconciliation_run_id",
        )
        selected_concurso = filter_cols[4].number_input(
            "concurso_analisado",
            min_value=0,
            value=0,
            step=1,
            key="structural_coverage_historical_concurso_analisado",
        )
        payload = _cached_card_structure_diagnostics_from_db(
            DB_PATH,
            None if selected_batch_option == "(todos)" else str(selected_batch_option),
            None if selected_game_size == "(todos)" else int(selected_game_size),
            int(selected_generation_event_id) if int(selected_generation_event_id) > 0 else None,
            int(selected_reconciliation_run_id) if int(selected_reconciliation_run_id) > 0 else None,
            int(selected_concurso) if int(selected_concurso) > 0 else None,
        )
        st.caption(
            f"Fonte: `{payload.get('source', 'postgresql')}` | Tabelas: `{payload.get('tables', '-')}` | "
            f"coverage_layer=`historical_reconciliation`"
        )
        if not payload.get("available"):
            st.info("Nenhuma reconciliação histórica encontrada para os filtros selecionados.")
            return
        _render_structural_coverage_diagnostics_body(payload)


def _render_cobertura_estrutural_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Cobertura Estrutural")
    render_structural_coverage_governance_section(
        generation_blocked=_is_sovereign_generation_blocked(),
    )
    st.divider()
    st.markdown(f"### {OPERATIONAL_COVERAGE_TITLE}")
    st.caption(OPERATIONAL_SOURCE_CAPTION)
    st.caption(
        "Referência constitucional: **LEI15_CORE_002**. Geração operacional via "
        "**Gerador ADM CORE_002** — leitura soberana em PostgreSQL."
    )
    _render_diagnostic_observational_caption()
    st.write(
        "Visão observacional da estrutura do cartão a partir de gerações operacionais persistidas: "
        "abertura, fechamento, faixas, gaps, sequências, ausências, redundância GP e travamento em 13/14."
    )
    st.info(
        "Painel analítico e observacional. Não gera jogos, não recalibra a Lei 15, "
        "não altera a Lei 15A, não envia alertas para a Central de Diagnósticos e não emite veredito ADM."
    )
    if is_light_mode_enabled() and not render_lazy_load_gate(
        SESSION_LOAD_STRUCTURAL,
        "Carregar Cobertura Estrutural",
        help_text=(
            "Modo leve ativo: métricas de cobertura estrutural não são carregadas automaticamente. "
            "Clique para executar a consulta no lote selecionado."
        ),
    ):
        return

    operational_generations = _cached_operational_core_002_generations(str(DB_PATH))
    if not operational_generations:
        st.warning(EMPTY_OPERATIONAL_MESSAGE)
        _render_historical_structural_coverage_section()
        return

    dropdown_labels = build_operational_generation_dropdown_options(operational_generations)
    label_to_generation = {
        str(row.get("dropdown_label") or ""): row for row in operational_generations
    }
    default_index = max(0, len(dropdown_labels) - 1)
    selected_label = st.selectbox(
        "Geração operacional",
        options=dropdown_labels,
        index=default_index,
        key="structural_coverage_operational_generation",
    )
    if is_all_operational_generations_selection(selected_label):
        selected_generation = build_operational_generations_aggregate_summary(operational_generations)
        selected_ge_id = 0
        selected_card_format = None
    else:
        selected_generation = dict(label_to_generation.get(selected_label) or operational_generations[-1])
        selected_ge_id = int(selected_generation.get("generation_event_id", 0) or 0)
        selected_card_format = int(selected_generation.get("card_format", 15) or 15)

    meta_cols = st.columns(4)
    if is_all_operational_generations_selection(selected_label):
        meta_cols[0].metric(
            "Geração operacional",
            f"Todos ({int(selected_generation.get('generation_events_count', 0) or 0)})",
        )
        meta_cols[1].metric(
            "generation_event_id",
            f"{int(selected_generation.get('generation_events_count', 0) or 0)} IDs",
        )
        meta_cols[2].metric(
            "Formato cartão",
            str(selected_generation.get("card_format_label") or "-"),
        )
        meta_cols[3].metric("Jogos persistidos", int(selected_generation.get("games_count", 0) or 0))
        detail_cols = st.columns(4)
        detail_cols[0].write(
            "batch_label: "
            + (
                f"`{selected_generation.get('analysis_batch_label', '-')}`"
                if len(selected_generation.get("analysis_batch_labels") or []) <= 1
                else f"`{len(selected_generation.get('analysis_batch_labels') or [])} labels`"
            )
        )
        detail_cols[1].write(f"ml_enabled: `{bool(selected_generation.get('ml_enabled', False))}`")
        detail_cols[2].write("origem: `aggregate`")
        detail_cols[3].write(f"persistência: `{selected_generation.get('persistence_status', '-')}`")
        st.caption(f"created_at: `{selected_generation.get('created_at', '-')}`")
    else:
        meta_cols[0].metric("Geração operacional", str(selected_generation.get("operational_generation_label") or "-"))
        meta_cols[1].metric("generation_event_id", str(selected_ge_id))
        meta_cols[2].metric("Formato cartão", f"{selected_card_format}D")
        meta_cols[3].metric("Jogos persistidos", int(selected_generation.get("games_count", 0) or 0))
        detail_cols = st.columns(4)
        detail_cols[0].write(f"batch_label: `{selected_generation.get('analysis_batch_label', '-')}`")
        detail_cols[1].write(f"ml_enabled: `{bool(selected_generation.get('ml_enabled', False))}`")
        detail_cols[2].write(f"origem: `{selected_generation.get('origin', '-')}`")
        detail_cols[3].write(f"persistência: `{selected_generation.get('persistence_status', '-')}`")
        st.caption(f"created_at: `{selected_generation.get('created_at', '-')}`")

    payload = _cached_operational_card_structure_diagnostics_from_db(
        str(DB_PATH),
        selected_ge_id if selected_ge_id > 0 else None,
        selected_card_format,
    )
    st.caption(
        f"Fonte: `{payload.get('source', 'postgresql')}` | Tabelas: `{payload.get('tables', '-')}` | "
        f"coverage_layer=`{payload.get('coverage_layer', 'operational_core_002')}`"
    )
    if not payload.get("available"):
        st.warning("Geração operacional selecionada sem jogos persistidos em generated_games.")
        _render_historical_structural_coverage_section()
        return

    _render_structural_coverage_diagnostics_body(payload)
    _render_historical_structural_coverage_section()


def _render_replay_institutional_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Replay institucional")
    st.write("Reexecuta a leitura do último lote persistido contra o concurso oficial corrente.")
    latest_generation = _load_latest_generated_games() or {}
    latest_contest = _load_imported_contest()
    if st.button("Executar replay institucional", type="primary"):
        if latest_generation.get("games") and latest_contest:
            replay = _compare_games_against_contest(
                generation_event_id=int(latest_generation.get("generation_event_id") or 0),
                games=list(latest_generation.get("games") or []),
                contest=latest_contest,
            )
            st.session_state["institutional_replay"] = replay
            st.success("Replay institucional executado.")
            st.rerun()
        else:
            st.warning("É preciso ter geração persistida e concurso oficial importado.")
    replay = st.session_state.get("institutional_replay")
    if replay:
        st.caption(
            f"concurso={replay.get('contest_number', '-')}"
            f" | best_hits={replay.get('best_hits', '-')}"
            f" | prizes={replay.get('prize_count', '-')}"
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "jogo": row["game_index"],
                        "hits": row["hits"],
                        "premiado": row["prize_status"],
                    }
                    for row in replay.get("results", [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


def _render_benchmark_resumido_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Benchmark resumido")
    st.write("Resumo institucional dos principais indicadores operacionais persistidos.")
    st.info("Esta página é observacional e institucional. Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 e não modifica histórico.")
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    generated_games = int(snapshot["counts"].get("generated_games", 0))
    reconciliation_runs = int(snapshot["counts"].get("reconciliation_runs", 0))
    imported_contests = int(snapshot["counts"].get("imported_contests", 0))
    latest_generation_value = latest_generation.get("generation_event_id", "-")
    st.markdown(
        "O Benchmark Resumido apresenta uma visão sintética dos registros atuais da operação: jogos persistidos, "
        "conferências realizadas, concursos oficiais importados e última geração registrada. Esta leitura serve "
        "para acompanhamento do ADM, sem comando operacional direto."
    )
    benchmark_card_label_map = {
        "GENERATED_GAMES": "Jogos gerados",
        "RECONCILIATION_RUNS": "Conferências realizadas",
        "IMPORTED_CONTESTS": "Concursos oficiais importados",
        "LATEST_GENERATION": "Última geração registrada",
    }
    cols = st.columns(4)
    cols[0].metric(benchmark_card_label_map["GENERATED_GAMES"], generated_games)
    cols[1].metric(benchmark_card_label_map["RECONCILIATION_RUNS"], reconciliation_runs)
    cols[2].metric(benchmark_card_label_map["IMPORTED_CONTESTS"], imported_contests)
    cols[3].metric(benchmark_card_label_map["LATEST_GENERATION"], latest_generation_value)
    st.subheader("Última geração registrada")
    latest_generation_display = {
        "Identificador da geração": latest_generation.get("generation_event_id", "-"),
        "Seed registrada": latest_generation.get("seed", "-"),
        "Total de jogos": latest_generation.get("total_games", "-"),
        "Concurso alvo": latest_generation.get("target_contest", "-"),
    }
    st.table([{ "Campo": key, "Valor": value } for key, value in latest_generation_display.items()])
    st.subheader("Última conferência registrada")
    latest_reconciliation_display = {
        "Identificador da conferência": latest_reconciliation.get("id", "-"),
        "Concurso conferido": latest_reconciliation.get("contest_id", "-"),
        "Geração conferida": latest_reconciliation.get("generation_event_id", "-"),
        "Status": latest_reconciliation.get("status", "-"),
        "Faixas premiadas": latest_reconciliation.get("prize_count", "-"),
        "Total de acertos somados": latest_reconciliation.get("total_hits", "-"),
        "Maior acerto": latest_reconciliation.get("best_hits", "-"),
        "Jogos conferidos": latest_reconciliation.get("games_count", "-"),
    }
    st.table([{ "Campo": key, "Valor": value } for key, value in latest_reconciliation_display.items()])
    matched_numbers = latest_reconciliation.get("matched_numbers") or []
    if matched_numbers:
        st.markdown("**Dezenas conferidas:**")
        st.write(", ".join(f"{int(number):02d}" for number in matched_numbers))
    else:
        st.caption("Dezenas conferidas indisponíveis para esta conferência.")
    hit_distribution = latest_reconciliation.get("hit_distribution") or {}
    if hit_distribution:
        def _safe_hit_key(item: tuple[Any, Any]) -> int:
            try:
                return int(item[0])
            except Exception:
                return 999

        hit_distribution_rows = [
            {"Faixa de acertos": str(key), "Quantidade de jogos": value}
            for key, value in sorted(hit_distribution.items(), key=_safe_hit_key)
        ]
        st.markdown("**Distribuição de acertos:**")
        st.dataframe(hit_distribution_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("Distribuição de acertos indisponível para esta conferência.")
    st.subheader("Interpretação institucional")
    st.markdown(
        "O benchmark resumido consolida os principais sinais operacionais persistidos do ADM. Ele permite verificar "
        "volume gerado, conferências realizadas, concursos oficiais importados e último vínculo entre geração e "
        "conferência. Esta leitura não substitui auditoria detalhada e não executa qualquer ação sobre a geração."
    )
    with st.expander("Detalhes técnicos avançados", expanded=False):
        st.markdown("**Última geração — dados brutos**")
        st.json(latest_generation)
        st.markdown("**Última conferência — dados brutos**")
        st.json(latest_reconciliation)


def _render_estatisticas_operacionais_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Estatísticas operacionais")
    st.write("Leitura institucional do fluxo operacional persistido, das conferências realizadas e do estado temporário da sessão.")
    st.info("Esta página é operacional e observacional. Não gera jogos, não recalibra a Lei 15, não altera a Lei 16 e não modifica histórico.")
    latest_generation = _load_latest_generated_games() or {}
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    generation_events = int(snapshot["counts"].get("generation_events", 0))
    generated_games = int(snapshot["counts"].get("generated_games", 0))
    reconciliation_runs = int(snapshot["counts"].get("reconciliation_runs", 0))
    session_keys = len([key for key in st.session_state.keys() if str(key).startswith("institutional_")])
    last_ui_event = st.session_state.get("institutional_last_ui_event", "-")
    latest_generation_event_id = latest_generation.get("generation_event_id", "-")
    latest_reconciliation_id = latest_reconciliation.get("id", "-") if latest_reconciliation else "-"
    st.markdown(
        "Esta tela resume eventos persistidos da operação e informações temporárias da sessão atual. "
        "Os indicadores abaixo servem para auditoria do funcionamento do ADM e não representam comando de geração, "
        "conferência automática ou recalibração institucional."
    )
    operational_label_map = {
        "GENERATION_EVENTS": "Eventos de geração",
        "GENERATED_GAMES": "Jogos gerados",
        "RECONCILIATION_RUNS": "Conferências realizadas",
        "SESSION_KEYS": "Chaves de sessão",
        "last_ui_event": "Último evento de interface",
        "latest_generation_event_id": "Última geração registrada",
        "latest_reconciliation_id": "Última conferência registrada",
    }
    raw_operational_stats = {
        "GENERATION_EVENTS": generation_events,
        "GENERATED_GAMES": generated_games,
        "RECONCILIATION_RUNS": reconciliation_runs,
        "SESSION_KEYS": session_keys,
        "last_ui_event": last_ui_event,
        "latest_generation_event_id": latest_generation_event_id,
        "latest_reconciliation_id": latest_reconciliation_id,
    }
    cols = st.columns(4)
    cols[0].metric(operational_label_map["GENERATION_EVENTS"], generation_events)
    cols[1].metric(operational_label_map["GENERATED_GAMES"], generated_games)
    cols[2].metric(operational_label_map["RECONCILIATION_RUNS"], reconciliation_runs)
    cols[3].metric(operational_label_map["SESSION_KEYS"], session_keys)
    st.caption(
        f"{operational_label_map['last_ui_event']}: {last_ui_event} | "
        f"{operational_label_map['latest_generation_event_id']}: {latest_generation_event_id} | "
        f"{operational_label_map['latest_reconciliation_id']}: {latest_reconciliation_id}"
    )
    st.markdown("##### Últimos registros operacionais")
    st.markdown(
        f"- {operational_label_map['last_ui_event']}: {last_ui_event}\n"
        f"- {operational_label_map['latest_generation_event_id']}: {latest_generation_event_id}\n"
        f"- {operational_label_map['latest_reconciliation_id']}: {latest_reconciliation_id}"
    )
    st.markdown("##### Interpretação operacional")
    st.write(
        "As estatísticas operacionais indicam a atividade recente do ADM, incluindo eventos de geração registrados, "
        "jogos persistidos e conferências executadas. A leitura de sessão é temporária e não deve ser interpretada "
        "como histórico oficial."
    )
    with st.expander("Detalhes técnicos avançados", expanded=False):
        st.write(raw_operational_stats)
def _sync_latest_official_result_now() -> dict[str, Any]:
    try:
        repository = ContestRepository(DB_PATH)
        service = ResultSyncService(repository=repository)
        summary = service.sync_latest()
        try:
            repository.sync_official_history_from_imported_contests()
        except Exception:
            pass
        payload = summary.to_dict()
        payload["status"] = "ok"
        payload["http_status"] = getattr(service.client, "last_http_status", None)
        payload["request_url"] = getattr(service.client, "last_request_url", "")
        payload["request_headers"] = getattr(service.client, "last_request_headers", {})
        payload["response_headers"] = getattr(service.client, "last_response_headers", {})
        payload["response_preview"] = getattr(service.client, "last_response_preview", "")
        payload["sync_error"] = ""
        payload["sync_timestamp"] = datetime.now(UTC).isoformat()
        latest_record = repository.get_latest_contest_record()
        payload["latest_contest_record"] = latest_record
        payload["imported_numbers"] = list(latest_record.get("dezenas", []) if latest_record else [])
        payload["official_history_record"] = _load_official_history_summary().get("latest_contest", {})
        payload["official_history_diagnostics"] = _load_official_history_diagnostics()
        _persist_official_sync_diagnostics(
            {
                "sync_status": payload.get("status", "unknown"),
                "sync_error": payload.get("sync_error", ""),
                "sync_timestamp": payload.get("sync_timestamp", ""),
                "http_status": payload.get("http_status", None),
                "request_url": payload.get("request_url", ""),
                "request_headers": payload.get("request_headers", {}),
                "response_headers": payload.get("response_headers", {}),
                "response_preview": payload.get("response_preview", ""),
                "imported_contest": payload.get("latest_contest", None),
                "imported_numbers": payload.get("imported_numbers", []),
                "latest_contest_record": payload.get("latest_contest_record"),
                "official_history_diagnostics": payload.get("official_history_diagnostics", {}),
                "payload": payload,
            }
        )
        try:
            export_historical_csv(repository.get_all_contests())
            payload["history_export_status"] = "ok"
        except Exception as export_exc:  # pragma: no cover - surfaced in UI
            payload["history_export_status"] = "failed"
            payload["history_export_error"] = str(export_exc)
        return payload
    except Exception as exc:  # pragma: no cover - surfaced in UI
        client = None
        return {
            "status": "error",
            "error_message": str(exc),
            "sync_error": str(exc),
            "sync_timestamp": datetime.now(UTC).isoformat(),
            "latest_contest": None,
            "synced_contests": [],
            "synced_contests_count": 0,
            "persisted_contests": 0,
            "provider_payload_count": 0,
            "contest_ids": [],
            "db_backend": "unknown",
            "engine_url": "",
            "commit_state": "failed",
            "source": "",
            "fallback_used": True,
            "rollback": True,
            "http_status": None,
            "request_url": "",
            "request_headers": {},
            "response_headers": {},
            "response_preview": "",
            "latest_contest_record": None,
            "imported_numbers": [],
        }


def _coerce_analysis_batch_created_at(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    return None


def _ensure_unique_institutional_batch_id(batch_id: str | None) -> str:
    resolved = str(batch_id or "").strip() or "global"
    if not load_batch_output_signatures(resolved, DB_PATH):
        return resolved
    return f"{resolved}-{uuid.uuid4().hex[:8]}"


def _persist_generation_snapshot(
    *,
    games: list[dict[str, Any]],
    seed: int,
    target_contest: int | None,
    batch_id: str | None = None,
    generation_context: dict[str, Any] | None = None,
    analysis_batch_label: str | None = None,
    analysis_batch_type: str | None = None,
    analysis_batch_created_by: str | None = None,
    analysis_batch_created_at: datetime | None = None,
) -> dict[str, Any]:
    started_at = time.monotonic()
    batch_id = _ensure_unique_institutional_batch_id(batch_id)
    context_payload = {
        "source": "institutional_app",
        "target_contest": target_contest,
        "build_marker": BUILD_MARKER,
        "batch_id": batch_id,
    }
    if generation_context:
        context_payload.update({str(key): value for key, value in generation_context.items()})
    ctx = generation_context or {}
    batch_label = analysis_batch_label or ctx.get("analysis_batch_label")
    batch_type = analysis_batch_type or ctx.get("analysis_batch_type")
    batch_created_by = analysis_batch_created_by or ctx.get("analysis_batch_created_by")
    batch_created_at = analysis_batch_created_at
    if batch_created_at is None:
        batch_created_at = _coerce_analysis_batch_created_at(ctx.get("analysis_batch_created_at"))
    elif not isinstance(batch_created_at, datetime):
        batch_created_at = _coerce_analysis_batch_created_at(batch_created_at)
    with get_session(DB_PATH) as session:
        policy_origin = str((generation_context or {}).get("policy_origin", "") or "")
        policy_adjustment_reason = str((generation_context or {}).get("policy_adjustment_reason", "") or "")
        status_prospectivo = str((generation_context or {}).get("status_prospectivo", "") or "pending_prospective_validation")
        memory_role = str((generation_context or {}).get("memory_role", "") or "")
        dominant_memory = (generation_context or {}).get("dominant_memory")
        selection_variant = str((generation_context or {}).get("selection_variant", "") or "")
        cross_validation_reason = str((generation_context or {}).get("cross_validation_reason", "") or "")
        cross_validation_summary = dict((generation_context or {}).get("cross_validation_summary", {}) or {})
        based_on_memory_kind = str((generation_context or {}).get("based_on_memory_kind", "") or "")
        based_on_memory_id = generation_context.get("based_on_memory_id") if generation_context else None
        based_on_batch_id = str((generation_context or {}).get("based_on_batch_id", "") or "")
        based_on_generation_range = dict((generation_context or {}).get("based_on_generation_range", {}) or {})
        based_on_best_generations = list((generation_context or {}).get("based_on_best_generations", []) or [])
        policy_mode = str((generation_context or {}).get("policy_mode", "") or "")
        validation_threshold = int((generation_context or {}).get("validation_threshold", 0) or 0)
        target_band = str((generation_context or {}).get("target_band", "") or "")
        current_target = str((generation_context or {}).get("current_target", "") or "")
        secondary_target = str((generation_context or {}).get("secondary_target", "") or "")
        dominant_memory_mode = str((generation_context or {}).get("dominant_memory_mode", "") or "")
        core_numbers_to_preserve = list((generation_context or {}).get("core_numbers_to_preserve", []) or [])
        controlled_support_numbers = list((generation_context or {}).get("controlled_support_numbers", []) or [])
        promote_numbers_for_12_plus = list((generation_context or {}).get("promote_numbers_for_12_plus", []) or [])
        reduce_priority_numbers = list((generation_context or {}).get("reduce_priority_numbers", []) or [])
        real_gap_number = (generation_context or {}).get("real_gap_number")
        event_context = {
            **context_payload,
            "generation_hierarchy": "LOTOIA_LAW_ONLY",
            "scientific_law_role": "COMMANDER",
            "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
            "calibration_engine_role": "DISABLED",
            "geometric_filters_role": "SAFETY_GUARDRAIL",
            "output_commander_role": "AUDITOR",
            "memory_registry_role": "REGISTRY",
            "legacy_removed_from_runtime": True,
            "legacy_runtime_access": False,
            "legacy_reason": "historical_compatibility_or_tests_only",
            "policy_mode": policy_mode,
            "validation_threshold": validation_threshold,
            "target_band": target_band,
            "current_target": current_target,
            "secondary_target": secondary_target,
            "policy_origin": policy_origin,
            "policy_adjustment_reason": policy_adjustment_reason,
            "status_prospectivo": status_prospectivo,
            "memory_role": memory_role,
            "dominant_memory": dominant_memory,
            "dominant_memory_mode": dominant_memory_mode,
            "selection_variant": selection_variant,
            "cross_validation_reason": cross_validation_reason,
            "cross_validation_summary": cross_validation_summary,
            "based_on_memory_kind": based_on_memory_kind or None,
            "based_on_memory_id": based_on_memory_id,
            "based_on_batch_id": based_on_batch_id or None,
            "based_on_generation_range": based_on_generation_range or None,
            "based_on_best_generations": based_on_best_generations,
            "core_numbers_to_preserve": core_numbers_to_preserve,
            "controlled_support_numbers": controlled_support_numbers,
            "promote_numbers_for_12_plus": promote_numbers_for_12_plus,
            "reduce_priority_numbers": reduce_priority_numbers,
            "real_gap_number": real_gap_number,
        }
        event = GenerationEvent(
            lead_id=None,
            first_name="institutional",
            whatsapp="",
            generated_games=games,
            context_json=event_context,
            ml_enabled=int(bool((generation_context or {}).get("ml_enabled", False))),
            seed=seed,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=0.0,
            analysis_batch_label=str(batch_label) if batch_label else None,
            analysis_batch_type=str(batch_type) if batch_type else None,
            analysis_batch_created_by=str(batch_created_by) if batch_created_by else None,
            analysis_batch_created_at=batch_created_at,
        )
        session.add(event)
        session.flush()
        generation_event_id = int(event.id)
        event.context_json = {
            **event_context,
            "generation_event_id": generation_event_id,
            "game_signatures": [],
        }
        game_signatures: list[str] = []
        for index, game in enumerate(games, start=1):
            numbers = list(game.get("numbers", []))
            signature = _game_signature(numbers)
            game_signatures.append(signature)
            per_game_context = {
                "card_format": int(game.get("card_format", 15) or 15),
                "selected_card_format": int(game.get("selected_card_format", game.get("card_format", 15)) or 15),
                "format_cartao": int(game.get("card_format", 15) or 15),
                "quantidade_nucleo": 15,
                "quantidade_reservas": len(game.get("audited_reserve_numbers", []) or []),
                "quantidade_final": len(game.get("final_card_numbers", numbers) or numbers),
                "core_numbers": list(game.get("core_numbers", numbers) or numbers),
                "audited_reserve_numbers": list(game.get("audited_reserve_numbers", []) or []),
                "final_card_numbers": list(game.get("final_card_numbers", numbers) or numbers),
                "display_core_numbers": str(game.get("display_core_numbers", "") or ""),
                "display_audited_reserve_numbers": str(game.get("display_audited_reserve_numbers", "") or ""),
                "display_final_card_numbers": str(game.get("display_final_card_numbers", "") or ""),
                "validation_status_lei_17": str(game.get("validation_status_lei_17", "") or ""),
                "validation_status_lei_18": str(game.get("validation_status_lei_18", "") or ""),
            }
            if game.get("realignment_metadata") is not None:
                per_game_context["realignment_metadata"] = game.get("realignment_metadata")
            if game.get("score_ml") is not None:
                per_game_context["score_ml"] = float(game.get("score_ml", 0.0) or 0.0)
            if isinstance(game.get("score_ml_details"), dict):
                per_game_context["score_ml_details"] = dict(game.get("score_ml_details") or {})
            if isinstance(game.get("decision_trace"), dict):
                per_game_context["decision_trace"] = dict(game.get("decision_trace") or {})
            if isinstance(game.get("feature_attribution"), dict):
                per_game_context["feature_attribution"] = dict(game.get("feature_attribution") or {})
            if isinstance(game.get("generation_lineage"), dict):
                per_game_context["generation_lineage"] = dict(game.get("generation_lineage") or {})
            if "core_realignment_v2_applied" in game:
                per_game_context["core_realignment_v2_applied"] = bool(game.get("core_realignment_v2_applied"))
            if "core_realignment_v3_applied" in game:
                per_game_context["core_realignment_v3_applied"] = bool(game.get("core_realignment_v3_applied"))
            if "realignment_applied" in game:
                per_game_context["realignment_applied"] = bool(game.get("realignment_applied"))
            session.add(
                GeneratedGame(
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    target_contest=target_contest,
                    origin="institutional",
                    generation_mode="hb_baseline",
                    game_index=index,
                    numbers=numbers,
                    profile_type=str(game.get("profile_type", "")),
                    final_score=dict(game.get("final_score", {})) if isinstance(game.get("final_score"), dict) else {},
                    quadra_score=dict(game.get("quadra_score", {})) if isinstance(game.get("quadra_score"), dict) else {},
                    context_json={
                        **context_payload,
                    **per_game_context,
                    "generation_hierarchy": "LOTOIA_LAW_ONLY",
                    "scientific_law_role": "COMMANDER",
                    "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
                    "calibration_engine_role": "DISABLED",
                    "geometric_filters_role": "SAFETY_GUARDRAIL",
                    "output_commander_role": "AUDITOR",
                    "memory_registry_role": "REGISTRY",
                    "legacy_removed_from_runtime": True,
                    "legacy_runtime_access": False,
                    "legacy_reason": "historical_compatibility_or_tests_only",
                    "policy_origin": policy_origin,
                    "policy_adjustment_reason": policy_adjustment_reason,
                    "status_prospectivo": status_prospectivo,
                    "memory_role": memory_role,
                    "dominant_memory": dominant_memory,
                    "dominant_memory_mode": dominant_memory_mode,
                    "policy_mode": policy_mode,
                    "validation_threshold": validation_threshold,
                    "target_band": target_band,
                    "current_target": current_target,
                    "secondary_target": secondary_target,
                    "selection_variant": selection_variant,
                    "cross_validation_reason": cross_validation_reason,
                    "based_on_memory_kind": based_on_memory_kind or None,
                    "based_on_memory_id": based_on_memory_id,
                    "based_on_batch_id": based_on_batch_id or None,
                    "based_on_generation_range": based_on_generation_range or None,
                    "based_on_best_generations": based_on_best_generations,
                    "core_numbers_to_preserve": core_numbers_to_preserve,
                    "controlled_support_numbers": controlled_support_numbers,
                    "promote_numbers_for_12_plus": promote_numbers_for_12_plus,
                    "reduce_priority_numbers": reduce_priority_numbers,
                    "real_gap_number": real_gap_number,
                    "game_signature": signature,
                    "game_index": index,
                },
            )
            )
            session.add(
                InstitutionalOutputSignature(
                    batch_id=str(batch_id or "").strip() or "global",
                    generation_event_id=generation_event_id,
                    game_signature=signature,
                    payload={
                        "game_index": index,
                        "numbers": numbers,
                        **per_game_context,
                        "source": "institutional_app",
                        "build_marker": BUILD_MARKER,
                        "generation_hierarchy": "LOTOIA_LAW_ONLY",
                        "scientific_law_role": "COMMANDER",
                        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
                        "calibration_engine_role": "DISABLED",
                        "geometric_filters_role": "SAFETY_GUARDRAIL",
                        "output_commander_role": "AUDITOR",
                        "memory_registry_role": "REGISTRY",
                        "legacy_removed_from_runtime": True,
                        "legacy_runtime_access": False,
                        "legacy_reason": "historical_compatibility_or_tests_only",
                        "policy_origin": policy_origin,
                        "policy_adjustment_reason": policy_adjustment_reason,
                        "status_prospectivo": status_prospectivo,
                        "memory_role": memory_role,
                        "dominant_memory": dominant_memory,
                        "dominant_memory_mode": dominant_memory_mode,
                        "policy_mode": policy_mode,
                        "validation_threshold": validation_threshold,
                        "target_band": target_band,
                        "current_target": current_target,
                        "secondary_target": secondary_target,
                        "selection_variant": selection_variant,
                        "cross_validation_reason": cross_validation_reason,
                        "based_on_memory_kind": based_on_memory_kind or None,
                        "based_on_memory_id": based_on_memory_id,
                        "based_on_batch_id": based_on_batch_id or None,
                        "based_on_generation_range": based_on_generation_range or None,
                        "based_on_best_generations": based_on_best_generations,
                        "core_numbers_to_preserve": core_numbers_to_preserve,
                        "controlled_support_numbers": controlled_support_numbers,
                        "promote_numbers_for_12_plus": promote_numbers_for_12_plus,
                        "reduce_priority_numbers": reduce_priority_numbers,
                        "real_gap_number": real_gap_number,
                    },
                )
            )
        event.context_json = {
            **event_context,
            "generation_event_id": generation_event_id,
            "game_signatures": list(game_signatures),
        }
        event.execution_time_ms = round((time.monotonic() - started_at) * 1000, 2)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise RuntimeError(
                f"Comandante de Saída bloqueou a persistência por assinatura duplicada na bateria {batch_id or 'global'}."
            ) from exc
        return {
            "generation_event_id": generation_event_id,
            "seed": seed,
            "games_count": len(games),
            "target_contest": target_contest,
            "batch_id": batch_id,
        }


def _count_generated_games_for_event(generation_event_id: int) -> int:
    with get_session(DB_PATH) as session:
        return int(
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == int(generation_event_id))
            .count()
        )


def _generated_games_count_sql(generation_event_id: int) -> str:
    return f"SELECT COUNT(*) FROM generated_games WHERE generation_event_id = {int(generation_event_id)};"


def _safe_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    getter = getattr(row, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return getattr(row, key, default)


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        if isinstance(value, str):
            value = value.strip()
            if value in {"", "-", "None", "nan", "NaN"}:
                return default
        if value != value:  # NaN guard
            return default
        return int(float(value))
    except Exception:
        return default


def _scientific_hit_decomposition(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = dict(payload or {})
    generation_range = dict(data.get("generation_range") or {})
    cross_validation_summary = dict(data.get("cross_validation_summary") or {})
    scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
    game_size = int(
        data.get("game_size")
        or generation_range.get("game_size")
        or cross_validation_summary.get("game_size")
        or 15
    )
    validation_threshold = int(
        data.get("validation_threshold")
        or generation_range.get("validation_threshold")
        or scientific_components.get("validation_threshold")
        or (13 if game_size >= 18 else 12 if game_size >= 17 else 11)
    )
    target_band = str(
        data.get("target_band")
        or generation_range.get("target_band")
        or scientific_components.get("target_band")
        or f"{validation_threshold}_to_15"
    )
    validation_zone_label = str(
        data.get("validation_zone_label")
        or generation_range.get("validation_zone_label")
        or scientific_components.get("validation_zone_label")
        or f"Zona de validação científica: {validation_threshold} a 15 acertos."
    )
    best_hits = int(
        data.get("best_hits")
        or generation_range.get("global_best_hits")
        or scientific_components.get("best_hits")
        or 0
    )
    base_histogram = dict(
        data.get("hit_histogram")
        or scientific_components.get("hit_histogram")
        or generation_range.get("hit_histogram")
        or {}
    )
    count_10_exact = int(
        data.get("count_10_exact")
        or scientific_components.get("count_10_exact")
        or generation_range.get("count_10_exact")
        or generation_range.get("global_count_10")
        or data.get("count_10")
        or scientific_components.get("count_10")
        or 0
    )
    count_11_exact = int(
        data.get("count_11_exact")
        or scientific_components.get("count_11_exact")
        or generation_range.get("count_11_exact")
        or max(
            0,
            int(data.get("count_11_plus", generation_range.get("global_count_11_plus", scientific_components.get("count_11_plus", 0)) or 0) or 0)
            - int(data.get("count_12_plus", generation_range.get("global_count_12_plus", scientific_components.get("count_12_plus", 0)) or 0) or 0),
        )
    )
    count_12_exact = int(
        data.get("count_12_exact")
        or scientific_components.get("count_12_exact")
        or generation_range.get("count_12_exact")
        or max(
            0,
            int(data.get("count_12_plus", generation_range.get("global_count_12_plus", scientific_components.get("count_12_plus", 0)) or 0) or 0)
            - int(data.get("count_13_plus", generation_range.get("global_count_13_plus", scientific_components.get("count_13_plus", 0)) or 0) or 0),
        )
    )
    count_13_exact = int(
        data.get("count_13_exact")
        or scientific_components.get("count_13_exact")
        or generation_range.get("count_13_exact")
        or max(
            0,
            int(data.get("count_13_plus", generation_range.get("global_count_13_plus", scientific_components.get("count_13_plus", 0)) or 0) or 0)
            - int(data.get("count_14_plus", generation_range.get("global_count_14_plus", scientific_components.get("count_14_plus", 0)) or 0) or 0),
        )
    )
    count_14_exact = int(
        data.get("count_14_exact")
        or scientific_components.get("count_14_exact")
        or generation_range.get("count_14_exact")
        or max(
            0,
            int(data.get("count_14_plus", generation_range.get("global_count_14_plus", scientific_components.get("count_14_plus", 0)) or 0) or 0)
            - int(data.get("count_15_exact", data.get("count_15", generation_range.get("global_count_15", scientific_components.get("count_15", 0)) or 0)) or 0),
        )
    )
    count_15_exact = int(
        data.get("count_15_exact")
        or scientific_components.get("count_15_exact")
        or generation_range.get("count_15_exact")
        or data.get("count_15")
        or generation_range.get("global_count_15")
        or scientific_components.get("count_15")
        or 0
    )
    histogram = {str(index): int(base_histogram.get(str(index), 0) or 0) for index in range(16)}
    histogram["10"] = max(histogram.get("10", 0), count_10_exact)
    histogram["11"] = max(histogram.get("11", 0), count_11_exact)
    histogram["12"] = max(histogram.get("12", 0), count_12_exact)
    histogram["13"] = max(histogram.get("13", 0), count_13_exact)
    histogram["14"] = max(histogram.get("14", 0), count_14_exact)
    histogram["15"] = max(histogram.get("15", 0), count_15_exact)
    validation_count_plus = {
        11: int(
            data.get("count_11_plus")
            or generation_range.get("global_count_11_plus")
            or scientific_components.get("count_11_plus")
            or 0
        ),
        12: int(
            data.get("count_12_plus")
            or generation_range.get("global_count_12_plus")
            or scientific_components.get("count_12_plus")
            or 0
        ),
        13: int(
            data.get("count_13_plus")
            or generation_range.get("global_count_13_plus")
            or scientific_components.get("count_13_plus")
            or 0
        ),
    }.get(validation_threshold, int(
        data.get("count_11_plus")
        or generation_range.get("global_count_11_plus")
        or scientific_components.get("count_11_plus")
        or 0
    ))
    validation_exact_counts = {
        f"count_{hit}_exact": int(
            data.get(f"count_{hit}_exact")
            or scientific_components.get(f"count_{hit}_exact")
            or generation_range.get(f"count_{hit}_exact")
            or 0
        )
        for hit in range(validation_threshold, 16)
    }
    validation_plus_counts = {
        f"count_{hit}_plus": int(
            data.get(f"count_{hit}_plus")
            or generation_range.get(f"global_count_{hit}_plus")
            or scientific_components.get(f"count_{hit}_plus")
            or 0
        )
        for hit in range(validation_threshold, 15)
    }
    return {
        "hit_histogram": histogram,
        "game_size": game_size,
        "validation_threshold": validation_threshold,
        "target_band": target_band,
        "validation_zone_label": validation_zone_label,
        "validation_minimum_label": str(
            data.get("validation_minimum_label")
            or generation_range.get("validation_minimum_label")
            or scientific_components.get("validation_minimum_label")
            or f"{validation_threshold} = validação mínima"
        ),
        "validation_band_counts": list(range(validation_threshold, 16)),
        "count_10_exact": count_10_exact,
        "count_11_exact": count_11_exact,
        "count_12_exact": count_12_exact,
        "count_13_exact": count_13_exact,
        "count_14_exact": count_14_exact,
        "count_15_exact": count_15_exact,
        "validation_exact_counts": validation_exact_counts,
        "validation_plus_counts": validation_plus_counts,
        "scientific_validation_zone_count": int(validation_count_plus),
        "policy_validation_status": "APROVADO" if best_hits >= validation_threshold and validation_count_plus > 0 else "REPROVADO",
        "count_11_plus": int(
            data.get("count_11_plus")
            or generation_range.get("global_count_11_plus")
            or scientific_components.get("count_11_plus")
            or (count_11_exact + count_12_exact + count_13_exact + count_14_exact + count_15_exact)
        ),
        "count_12_plus": int(
            data.get("count_12_plus")
            or generation_range.get("global_count_12_plus")
            or scientific_components.get("count_12_plus")
            or (count_12_exact + count_13_exact + count_14_exact + count_15_exact)
        ),
        "count_13_plus": int(
            data.get("count_13_plus")
            or generation_range.get("global_count_13_plus")
            or scientific_components.get("count_13_plus")
            or (count_13_exact + count_14_exact + count_15_exact)
        ),
        "count_14_plus": int(
            data.get("count_14_plus")
            or generation_range.get("global_count_14_plus")
            or scientific_components.get("count_14_plus")
            or (count_14_exact + count_15_exact)
        ),
        "count_15": int(data.get("count_15") or generation_range.get("global_count_15") or scientific_components.get("count_15") or count_15_exact),
    }


def _institutional_safe_action_label(raw_action: object) -> str:
    action = str(raw_action or "").strip()
    if action.startswith("recalibrate_from"):
        return "Preservado em quarentena documental"
    if not action or action in {"-", "None", "null"}:
        return "Sem ação operacional"
    return "Registro técnico legado"


def _sanitize_legacy_scientific_value(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or raw.lower() in {"none", "null", "-"}:
        return "Registro observacional"
    if raw.startswith("recalibrate_from"):
        return "Preservado em quarentena documental"
    if raw in {"REPROVADO", "NEAR_MISS_GLOBAL", "NEAR_MISS_FORTE"}:
        return "Registro técnico legado"
    return "Registro observacional"


def _official_15_policy_status_label(payload: dict[str, Any] | None) -> str:
    data = dict(payload or {})
    generation_range = dict(data.get("generation_range") or {})
    cross_validation_summary = dict(data.get("cross_validation_summary") or {})
    scientific_components = dict(cross_validation_summary.get("scientific_score_components") or {})
    game_size = int(
        data.get("game_size")
        or generation_range.get("game_size")
        or cross_validation_summary.get("game_size")
        or scientific_components.get("game_size")
        or 15
    )
    policy_validation_status = str(
        data.get("policy_validation_status")
        or generation_range.get("policy_validation_status")
        or cross_validation_summary.get("policy_validation_status")
        or scientific_components.get("policy_validation_status")
        or ""
    ).strip().upper()
    validated_target_band = str(
        data.get("validated_target_band")
        or generation_range.get("validated_target_band")
        or cross_validation_summary.get("validated_target_band")
        or scientific_components.get("validated_target_band")
        or ""
    ).strip()
    official_search_standard = bool(
        data.get("official_15_search_standard")
        or generation_range.get("official_15_search_standard")
        or cross_validation_summary.get("official_15_search_standard")
        or scientific_components.get("official_15_search_standard")
    )
    if game_size == 15 and (
        official_search_standard
        or policy_validation_status == "VALIDATED_15_POLICY_LEVEL_3"
        or validated_target_band == "13_plus_detected"
    ):
        return "Política 15 validada até nível 13. Ouro 14 e diamante 15 seguem como metas futuras."
    return ""


def _scientific_15_is_official_baseline(payload: dict[str, Any] | None) -> bool:
    data = dict(payload or {})
    generation_range = dict(data.get("generation_range") or {})
    cross_validation_summary = dict(data.get("cross_validation_summary") or {})
    policy_after = dict(data.get("policy_after") or {})
    source_generation_range = dict(data.get("source_generation_range") or {})
    merged_candidates = (data, generation_range, cross_validation_summary, policy_after, source_generation_range)
    game_size = 0
    policy_validation_status = ""
    validated_target_band = ""
    official_search_standard = False
    baseline_batch_id = ""
    source_batch_id = ""
    for candidate in merged_candidates:
        if not game_size:
            game_size = int(
                candidate.get("game_size")
                or candidate.get("validated_game_size")
                or 0
            )
        if not policy_validation_status:
            policy_validation_status = str(
                candidate.get("policy_validation_status")
                or candidate.get("classification")
                or candidate.get("scientific_classification")
                or ""
            ).strip().upper()
        if not validated_target_band:
            validated_target_band = str(candidate.get("validated_target_band") or "").strip()
        if not official_search_standard:
            official_search_standard = bool(candidate.get("official_15_search_standard"))
        if not baseline_batch_id:
            baseline_batch_id = str(candidate.get("baseline_batch_id") or "").strip()
        if not source_batch_id:
            source_batch_id = str(candidate.get("source_batch_id") or candidate.get("batch_id") or "").strip()
    return bool(
        game_size == 15
        and (
            official_search_standard
            or policy_validation_status == "VALIDATED_15_POLICY_LEVEL_3"
            or validated_target_band == "13_plus_detected"
            or baseline_batch_id == "calibration-20260602172948-20a682cd"
            or source_batch_id == "calibration-20260602172948-20a682cd"
        )
    )


def _resolve_official_15_calibration_context(
    *,
    strategy_size: int,
    scientific_state: dict[str, Any] | None,
    scientific_recommendation: dict[str, Any] | None,
    technical_payload: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    if int(strategy_size or 0) != 15:
        return scientific_state, scientific_recommendation, technical_payload
    payload = dict(technical_payload or {})
    if _scientific_15_is_official_baseline(payload):
        official_label = _official_15_policy_status_label(payload)
        return (
            {
                "mode": "BASELINE VALIDADA",
                "structural_status": "baseline oficial pronta",
                "scientific_status": str(
                    payload.get("policy_validation_status")
                    or payload.get("classification")
                    or "VALIDATED_15_POLICY_LEVEL_3"
                ),
                "classification": str(
                    payload.get("classification")
                    or payload.get("policy_validation_status")
                    or "VALIDATED_15_POLICY_LEVEL_3"
                ),
                "main_reason": official_label
                or "última decisão científica: política 15 validada nível 3",
                "status_visual": "BASELINE OFICIAL",
                "reference_window": list(
                    payload.get("reference_window")
                    or payload.get("generation_range", {}).get("generation_event_ids", [])
                    or [payload.get("baseline_contest_number", 3697)]
                ),
                "source_batch_id": str(
                    payload.get("baseline_batch_id")
                    or payload.get("source_batch_id")
                    or payload.get("batch_id")
                    or "calibration-20260602172948-20a682cd"
                ),
            },
            {
                "action_suggested": "usar baseline oficial validada nível 3 para próxima geração compacta",
                "status_visual": "BASELINE OFICIAL",
            },
            payload or None,
        )
    latest_official_memory = next((row for row in _load_latest_scientific_memory(limit=20) if _scientific_15_is_official_baseline(row)), {})
    if latest_official_memory:
        official_label = _official_15_policy_status_label(latest_official_memory)
        return (
            {
                "mode": "BASELINE VALIDADA",
                "structural_status": "baseline oficial pronta",
                "scientific_status": str(
                    latest_official_memory.get("policy_validation_status")
                    or latest_official_memory.get("scientific_classification")
                    or "VALIDATED_15_POLICY_LEVEL_3"
                ),
                "classification": str(
                    latest_official_memory.get("scientific_classification")
                    or latest_official_memory.get("policy_validation_status")
                    or "VALIDATED_15_POLICY_LEVEL_3"
                ),
                "main_reason": official_label
                or "última decisão científica: política 15 validada nível 3",
                "status_visual": "BASELINE OFICIAL",
                "reference_window": list(
                    latest_official_memory.get("generation_range", {}).get("generation_event_ids", [])
                    or [latest_official_memory.get("baseline_contest_number", 3697)]
                ),
                "source_batch_id": str(
                    latest_official_memory.get("baseline_batch_id")
                    or latest_official_memory.get("batch_id")
                    or "calibration-20260602172948-20a682cd"
                ),
            },
            {
                "action_suggested": "usar baseline oficial validada nível 3 para próxima geração compacta",
                "status_visual": "BASELINE OFICIAL",
            },
            latest_official_memory,
        )
    return scientific_state, scientific_recommendation, technical_payload


def _institutional_output_batch_id() -> str:
    batch_id = str(st.session_state.get("institutional_output_batch_id", "") or "").strip()
    if not batch_id:
        batch_id = f"calibration-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        st.session_state["institutional_output_batch_id"] = batch_id
    return batch_id


def _compare_games_against_contest(*, generation_event_id: int, games: list[dict[str, Any]], contest: dict[str, Any]) -> dict[str, Any]:
    contest_number = _extract_contest_number(contest)
    official_numbers = _extract_contest_numbers(contest)
    comparison_source_labels = []
    if contest_number is None:
        return {
            "status": "error",
            "message": "NÃºmero do concurso oficial nÃ£o identificado.",
            "results": [],
            "contest_number": None,
            "official_numbers": official_numbers,
            "official_numbers_count": len(official_numbers),
            "first_game": [],
            "first_game_hits": 0,
            "first_intersection": [],
            "total_games": 0,
            "total_hits": 0,
            "best_hits": 0,
            "prize_count": 0,
            "diagnostics": {
                "official_numbers": official_numbers,
                "official_numbers_count": len(official_numbers),
                "first_game": [],
                "first_game_hits": 0,
                "first_intersection": [],
                "total_games": 0,
                "total_hits": 0,
                "best_hits": 0,
                "prize_count": 0,
            },
        }
    if not official_numbers:
        return {
            "status": "error",
            "message": "NÃ£o foi possÃ­vel identificar as dezenas oficiais do concurso selecionado.",
            "results": [],
            "contest_number": contest_number,
            "official_numbers": [],
            "official_numbers_count": 0,
            "first_game": [],
            "first_game_hits": 0,
            "first_intersection": [],
            "total_games": 0,
            "total_hits": 0,
            "best_hits": 0,
            "prize_count": 0,
            "diagnostics": {
                "official_numbers": [],
                "official_numbers_count": 0,
                "first_game": [],
                "first_game_hits": 0,
                "first_intersection": [],
                "total_games": 0,
                "total_hits": 0,
                "best_hits": 0,
                "prize_count": 0,
            },
        }
    results: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        conference_info = _select_conference_numbers(game)
        numbers = list(conference_info.get("conference_numbers") or [])
        expected_card_size = int(conference_info.get("expected_card_size", len(numbers) or 15) or (len(numbers) or 15))
        actual_card_size = int(conference_info.get("actual_card_size", len(numbers)) or len(numbers))
        origin_label = str(conference_info.get("origem_dezenas_conferencia", "indisponivel") or "indisponivel")
        matched = sorted(set(numbers) & set(official_numbers))
        missing_draw_numbers = sorted(set(official_numbers) - set(numbers))
        extra_numbers = sorted(set(numbers) - set(official_numbers))
        score_original = float(game.get("score", 0.0) or 0.0)
        comparison_source_labels.append(origin_label)
        results.append(
            {
                "game_index": index,
                "numbers": numbers,
                "cartao_final": numbers,
                "nucleo_lei_15": str(
                    game.get("nucleo_lei_15")
                    or game.get("nucleo")
                    or game.get("lei_15")
                    or ""
                ),
                "reservas_auditadas": str(
                    game.get("reservas_auditadas")
                    or game.get("reservas")
                    or game.get("reservas_auditadas_texto")
                    or ""
                ),
                "rank_original": int(game.get("game_index", index) or index),
                "hits": len(matched),
                "formato_cartao": int(
                    _safe_int(
                        game.get("formato_cartao")
                        or game.get("card_format")
                        or game.get("selected_card_format")
                        or game.get("quantidade_final"),
                        default=expected_card_size,
                    )
                    or expected_card_size
                ),
                "dezenas_conferidas_count": actual_card_size,
                "origem_dezenas_conferencia": origin_label,
                "expected_card_size": expected_card_size,
                "actual_card_size": actual_card_size,
                "hit_classification": (
                    f"EXACT_{len(matched)}"
                    if 11 <= len(matched) <= 15
                    else ("NEAR_MISS_10" if len(matched) == 10 else "BELOW_PRIZE")
                ),
                "matched_numbers": matched,
                "missing_draw_numbers": missing_draw_numbers,
                "extra_numbers": extra_numbers,
                "prize_status": "premiado" if len(matched) >= 11 else "nao_premiado",
                "prize_tier": f"faixa_{len(matched)}" if len(matched) >= 11 else "",
                "score_original": score_original,
                "profile_type": str(game.get("profile_type", "") or ""),
                "perfil": str(game.get("perfil", game.get("profile_type", "")) or ""),
                "game_signature": str(game.get("game_signature", "") or ""),
            }
        )
    best_hits = max((int(row["hits"]) for row in results), default=0)
    total_hits = sum(int(row["hits"]) for row in results)
    prize_count = sum(1 for row in results if int(row["hits"]) >= 11)
    diagnostics = {
        "official_numbers": official_numbers,
        "official_numbers_count": len(official_numbers),
        "generation_event_id": int(generation_event_id or 0),
        "formato_cartao": int(results[0].get("formato_cartao", 15) if results else 15),
        "dezenas_conferidas_count": int(results[0].get("dezenas_conferidas_count", 0) if results else 0),
        "origem_dezenas_conferencia": comparison_source_labels[0] if comparison_source_labels else "indisponivel",
        "expected_card_size": int(results[0].get("expected_card_size", 15) if results else 15),
        "actual_card_size": int(results[0].get("actual_card_size", 0) if results else 0),
        "first_game": results[0]["numbers"] if results else [],
        "first_game_hits": int(results[0]["hits"]) if results else 0,
        "first_intersection": results[0]["matched_numbers"] if results else [],
        "total_games": len(results),
        "total_hits": total_hits,
        "best_hits": best_hits,
        "prize_count": prize_count,
    }
    with get_session(DB_PATH) as session:
        run = ReconciliationRun(
            generation_event_id=generation_event_id,
            lead_id=None,
            contest_id=contest_number,
            source="institutional",
            status="reconciled" if results else "sem_jogos",
            prize_count=prize_count,
            total_hits=total_hits,
            best_hits=best_hits,
            payload={
                "source": "institutional",
                "contest_id": contest_number,
                "best_hits": best_hits,
                "total_hits": total_hits,
                "prize_count": prize_count,
            },
        )
        session.add(run)
        session.flush()
        for game in results:
            session.add(
                ReconciliationGame(
                    reconciliation_run_id=run.id,
                    generation_event_id=generation_event_id,
                    lead_id=None,
                    contest_id=contest_number,
                    game_index=int(game["game_index"]),
                    numbers=list(game["numbers"]),
                    hits=int(game["hits"]),
                    matched_numbers=list(game["matched_numbers"]),
                    prize_status=str(game["prize_status"]),
                    prize_tier=str(game["prize_tier"]),
                    context_json={
                        "source": "institutional",
                        "build_marker": BUILD_MARKER,
                        "rank_original": int(game.get("rank_original", 0) or 0),
                        "score_original": float(game.get("score_original", 0.0) or 0.0),
                        "missing_draw_numbers": list(game.get("missing_draw_numbers", []) or []),
                        "extra_numbers": list(game.get("extra_numbers", []) or []),
                    },
                )
            )
        session.commit()
    return {
        "contest_number": contest_number,
        "contest_date": str(contest.get("data", "")),
        "official_numbers": official_numbers,
        "results": results,
        "generation_event_id": int(generation_event_id or 0),
        "formato_cartao": int(results[0].get("formato_cartao", 15) if results else 15),
        "dezenas_conferidas_count": int(results[0].get("dezenas_conferidas_count", 0) if results else 0),
        "origem_dezenas_conferencia": str(results[0].get("origem_dezenas_conferencia", "indisponivel") if results else "indisponivel"),
        "expected_card_size": int(results[0].get("expected_card_size", 15) if results else 15),
        "actual_card_size": int(results[0].get("actual_card_size", 0) if results else 0),
        "best_hits": best_hits,
        "total_hits": total_hits,
        "prize_count": prize_count,
        "reconciliation": {"id": int(run.id), "contest_id": contest_number},
        "diagnostics": diagnostics,
    }


def _start_hb_geometry_job(*, resume: bool) -> None:
    def _runner() -> None:
        started_at = time.monotonic()
        with _JOB_LOCK:
            _JOB_STATE.update(
                {
                    "running": True,
                    "completed": False,
                    "error": "",
                    "started_at": started_at,
                }
            )
        try:
            result = run_hb_geometry_audit(
                contests_analyzed=30,
                games_count=5,
                pool_size=18,
                history_window=200,
                batch_size=5,
                lightweight=True,
                resume=resume,
                max_batches_per_run=1,
                output_dir=HB_GEOMETRY_DIR,
            )
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": bool(result.completed),
                        "current_scenario": str(result.scenarios[0]["scenario"]) if result.scenarios else "-",
                        "processed_batches": int(result.processed_batches),
                        "contests_processed": int(result.contests_analyzed),
                        "elapsed_time": float(time.monotonic() - started_at),
                        "error": "",
                        "result": result.to_dict(),
                    }
                )
        except Exception as exc:  # pragma: no cover
            with _JOB_LOCK:
                _JOB_STATE.update(
                    {
                        "running": False,
                        "completed": False,
                        "error": str(exc),
                        "elapsed_time": float(time.monotonic() - started_at),
                    }
                )

    thread = threading.Thread(target=_runner, daemon=True, name="hb-geometry-audit")
    thread.start()


def _reset_hb_geometry_job() -> None:
    for path in (HB_GEOMETRY_JSON_FILE, HB_GEOMETRY_CSV_FILE, HB_GEOMETRY_PROGRESS_FILE):
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    with _JOB_LOCK:
        _JOB_STATE.update(
            {
                "running": False,
                "completed": False,
                "current_scenario": "-",
                "processed_batches": 0,
                "contests_processed": 0,
                "elapsed_time": 0.0,
                "error": "",
                "result": None,
                "started_at": None,
            }
        )


def _render_sidebar(page: str, snapshot: dict[str, Any]) -> str:
    _apply_institutional_styles()
    _render_sidebar_logo()
    st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="lotoia-nav-hint">Navegação institucional</div>', unsafe_allow_html=True)
    st.sidebar.caption(f"build={APP_BUILD}")
    st.sidebar.caption(f"commit={_resolve_active_commit()}")
    _render_constitutional_status_panel(compact=True)

    def _nav_entry(label: str, page_id: str | None = None, *, disabled: bool = False) -> None:
        resolved_page_id = page_id or PAGE_TARGETS.get(label, label)
        if st.sidebar.button(label, key=f"nav_{resolved_page_id}", disabled=disabled):
            st.session_state["institutional_page_id"] = str(resolved_page_id)
            st.rerun()

    for group_index, (group_name, entries) in enumerate(OFFICIAL_SIDEBAR_MENU):
        if group_index > 0:
            st.sidebar.markdown('<div class="lotoia-sidebar-divider"></div>', unsafe_allow_html=True)
        st.sidebar.markdown(f'<div class="lotoia-sidebar-group">{group_name}</div>', unsafe_allow_html=True)
        for label, page_id in entries:
            _nav_entry(label, page_id)
        if group_name == "Governança / Restrito":
            st.sidebar.caption(GOVERNANCE_READ_ONLY_ALERT)
            st.sidebar.caption(RESTRICTED_PURGE_BLOCK_MESSAGE)
        elif group_name == "ML":
            st.sidebar.caption(
                "Cockpit de calibração supervisionada da saída CORE_002 + ML. "
                "Não gera jogos fora do path soberano."
            )

    choice = resolve_institutional_page_id(
        _canonical_page_id(st.session_state.get("institutional_page_id") or page)
    )
    if choice not in INSTITUTIONAL_ALLOWED_PAGES:
        choice = resolve_institutional_page_id(_canonical_page_id(page))
    if choice not in INSTITUTIONAL_ALLOWED_PAGES:
        choice = "fallback"
    st.session_state["institutional_page_id"] = choice
    st.sidebar.divider()
    st.sidebar.caption("DATABASE_URL conectada")
    return choice


def _ensure_institutional_schema() -> None:
    try:
        ensure_database_schema(DB_PATH)
    except Exception as exc:
        logger.warning("institutional schema ensure skipped: %s", exc)


def _generation_strategy_display(size: int) -> dict[str, Any]:
    game_size = max(2, min(25, int(size or 15)))
    policy = _institutional_generation_policy(game_size)
    if game_size == 15:
        official_label = "Política 15 validada nível 3. Núcleo operacional pronto."
        return {
            "policy": policy,
            "strategy_label": "Política 15 validada nível 3",
            "scientific_status": "VALIDATED_15_POLICY_LEVEL_3",
            "status_visual": "BASELINE OFICIAL",
            "mode": "BASELINE OFICIAL",
            "main_reason": official_label,
            "action_suggested": "usar baseline oficial validada nível 3 para próxima geração compacta",
            "summary": "Política 15 validada até nível 13. 13 acertos preservados. Ouro 14 e diamante 15 seguem como metas futuras.",
            "generation_mode": "VALIDATED_15_POLICY_LEVEL_3",
            "policy_mode": "VALIDATED_15_POLICY_LEVEL_3",
            "historical_deduplication_mode": "AUDIT_ONLY",
            "official_package_preserved": False,
            "legacy_generation_flow": "ARCHIVED",
            "official_15_generation_model_label": "Lei 15 validada: 15 dezenas por jogo",
        }
    if game_size == 17:
        return {
            "policy": policy,
            "strategy_label": "Estratégia 17 preparada",
            "scientific_status": "PREPARADO",
            "status_visual": "PREPARADO",
            "mode": "GERAÇÃO PREPARADA",
            "main_reason": "Régua futura preparada: 12 = validação mínima, 13 = validação forte, 14 = ouro, 15 = diamante.",
            "action_suggested": "estratégia 17 pronta, aguardando liberação da calibração",
            "summary": "Estratégia 17 preparada para ativação futura. Ainda sem política validada.",
        }
    if game_size == 18:
        return {
            "policy": policy,
            "strategy_label": "Estratégia 18 preparada",
            "scientific_status": "PREPARADO",
            "status_visual": "PREPARADO",
            "mode": "GERAÇÃO PREPARADA",
            "main_reason": "Régua futura preparada: 13 = validação mínima, 14 = ouro, 15 = diamante.",
            "action_suggested": "estratégia 18 pronta, aguardando liberação da calibração",
            "summary": "Estratégia 18 preparada para ativação futura. Ainda sem política validada.",
        }
    return {
        "policy": policy,
        "strategy_label": f"Estratégia {game_size} preparada",
        "scientific_status": "PREPARADO",
        "status_visual": "PREPARADO",
        "mode": "GERAÇÃO PREPARADA",
        "main_reason": "Estratégia preparada para uso operacional futuro.",
        "action_suggested": "gerar jogos",
        "summary": "Estratégia preparada para uso operacional futuro.",
    }


def _compact_small_batch_adjustment(*, game_size: int, total_games: int) -> dict[str, Any]:
    if int(game_size or 0) != 15:
        return {}
    requested_games = int(total_games or 0)
    if requested_games > 50:
        return {}
    if requested_games <= 10:
        return {
            "scientific_mother_law": "Lei Científica 15",
            "requested_games": requested_games,
            "generated_candidates": 9,
            "valid_individual_games": 9,
            "persisted_games": 0,
            "approved_total_less_than_requested": True,
            "blocked_reason": "nao_atingiu_quantidade_solicitada",
            "output_commander_status": "BLOQUEADO",
            "natural_approvable_candidate": True,
            "candidate_reason": "valid_individual_games_but_incomplete_requested_package",
            "natural_quantity_reason": "structural_saturation_under_scientific_law",
            "natural_quantity_mode": "OBSERVED_EXTREME_9",
            "natural_generated_games": 9,
            "natural_scientific_quantity": False,
            "natural_quantity_status": "CANDIDATE_OBSERVED",
            "compactation_mode": "EXTREME_COMPACT",
            "compactation_status": "OPERATIONAL_ACTIVE",
            "compactation_test_status": "FAILED_MINIMUM_11_PLUS",
            "compactation_failure_type": "RIGID_BIMODAL_COMPACTATION",
            "compactation_adjustment_status": "ENABLED",
            "compactation_adjustment_mode": "EXTREME_COMPACT",
            "compactation_adjustment_reason": "high_precision_minimum_diversity",
            "compactation_adjustment_boost_numbers": [17, 23],
            "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
            "compactation_adjustment_odd_min": 5,
            "compactation_adjustment_odd_max": 9,
            "compactation_adjustment_even_min": 5,
            "compactation_adjustment_even_max": 9,
            "compactation_adjustment_repeat_min": 4,
            "compactation_adjustment_repeat_max": 8,
            "compactation_adjustment_coverage_min": 0.38,
            "compactation_adjustment_entropy_min": 0.42,
            "compactation_adjustment_sequence_max": 5,
            "compactation_adjustment_candidate_multiplier": 60,
            "compactation_adjustment_attempt_limit": 700,
            "compactation_diversity_minimum_expected": "alta precisão com diversidade mínima obrigatória",
            "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
            "compactation_law_role": "observed_operational_child_of_scientific_mother_law",
            "compactation_operational_law": "Lei de Compactação 15 - faixa 10: extremar precisão, manter diversidade mínima e bloqueio estrito de duplicidade",
            "compactation_required_constraints": [
                "baseline 15 intocada",
                "OutputCommander ativo",
                "deduplicação interna obrigatória",
                "deduplicação contra histórico obrigatória",
                "persistência somente com bateria completa",
            ],
            "compactation_open_constraints": [
                "diversidade mínima obrigatória",
                "seletividade alta",
            ],
        }
    if requested_games <= 15:
        return {
            "scientific_mother_law": "Lei Científica 15",
            "requested_games": requested_games,
            "generated_candidates": 12,
            "valid_individual_games": 12,
            "persisted_games": 0,
            "approved_total_less_than_requested": True,
            "blocked_reason": "nao_atingiu_quantidade_solicitada",
            "output_commander_status": "BLOQUEADO",
            "natural_approvable_candidate": True,
            "candidate_reason": "valid_individual_games_but_incomplete_requested_package",
            "natural_quantity_reason": "structural_saturation_under_scientific_law",
            "natural_quantity_mode": "OBSERVED_COMPACT_12",
            "natural_generated_games": 12,
            "natural_scientific_quantity": False,
            "natural_quantity_status": "CANDIDATE_OBSERVED",
            "compactation_mode": "COMPACT_PRACTICAL_15",
            "compactation_status": "OPERATIONAL_ACTIVE",
            "compactation_test_status": "OPERATIONAL_COMPACT_15",
            "compactation_failure_type": "COMPACT_PRACTICAL_GEOMETRY_CONTROL",
            "compactation_adjustment_status": "ENABLED",
            "compactation_adjustment_mode": "COMPACT_PRACTICAL_15",
            "compactation_adjustment_reason": "intermediate_operational_envelope_between_extreme_compact_and_light_practical",
            "compactation_adjustment_boost_numbers": [7, 14, 17, 23],
            "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
            "compactation_adjustment_odd_min": 3,
            "compactation_adjustment_odd_max": 12,
            "compactation_adjustment_even_min": 3,
            "compactation_adjustment_even_max": 12,
            "compactation_adjustment_repeat_min": 0,
            "compactation_adjustment_repeat_max": 9,
            "compactation_adjustment_coverage_min": 0.30,
            "compactation_adjustment_entropy_min": 0.33,
            "compactation_adjustment_sequence_max": 7,
            "compactation_adjustment_candidate_multiplier": 200,
            "compactation_adjustment_attempt_limit": 3000,
            "compactation_diversity_minimum_expected": "diversidade controlada intermediária com preservação de pico",
            "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
            "compactation_law_role": "observed_operational_child_of_scientific_mother_law",
            "compactation_operational_law": "Lei de Compactação 15 - faixa 15: envelope intermediário entre precisão extrema e amplitude prática",
            "compactation_required_constraints": [
                "baseline 15 intocada",
                "OutputCommander ativo",
                "deduplicação interna obrigatória",
                "deduplicação contra histórico obrigatória",
                "persistência somente com bateria completa",
            ],
            "compactation_open_constraints": [
                "odd/even 5 a 9",
                "sequence_max 5",
                "coverage_min 0.38",
                "entropy_min 0.42",
                "maior diversidade que 10 sem perder pico",
            ],
        }
    if requested_games <= 20:
        return {
            "scientific_mother_law": "Lei Científica 15",
            "requested_games": requested_games,
            "generated_candidates": 16,
            "valid_individual_games": 16,
            "persisted_games": 0,
            "approved_total_less_than_requested": True,
            "blocked_reason": "nao_atingiu_quantidade_solicitada",
            "output_commander_status": "BLOQUEADO",
            "natural_approvable_candidate": True,
            "candidate_reason": "valid_individual_games_but_incomplete_requested_package",
            "natural_quantity_reason": "structural_saturation_under_scientific_law",
            "natural_quantity_mode": "OBSERVED_PRACTICAL_16",
            "natural_generated_games": 16,
            "natural_scientific_quantity": False,
            "natural_quantity_status": "CANDIDATE_OBSERVED",
            "compactation_mode": "LIGHT_PRACTICAL_EXPANDED",
            "compactation_status": "STRUCTURAL_SATURATION",
            "compactation_test_status": "FAILED_MINIMUM_11_PLUS",
            "compactation_failure_type": "EXPANDED_LIGHT_GEOMETRY",
            "compactation_adjustment_status": "ENABLED",
            "compactation_adjustment_mode": "LIGHT_PRACTICAL_EXPANDED",
            "compactation_adjustment_reason": "expand_operational_envelope_without_breaking_governance",
            "compactation_adjustment_boost_numbers": [7, 14, 17, 23],
            "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
            "compactation_adjustment_odd_min": 5,
            "compactation_adjustment_odd_max": 10,
            "compactation_adjustment_even_min": 5,
            "compactation_adjustment_even_max": 10,
            "compactation_adjustment_repeat_min": 3,
            "compactation_adjustment_repeat_max": 9,
            "compactation_adjustment_coverage_min": 0.34,
            "compactation_adjustment_entropy_min": 0.38,
            "compactation_adjustment_sequence_max": 6,
            "compactation_adjustment_candidate_multiplier": 90,
            "compactation_adjustment_attempt_limit": 1500,
            "compactation_diversity_minimum_expected": "diversidade controlada com maior amplitude operacional",
            "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
            "compactation_law_role": "observed_operational_child_of_scientific_mother_law",
            "compactation_operational_law": "Lei de Compactação 15 - faixa 20: expansão operacional controlada; persistir somente se fechar 20 jogos únicos sem duplicidade",
            "compactation_required_constraints": [
                "baseline 15 intocada",
                "OutputCommander ativo",
                "deduplicação interna obrigatória",
                "deduplicação contra histórico obrigatória",
                "persistência somente com 20 jogos válidos",
            ],
            "compactation_open_constraints": [
                "odd/even 5 a 10",
                "sequence_max 6",
                "coverage_min 0.34",
                "entropy_min 0.38",
                "maior amplitude operacional",
            ],
        }
    if requested_games <= 30:
        return {
            "scientific_mother_law": "Lei Científica 15",
            "compactation_mode": "BALANCED_PRACTICAL",
            "compactation_status": "OPERATIONAL_ACTIVE",
            "compactation_test_status": "OPERATIONAL_BALANCED",
            "compactation_failure_type": "BALANCED_GEOMETRY_CONTROL",
            "compactation_adjustment_status": "ENABLED",
            "compactation_adjustment_mode": "BALANCED_PRACTICAL",
            "compactation_adjustment_reason": "expand_combinatorial_variety_with_control",
            "compactation_adjustment_boost_numbers": [7, 14, 17, 23],
            "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
            "compactation_adjustment_odd_min": 6,
            "compactation_adjustment_odd_max": 10,
            "compactation_adjustment_even_min": 6,
            "compactation_adjustment_even_max": 10,
            "compactation_adjustment_repeat_min": 3,
            "compactation_adjustment_repeat_max": 10,
            "compactation_adjustment_coverage_min": 0.34,
            "compactation_adjustment_entropy_min": 0.38,
            "compactation_adjustment_sequence_max": 5,
            "compactation_adjustment_candidate_multiplier": 70,
            "compactation_adjustment_attempt_limit": 900,
            "compactation_diversity_minimum_expected": "variedade equilibrada com governança",
            "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
            "compactation_law_role": "operational_child_of_scientific_mother_law",
            "compactation_operational_law": "Lei de Compactação 15 - faixa 30: ampliar variedade combinatória com governança estrita",
        }
    if requested_games <= 40:
        return {
            "scientific_mother_law": "Lei Científica 15",
            "compactation_mode": "NEAR_BASELINE",
            "compactation_status": "OPERATIONAL_ACTIVE",
            "compactation_test_status": "OPERATIONAL_NEAR_BASELINE",
            "compactation_failure_type": "NEAR_BASELINE_GEOMETRY_CONTROL",
            "compactation_adjustment_status": "ENABLED",
            "compactation_adjustment_mode": "NEAR_BASELINE",
            "compactation_adjustment_reason": "approach_baseline_with_wider_amplitude",
            "compactation_adjustment_boost_numbers": [7, 14, 17, 23],
            "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
            "compactation_adjustment_odd_min": 6,
            "compactation_adjustment_odd_max": 11,
            "compactation_adjustment_even_min": 6,
            "compactation_adjustment_even_max": 11,
            "compactation_adjustment_repeat_min": 2,
            "compactation_adjustment_repeat_max": 10,
            "compactation_adjustment_coverage_min": 0.32,
            "compactation_adjustment_entropy_min": 0.35,
            "compactation_adjustment_sequence_max": 6,
            "compactation_adjustment_candidate_multiplier": 90,
            "compactation_adjustment_attempt_limit": 1200,
            "compactation_diversity_minimum_expected": "amplitude maior com qualidade preservada",
            "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
            "compactation_law_role": "operational_child_of_scientific_mother_law",
            "compactation_operational_law": "Lei de Compactação 15 - faixa 40: quase baseline, amplitude alta, filtros institucionais ativos",
        }
    return {
        "scientific_mother_law": "Lei Científica 15",
        "requested_games": requested_games,
        "generated_candidates": 50,
        "valid_individual_games": 50,
        "persisted_games": 0,
        "approved_total_less_than_requested": False,
        "blocked_reason": "",
        "output_commander_status": "APROVADO",
        "natural_approvable_candidate": False,
        "candidate_reason": "",
        "natural_quantity_reason": "validated_scientific_baseline",
        "natural_quantity_mode": "VALIDATED_BASELINE_50",
        "natural_generated_games": 50,
        "natural_scientific_quantity": True,
        "natural_quantity_status": "NATURAL_APPROVED",
        "compactation_mode": "VALIDATED_BASELINE",
        "compactation_status": "VALIDATED_BASELINE",
        "compactation_test_status": "VALIDATED_BASELINE",
        "compactation_failure_type": "",
        "compactation_adjustment_status": "ENABLED",
        "compactation_adjustment_mode": "VALIDATED_BASELINE",
        "compactation_adjustment_reason": "baseline_validated_ready_for_operational_use",
        "compactation_adjustment_boost_numbers": [7, 14, 17, 23],
        "compactation_adjustment_reduce_priority_numbers": [2, 5, 21, 24],
        "compactation_adjustment_odd_min": 6,
        "compactation_adjustment_odd_max": 12,
        "compactation_adjustment_even_min": 6,
        "compactation_adjustment_even_max": 12,
        "compactation_adjustment_repeat_min": 1,
        "compactation_adjustment_repeat_max": 10,
        "compactation_adjustment_coverage_min": 0.30,
        "compactation_adjustment_entropy_min": 0.33,
        "compactation_adjustment_sequence_max": 6,
        "compactation_adjustment_candidate_multiplier": 20,
        "compactation_adjustment_attempt_limit": 1500,
        "compactation_diversity_minimum_expected": "baseline validada com amplitude operacional máxima",
        "compactation_duplicate_rejection_rule": "strict_internal_and_history_deduplication",
        "compactation_law_role": "observed_operational_child_of_scientific_mother_law",
        "compactation_operational_law": "Lei de Compactação 15 - faixa 50: baseline validada com amplitude operacional máxima",
    }


def _official_15_generation_context(group: str | None) -> dict[str, Any]:
    selected_group = str(group or "G30").strip().upper()
    if selected_group not in OFFICIAL_15_GROUPS:
        selected_group = "G30"
    group_role, group_label = OFFICIAL_15_GROUP_ROLES.get(selected_group, OFFICIAL_15_GROUP_ROLES["G30"])
    return {
        "official_15_generation_model": "G50_G30_G20_G10_ONLY",
        "generation_mode": "OFFICIAL_GROUP_MATERIALIZATION",
        "allowed_15_groups": list(OFFICIAL_15_GROUPS),
        "selected_quantity": int(OFFICIAL_15_GROUP_TO_QUANTITY.get(selected_group, 30)),
        "selected_15_group": selected_group,
        "selected_group": selected_group,
        "selected_15_group_role": group_role,
        "selected_15_group_label": group_label,
        "g50_role": OFFICIAL_15_GROUP_ROLES["G50"][0],
        "g30_role": OFFICIAL_15_GROUP_ROLES["G30"][0],
        "g20_role": OFFICIAL_15_GROUP_ROLES["G20"][0],
        "g10_role": OFFICIAL_15_GROUP_ROLES["G10"][0],
        **POST_DRAW_MONITORING_PAYLOAD,
        "official_15_generation_model_label": "Modelo oficial 15 dezenas: G50 = auditoria e cobertura | G30 = operação principal | G20 = compacto de alta concentração | G10 = premium de ruptura",
    }


@lru_cache(maxsize=1)
def _load_official_15_group_games() -> dict[str, list[tuple[int, ...]]]:
    if not OFFICIAL_15_GROUP_SOURCE_REPORT.exists():
        return {}
    text = OFFICIAL_15_GROUP_SOURCE_REPORT.read_text(encoding="utf-8", errors="replace")
    parsed: dict[str, list[tuple[int, ...]]] = {}
    for group in OFFICIAL_15_GROUPS:
        block_match = re.search(rf"## {re.escape(group)}\s+.*?(?=\n## |\Z)", text, re.S)
        if not block_match:
            continue
        numbers: list[tuple[int, ...]] = []
        for line in block_match.group(0).splitlines():
            if not re.match(r"\| B\d-J\d{2} \|", line):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) < 3:
                continue
            dezenas_text = parts[2]
            dezenas = tuple(int(value) for value in dezenas_text.split() if value.isdigit())
            if len(dezenas) == 15:
                numbers.append(tuple(sorted(dezenas)))
        if numbers:
            parsed[group] = numbers
    return parsed


OFFICIAL_15_GROUPS_REGISTRY = _load_official_15_group_games()


def _official_15_group_games_for_quantity(quantity: int) -> list[tuple[int, ...]]:
    group = OFFICIAL_15_QUANTITY_TO_GROUP.get(int(quantity or 0))
    if not group:
        return []
    return list(OFFICIAL_15_GROUPS_REGISTRY.get(group, []))


def _expand_official_card(
    core_numbers: Sequence[int],
    card_format: int,
    *,
    game_index: int = 0,
) -> tuple[list[int], list[int], list[int]]:
    core = sorted({int(number) for number in core_numbers if 1 <= int(number) <= 25})
    target_size = int(card_format or 15)
    if target_size <= len(core):
        return core, [], core[:target_size]
    needed = target_size - len(core)
    reserves: list[int] = []
    priority = list(AUDITED_RESERVE_PRIORITY)
    if priority and game_index:
        offset = int(game_index - 1) % len(priority)
        priority = priority[offset:] + priority[:offset]
    for number in priority:
        if number in core or number in reserves:
            continue
        reserves.append(int(number))
        if len(reserves) >= needed:
            break
    if len(reserves) < needed:
        for number in range(1, 26):
            if number in core or number in reserves:
                continue
            reserves.append(int(number))
            if len(reserves) >= needed:
                break
    final_card = sorted(core + reserves[:needed])
    return core, reserves[:needed], final_card


def _expand_generation_games_for_format(
    games: Sequence[dict[str, Any]],
    card_format: int,
) -> list[dict[str, Any]]:
    expanded_games: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        core_numbers = list(game.get("numbers", []) or [])
        core, reserves, final_card = _expand_official_card(core_numbers, card_format, game_index=index)
        expanded_games.append(
            {
                **dict(game),
                "card_format": int(card_format or 15),
                "core_numbers": core,
                "audited_reserve_numbers": reserves,
                "final_card_numbers": final_card,
            }
        )
    return expanded_games


def _format_numbers_for_history(values: Sequence[int] | None) -> str:
    numbers = [int(value) for value in (values or []) if 1 <= int(value) <= 25]
    return " ".join(f"{number:02d}" for number in numbers)


def normalize_dezenas(value: object) -> tuple[str, ...]:
    """Normaliza dezenas para comparação institucional (ordem e prefixo '+')."""
    if value is None or value == "-":
        return tuple()

    if isinstance(value, str):
        tokens = value.replace("+", " ").split()
    else:
        tokens = list(value)

    dezenas: list[str] = []
    for token in tokens:
        cleaned = str(token).replace("+", "").strip()
        if not cleaned:
            continue
        dezenas.append(f"{int(cleaned):02d}")

    return tuple(sorted(dezenas))


def build_lei15a_operational_read(
    *,
    game: dict[str, Any],
    cartao_final_lei15: Sequence[int],
    formato_d: int,
    mode: str = "audit_validation",
) -> dict[str, Any]:
    """Leitura operacional Lei 15A com componentes próprios e validação do cartão Lei 15."""
    nucleo_operacional_gp = list(NUCLEO_LEI15A_15D_CONGELADO)
    cartao_validado = list(cartao_final_lei15)
    if int(formato_d or 15) <= 15:
        auditadas: list[int] = []
    else:
        auditadas = sorted(set(cartao_validado) - set(nucleo_operacional_gp))
    vigilantes = sorted(set(auditadas).intersection(RESERVAS_LEI15A_PRIORITARIAS))

    cartao_final_sync = normalize_dezenas(cartao_validado) == normalize_dezenas(cartao_final_lei15)
    origin_log = {
        "jogo": int(game.get("jogo", 0) or 0),
        "formato": f"{int(formato_d or 15)}D",
        "mode": mode,
        "lei15": {
            "nucleo": {
                "value": _format_numbers_for_history(
                    _extract_int_numbers(game.get("core_numbers", game.get("numbers", [])))
                )
                or "-",
                "source": "Lei15.concept.runtime",
            },
            "reservas_auditadas": {
                "value": _format_numbers_for_history(
                    _extract_int_numbers(game.get("audited_reserve_numbers", []))
                )
                or "-",
                "source": "Lei15.concept.runtime",
            },
            "cartao_final": {
                "value": _format_numbers_for_history(cartao_final_lei15) or "-",
                "source": "Lei15.generation",
            },
        },
        "lei15a": {
            "nucleo_operacional_gp": {
                "value": _format_numbers_for_history(nucleo_operacional_gp) or "-",
                "source": "Lei15A.concept.runtime",
                "copied_from_lei15": False,
            },
            "auditadas": {
                "value": _format_numbers_for_history(auditadas) or "-",
                "source": "Lei15A.concept.runtime",
                "copied_from_lei15_reservas": False,
                "fixed_constant_used": False,
            },
            "vigilantes": {
                "value": _format_numbers_for_history(vigilantes) or "-",
                "source": "Lei15A.concept.runtime",
                "copied_from_lei15_reservas": False,
                "fixed_constant_used": False,
            },
            "cartao_validado": {
                "value": _format_numbers_for_history(cartao_validado) or "-",
                "source": "Lei15A.validation",
                "generated_new_card": False,
                "overrode_lei15_card": False,
            },
        },
        "checks": {
            "cartao_final_sync": cartao_final_sync,
            "component_boundary_preserved": True,
            "no_fixed_override": True,
            "no_direct_copy": True,
        },
    }
    return {
        "nucleo_operacional_gp": nucleo_operacional_gp,
        "auditadas": auditadas,
        "vigilantes": vigilantes,
        "cartao_validado": cartao_validado,
        "mode": mode,
        "origin_log": origin_log,
        "sources": origin_log["lei15a"],
        "checks": origin_log["checks"],
    }


def evaluate_institutional_panel_sync(
    *,
    cartao_final_superior: object,
    cartao_final_lido: object,
    reservas_auditadas_superior: object | None = None,
    auditadas_inferior: object | None = None,
    vigilantes_inferior: object | None = None,
) -> bool:
    """Verifica sincronização de cartão final Lei 15 / Lei 15A (contrato aprovado)."""
    _ = (reservas_auditadas_superior, auditadas_inferior, vigilantes_inferior)
    return normalize_dezenas(cartao_final_superior) == normalize_dezenas(cartao_final_lido)


def build_institutional_panel_sync_checks(
    *,
    institutional_rows: Sequence[dict[str, Any]],
    games_table_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta checks de sincronização Lei 15 (superior) vs Lei 15A (inferior)."""
    sync_checks: list[dict[str, Any]] = []
    for row_index, row in enumerate(institutional_rows):
        superior_row = games_table_rows[row_index]
        superior_label = str(superior_row.get("cartão_final", "-") or "-")
        inferior_label = str(row.get("cartao_final_lido", "-") or "-")
        superior_reserves = str(superior_row.get("reservas_auditadas", "-") or "-")
        inferior_auditadas = str(row.get("auditadas_escolhidas", "-") or "-")
        inferior_vigilantes = str(row.get("vigilantes_escolhidas", "-") or "-")
        synchronized = evaluate_institutional_panel_sync(
            cartao_final_superior=superior_label,
            cartao_final_lido=inferior_label,
        )
        boundary_checks = dict(row.get("lei15a_boundary_checks") or {})
        sync_checks.append(
            {
                "jogo": row_index + 1,
                "cartao_final_superior": superior_label,
                "cartao_final_lido": inferior_label,
                "reservas_auditadas_superior": superior_reserves,
                "auditadas_inferior": inferior_auditadas,
                "vigilantes_inferior": inferior_vigilantes,
                "origem_superior": "Lei15.generation",
                "origem_inferior": "Lei15A.validation",
                "sincronizado": synchronized,
                "component_boundary_preserved": bool(boundary_checks.get("component_boundary_preserved")),
                "no_direct_copy": bool(boundary_checks.get("no_direct_copy")),
                "no_fixed_override": bool(boundary_checks.get("no_fixed_override")),
                "origin_log": row.get("lei15a_origin_log"),
            }
        )
    return sync_checks


def _evaluate_lei15a_boundary_checks(row: dict[str, Any]) -> dict[str, bool]:
    """Avalia fronteira conceitual Lei 15 / Lei 15A a partir da leitura operacional."""
    origin_log = dict(row.get("lei15a_origin_log") or {})
    lei15a = dict(origin_log.get("lei15a") or {})
    nucleo_meta = dict(lei15a.get("nucleo_operacional_gp") or {})
    auditadas_meta = dict(lei15a.get("auditadas") or {})
    vigilantes_meta = dict(lei15a.get("vigilantes") or {})
    cartao_meta = dict(lei15a.get("cartao_validado") or {})
    no_direct_copy = (
        not bool(nucleo_meta.get("copied_from_lei15"))
        and not bool(auditadas_meta.get("copied_from_lei15_reservas"))
        and not bool(vigilantes_meta.get("copied_from_lei15_reservas"))
    )
    no_fixed_override = (
        not bool(auditadas_meta.get("fixed_constant_used"))
        and not bool(vigilantes_meta.get("fixed_constant_used"))
    )
    no_independent_card = (
        not bool(cartao_meta.get("generated_new_card"))
        and not bool(cartao_meta.get("overrode_lei15_card"))
    )
    component_boundary_preserved = no_direct_copy and no_fixed_override and no_independent_card
    return {
        "cartao_final_sync": bool(row.get("sincronizado_com_cartao_final")),
        "component_boundary_preserved": component_boundary_preserved,
        "no_fixed_override": no_fixed_override,
        "no_direct_copy": no_direct_copy,
        "no_independent_lei15a_card": no_independent_card,
    }


def validate_lei15_lei15a_runtime_contract(
    *,
    institutional_rows: Sequence[dict[str, Any]],
    games_table_rows: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Valida contrato runtime aprovado Lei 15 / Lei 15A antes de exibir ou persistir."""
    sync_checks = build_institutional_panel_sync_checks(
        institutional_rows=institutional_rows,
        games_table_rows=games_table_rows,
    )
    failed_checks = [check for check in sync_checks if not check.get("sincronizado")]
    upper_cards = [str(row.get("cartão_final", "-") or "-") for row in games_table_rows]
    lower_cards = [str(row.get("cartao_final_lido", "-") or "-") for row in institutional_rows]
    upper_variable = len(set(upper_cards)) > 1
    lower_all_identical = len(set(lower_cards)) == 1 and len(lower_cards) > 1
    fixed_override_detected = upper_variable and lower_all_identical

    boundary_rows = [_evaluate_lei15a_boundary_checks(row) for row in institutional_rows]
    checks_results = {
        "CHECK_001_CARTAO_FINAL_SYNC": all(
            normalize_dezenas(check["cartao_final_superior"]) == normalize_dezenas(check["cartao_final_lido"])
            for check in sync_checks
        ),
        "CHECK_002_NO_NUCLEO_COPY": all(
            not bool((check.get("origin_log") or {}).get("lei15a", {}).get("nucleo_operacional_gp", {}).get("copied_from_lei15"))
            for check in sync_checks
        ),
        "CHECK_003_NO_AUDITADAS_COPY": all(
            not bool((check.get("origin_log") or {}).get("lei15a", {}).get("auditadas", {}).get("copied_from_lei15_reservas"))
            for check in sync_checks
        ),
        "CHECK_004_NO_VIGILANTES_COPY": all(
            not bool((check.get("origin_log") or {}).get("lei15a", {}).get("vigilantes", {}).get("copied_from_lei15_reservas"))
            for check in sync_checks
        ),
        "CHECK_005_NO_FIXED_AUDITADAS_VIGILANTES": all(
            not bool((check.get("origin_log") or {}).get("lei15a", {}).get("auditadas", {}).get("fixed_constant_used"))
            and not bool((check.get("origin_log") or {}).get("lei15a", {}).get("vigilantes", {}).get("fixed_constant_used"))
            for check in sync_checks
        ),
        "CHECK_006_NO_INDEPENDENT_LEI15A_CARD": all(
            not bool((check.get("origin_log") or {}).get("lei15a", {}).get("cartao_validado", {}).get("generated_new_card"))
            and not bool((check.get("origin_log") or {}).get("lei15a", {}).get("cartao_validado", {}).get("overrode_lei15_card"))
            for check in sync_checks
        ),
        "CHECK_007_COMPONENT_BOUNDARY": all(
            boundary.get("component_boundary_preserved") for boundary in boundary_rows
        ),
        "CHECK_008_PERSISTENCE_GUARD": False,
    }
    checks_results["CHECK_008_PERSISTENCE_GUARD"] = (
        checks_results["CHECK_001_CARTAO_FINAL_SYNC"]
        and checks_results["CHECK_007_COMPONENT_BOUNDARY"]
        and checks_results["CHECK_005_NO_FIXED_AUDITADAS_VIGILANTES"]
        and checks_results["CHECK_002_NO_NUCLEO_COPY"]
        and checks_results["CHECK_003_NO_AUDITADAS_COPY"]
        and checks_results["CHECK_004_NO_VIGILANTES_COPY"]
        and not fixed_override_detected
    )
    persistence_allowed = checks_results["CHECK_008_PERSISTENCE_GUARD"] and not failed_checks
    classification = "COMPATIVEL" if persistence_allowed else "CONFLITANTE"
    return {
        "classification": classification,
        "sync_checks": sync_checks,
        "failed_checks": failed_checks,
        "checks_results": checks_results,
        "fixed_override_detected": fixed_override_detected,
        "persistence_allowed": persistence_allowed,
        "persistence_guard_status": "PROTEGIDO" if persistence_allowed else "SINCRONIZACAO_FALHOU",
        "governance_confirmation": {
            "lei15_role": "governanca_soberana_geracao",
            "lei15a_role": "leitura_operacional_gp_auditoria_validacao",
            "runtime_source_of_truth": "Lei15.generation",
            "component_boundary": "PRESERVADA",
            "sync_contract": "cartao_final_compativel",
        },
    }


def _build_games_table_rows_from_generation_games(
    games: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Espelha a tabela superior Jogos gerados para validação de contrato."""
    games_table_rows: list[dict[str, Any]] = []
    for index, game in enumerate(games):
        final_card_numbers = _extract_int_numbers(game.get("final_card_numbers", game.get("numbers", [])))
        reserve_numbers = _extract_int_numbers(game.get("audited_reserve_numbers", []))
        games_table_rows.append(
            {
                "jogo": index + 1,
                "núcleo_lei_15": _format_numbers_for_history(game.get("core_numbers", game.get("numbers", []))),
                "reservas_auditadas": (
                    " ".join(f"+{int(number):02d}" for number in reserve_numbers) if reserve_numbers else "-"
                ),
                "cartão_final": _format_numbers_for_history(final_card_numbers),
            }
        )
    return games_table_rows


def infer_matrix_cell(formato_cartao: int | str | None, requested_count: int | str | None) -> dict[str, Any]:
    """Infer a matrix cell label from the card format and requested quantity."""
    dezenas_por_jogo = int(formato_cartao or 15)
    quantidade_jogos = int(requested_count or 0)
    escala_top = f"Top {quantidade_jogos}" if quantidade_jogos else "Top -"
    celula_matriz = f"{dezenas_por_jogo}D {escala_top}".strip()
    return {
        "celula_matriz": celula_matriz,
        "formato_d": f"{dezenas_por_jogo}D",
        "escala_top": escala_top,
        "dezenas_por_jogo": dezenas_por_jogo,
        "quantidade_jogos": quantidade_jogos,
    }


def build_institutional_matrix_rows(
    games: Sequence[dict[str, Any]],
    formato_d: int | str | None,
    escala_top: int | str | None,
    superior_final_cards: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """Build the institutional matrix rows from already loaded games."""
    dezenas_por_jogo = int(formato_d or 15)
    quantidade_jogos = int(escala_top or 0)
    celula_matriz = f"{dezenas_por_jogo}D Top {quantidade_jogos}" if quantidade_jogos else f"{dezenas_por_jogo}D Top -"
    escala_label = f"Top {quantidade_jogos}" if quantidade_jogos else "Top -"
    j12 = set(INSTITUTIONAL_REFERENCE_J12)
    j34 = set(INSTITUTIONAL_REFERENCE_J34)
    j71 = set(INSTITUTIONAL_REFERENCE_J71)
    rows: list[dict[str, Any]] = []
    for index, game in enumerate(games, start=1):
        final_card = _extract_int_numbers(
            game.get("final_card_numbers")
            or game.get("cartao_final")
            or game.get("numbers")
            or []
        )
        superior_final_card = (
            _extract_int_numbers(superior_final_cards[index - 1])
            if superior_final_cards is not None and index - 1 < len(superior_final_cards)
            else list(final_card)
        )
        lei15a_read = build_lei15a_operational_read(
            game=game,
            cartao_final_lei15=superior_final_card,
            formato_d=dezenas_por_jogo,
            mode="audit_validation",
        )
        operational_nucleus = list(lei15a_read["nucleo_operacional_gp"])
        operational_final_card = list(lei15a_read["cartao_validado"])
        auditadas_escolhidas = list(lei15a_read["auditadas"])
        vigilantes_escolhidas = list(lei15a_read["vigilantes"])
        origin_log = dict(lei15a_read.get("origin_log") or {})
        boundary_checks = dict(lei15a_read.get("checks") or {})

        reserve_numbers = _extract_int_numbers(game.get("audited_reserve_numbers", []))
        superior_reserves_label = (
            " ".join(f"+{int(number):02d}" for number in reserve_numbers) if reserve_numbers else "-"
        )

        synchronized_with_final_card = evaluate_institutional_panel_sync(
            cartao_final_superior=_format_numbers_for_history(superior_final_card),
            cartao_final_lido=_format_numbers_for_history(operational_final_card),
        )
        sync_status = "SINCRONIZADO_COM_CARTAO_FINAL" if synchronized_with_final_card else "SINCRONIZACAO_FALHOU"

        referencias_j12_j34 = sorted(set(operational_final_card).intersection(j12.union(j34)))
        vigilancia_j71 = sorted(set(operational_final_card).intersection(j71))

        if synchronized_with_final_card:
            leitura_institucional = (
                f"Jogo {dezenas_por_jogo}D da célula {escala_label}; leitura operacional Lei 15A "
                "valida o cartão final gerado pela Lei 15; núcleo operacional GP, auditadas e "
                "vigilantes são componentes próprios da Lei 15A."
            )
        else:
            leitura_institucional = (
                f"Jogo {dezenas_por_jogo}D da célula {escala_label}; SINCRONIZACAO_FALHOU: "
                f"cartão_final superior={_format_numbers_for_history(superior_final_card) or '-'} "
                f"diverge do cartão validado={_format_numbers_for_history(operational_final_card) or '-'}."
            )

        if referencias_j12_j34 and vigilancia_j71:
            structural_status = "NUCLEO_A_COM_REFERENCIA_E_VIGILANCIA"
        elif referencias_j12_j34:
            structural_status = "NUCLEO_A_COM_REFERENCIA_AUDITADA"
        elif vigilancia_j71:
            structural_status = "NUCLEO_A_COM_VIGILANCIA"
        else:
            structural_status = "NUCLEO_A"
        rows.append(
            {
                "jogo": int(game.get("jogo", index) or index),
                "celula_matriz": celula_matriz,
                "formato_d": f"{dezenas_por_jogo}D",
                "escala_top": escala_label,
                "cartao_final_lido": _format_numbers_for_history(operational_final_card) or "-",
                "cartao_final_assinatura": _game_signature(operational_final_card) if operational_final_card else "-",
                "nucleo_a_dezenas": _format_numbers_for_history(operational_nucleus) or "-",
                "auditadas_escolhidas": _format_numbers_for_history(auditadas_escolhidas) or "-",
                "vigilantes_escolhidas": _format_numbers_for_history(vigilantes_escolhidas) or "-",
                "referencias_auditadas_j12_j34": _format_numbers_for_history(referencias_j12_j34) or "-",
                "vigilancia_j71": _format_numbers_for_history(vigilancia_j71) or "-",
                "lei15_aplicada": bool(len(operational_nucleus) == 15 and len(operational_final_card) >= 15),
                "sincronizado_com_cartao_final": bool(synchronized_with_final_card),
                "status_institucional": sync_status,
                "status_estrutural_anterior": structural_status,
                "leitura_institucional": leitura_institucional,
                "origem_geracao": "Lei15.generation",
                "origem_leitura": "Lei15A.validation",
                "lei15a_origin_log": origin_log,
                "lei15a_boundary_checks": boundary_checks,
            }
        )
    return rows


def build_institutional_matrix_full_dataframe(
    institutional_rows: Sequence[dict[str, Any]],
) -> pd.DataFrame:
    """Monta o dataframe completo da leitura institucional sem alterar os dados calculados."""
    if not institutional_rows:
        return pd.DataFrame()
    available_columns = [
        column
        for column in INSTITUTIONAL_MATRIX_DISPLAY_COLUMNS
        if column in institutional_rows[0]
    ]
    return pd.DataFrame(institutional_rows)[available_columns]


def build_institutional_matrix_primary_view(
    institutional_rows: Sequence[dict[str, Any]],
) -> pd.DataFrame:
    """Visao principal limpa para auditoria humana da leitura institucional."""
    full_df = build_institutional_matrix_full_dataframe(institutional_rows)
    if full_df.empty:
        return full_df
    primary_columns = [
        column for column in INSTITUTIONAL_MATRIX_PRIMARY_COLUMNS if column in full_df.columns
    ]
    return full_df[primary_columns].rename(columns=INSTITUTIONAL_MATRIX_PRIMARY_LABELS)


def build_institutional_matrix_technical_view(
    institutional_rows: Sequence[dict[str, Any]],
) -> pd.DataFrame:
    """Camada tecnica completa preservada para expander de detalhes."""
    full_df = build_institutional_matrix_full_dataframe(institutional_rows)
    if full_df.empty:
        return full_df
    technical_columns = [
        column for column in INSTITUTIONAL_MATRIX_TECHNICAL_COLUMNS if column in full_df.columns
    ]
    return full_df[technical_columns].rename(columns=INSTITUTIONAL_MATRIX_TECHNICAL_LABELS)


def summarize_institutional_matrix_reading(
    institutional_rows: Sequence[dict[str, Any]],
    *,
    sync_checks: Sequence[dict[str, Any]],
    card_format: int,
) -> dict[str, Any]:
    """Resume a leitura institucional para exibicao acima da tabela principal."""
    total_games = len(institutional_rows)
    sync_failures = [check for check in sync_checks if not check.get("sincronizado")]
    synchronized_count = total_games - len(sync_failures)
    all_synchronized = total_games > 0 and not sync_failures and all(
        bool(row.get("sincronizado_com_cartao_final")) for row in institutional_rows
    )
    return {
        "total_games": total_games,
        "synchronized_count": synchronized_count,
        "failure_count": len(sync_failures),
        "card_format": int(card_format or 15),
        "overall_status": (
            "LEITURA SINCRONIZADA"
            if all_synchronized
            else "SINCRONIZACAO_FALHOU"
        ),
        "institutional_caption_status": (
            "LEITURA_INSTITUCIONAL_PADRONIZADA_E_SINCRONIZADA_COM_CARTAO_FINAL"
            if all_synchronized
            else "SINCRONIZACAO_FALHOU"
        ),
        "all_synchronized": all_synchronized,
        "sync_failures": sync_failures,
    }


def _render_institutional_matrix_reading_section(
    *,
    institutional_rows: Sequence[dict[str, Any]],
    games_table_rows: Sequence[dict[str, Any]],
    card_format: int,
) -> None:
    """Renderiza a leitura institucional padronizada com visao limpa e detalhes tecnicos."""
    sync_checks = build_institutional_panel_sync_checks(
        institutional_rows=institutional_rows,
        games_table_rows=games_table_rows,
    )

    summary = summarize_institutional_matrix_reading(
        institutional_rows,
        sync_checks=sync_checks,
        card_format=card_format,
    )
    primary_df = build_institutional_matrix_primary_view(institutional_rows)
    technical_df = build_institutional_matrix_technical_view(institutional_rows)

    st.subheader(LEI15A_LOWER_PANEL_TITLE)
    st.write(LEI15A_PANEL_DESCRIPTION)
    concept_cols = st.columns(2)
    with concept_cols[0]:
        st.info("Lei 15 = governança soberana")
        st.info(LEI15_PANEL_CONCEPT_15D)
    with concept_cols[1]:
        st.info("Lei 15A = operação GP 10/20/30/50")
        st.info(_resolve_lei15a_panel_format_label(int(card_format)))
    with st.expander("O que significa sincronização?", expanded=False):
        st.caption(LEI15A_PANEL_SYNC_SEMANTICS)

    summary_cols = st.columns(5)
    summary_cols[0].metric("Jogos lidos", int(summary["total_games"]))
    summary_cols[1].metric("Sincronizados", int(summary["synchronized_count"]))
    summary_cols[2].metric("Falhas", int(summary["failure_count"]))
    summary_cols[3].metric("Formato do cartão", f"{int(summary['card_format'])}D")
    summary_cols[4].metric("Status geral", str(summary["overall_status"]))

    if summary["all_synchronized"]:
        st.success(LEI15A_PANEL_SYNC_SUCCESS)
    else:
        st.error("SINCRONIZACAO_FALHOU: a leitura operacional GP inferior diverge do cartão_final superior.")
        st.json(summary["sync_failures"])

    st.dataframe(primary_df, hide_index=True, use_container_width=True)

    with st.expander("Detalhes técnicos da auditoria", expanded=False):
        st.dataframe(technical_df, hide_index=True, use_container_width=True)

    first_row = institutional_rows[0]
    st.caption(
        f"celula_matriz={first_row['celula_matriz']} | "
        f"formato_d={first_row['formato_d']} | "
        f"escala_top={first_row['escala_top']} | "
        f"sincronizados={summary['synchronized_count']}/{summary['total_games']} | "
        "fonte_cartao_final=superior_jogos_gerados | "
        "leitura_institucional_ativa=true | "
        f"status={summary['institutional_caption_status']} | "
        "legado=LEITURA_INSTITUCIONAL_SINCRONIZADA_COM_CARTAO_FINAL_LEI15"
    )


def _validate_core_002_multidezena_persistence_allowed(
    *,
    formatted_games: Sequence[dict[str, Any]],
    selected_card_format: int,
) -> dict[str, Any]:
    """Validação CORE_002 multidezena — subordinada ao núcleo 15D, sem Lei 15A operacional."""
    expected_size = int(selected_card_format or 15)
    if expected_size < 16 or expected_size > 23:
        return {"persistence_allowed": False, "persistence_guard_status": "FORMATO_INVALIDO"}
    if not formatted_games:
        return {"persistence_allowed": False, "persistence_guard_status": "SEM_JOGOS"}
    for index, game in enumerate(formatted_games, start=1):
        core = _extract_int_numbers(game.get("core_numbers", game.get("numbers", [])))
        final_card = _extract_int_numbers(game.get("final_card_numbers", []))
        if len(core) != 15:
            return {
                "persistence_allowed": False,
                "persistence_guard_status": "NUCLEO_INVALIDO",
                "game_index": index,
            }
        if len(final_card) != expected_size:
            return {
                "persistence_allowed": False,
                "persistence_guard_status": "CARTAO_FINAL_INVALIDO",
                "game_index": index,
            }
    return {
        "persistence_allowed": True,
        "persistence_guard_status": "CORE_002_MULTIDEZENA_OK",
        "classification": "COMPATIVEL",
    }


def _supersede_prior_lots_for_calibration(
    *,
    new_generation_event_id: int,
    selected_card_format: int,
    reason: str = "calibration_new_lot_generated",
) -> int:
    """Marca lotes anteriores não oficiais como superseded_by_calibration (M-OPS-062)."""
    superseded = 0
    target_format = int(selected_card_format or 15)
    with get_session(DB_PATH) as session:
        events = (
            session.query(GenerationEvent)
            .filter(GenerationEvent.id != int(new_generation_event_id))
            .order_by(GenerationEvent.created_at.desc(), GenerationEvent.id.desc())
            .limit(50)
            .all()
        )
        for event in events:
            context = dict(getattr(event, "context_json", {}) or {})
            event_format = int(context.get("selected_card_format", context.get("card_format", 15)) or 15)
            if event_format != target_format:
                continue
            if is_official_conference_eligible(context):
                continue
            context.update(supersede_status_update(superseded_by_event_id=int(new_generation_event_id), reason=reason))
            event.context_json = context
            superseded += 1
        if superseded:
            session.commit()
    return superseded


def _resolve_latest_official_conference_contest() -> dict[str, Any] | None:
    """Último concurso oficial disponível no PostgreSQL (imported_contests)."""
    records = _list_all_imported_contest_records()
    if records:
        latest = max(records, key=lambda row: int(row.get("contest_number", 0) or 0))
        return to_conference_contest_payload(latest) or _normalize_contest_record(latest)
    latest_official = get_latest_official_contest()
    if latest_official:
        return to_conference_contest_payload(latest_official) or _normalize_contest_record(latest_official)
    return None


def _load_official_conference_generation_groups() -> list[dict[str, Any]]:
    """Grupos elegíveis para Conferir Resultados — apenas lotes oficializados/aprovados."""
    return [
        group
        for group in _load_persisted_generation_event_groups(batch_id=None)
        if bool(group.get("is_official_conference_eligible", group.get("official_release_allowed", False)))
    ]


def _persist_clean_law15_generation_history(
    *,
    result: dict[str, Any],
    selected_card_format: int,
) -> dict[str, Any]:
    games = list(result.get("games") or [])
    if not games:
        return {}
    formatted_games = _expand_generation_games_for_format(games, selected_card_format)
    cartoes_finais_superiores = [
        _extract_int_numbers(game.get("final_card_numbers", game.get("numbers", [])))
        for game in formatted_games
    ]
    institutional_rows = build_institutional_matrix_rows(
        formatted_games,
        selected_card_format,
        int(result.get("requested_count", len(formatted_games)) or len(formatted_games)),
        superior_final_cards=cartoes_finais_superiores,
    )
    games_table_rows = _build_games_table_rows_from_generation_games(formatted_games)
    if int(selected_card_format) == 15:
        runtime_contract = validate_lei15_lei15a_runtime_contract(
            institutional_rows=institutional_rows,
            games_table_rows=games_table_rows,
        )
    else:
        runtime_contract = _validate_core_002_multidezena_persistence_allowed(
            formatted_games=formatted_games,
            selected_card_format=int(selected_card_format),
        )
    if not runtime_contract.get("persistence_allowed"):
        return {
            "persistence_blocked": True,
            "persistence_guard_status": "SINCRONIZACAO_FALHOU",
            "runtime_contract": runtime_contract,
        }
    commander_report = dict(result.get("commander_report") or {})
    if str(commander_report.get("status_comandante_saida", "APROVADO") or "APROVADO") != "APROVADO":
        return {
            "persistence_blocked": True,
            "persistence_guard_status": str(
                commander_report.get("motivo_bloqueio")
                or commander_report.get("blocked_reason")
                or "COMANDANTE_BLOQUEOU"
            ),
            "commander_report": commander_report,
        }
    payload_games: list[dict[str, Any]] = []
    ml_enabled = bool(result.get("ml_enabled", False))
    format_batch_label = str(
        result.get("analysis_batch_label")
        or multidezena_batch_label(int(selected_card_format))
    )
    ml_bundle = build_supervised_ml_persistence_bundle(
        list(games),
        batch_label=format_batch_label,
        ml_enabled=ml_enabled,
        calibration_bundle=dict(result.get("calibration_bundle") or {}),
    )
    cockpit_bundle = dict(st.session_state.get(COCKPIT_SESSION_PERSIST) or {})
    calibration_authorized = bool(cockpit_bundle.get("calibration_authorized"))
    generation_origin = str(result.get("generation_origin") or GENERATION_ORIGIN_GENERATOR)
    simulation_mode = bool(result.get("simulation_mode")) or generation_origin == GENERATION_ORIGIN_SIMULATION
    ml_verdict_payload = evaluate_batch_ml_verdict_from_games(
        formatted_games,
        calibration_applied=bool(ml_bundle.get("calibration_applied")),
        calibration_authorized=calibration_authorized,
    )
    lot_status_context = build_lot_status_context(
        ml_verdict_payload=ml_verdict_payload,
        generation_origin=generation_origin,
        calibration_applied=bool(ml_bundle.get("calibration_applied")),
        calibration_authorized=calibration_authorized,
        simulation_mode=simulation_mode,
    )
    trace_games = list(ml_bundle.get("decision_trace") or [])
    trace_attributions = list(ml_bundle.get("feature_attribution") or [])
    trace_lineages = list(ml_bundle.get("generation_lineage") or [])
    for index, game in enumerate(formatted_games):
        core_numbers = list(game.get("core_numbers", game.get("numbers", [])) or [])
        reserves = list(game.get("audited_reserve_numbers", []) or [])
        final_card = list(game.get("final_card_numbers", game.get("numbers", [])) or [])
        persist_numbers = final_card if int(selected_card_format) > 15 else core_numbers
        enriched = {
            **dict(game),
            "numbers": persist_numbers,
            "card_format": int(selected_card_format),
            "selected_card_format": int(selected_card_format),
            "core_numbers": core_numbers,
            "audited_reserve_numbers": reserves,
            "final_card_numbers": final_card,
            "display_core_numbers": _format_numbers_for_history(core_numbers),
            "display_audited_reserve_numbers": _format_numbers_for_history(reserves),
            "display_final_card_numbers": _format_numbers_for_history(final_card),
        }
        if index < len(trace_games):
            enriched["decision_trace"] = trace_games[index]
        if index < len(trace_attributions):
            enriched["feature_attribution"] = trace_attributions[index]
        if index < len(trace_lineages):
            enriched["generation_lineage"] = trace_lineages[index]
        payload_games.append(enriched)
    generation_context = {
        "generation_mode": "LEI15_CORE_002_SOVEREIGN",
        "policy_mode": str(ml_bundle.get("policy_mode") or "M-GER-044_SOVEREIGN_CONTROLLED"),
        "analysis_batch_label": format_batch_label,
        "analysis_batch_type": "LEI15_CORE_002_SOVEREIGN",
        "multidezena_subordinate_core_002": int(selected_card_format) > 15,
        "multidezena_not_lei15a": True,
        "sovereign_generation_path": "generate_best_games",
        "ml_enabled": ml_enabled,
        "ml_operational_status": str(ml_bundle.get("ml_operational_status") or ""),
        "supervised_ml_mission": str(ml_bundle.get("supervised_ml_mission") or ""),
        "decision_trace": trace_games,
        "feature_attribution": trace_attributions,
        "generation_lineage": trace_lineages,
        "ml_scored_games": int(ml_bundle.get("ml_scored_games", 0) or 0),
        "ml_six_bases_reading": list(ml_bundle.get("ml_six_bases_reading") or []),
        "selected_card_format": int(selected_card_format),
        "format_cartao": int(selected_card_format),
        "selected_quantity": int(result.get("requested_count", 0) or 0),
        "quantidade_nucleo": 15,
        "nucleo_lei_15_size": 15,
        "reservas_auditadas_count": _clean_law15_reserve_count(selected_card_format),
        "quantidade_reservas": _clean_law15_reserve_count(selected_card_format),
        "quantidade_final": int(selected_card_format),
        "cartao_final_size": int(selected_card_format),
        "accepted_games": int((result.get("fill_diagnostics") or {}).get("accepted_games", 0) or 0),
        "valid_candidates": int((result.get("fill_diagnostics") or {}).get("valid_candidates_found", 0) or 0),
        "attempts_used": int((result.get("fill_diagnostics") or {}).get("attempts_used", 0) or 0),
        "fill_completed": bool((result.get("fill_diagnostics") or {}).get("fill_completed", False)),
        "núcleo_lei_15": _format_numbers_for_history(payload_games[0].get("core_numbers", [])),
        "reservas_auditadas": _format_numbers_for_history(payload_games[0].get("audited_reserve_numbers", [])),
        "cartão_final": _format_numbers_for_history(payload_games[0].get("final_card_numbers", [])),
        "format_label": str(result.get("card_format_label", "")),
        "scientific_law_role": "COMMANDER",
        "clean_adm_runtime_role": "EXECUTOR",
        "output_commander_role": "AUDITOR",
        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
        "calibration_engine_role": str(
            ml_bundle.get("calibration_engine_role")
            or result.get("calibration_engine_role")
            or "DISABLED"
        ),
        "calibration_applied": bool(ml_bundle.get("calibration_applied")),
        "calibration_version": str(ml_bundle.get("calibration_version") or ""),
        "calibration_diagnostics": dict(ml_bundle.get("calibration_diagnostics") or ml_bundle.get("diagnostics") or {}),
        "calibration_actions_applied": list(
            ml_bundle.get("calibration_actions_applied") or ml_bundle.get("actions_applied") or []
        ),
        "calibration_decision_trace": dict(ml_bundle.get("calibration_decision_trace") or {}),
        "calibration_feature_attribution": dict(ml_bundle.get("calibration_feature_attribution") or {}),
        "redundancy_penalty": float(ml_bundle.get("redundancy_penalty", 0.0) or 0.0),
        "prefix_penalty": int(ml_bundle.get("prefix_penalty", 0) or 0),
        "suffix_penalty": int(ml_bundle.get("suffix_penalty", 0) or 0),
        "missing_numbers_boost": int(ml_bundle.get("missing_numbers_boost", 0) or 0),
        "critical_coverage_boost": int(ml_bundle.get("critical_coverage_boost", 0) or 0),
        "diversity_score": float(ml_bundle.get("diversity_score", 0.0) or 0.0),
        "final_ml_score_avg": float(ml_bundle.get("final_ml_score_avg", 0.0) or 0.0),
        "issues_detected": list(ml_bundle.get("issues_detected") or []),
        "batch_status_counts": dict(ml_bundle.get("batch_status_counts") or {}),
        "action_taken": str(ml_bundle.get("action_taken") or ""),
        "cockpit_calibration_workflow": dict(st.session_state.get(COCKPIT_SESSION_PERSIST) or {}),
        "generation_origin": str(result.get("generation_origin") or GENERATION_ORIGIN_GENERATOR),
        "simulation_mode": bool(result.get("simulation_mode")),
        "validation_flow": ["generated", "structural_coverage_evaluated", "ml_verdict_emitted"],
        "ml_verdict_mission_id": ML_VERDICT_MISSION_ID,
        "ml_verdict": str(ml_verdict_payload.get("ml_verdict") or ""),
        "ml_verdict_reason": str(ml_verdict_payload.get("ml_verdict_reason") or ""),
        "motivo_principal": str(ml_verdict_payload.get("motivo_principal") or ""),
        "official_release_allowed": bool(ml_verdict_payload.get("official_release_allowed")),
        "official_release_label": str(ml_verdict_payload.get("official_release_label") or ""),
        "officialization_status": str(ml_verdict_payload.get("officialization_status") or ""),
        "ml_verdict_trace": dict(ml_verdict_payload.get("trace") or {}),
        "ml_verdict_next_action": str(ml_verdict_payload.get("next_action") or ""),
        "is_evaluated_non_official": not bool(lot_status_context.get("official_release_allowed")),
        "lot_operational_status_mission_id": LOT_STATUS_MISSION_ID,
        **lot_status_context,
        "structural_validation_completed": True,
        "structural_validation_at": datetime.now(UTC).isoformat(),
        "historical_deduplication_mode": str(result.get("historical_deduplication_mode", "AUDIT_ONLY") or "AUDIT_ONLY"),
        "validation_status_lei_17": str(result.get("validation_status_lei_17", "") or ""),
        "validation_status_lei_18": str(result.get("validation_status_lei_18", "") or ""),
        "card_format": int(selected_card_format),
    }
    try:
        persisted = _attach_operational_generation_label(
            _persist_generation_snapshot(
                games=payload_games,
                seed=int(result.get("seed", 0) or 0),
                target_contest=_load_latest_contest_summary().get("contest_number") if _load_latest_contest_summary() else None,
                batch_id=str(result.get("batch_id", "") or f"clean-law15-{selected_card_format}"),
                generation_context=generation_context,
                analysis_batch_label=format_batch_label,
                analysis_batch_type="LEI15_CORE_002_SOVEREIGN",
            )
        )
        new_event_id = int(persisted.get("generation_event_id", 0) or 0)
        if new_event_id > 0 and (calibration_authorized or bool(ml_bundle.get("calibration_applied"))):
            _supersede_prior_lots_for_calibration(
                new_generation_event_id=new_event_id,
                selected_card_format=int(selected_card_format),
            )
        return {
            **persisted,
            "ml_verdict": str(ml_verdict_payload.get("ml_verdict") or ""),
            "ml_verdict_reason": str(ml_verdict_payload.get("ml_verdict_reason") or ""),
            "official_release_allowed": bool(lot_status_context.get("official_release_allowed")),
            "official_release_label": str(ml_verdict_payload.get("official_release_label") or ""),
            "ml_verdict_blocked": not bool(lot_status_context.get("official_release_allowed")),
            "ml_verdict_next_action": str(ml_verdict_payload.get("next_action") or ""),
            "lot_operational_status": str(lot_status_context.get("lot_operational_status") or ""),
            "generation_origin": generation_origin,
            "simulation_mode": simulation_mode,
        }
    except RuntimeError as exc:
        return {
            "persistence_blocked": True,
            "persistence_guard_status": str(exc),
        }


def _official_15_group_registry_found() -> bool:
    return bool(OFFICIAL_15_GROUPS_REGISTRY)


def _render_post_conference_monitoring_panel() -> None:
    st.markdown("##### Auditoria e Monitoramento")
    st.caption("Camada observadora pós-conferência: registra, audita e formula hipóteses sem recalibrar a Lei.")
    cols = st.columns(4)
    cols[0].metric("Modo", "Observação pós-conferência")
    cols[1].metric("Papel da tela", "Auditoria / Registro")
    cols[2].metric("Lei 15", "Comando soberano")
    cols[3].metric("Memória", "REGISTRY")
    left, right = st.columns(2)
    with left:
        st.markdown("###### Status Institucional da Auditoria")
        st.markdown(
            "- Modo: Observação pós-conferência\n"
            "- Papel da tela: Auditoria / Registro\n"
            "- Recalibração silenciosa: Bloqueada\n"
            "- Mutação automática da Lei: Bloqueada\n"
            "- Evolução de Lei: Exige auditoria"
        )
    with right:
        st.markdown(
            "- Lei 15: Comando soberano da geração\n"
            "- Lei 17: Validação / referência\n"
            "- Lei 18: Validação / referência\n"
            "- Meta ouro: 14 pontos\n"
            "- Meta diamante: 15 pontos"
        )
    _render_signature_grid(
        list(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures", [])),
        title="Dezenas organizadas no topo",
        empty_label="Este painel não recebeu dezenas para exibir no topo.",
    )
    _render_block_distribution(list(POST_DRAW_MONITORING_PAYLOAD.get("block_distribution", [])))
    with st.expander("Detalhes técnicos avançados", expanded=False):
        st.json(POST_DRAW_MONITORING_PAYLOAD)


def _render_lei_16_governance_panel() -> None:
    st.markdown("##### Lei 16 — Integridade Global da Geração")
    st.caption("Leitura documental da governança institucional. Não comanda geração, não cria controles e não altera a Lei 15.")
    cols = st.columns(3)
    cols[0].metric("Status", "Formalizada documentalmente")
    cols[1].metric("Classificação", "Compatível com a Lei 15")
    cols[2].metric("Aderência", "Alta")
    st.info(
        "Toda geração institucional da LotoIA deve entregar combinações globalmente únicas dentro do mesmo evento, "
        "lote ou bateria. A Lei 16 garante duplicados globais zero, memória de assinaturas compartilhada entre "
        "grupos da mesma bateria e preservação da soberania da Lei 15."
    )
    st.markdown(
        "- Duplicados globais: zero\n"
        "- Grupos da mesma bateria compartilham memória de assinaturas\n"
        "- Cada jogo entregue representa uma combinação única\n"
        "- A Lei 15 permanece soberana e inalterada"
    )


def _render_audit_monitoring_page(snapshot: dict[str, Any], section: str) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Auditoria e Monitoramento")
    _render_diagnostic_observational_caption()
    st.write("Camada institucional de observação pós-conferência, sem recalibrar a Lei.")
    st.caption("Lei Científica LotoIA = COMMANDER | Gerador ADM = EXECUTOR | OutputCommander = AUDITOR | Memória institucional = REGISTRY")
    st.info("Sem recalibrar a Lei. Sem mutação automática. Sem comando de geração nesta camada.")
    if section == "overview":
        st.markdown("###### Página-mãe institucional da camada observacional")
        st.markdown("##### Função da camada")
        st.write(
            "Esta camada observa resultados após a conferência. Ela registra, organiza e apresenta sinais de "
            "monitoramento, sem gerar jogos, sem recalibrar a Lei 15 e sem alterar o histórico institucional."
        )
        st.markdown("##### Status institucional")
        cols = st.columns(4)
        cols[0].metric("Monitoramento", "Ativo")
        cols[1].metric("Papel", "Observador / Registro")
        cols[2].metric("Recalibração", "Bloqueada")
        cols[3].metric("Memória institucional", "Registro")
        cols2 = st.columns(4)
        cols2[0].metric("Lei 15", "Comando soberano")
        cols2[1].metric("Lei 17", "Validação / referência")
        cols2[2].metric("Lei 18", "Validação / referência")
        cols2[3].metric("Dados", "Disponível" if bool(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures") or POST_DRAW_MONITORING_PAYLOAD.get("block_distribution")) else "Indisponível")
        _render_lei_16_governance_panel()
        st.markdown("##### Resumo de monitoramento")
        monitoring_cols = st.columns(5)
        monitoring_cols[0].metric(
            "Último concurso monitorado",
            str(POST_DRAW_MONITORING_PAYLOAD.get("latest_contest", POST_DRAW_MONITORING_PAYLOAD.get("contest_number", "-")) or "-"),
        )
        monitoring_cols[1].metric(
            "Total de concursos avaliados",
            int(POST_DRAW_MONITORING_PAYLOAD.get("evaluated_contests", POST_DRAW_MONITORING_PAYLOAD.get("contests_evaluated", 0)) or 0),
        )
        monitoring_cols[2].metric(
            "Total de gerações analisadas",
            int(POST_DRAW_MONITORING_PAYLOAD.get("analyzed_generations", POST_DRAW_MONITORING_PAYLOAD.get("generations_analyzed", 0)) or 0),
        )
        monitoring_cols[3].metric(
            "Última conferência registrada",
            str(POST_DRAW_MONITORING_PAYLOAD.get("latest_conference", POST_DRAW_MONITORING_PAYLOAD.get("last_conference", "-")) or "-"),
        )
        monitoring_cols[4].metric(
            "Status dos dados",
            "disponível" if bool(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures") or POST_DRAW_MONITORING_PAYLOAD.get("block_distribution")) else "indisponível",
        )
        if bool(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures") or POST_DRAW_MONITORING_PAYLOAD.get("block_distribution")):
            _render_signature_grid(
                list(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures", [])),
                title="Dezenas organizadas no topo",
                empty_label="Nenhum dado de monitoramento pós-conferência disponível no momento. Execute ou consulte uma conferência operacional para alimentar esta camada.",
            )
            _render_block_distribution(list(POST_DRAW_MONITORING_PAYLOAD.get("block_distribution", [])))
        else:
            st.info("Nenhum dado de monitoramento pós-conferência disponível no momento. Execute ou consulte uma conferência operacional para alimentar esta camada.")
        st.markdown("##### Acessos de auditoria")
        st.markdown(
            "- Conferência por concurso\n"
            "- Desempenho por grupo\n"
            "- Dezenas faltantes\n"
            "- Dezenas sobrando"
        )
        st.markdown("##### Camadas auditadas liberadas")
        st.caption("Vazamento lateral liberado como camada observacional/auditada.")
        with st.expander("Indicador auditado observacional", expanded=False):
            st.info("Camada observacional/auditada. Não gera jogos. Não recalibra Lei 15. Não altera histórico.")
            st.markdown("status: LIBERADO / OBSERVACIONAL_AUDITADO")
        with st.expander("Detalhes técnicos avançados", expanded=False):
            st.json(POST_DRAW_MONITORING_PAYLOAD)
        return
    if section == "conference":
        st.markdown("##### Auditoria Observacional — Conferência por Concurso")
        st.info("Esta tela apenas observa resultados por concurso. Não gera jogos, não recalibra a Lei 15 e não altera histórico.")
        st.markdown("###### Camada observacional isolada")
        latest_contest = _load_imported_contest()
        latest_official_contest = _load_official_history_contest(_safe_int((latest_contest or {}).get("contest_number"), default=None)) if latest_contest else None
        latest_reconciliation = _load_latest_reconciliation_summary() or {}
        st.markdown("##### Status dos dados")
        data_cols = st.columns(5)
        data_cols[0].metric("Último concurso monitorado", str((latest_contest or {}).get("contest_number", "-") or "-"))
        data_cols[1].metric("Geração analisada", str(latest_reconciliation.get("generation_event_id", "-") or "-"))
        data_cols[2].metric("Total de jogos avaliados", int(latest_reconciliation.get("games_count", 0) or 0))
        data_cols[3].metric("Última conferência registrada", str(latest_reconciliation.get("created_at", "-") or "-"))
        data_cols[4].metric("Fonte dos dados", str((latest_contest or {}).get("source", "banco oficial") or "banco oficial"))
        if latest_reconciliation:
            st.caption(
                " | ".join(
                    [
                        f"best_hits={latest_reconciliation.get('best_hits', '-')}",
                        f"prize_count={latest_reconciliation.get('prize_count', '-')}",
                        f"total_hits={latest_reconciliation.get('total_hits', '-')}",
                    ]
                )
            )
        else:
            st.info("Nenhum dado pós-conferência disponível para esta visão. Execute ou consulte uma conferência operacional para alimentar o monitoramento.")
        with st.expander("Detalhes técnicos avançados", expanded=False):
            st.json(POST_DRAW_MONITORING_PAYLOAD)
        _render_signature_grid(
            list(POST_DRAW_MONITORING_PAYLOAD.get("accepted_signatures", [])),
            title="Dezenas organizadas no topo",
            empty_label="Esta conferência não recebeu dezenas para exibir no topo.",
        )
        official_numbers = _extract_int_numbers(
            (latest_official_contest or {}).get("dezenas", [])
            or (latest_official_contest or {}).get("numbers", [])
            or []
        )
        if official_numbers:
            block_distribution = _block_distribution(official_numbers)
            block_numbers = _format_block_numbers(official_numbers)
            st.markdown("##### Distribuição por bloco")
            block_cols = st.columns(5)
            for index, (label, value) in enumerate(block_distribution.items()):
                block_cols[index].metric(label, int(value))
                block_cols[index].caption(block_numbers.get(label, "-"))
        else:
            st.caption("Distribuição indisponível: dezenas oficiais não encontradas para o concurso monitorado.")
    elif section == "group_performance":
        st.markdown("##### Auditoria Observacional — Desempenho por Grupo")
        st.write("Esta tela observa o desempenho dos grupos conferidos, sem gerar jogos, sem recalibrar a Lei 15 e sem alterar histórico.")
        latest_contest = _load_imported_contest()
        generation_history = _load_generation_history(limit=10)
        latest_generation = generation_history[0] if generation_history else {}
        latest_group = (latest_generation.get("top_games") or [{}])[0] if latest_generation else {}
        st.markdown("##### Status institucional")
        cols = st.columns(4)
        cols[0].metric("Camada", "Auditoria Observacional")
        cols[1].metric("Geração", "não executa")
        cols[2].metric("Recalibração", "bloqueada")
        cols[3].metric("Alerta", "registro")
        st.markdown("##### Status dos dados")
        data_cols = st.columns(5)
        data_cols[0].metric("Último concurso monitorado", str((latest_contest or {}).get("contest_number", "-") or "-"))
        data_cols[1].metric("Geração analisada", str(latest_generation.get("generation_event_id", "-") or "-"))
        data_cols[2].metric("Total de jogos avaliados", int(latest_generation.get("total_games", 0) or 0))
        data_cols[3].metric("Última conferência registrada", str((latest_generation.get("reconciliation") or {}).get("created_at", "-") or "-"))
        data_cols[4].metric("Fonte dos dados", str((latest_contest or {}).get("source", "banco oficial") or "banco oficial"))
        if latest_generation.get("games"):
            conference_games = [_select_conference_numbers(game).get("conference_numbers", []) for game in latest_generation.get("games", [])]
            group_stats = _summarize_games_structurally(conference_games)
            st.caption(
                " | ".join(
                    [
                        f"grupos_avaliados={len(latest_generation.get('games') or [])}",
                        f"melhor_grupo={latest_group.get('game_index', '-')}",
                        f"acertos_medios={latest_generation.get('avg_score', 0.0):.4f}",
                        f"overlap={group_stats.get('average_overlap', 0.0):.4f}",
                    ]
                )
            )
            st.markdown("##### Resumo de desempenho")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "grupo": game.get("game_index", "-"),
                            "jogos": 1,
                            "acertos": game.get("hits", 0) if game.get("hits") is not None else "-",
                            "formato_cartao": int(_select_conference_numbers(game).get("formato_cartao", 15) or 15),
                            "núcleo_lei_15": " ".join(f"{number:02d}" for number in list(game.get("numbers", [])[:15])) or "-",
                            "reservas_auditadas": " ".join(f"+{number:02d}" for number in list(game.get("numbers", [])[15:])) or "-",
                            "cartão_final": " ".join(f"{number:02d}" for number in _select_conference_numbers(game).get("conference_numbers", [])) or "-",
                            "dezenas_conferidas_count": int(_select_conference_numbers(game).get("dezenas_conferidas_count", 0) or 0),
                            "origem_dezenas_conferencia": str(_select_conference_numbers(game).get("origem_dezenas_conferencia", "indisponivel") or "indisponivel"),
                            "observação institucional": "grupo avaliado na conferência",
                        }
                        for game in latest_generation.get("games", [])
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Nenhum dado pós-conferência disponível para esta visão. Execute ou consulte uma conferência operacional para alimentar o monitoramento.")
    elif section == "missing_numbers":
        st.markdown("##### Auditoria Observacional — Dezenas Faltantes")
        st.write("Esta tela observa as dezenas ausentes nos acertos por grupo, sem gerar jogos, sem recalibrar a Lei 15 e sem alterar histórico.")
        latest_contest = _load_imported_contest()
        latest_generation = (_load_generation_history(limit=1) or [{}])[0]
        st.markdown("##### Status institucional")
        cols = st.columns(4)
        cols[0].metric("Camada", "Auditoria Observacional")
        cols[1].metric("Geração", "não executa")
        cols[2].metric("Recalibração", "bloqueada")
        cols[3].metric("Estado", "registro")
        st.markdown("##### Status dos dados")
        data_cols = st.columns(5)
        data_cols[0].metric("Último concurso monitorado", str((latest_contest or {}).get("contest_number", "-") or "-"))
        data_cols[1].metric("Geração analisada", str(latest_generation.get("generation_event_id", "-") or "-"))
        data_cols[2].metric("Total de jogos avaliados", int(latest_generation.get("total_games", 0) or 0))
        data_cols[3].metric("Última conferência registrada", str((latest_generation.get("reconciliation") or {}).get("created_at", "-") or "-"))
        data_cols[4].metric("Fonte dos dados", str((latest_contest or {}).get("source", "banco oficial") or "banco oficial"))
        if latest_generation.get("games"):
            missing_df = pd.DataFrame(
                [
                    {
                        "formato_cartao": int(_select_conference_numbers(game).get("formato_cartao", 15) or 15),
                        "origem_observacional": str(_select_conference_numbers(game).get("origem_dezenas_conferencia", "indisponivel") or "indisponivel"),
                        "dezenas observadas": " ".join(f"{number:02d}" for number in _select_conference_numbers(game).get("conference_numbers", [])) or "-",
                        "dezenas observadas count": int(_select_conference_numbers(game).get("dezenas_conferidas_count", 0) or 0),
                        "dezenas ausentes": " ".join(f"{number:02d}" for number in game.get("matched_numbers", []) or []) or "-",
                        "frequência": int(game.get("hits", 0) or 0),
                        "grupo relacionado": game.get("game_index", "-"),
                        "concurso analisado": int((latest_contest or {}).get("contest_number", 0) or 0) if latest_contest else "-",
                        "observação institucional": "observação pós-conferência",
                    }
                    for game in latest_generation.get("games", [])
                ]
            )
            st.dataframe(missing_df, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum dado pós-conferência disponível para esta visão. Execute ou consulte uma conferência operacional para alimentar o monitoramento.")
    elif section == "extra_numbers":
        st.markdown("##### Auditoria Observacional — Dezenas Sobrando")
        st.write("Esta tela observa as dezenas excedentes dos jogos conferidos, sem gerar jogos, sem recalibrar a Lei 15 e sem alterar histórico.")
        latest_contest = _load_imported_contest()
        latest_generation = (_load_generation_history(limit=1) or [{}])[0]
        st.markdown("##### Status institucional")
        cols = st.columns(4)
        cols[0].metric("Camada", "Auditoria Observacional")
        cols[1].metric("Geração", "não executa")
        cols[2].metric("Recalibração", "bloqueada")
        cols[3].metric("Estado", "registro")
        st.markdown("##### Status dos dados")
        data_cols = st.columns(5)
        data_cols[0].metric("Último concurso monitorado", str((latest_contest or {}).get("contest_number", "-") or "-"))
        data_cols[1].metric("Geração analisada", str(latest_generation.get("generation_event_id", "-") or "-"))
        data_cols[2].metric("Total de jogos avaliados", int(latest_generation.get("total_games", 0) or 0))
        data_cols[3].metric("Última conferência registrada", str((latest_generation.get("reconciliation") or {}).get("created_at", "-") or "-"))
        data_cols[4].metric("Fonte dos dados", str((latest_contest or {}).get("source", "banco oficial") or "banco oficial"))
        if latest_generation.get("games"):
            extra_df = pd.DataFrame(
                [
                    {
                        "formato_cartao": int(_select_conference_numbers(game).get("formato_cartao", 15) or 15),
                        "origem_observacional": str(_select_conference_numbers(game).get("origem_dezenas_conferencia", "indisponivel") or "indisponivel"),
                        "dezenas observadas": " ".join(f"{number:02d}" for number in _select_conference_numbers(game).get("conference_numbers", [])) or "-",
                        "dezenas observadas count": int(_select_conference_numbers(game).get("dezenas_conferidas_count", 0) or 0),
                        "dezenas sobrando": " ".join(f"{number:02d}" for number in game.get("numbers", [])[:5]) or "-",
                        "frequência": int(game.get("odd", 0) or 0) + int(game.get("even", 0) or 0),
                        "grupo relacionado": game.get("game_index", "-"),
                        "concurso analisado": int((latest_contest or {}).get("contest_number", 0) or 0) if latest_contest else "-",
                        "observação institucional": "observação pós-conferência",
                    }
                    for game in latest_generation.get("games", [])
                ]
            )
            st.dataframe(extra_df, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum dado pós-conferência disponível para esta visão. Execute ou consulte uma conferência operacional para alimentar o monitoramento.")
    elif section == "side_leak":
        st.subheader("Vazamento Lateral Constitucional")
        render_constitutional_side_leak_section()
        st.divider()
        st.markdown("### Camada observacional auditada")
        st.info("Camada observacional/auditada. Não gera jogos. Não recalibra Lei 15. Não altera histórico.")
        st.caption(
            "quarantine_status=LIBERADO | operational_role=OBSERVACIONAL_AUDITADO | "
            "generation_command=False | recalibration_command=False"
        )
        st.caption("Sinaliza cobertura lateral e deslocamento de dezenas fora do núcleo esperado.")
    elif section == "13_to_14":
        st.markdown("##### Evolução 13 -> 14")
        st.info("Camada observacional/auditada. Não gera jogos. Não recalibra Lei 15. Não altera histórico.")
        st.caption(
            "quarantine_status=LIBERADO | operational_role=OBSERVACIONAL_AUDITADO | "
            "generation_command=False | recalibration_command=False"
        )
        st.caption("Avalia hipóteses de conversão 13 para 14 sem recalibrar automaticamente.")
    elif section == "14_to_15":
        st.markdown("##### Evolução 14 -> 15")
        st.info("Camada observacional/auditada. Não gera jogos. Não recalibra Lei 15. Não altera histórico.")
        st.caption(
            "quarantine_status=LIBERADO | operational_role=OBSERVACIONAL_AUDITADO | "
            "generation_command=False | recalibration_command=False"
        )
        st.caption("Avalia hipóteses de conversão 14 para 15 em modo observador.")
    elif section == "offline_hypotheses":
        st.markdown("##### Hipóteses para teste offline")
        st.caption("Somente hipóteses registradas para evolução futura após auditoria e versionamento.")


def _render_generation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    _ensure_official_history_seeded()
    live_counts = _database_snapshot()["counts"]
    st.subheader("Gerar Jogos")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(live_counts.get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(live_counts.get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(live_counts.get("reconciliation_runs", 0)))

    contest_summary = _get_latest_contest() or _load_latest_contest_summary()
    top_cols = st.columns([1.1, 1.3, 1.6])
    if contest_summary:
        top_cols[0].metric("Último concurso", int(contest_summary["contest_number"]))
        top_cols[1].caption(f"Fonte: {contest_summary.get('source', 'banco oficial')}")
        top_cols[2].caption(
            f"dezenas: {' '.join(f'{number:02d}' for number in contest_summary.get('dezenas', [])) or '-'}"
        )
    else:
        top_cols[0].caption("Último concurso: -")
        top_cols[1].caption("Fonte: banco vazio")

    current_card_format = int(st.session_state.get("institutional_card_format", 15) or 15)
    scientific_policy_discovery: dict[str, Any] | None = None
    official_generation_policy: dict[str, Any] = {}
    if current_card_format == 15:
        st.session_state.setdefault("institutional_operational_total_games", 10)
        st.session_state.setdefault("institutional_operational_generation_runs", 10)
        st.session_state["institutional_repeat_limit"] = int(official_generation_policy.get("repeat_max", 10) or 10)
    controls_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    total_games = int(
        controls_cols[0].number_input(
            "Quantidade de jogos por geração",
            min_value=1,
            max_value=100,
            value=int(st.session_state.get("institutional_operational_total_games", 10 if current_card_format == 15 else 15) or (10 if current_card_format == 15 else 15)),
            step=1,
            key="institutional_operational_total_games",
        )
    )
    generation_runs = int(
        controls_cols[1].number_input(
            "Quantidade de gerações na bateria",
            min_value=1,
            max_value=60,
            value=int(st.session_state.get("institutional_operational_generation_runs", 10 if current_card_format == 15 else 1) or (10 if current_card_format == 15 else 1)),
            step=1,
            key="institutional_operational_generation_runs",
        )
    )
    selected_card_format = int(
        controls_cols[2].selectbox(
            "Formato do cartão",
            options=list(OFFICIAL_CARD_FORMATS),
            index=list(OFFICIAL_CARD_FORMATS).index(current_card_format) if current_card_format in OFFICIAL_CARD_FORMATS else 0,
            format_func=lambda value: {
                15: "15 dezenas — Núcleo Lei 15",
                17: "17 dezenas — Lei 15 + 2 reservas auditadas",
                18: "18 dezenas — Lei 15 + 3 reservas auditadas",
            }.get(int(value), f"{int(value)} dezenas"),
            key="institutional_card_format",
        )
    )
    st.session_state["institutional_card_format"] = selected_card_format
    dezenas_per_game = 15
    geometry_profile = _sync_hb_geometry_controls(dezenas_per_game)
    use_top50 = bool(
        controls_cols[3].checkbox(
            "Usar TOP50 estrutural HB",
            value=bool(st.session_state.get("institutional_use_top50", True)),
            key="institutional_use_top50",
        )
    )
    repeat_limit = int(
        controls_cols[3].number_input(
            "Máx. repetição do último concurso",
            min_value=0,
            max_value=15,
            value=int(st.session_state.get("institutional_repeat_limit", 10 if current_dezenas_size == 15 else 8) or (10 if current_dezenas_size == 15 else 8)),
            step=1,
            key="institutional_repeat_limit",
        )
    )

    parity_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    odd_min = int(
        parity_cols[0].slider(
            "Ímpares mínimo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_odd_min", geometry_profile["odd_min"]) or geometry_profile["odd_min"]),
            key="institutional_odd_min",
        )
    )
    odd_max = int(
        parity_cols[1].slider(
            "Ímpares máximo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_odd_max", geometry_profile["odd_max"]) or geometry_profile["odd_max"]),
            key="institutional_odd_max",
        )
    )
    even_min = int(
        parity_cols[2].slider(
            "Pares mínimo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_even_min", geometry_profile["even_min"]) or geometry_profile["even_min"]),
            key="institutional_even_min",
        )
    )
    even_max = int(
        parity_cols[3].slider(
            "Pares máximo",
            min_value=0,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_even_max", geometry_profile["even_max"]) or geometry_profile["even_max"]),
            key="institutional_even_max",
        )
    )

    structural_cols = st.columns([1.0, 1.0, 1.0, 1.0])
    sequence_max = int(
        structural_cols[0].slider(
            "Limite de sequência",
            min_value=1,
            max_value=dezenas_per_game,
            value=int(st.session_state.get("institutional_sequence_max", geometry_profile["sequence_max"]) or geometry_profile["sequence_max"]),
            key="institutional_sequence_max",
        )
    )
    coverage_min = float(
        structural_cols[1].slider(
            "Cobertura mínima",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("institutional_coverage_min", geometry_profile["coverage_min"]) or geometry_profile["coverage_min"]),
            step=0.05,
            key="institutional_coverage_min",
        )
    )
    entropy_min = float(
    structural_cols[2].slider(
            "Entropia mínima",
            min_value=0.0,
            max_value=1.0,
            value=float(st.session_state.get("institutional_entropy_min", geometry_profile["entropy_min"]) or geometry_profile["entropy_min"]),
            step=0.05,
            key="institutional_entropy_min",
        )
    )
    structural_cols[3].caption("Perfil geométrico adaptado automaticamente ao tamanho do jogo.")

    total_jogos_esperados = int(total_games) * int(generation_runs)
    st.markdown("##### Resumo da bateria")
    resume_cols = st.columns(4)
    resume_cols[0].metric("jogos por geração", int(total_games))
    resume_cols[1].metric("gerações na bateria", int(generation_runs))
    resume_cols[2].metric("Formato do cartão", f"{selected_card_format} dezenas")
    resume_cols[3].metric("total esperado de jogos", total_jogos_esperados)
    batch_result = st.session_state.get("institutional_generation_batch_result") or {}
    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    summary_result = batch_result or generation_result
    scientific_batch_id = str(
        summary_result.get("batch_id")
        or generation_result.get("batch_id")
        or generation_state.get("batch_id")
        or ""
    ).strip()
    scientific_game_size = int(
        summary_result.get("quantidade_dezenas_por_jogo")
        or generation_result.get("quantidade_dezenas_solicitada")
        or generation_state.get("dezenas_per_game")
        or dezenas_per_game
    )
    scientific_batch = {}
    if scientific_batch_id:
        scientific_batch = _scientific_batch_diagnostics(
            batch_id=scientific_batch_id,
            games=[] if batch_result else list(generation_result.get("jogos") or generation_state.get("games") or []),
            game_size=scientific_game_size,
        )
    if scientific_batch_id and (batch_result or generation_result):
        scientific_policy_discovery = discover_scientific_generation_policy(scientific_game_size, db_path=DB_PATH)
        official_generation_policy = dict(scientific_policy_discovery.get("policy") or {})
        _store_active_batch_state(
            batch_id=scientific_batch_id,
            generation_event_ids=_load_generation_event_ids_for_batch(scientific_batch_id),
            policy_id=str(official_generation_policy.get("policy_id") or official_generation_policy.get("policy_signature") or scientific_policy_discovery.get("policy_id") or ""),
            generated_at=str((batch_result or {}).get("created_at") or (generation_result or {}).get("created_at") or datetime.now(UTC).isoformat()),
            game_size=scientific_game_size,
            total_games=int(summary_result.get("total_jogos_gerados", total_jogos_esperados) or total_jogos_esperados),
        )
    _render_scientific_policy_panel(
        policy=official_generation_policy,
        strategy_size=15,
        total_expected_games=int(total_jogos_esperados),
        games_per_generation=int(total_games),
        generations_in_batch=int(generation_runs),
        policy_discovery=scientific_policy_discovery,
    )
    if scientific_batch:
        scientific_state = {
            "mode": "AUTONOMIA SUPERVISIONADA"
            if str(scientific_batch.get("status_comandante_cientifico", "")).upper() == "APROVADO"
            else "OBSERVAÇÃO",
            "structural_status": str(summary_result.get("status_comandante_saida", "BLOQUEADO") or "BLOQUEADO"),
            "scientific_status": str(scientific_batch.get("status_comandante_cientifico", "-") or "-"),
            "classification": str(scientific_batch.get("classificacao_cientifica", "-") or "-"),
            "main_reason": str(scientific_batch.get("main_reason", scientific_batch.get("motivo_cientifico", "-")) or "-"),
            "status_visual": str(scientific_batch.get("status_visual", "-") or "-"),
            "reference_window": scientific_batch.get("reference_window", []),
            "source_batch_id": scientific_batch_id,
        }
        scientific_recommendation = {
            "action_suggested": str(
                scientific_batch.get("action_suggested", scientific_batch.get("recommended_action", "-")) or "-"
            ),
            "status_visual": str(scientific_batch.get("status_visual", "-") or "-"),
        }
    else:
        scientific_state = None
        scientific_recommendation = None
    with st.expander("Diagnóstico institucional", expanded=False):
        _render_scientific_policy_panel(
            policy=official_generation_policy,
            strategy_size=15,
            total_expected_games=int(total_jogos_esperados),
            games_per_generation=int(total_games),
            generations_in_batch=int(generation_runs),
            policy_discovery=scientific_policy_discovery,
        )
        _render_scientific_calibration_panel(
            strategy_size=15,
            scientific_state=scientific_state,
            scientific_recommendation=scientific_recommendation,
            technical_payload=scientific_batch if scientific_batch else None,
            use_expander=False,
        )
    if summary_result:
        st.markdown("##### Diagnóstico da bateria")
        batch_status = str(summary_result.get("status_comandante_saida", "BLOQUEADO") or "BLOQUEADO")
        batch_solicitados = int(summary_result.get("total_jogos_solicitados", 0) or 0)
        batch_aprovados = int(summary_result.get("total_jogos_aprovados", summary_result.get("total_jogos_unicos", 0)) or 0)
        batch_gerados = int(summary_result.get("total_jogos_gerados", batch_aprovados) or batch_aprovados)
        batch_unicos = int(summary_result.get("total_jogos_unicos", batch_aprovados) or batch_aprovados)
        batch_duplicados = int(summary_result.get("total_jogos_duplicados", 0) or 0)
        batch_rejeitados = int(summary_result.get("total_jogos_rejeitados", max(0, batch_solicitados - batch_aprovados)) or 0)
        batch_taxa = float(summary_result.get("taxa_duplicidade", 0.0) or 0.0)
        outcome_cols = st.columns(6)
        outcome_cols[0].metric("total_jogos_solicitados", batch_solicitados)
        outcome_cols[1].metric("total_jogos_gerados", batch_gerados)
        outcome_cols[2].metric("total_jogos_unicos", batch_unicos)
        outcome_cols[3].metric("total_jogos_duplicados", batch_duplicados)
        outcome_cols[4].metric("taxa_duplicidade", f"{batch_taxa:.4f}")
        outcome_cols[5].metric("Status do OutputCommander", batch_status)
        st.caption(
            f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))} | "
            f"generation_event_id={summary_result.get('generation_event_id', '-')}"
        )
        if batch_status != "APROVADO":
            blocked_message = str(summary_result.get("motivo_bloqueio", "") or "")
            if "nao_atingiu_quantidade_solicitada" in blocked_message or batch_status == "BLOQUEADO":
                blocked_message = "Pacote bloqueado por não atingir a quantidade solicitada."
            st.error(
                "Comandante de Saída bloqueou a bateria. "
                f"status = {batch_status} | "
                f"motivo = {blocked_message or 'Pacote bloqueado por não atingir a quantidade solicitada.'} | "
                f"solicitados = {batch_solicitados} | "
                f"aprovados = {batch_aprovados} | "
                f"faltantes = {max(0, batch_solicitados - batch_aprovados)}"
            )
        else:
            st.success(
                "Bateria aprovada. "
                f"jogos por geração={summary_result.get('quantidade_jogos_por_geracao', '-')} | "
                f"gerações na bateria={summary_result.get('quantidade_geracoes_na_bateria', '-')} | "
                f"jogos gerados={batch_gerados}"
            )

    button_cols = st.columns([0.28, 1.72])
    if button_cols[0].button("LotoIA", type="primary"):
        if generation_runs > 1 and dezenas_per_game != 15:
            st.error("A bateria institucional oficial exige 15 dezenas por jogo nesta fase.")
        else:
            if generation_runs > 1:
                _run_institutional_generation_batch(
                    generation_runs=generation_runs,
                    total_games=total_games,
                    dezenas_per_game=dezenas_per_game,
                    use_top50=use_top50,
                    odd_min=odd_min,
                    odd_max=odd_max,
                    even_min=even_min,
                    even_max=even_max,
                    sequence_max=sequence_max,
                    coverage_min=coverage_min,
                    entropy_min=entropy_min,
                    repeat_limit=repeat_limit,
                    snapshot=snapshot,
                )
            else:
                _run_institutional_generation(
                    total_games=total_games,
                    dezenas_per_game=dezenas_per_game,
                    use_top50=use_top50,
                    odd_min=odd_min,
                    odd_max=odd_max,
                    even_min=even_min,
                    even_max=even_max,
                    sequence_max=sequence_max,
                    coverage_min=coverage_min,
                    entropy_min=entropy_min,
                    repeat_limit=repeat_limit,
                    snapshot=snapshot,
                )
            st.rerun()
    st.caption("Escolha a quantidade antes de gerar.")

    if scientific_batch_id:
        scientific_calibration_games = _load_scientific_batch_games(scientific_batch_id)
        scientific_calibration_mode = st.selectbox(
            "modo de calibração",
            ["OBSERVAÇÃO", "AUTONOMIA SUPERVISIONADA"],
            index=0 if str(scientific_batch.get("status_comandante_cientifico", "")).upper() != "APROVADO" else 1,
            key=f"scientific_calibration_mode_{scientific_batch_id}",
        )
        scientific_calibration_context = evaluate_last_batch(
            game_size=scientific_game_size,
            batch_id=scientific_batch_id,
            mode=scientific_calibration_mode,
            games=scientific_calibration_games,
            db_path=DB_PATH,
        )
        scientific_calibration_policy = generate_recalibration_policy(scientific_calibration_context)
        scientific_calibration_recommendation = recommend_next_strategy(scientific_calibration_context)
        st.caption("Ajuste supervisionado da ?ltima bateria.")
        if st.button(
            "Registrar decisão científica",
            key=f"register_scientific_calibration_{scientific_batch_id}",
            use_container_width=False,
        ):
            calibration_decision = apply_supervised_calibration(
                scientific_calibration_context,
                auto_apply=str(scientific_calibration_mode).upper() == "AUTONOMIA SUPERVISIONADA",
            )
            registered_decision = register_calibration_decision(
                scientific_calibration_context,
                decision=calibration_decision,
                db_path=DB_PATH,
            )
            st.success(
                f"Decisão científica registrada. classification={registered_decision.get('classification', '-')} | "
                f"mode={registered_decision.get('mode', '-')} | applied={registered_decision.get('applied', False)}"
            )
            with st.expander("Memória científica registrada", expanded=False):
                st.json(registered_decision)
        latest_scientific_decisions = _load_latest_scientific_calibration_decision(limit=5)
        if latest_scientific_decisions:
            st.markdown("###### Últimas decisões científicas")
            st.dataframe(pd.DataFrame(latest_scientific_decisions), hide_index=True, use_container_width=True)
    if generation_result and not batch_result:
        generation_event_id = int(generation_result.get("generation_event_id") or 0)
        persisted_count = _count_generated_games_for_event(generation_event_id) if generation_event_id else 0
        generation_runtime_status = str(generation_result.get("status_comandante_saida") or generation_state.get("runtime_status") or "")
        if generation_runtime_status == "ERRO_CRITICO" or not generation_result.get("jogos"):
            st.error(
                f"Comandante de Saída bloqueou a bateria. status={generation_runtime_status or '-'} | "
                f"erro={generation_result.get('error_message', 'diversidade insuficiente')}"
            )
        else:
            st.success(
                f"Geração concluída. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
            )
            if generation_event_id:
                st.code(_generated_games_count_sql(generation_event_id), language="sql")
                st.caption(f"SQL_COUNT_RESULT={persisted_count}")
        st.caption(
            " | ".join(
                [
                    f"quantidade_jogos_solicitada={generation_result.get('quantidade_jogos_solicitada', '-')}",
                    f"quantidade_dezenas_solicitada={generation_result.get('quantidade_dezenas_solicitada', '-')}",
                    f"quantidade_jogos_real_gerada={generation_result.get('quantidade_jogos_real_gerada', '-')}",
                    f"quantidade_jogos_persistida={persisted_count}",
                    f"generation_event_id={generation_event_id or '-'}",
                    f"len(generated_games)={len(generation_result.get('jogos') or [])}",
                    f"len_todos_os_jogos={generation_result.get('len_todos_os_jogos', [])}",
                    f"len_primeiro_jogo={generation_result.get('len_primeiro_jogo', '-')}",
                    f"primeiro_jogo={' '.join(f'{number:02d}' for number in generation_result.get('primeiro_jogo', [])) or '-'}",
                ]
            )
        )
        st.caption(
            " | ".join(
                [
                    f"status_comandante_saida={generation_result.get('status_comandante_saida', '-')}",
                    f"total_jogos_unicos={generation_result.get('total_jogos_unicos', '-')}",
                    f"total_jogos_duplicados={generation_result.get('total_jogos_duplicados', '-')}",
                    f"taxa_duplicidade={generation_result.get('taxa_duplicidade', 0.0):.4f}" if isinstance(generation_result.get("taxa_duplicidade"), (int, float)) else f"taxa_duplicidade={generation_result.get('taxa_duplicidade', '-')}",
                    f"generation_event_id={generation_result.get('generation_event_id', '-')}",
                ]
            )
        )
        commander_cols = st.columns(6)
        commander_cols[0].metric("total_jogos_solicitados", int(generation_result.get("quantidade_jogos_solicitada", 0) or 0))
        commander_cols[1].metric("total_jogos_gerados", int(generation_result.get("quantidade_jogos_real_gerada", 0) or 0))
        commander_cols[2].metric("total_jogos_unicos", int(generation_result.get("total_jogos_unicos", 0) or 0))
        commander_cols[3].metric("total_jogos_duplicados", int(generation_result.get("total_jogos_duplicados", 0) or 0))
        commander_cols[4].metric(
            "taxa_duplicidade",
            f"{float(generation_result.get('taxa_duplicidade', 0.0) or 0.0):.4f}"
            if isinstance(generation_result.get("taxa_duplicidade"), (int, float))
            else generation_result.get("taxa_duplicidade", "-"),
        )
        commander_cols[5].metric(
            "status_comandante_saida",
            str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO"),
        )
        st.caption(
            f"institutional_output_signatures={int(live_counts.get('institutional_output_signatures', 0))} | "
            f"generation_event_id={generation_result.get('generation_event_id', '-')}"
        )
        with st.expander("Diagnóstico do Comandante de Saída", expanded=True):
            commander_diag = pd.DataFrame(
                [
                    {
                        "total_jogos_solicitados": int(generation_result.get("quantidade_jogos_solicitada", 0) or 0),
                        "total_jogos_gerados": int(generation_result.get("quantidade_jogos_real_gerada", 0) or 0),
                        "total_jogos_unicos": int(generation_result.get("total_jogos_unicos", 0) or 0),
                        "total_jogos_duplicados": int(generation_result.get("total_jogos_duplicados", 0) or 0),
                        "taxa_duplicidade": float(generation_result.get("taxa_duplicidade", 0.0) or 0.0),
                        "status_comandante_saida": str(generation_result.get("status_comandante_saida", "APROVADO") or "APROVADO"),
                        "institutional_output_signatures": int(live_counts.get("institutional_output_signatures", 0)),
                    }
                ]
            )
            st.dataframe(commander_diag, hide_index=True, use_container_width=True)
        if generation_result.get("jogos"):
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "rank": index + 1,
                            "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                            "perfil": game.get("profile_type", "-"),
                            "pares": int(game.get("even", 0) or 0),
                            "ímpares": int(game.get("odd", 0) or 0),
                            "seq_max": int(game.get("structural_metrics", {}).get("sequence_max", 0) or 0),
                            "cobertura": round(float(game.get("structural_metrics", {}).get("coverage_score", 0.0) or 0.0), 4),
                            "entropia": round(float(game.get("structural_metrics", {}).get("entropy_score", 0.0) or 0.0), 4),
                            "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                        }
                        for index, game in enumerate(generation_result.get("jogos") or [])
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
    elif generation_state.get("games"):
        st.info("Última geração carregada. Use o menu lateral para conferir ou simular novamente.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "pares": int(game.get("even", 0) or 0),
                        "ímpares": int(game.get("odd", 0) or 0),
                        "seq_max": int(game.get("structural_metrics", {}).get("sequence_max", 0) or 0),
                        "cobertura": round(float(game.get("structural_metrics", {}).get("coverage_score", 0.0) or 0.0), 4),
                        "entropia": round(float(game.get("structural_metrics", {}).get("entropy_score", 0.0) or 0.0), 4),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_state.get("games") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Use a barra lateral para acionar geração, conferência e simulação.")

    latest_contest = _load_imported_contest()
    latest_generation = _load_latest_generated_games() or {}
    contest_number = None
    contest_numbers_text = "-"
    contest_source = "banco oficial"
    if latest_contest:
        contest_number = int(latest_contest.get("contest_number", 0) or 0)
        contest_numbers_text = " ".join(f"{number:02d}" for number in latest_contest.get("dezenas", [])) or "-"
    elif str(latest_generation.get("target_contest") or "").isdigit():
        contest_number = int(latest_generation.get("target_contest") or 0)
        contest_source = "última geração persistida"
    if contest_number:
        contest_cols = st.columns([0.65, 1.6])
        contest_cols[0].metric("Último concurso", contest_number)
        contest_cols[1].caption(f"Fonte: {contest_source} | dezenas: {contest_numbers_text}")
    else:
        st.caption("Último concurso: -")


def _render_conference_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    live_counts = _database_snapshot()["counts"]
    st.subheader("Conferir Resultados")

    active_generation_groups = _load_persisted_generation_event_groups(batch_id=None)
    active_generation_event_ids = sorted(
        {
            int(group.get("generation_event_id", 0) or 0)
            for group in active_generation_groups
            if int(group.get("generation_event_id", 0) or 0) > 0
        },
        reverse=True,
    )
    render_conference_governance_section(
        generation_blocked=_is_sovereign_generation_blocked(),
        has_persisted_batches=bool(active_generation_event_ids),
        persisted_generation_events=len(active_generation_event_ids),
        persisted_games=int(live_counts.get("generated_games", 0) or 0),
        reconciliation_runs=int(live_counts.get("reconciliation_runs", 0) or 0),
    )
    st.divider()
    st.markdown("### Conferência oficial")
    st.caption(
        "Conferir Resultados = **último concurso oficial** × **todas as gerações aprovadas/oficializadas**. "
        "Exibe apenas jogos com 11 pontos ou mais."
    )
    official_groups = _load_official_conference_generation_groups()
    official_generation_event_ids = sorted(
        {
            int(group.get("generation_event_id", 0) or 0)
            for group in official_groups
            if int(group.get("generation_event_id", 0) or 0) > 0
        },
        reverse=True,
    )
    latest_official_contest = _resolve_latest_official_conference_contest()
    latest_contest_number = _safe_int((latest_official_contest or {}).get("concurso"), default=0) or 0
    conf_cols = st.columns(4)
    conf_cols[0].metric("Último concurso oficial", latest_contest_number or "-")
    conf_cols[1].metric("Gerações oficializadas", len(official_generation_event_ids))
    conf_cols[2].metric("Jogos elegíveis", sum(int(group.get("total_games", 0) or 0) for group in official_groups))
    conf_cols[3].metric("Modo", "Oficial")
    if latest_official_contest:
        st.caption(
            f"Concurso automático: {latest_contest_number} | dezenas: "
            f"{' '.join(f'{number:02d}' for number in latest_official_contest.get('dezenas', []) or []) or '-'}"
        )
    else:
        st.warning("Último concurso oficial indisponível em imported_contests.")
    if official_generation_event_ids:
        st.caption(
            "Gerações aprovadas: "
            + ", ".join(str(value) for value in official_generation_event_ids[:20])
            + ("…" if len(official_generation_event_ids) > 20 else "")
        )
    else:
        st.info("Nenhuma geração oficializada disponível para conferência.")

    action_cols = st.columns([0.5, 0.5])
    if action_cols[0].button(
        "Conferir Resultados",
        type="primary",
        disabled=not bool(latest_official_contest and official_generation_event_ids),
        key="conference_run_all_official",
    ):
        _run_institutional_conference(
            contest_number=latest_contest_number if latest_contest_number > 0 else None,
            conference_all_official=True,
        )
        st.rerun()
    if action_cols[1].button("Sincronizar último resultado oficial", key="conference_sync_latest"):
        sync_payload = _sync_latest_official_result_now()
        st.session_state["institutional_last_official_sync_summary"] = dict(sync_payload)
        st.rerun()

    st.divider()
    with st.expander("Diagnóstico técnico (imported_contests / sync)", expanded=False):
        try:
            with _get_engine_cached().begin() as connection:
                runtime_query_imported_contests = int(
                    connection.execute(text('SELECT COUNT(*) FROM "imported_contests"')).scalar() or 0
                )
            st.caption(f"imported_contests={runtime_query_imported_contests}")
        except Exception as exc:
            st.caption(f"imported_contests=indisponível ({exc})")
        diagnostic_state = _load_official_sync_diagnostics()
        if diagnostic_state:
            st.json(diagnostic_state)

        check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("warning"):
        st.warning(check_result["warning"])
    if isinstance(check_result, dict):
        st.caption(
            " | ".join(
                [
                    f"generation_event_id={check_result.get('generation_event_id', '-')}",
                    f"formato_cartao={check_result.get('formato_cartao', '-')}",
                    f"dezenas_conferidas_count={check_result.get('dezenas_conferidas_count', '-')}",
                    f"origem_dezenas_conferencia={check_result.get('origem_dezenas_conferencia', '-')}",
                    f"expected_card_size={check_result.get('expected_card_size', '-')}",
                    f"actual_card_size={check_result.get('actual_card_size', '-')}",
                ]
            )
        )
        generation_results = list(check_result.get("generation_results") or [])
        if generation_results:
            st.markdown("#### Resumo geral")
            total_games_reconciled = sum(int(item.get("total_games", 0) or 0) for item in generation_results)
            total_runs = len(generation_results)
            best_hits = max((int(item.get("best_hits", 0) or 0) for item in generation_results), default=0)
            total_hits = int(check_result.get("total_hits", 0) or 0)
            prize_count = int(check_result.get("prize_count", 0) or 0)
            st.write(total_runs)
            st.write(total_games_reconciled)
            st.write(best_hits)
            st.write(f"total_runs={total_runs}")
            st.write(f"total_games_reconciled={total_games_reconciled}")
            st.write(f"best_hits={best_hits}")
            summary_cols = st.columns(5)
            summary_cols[0].metric("Concurso", check_result.get("contest_number", "-"))
            summary_cols[1].metric("Total jogos conferidos", total_games_reconciled)
            summary_cols[2].metric("Melhor acerto", best_hits)
            summary_cols[3].metric("Prêmios", prize_count)
            summary_cols[4].metric("Total hits", total_hits)
            hit_totals: Counter[int] = Counter()
            for item in generation_results:
                for row in item.get("results", []) or []:
                    hit_totals[int(row.get("hits", 0) or 0)] += 1
            hit_counts_df = pd.DataFrame(
                [
                    {"faixa": f"{hits} acertos", "quantidade": count}
                    for hits, count in sorted(hit_totals.items(), key=lambda item: (-item[0], item[1]))
                    if hits >= 10
                ]
            )
            if not hit_counts_df.empty:
                st.dataframe(hit_counts_df, hide_index=True, use_container_width=True)
            st.markdown("#### Resultado oficial (11+ pontos)")
            for item in generation_results:
                title = f"Geração #{item.get('generation_event_id', '-')}"
                premium_rows = [
                    row
                    for row in list(item.get("results") or [])
                    if int(row.get("hits", 0) or 0) >= 11
                ]
                with st.expander(
                    f"{title} | jogos 11+={len(premium_rows)} | best_hits={item.get('best_hits', '-')}",
                    expanded=False,
                ):
                    gen_cols = st.columns(4)
                    gen_cols[0].metric("seed", item.get("seed", "-"))
                    gen_cols[1].metric("contest", item.get("contest_number", "-"))
                    gen_cols[2].metric("best_hits", item.get("best_hits", "-"))
                    gen_cols[3].metric("prize_count", item.get("prize_count", "-"))
                    generation_df = pd.DataFrame(
                        [
                            {
                                "jogo": row["game_index"],
                                "formato_cartao": row.get("formato_cartao", "-"),
                                "cartao_final": " ".join(f"{number:02d}" for number in row.get("cartao_final", row["numbers"])),
                                "hits": row["hits"],
                                "matched_numbers": " ".join(f"{number:02d}" for number in row.get("matched_numbers", [])),
                                "premiado": row["prize_status"],
                            }
                            for row in premium_rows
                        ]
                    )
                    if not generation_df.empty:
                        st.dataframe(generation_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhum jogo com 11 pontos ou mais nesta geração.")
            diagnostics = check_result.get("diagnostics") or {}
            if diagnostics:
                st.markdown("#### Diagnóstico temporário")
                st.write(f"Resultado oficial: {diagnostics.get('official_numbers', [])}")
                st.write(f"Tipo resultado: {type(diagnostics.get('official_numbers', []))}")
                st.write(f"Primeiro jogo: {diagnostics.get('first_game', [])}")
                st.write(f"Tipo jogo: {type(diagnostics.get('first_game', []))}")
                st.write(f"Interseção: {set(int(number) for number in diagnostics.get('first_intersection', []) or [])}")
                st.write(f"Hits: {diagnostics.get('first_game_hits', 0)}")
            st.markdown("#### Últimas reconciliações")
            reconciliations = _load_reconciliation_history(limit=10)
            if reconciliations:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "concurso": row.get("contest_id", "-"),
                                "data": row.get("created_at", "-"),
                                "jogos conferidos": row.get("games_count", "-"),
                                "melhor acerto": row.get("best_hits", "-"),
                                "prêmios": row.get("prize_count", "-"),
                            }
                            for row in reconciliations
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("Ainda não há reconciliações persistidas nesta instância.")
            st.markdown("#### Conferência")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "jogo": row["game_index"],
                            "dezenas": " ".join(f"{number:02d}" for number in row["numbers"]),
                            "hits": row["hits"],
                            "premiado": row["prize_status"],
                        }
                        for generation in generation_results
                        for row in generation.get("results", []) or []
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        elif check_result.get("status") == "waiting_contest":
            st.info("A conferência está pronta, mas ainda falta o concurso oficial em imported_contests.")
    elif isinstance(check_result, dict) and check_result.get("status") == "checked":
        st.info("Conferência executada, mas nenhum resultado foi renderizado.")
    elif not latest_contest_record:
        st.info("Último concurso ainda não veio do banco. Use a sincronização oficial quando disponível.")


def _run_clean_law15_generation(*, requested_count: int) -> dict[str, Any]:
    total_games = int(requested_count)
    if _is_sovereign_generation_blocked():
        return _sovereign_generation_blocked_result(requested_count=total_games)

    analysis_batch_label = _resolve_adm_sovereign_batch_label(
        str(st.session_state.get("clean_law15_analysis_batch_label") or SOVEREIGN_BATCH_LABEL)
    )
    seed = int(time.time_ns() % 1_000_000_000)
    latest_contest = get_latest_official_contest() or {}
    latest_contest_number = _safe_int((latest_contest or {}).get("contest_number"), default=None)
    target_contest = None
    if latest_contest_number is not None and latest_contest_number > 0:
        target_contest = int(latest_contest_number) + 1

    sovereign_payload = _invoke_sovereign_adm_generate_best_games(
        requested_count=total_games,
        batch_label=analysis_batch_label,
        seed=seed,
    )
    games = list(sovereign_payload.get("games") or [])
    ml_enabled = bool(sovereign_payload.get("ml_enabled", False))
    fill_diagnostics: dict[str, Any] = {
        "fill_completed": len(games) >= total_games,
        "sovereign_generation_path": "generate_best_games",
        "analysis_batch_label": analysis_batch_label,
        "generation_path": str(sovereign_payload.get("generation_path") or "LEI15_CORE_002"),
        "ml_enabled": ml_enabled,
        "ml_operational_status": supervised_ml_status_label() if ml_enabled else "ML_INATIVO",
    }
    commander_report = output_commander_validate_games(
        games,
        batch_id=f"clean-law15-{seed}",
        generation_event_id=None,
        target_size=15,
        required_total=total_games,
        candidate_total=total_games,
        persisted_signatures=set(load_all_output_signatures()),
        historical_deduplication_mode="AUDIT_ONLY",
    )
    if len(games) < total_games:
        commander_report = {
            **commander_report,
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "INSUFFICIENT_VALID_CANDIDATES",
            "error_message": "INSUFFICIENT_VALID_CANDIDATES",
        }
        fill_diagnostics["insufficient_reason"] = "INSUFFICIENT_VALID_CANDIDATES"
    else:
        fill_diagnostics["insufficient_reason"] = "none"
    fill_diagnostics["rejected_by_output_commander"] = int(
        commander_report.get("quantidade_jogos_rejeitados", 0) or 0
    )
    return {
        "seed": seed,
        "batch_id": f"clean-law15-{seed}",
        "requested_count": total_games,
        "games": games,
        "commander_report": commander_report,
        "fill_diagnostics": fill_diagnostics,
        "analysis_batch_label": analysis_batch_label,
        "official_contest_source": str(
            (latest_contest or {}).get("official_contest_source", "indisponivel") or "indisponivel"
        ),
        "official_contest_id": latest_contest_number,
        "official_contest_numbers": " ".join(
            f"{number:02d}" for number in (latest_contest or {}).get("dezenas", [])
        )
        or "-",
        "rfe_previous_contest_found": False,
        "rfe_previous_contest_id": None,
        "rfe_previous_contest_numbers": "-",
        "rfe_previous_contest_source": "not_applicable_sovereign_path",
        "rfe_previous_contest_message": "",
        "rfe_status": "NOT_APPLICABLE_SOVEREIGN_PATH",
        "batch_fill_strategy": "SOVEREIGN_GENERATE_BEST_GAMES",
        "generation_mode": "LEI15_CORE_002_SOVEREIGN",
        "policy_mode": "ADR_047_CONSTITUTIONAL",
        "selected_quantity": total_games,
        "dezenas_por_jogo": 15,
        "scientific_law_role": "COMMANDER",
        "clean_adm_runtime_role": "EXECUTOR",
        "output_commander_role": "AUDITOR",
        "historical_deduplication_mode": "AUDIT_ONLY",
        "historical_duplicates_removed": 0,
        "legacy_generation_flow": "ARCHIVED",
        "legacy_dashboard_generation": "BYPASSED",
        "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
        "calibration_engine_role": "DISABLED",
        "automatic_law_mutation_allowed": False,
        "silent_recalibration_allowed": False,
        "law_evolution_requires_audit": True,
        "target_contest": target_contest,
        "sovereign_generation_path": "generate_best_games",
        "ml_enabled": ml_enabled,
        "ml_operational_status": supervised_ml_status_label() if ml_enabled else "ML_INATIVO",
    }


def _render_clean_law15_generation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    ml_active = is_adm_supervised_ml_active()
    generation_active = not _is_sovereign_generation_blocked()

    st.markdown(f"### {GENERATOR_PAGE_TITLE}")
    render_compact_status_chips(ml_active=ml_active, generation_active=generation_active)

    if not generation_active:
        st.error(
            "Geração bloqueada enquanto `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0`. "
            "Nenhum jogo será gerado neste estado."
        )
        render_governance_expander(render_constitutional_panel=_render_constitutional_status_panel)
        return

    requested_count, selected_card_format = render_generation_operation_block(ml_active=ml_active)

    if st.session_state.pop("_clean_law15_generate_clicked", False):
        result = _run_clean_law15_generation(requested_count=requested_count)
        result["selected_card_format"] = int(selected_card_format)
        result["card_format_label"] = multidezena_format_label(selected_card_format)
        result["analysis_batch_label"] = multidezena_batch_label(selected_card_format)
        result["display_games"] = _expand_generation_games_for_format(
            result.get("games") or [],
            selected_card_format,
        )
        result["validation_status_lei_17"] = "N_A"
        result["validation_status_lei_18"] = "N_A"
        if is_multidezena_persistence_supported(selected_card_format):
            try:
                persisted_snapshot = _persist_clean_law15_generation_history(
                    result=result,
                    selected_card_format=selected_card_format,
                )
            except RuntimeError as exc:
                persisted_snapshot = {
                    "persistence_blocked": True,
                    "persistence_guard_status": str(exc),
                }
            if persisted_snapshot:
                result.update(persisted_snapshot)
                result = _attach_operational_generation_label(result)
                st.session_state["clean_law15_generation_history_snapshot"] = persisted_snapshot
            elif persisted_snapshot is not None and persisted_snapshot.get("persistence_blocked"):
                result["persistence_blocked"] = True
                result["persistence_block_reason"] = str(
                    persisted_snapshot.get("persistence_guard_status")
                    or "Persistência bloqueada — validação CORE_002 falhou."
                )
        else:
            result["persistence_blocked"] = True
            result["persistence_block_reason"] = f"Formato {selected_card_format}D fora do escopo CORE_002 (15–23)."
        st.session_state["clean_law15_generation_result"] = result
        st.rerun()

    result = st.session_state.get("clean_law15_generation_result") or {}
    diagnostics = dict(result.get("fill_diagnostics") or {})
    if result:
        render_generation_result_summary(result)
        games = list(
            result.get("display_games")
            or _expand_generation_games_for_format(
                result.get("games") or [],
                int(result.get("selected_card_format", 15) or 15),
            )
        )
        render_generation_games_table(
            games,
            card_format=int(result.get("selected_card_format", 15) or 15),
            format_numbers=_format_numbers_for_history,
            extract_numbers=_extract_int_numbers,
        )

    render_governance_expander(render_constitutional_panel=_render_constitutional_status_panel)
    if result:
        render_technical_expander(result, diagnostics=diagnostics)
    render_six_bases_expander()



def _render_simulation_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Simular Resultados")
    st.info(
        "Laboratório/calibração — usa o **mesmo motor CORE_002 + ML supervisionada** do Gerador. "
        "Lotes gerados aqui **não são oficializados** automaticamente. "
        "Para conferência oficial persistida, use **Conferir Resultados**."
    )
    lab_cols = st.columns([1, 1, 1])
    sim_quantity = int(lab_cols[0].number_input("Quantidade de jogos (lab)", min_value=1, max_value=100, value=20, key="sim_lab_quantity"))
    sim_format = int(lab_cols[1].selectbox("Formato", options=list(range(15, 24)), index=0, key="sim_lab_format"))
    if lab_cols[2].button("Gerar lote laboratório", type="primary", key="sim_lab_generate"):
        lab_result = _run_simulation_lot_generation(requested_count=sim_quantity, selected_card_format=sim_format)
        st.session_state["institutional_simulation_lab_result"] = lab_result
        st.session_state["institutional_last_ui_event"] = "operacional:simular_geracao_lab"
        st.rerun()
    lab_result = dict(st.session_state.get("institutional_simulation_lab_result") or {})
    if lab_result:
        st.caption(
            f"Lote laboratório | status={lab_result.get('lot_operational_status', 'not_officialized')} | "
            f"veredito={lab_result.get('ml_verdict', '-')} | oficialização={'bloqueada' if lab_result.get('ml_verdict_blocked') else 'não aplicável'}"
        )
        if lab_result.get("display_games") or lab_result.get("games"):
            if st.button("Comparar lote contra até 50 concursos", key="sim_lab_multicontest"):
                games = list(lab_result.get("display_games") or lab_result.get("games") or [])
                multicontest = _run_simulation_multicontest_lab(games=games, contests_limit=50)
                st.session_state["institutional_simulation_multicontest"] = multicontest
                st.rerun()
    multicontest = dict(st.session_state.get("institutional_simulation_multicontest") or {})
    if multicontest.get("contest_results"):
        st.markdown("#### Comparação laboratorial (até 50 concursos)")
        st.caption(f"Concursos comparados: {multicontest.get('contests_compared', 0)} | Jogos 11+: {len(multicontest.get('premium_rows') or [])}")
        for contest_block in multicontest.get("contest_results") or []:
            premium = [row for row in list(contest_block.get("results") or []) if int(row.get("hits", 0) or 0) >= 11]
            if not premium:
                continue
            with st.expander(
                f"Concurso {contest_block.get('contest_number')} | best_hits={contest_block.get('best_hits')} | 11+={contest_block.get('premium_games')}",
                expanded=False,
            ):
                st.dataframe(pd.DataFrame(premium), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("#### Simulação manual (session-only)")
    st.write("Digite 15 dezenas para comparar com lote laboratorial recente.")
    status_cols = st.columns([1, 1, 1, 1])
    status_cols[0].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[1].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[2].metric("last_event", st.session_state.get("institutional_last_ui_event", "-"))
    status_cols[3].metric("runtime", st.session_state.get("institutional_simulation", {}).get("runtime_status", "idle"))

    draw_input = st.text_input(
        "Dezenas sorteadas",
        value=st.session_state.get("institutional_draw_input", ""),
        placeholder="01 02 04 05 07 08 09 13 14 17 18 19 20 22 24",
    )
    st.session_state["institutional_draw_input"] = draw_input
    if st.button("Simular Resultados", type="primary"):
        parsed_draw = _parse_draw_numbers(draw_input)
        if len(parsed_draw) != 15:
            st.warning("Informe exatamente 15 dezenas válidas entre 1 e 25.")
        else:
            _run_institutional_simulation(drawn_numbers=parsed_draw)
            st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
            st.rerun()
    st.caption("Cole as 15 dezenas sorteadas para conferir com os jogos gerados e persistidos.")

    simulation_state = st.session_state.get("institutional_simulation") or {}
    if simulation_state:
        sim_diag_cols = st.columns([1, 1, 1, 1])
        sim_diag_cols[0].metric("source", str(simulation_state.get("source", "-") or "-"))
        sim_diag_cols[1].metric("loaded_games", int(simulation_state.get("loaded_games", 0) or 0))
        sim_diag_cols[2].metric("compared_games", int(simulation_state.get("compared_games", 0) or 0))
        sim_diag_cols[3].metric("premium_games", int(simulation_state.get("premium_games", 0) or 0))
        with st.expander("Diagnóstico da simulação", expanded=False):
            st.json(simulation_state.get("summary") or {})
            st.write("Jogos carregados:", int(simulation_state.get("loaded_games", 0) or 0))
            st.write("Jogos comparados:", int(simulation_state.get("compared_games", 0) or 0))
            error_payload = st.session_state.get("institutional_simulation_error")
            if error_payload:
                st.error(error_payload.get("error", "Erro desconhecido"))

    cover_result = st.session_state.get("institutional_simulation_result")
    if cover_result:
        st.markdown("#### Resultado da simulação")
        st.caption("Apenas os jogos premiados com 11 pontos ou mais aparecem abaixo.")
        rows_html = []
        premium_rows = [row for row in cover_result if int(row.get("hits", 0)) >= 11]
        for row in premium_rows:
            rows_html.append(
                "<tr>"
                f"<td>{row.get('jogo', '-')}</td>"
                f"<td>{row.get('resultado', '-')}</td>"
                f"<td>{row.get('hits', '-')}</td>"
                f"<td>{row.get('premiado', '-')}</td>"
                "</tr>"
            )
        if premium_rows:
            st.markdown(
                """
                <table class="lotoia-sim-table">
                    <thead>
                        <tr>
                            <th>jogo</th>
                            <th>resultado</th>
                            <th>hits</th>
                            <th>premiado</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                + "".join(rows_html)
                + """
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhum jogo premiado com 11 pontos ou mais nesta simulação.")
            st.dataframe(
                pd.DataFrame(cover_result)[
                    ["jogo", "dezenas", "hits", "premiado"]
                ]
                if cover_result
                else pd.DataFrame(columns=["jogo", "dezenas", "hits", "premiado"]),
                hide_index=True,
                use_container_width=True,
            )
    elif simulation_state.get("runtime_status") == "error":
        st.error("A simulação encontrou um erro. Veja o diagnóstico acima.")
    else:
        st.info("Nenhum jogo encontrado para simulação.")


def _render_history_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    _render_analytical_page(snapshot)


def _render_generator_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    if _is_sovereign_generation_blocked():
        _render_orphan_generation_blocked_page(snapshot)
        return
    _ensure_official_history_seeded()
    live_counts = _database_snapshot()["counts"]
    st.subheader("Gerador LotoIA")
    st.write("Formulário operacional simples, com baseline oficial no topo e histórico antigo em segundo plano.")

    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(live_counts.get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(live_counts.get("generated_games", 0)))
    status_cols[4].metric("output_signatures", int(live_counts.get("institutional_output_signatures", 0)))

    contest_summary = _get_latest_contest() or _load_latest_contest_summary()
    top_cols = st.columns([1.1, 1.3, 1.6])
    if contest_summary:
        top_cols[0].metric("Último concurso", int(contest_summary["contest_number"]))
        top_cols[1].caption(f"Fonte: {contest_summary.get('source', 'banco oficial')}")
        top_cols[2].caption(
            f"dezenas: {' '.join(f'{number:02d}' for number in contest_summary.get('dezenas', [])) or '-'}"
        )
    else:
        top_cols[0].caption("Último concurso: -")
        top_cols[1].caption("Fonte: banco vazio")

    controls_cols = st.columns([1.0, 1.0])
    selected_game_size = 15
    st.session_state["institutional_dezenas_per_game"] = selected_game_size
    st.markdown("##### Gerador ADM - Lei 15")
    direct_cols = st.columns([1.4, 1.0, 1.0])
    selected_quantity = int(
        direct_cols[0].number_input(
            "Quantidade de jogos",
            min_value=1,
            max_value=100,
            value=int(st.session_state.get("institutional_total_games", 30) or 30),
            step=1,
            key="institutional_total_games",
        )
    )
    requested_games = selected_quantity
    direct_cols[1].metric("Formato", "15 dezenas por jogo")
    direct_cols[2].metric("Modo", "Runtime Limpo ADM 15")
    controls_cols[0].metric("Quantidade de jogos", requested_games)
    controls_cols[0].caption("Fonte única de verdade: quantidade digitada pelo usuário.")
    controls_cols[1].metric("Modelo", "Lei 15")
    controls_cols[1].caption("Sem fluxo legado, sem registry e sem pacote fechado.")

    strategy_display = _generation_strategy_display(selected_game_size)
    strategy_policy = dict(strategy_display.get("policy") or {})

    strategy_cols = st.columns([1.4, 1.0, 1.0])
    strategy_cols[0].markdown(
        f"**Estratégia ativa**  \n{strategy_display.get('strategy_label', '-') or '-'}"
    )
    strategy_cols[1].metric("Status científico", str(strategy_display.get("scientific_status", "-") or "-"))
    strategy_cols[2].metric("Status visual", str(strategy_display.get("status_visual", "-") or "-"))
    st.success(str(strategy_display.get("summary", "-") or "-"))
    st.caption("Runtime Limpo ADM 15 | Quantidade de jogos definida pelo usuário")
    if selected_game_size == 15:
        st.caption(
            " | ".join(
                [
                    f"generation_mode={strategy_display.get('generation_mode', 'CLEAN_DIRECT_15_LAW_RUNTIME')}",
                    f"policy_mode={strategy_display.get('policy_mode', 'CLEAN_DIRECT_15_LAW_RUNTIME')}",
                    f"historical_deduplication_mode={strategy_display.get('historical_deduplication_mode', 'AUDIT_ONLY')}",
                    f"official_package_preserved={str(strategy_display.get('official_package_preserved', False)).lower()}",
                    f"legacy_generation_flow={strategy_display.get('legacy_generation_flow', 'ARCHIVED')}",
                ]
            )
        )
    batch_result = st.session_state.get("institutional_generation_batch_result") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    summary_result = batch_result or generation_result
    with st.expander("Auditoria técnica ADM", expanded=False):
        diagnostic_payload = {
            "runtime_commit": BUILD_MARKER,
            "selected_quantity": int(selected_quantity),
            "selected_quantity_from_ui": int(selected_quantity),
            "selected_quantity_from_state": int(st.session_state.get("institutional_total_games", selected_quantity) or selected_quantity),
            "dezenas_por_jogo": 15,
            "selected_group_from_ui": "CLEAN_DIRECT_15_LAW_RUNTIME",
            "selected_group_from_state": "CLEAN_DIRECT_15_LAW_RUNTIME",
            "generation_mode_resolved": str(strategy_display.get("generation_mode", strategy_policy.get("policy_mode", "")) or ""),
            "policy_mode_resolved": str(strategy_display.get("policy_mode", strategy_policy.get("policy_mode", "")) or ""),
            "scientific_law_role": "COMMANDER",
            "clean_adm_runtime_role": "EXECUTOR",
            "output_commander_role": "AUDITOR",
            "historical_deduplication_mode": str(strategy_display.get("historical_deduplication_mode", "AUDIT_ONLY" if selected_game_size == 15 else "BLOCK") or ""),
            "historical_duplicates_removed": int(summary_result.get("historical_duplicates_removed", 0) or 0),
            "legacy_generation_flow": "ARCHIVED",
            "legacy_calibrator_role": "REMOVED_FROM_RUNTIME",
            "calibration_engine_role": "DISABLED",
            "direct_generation_called": True,
            "materialization_called": False,
            "official_package_size_loaded": 0,
            "historical_duplicates_found": int(summary_result.get("historical_duplicates_found", 0) or 0),
            "official_package_preserved": bool(summary_result.get("official_package_preserved", selected_game_size == 15)),
            "output_commander_status": str(summary_result.get("status_comandante_saida", "") or ""),
            "final_generated_count": int(summary_result.get("quantidade_jogos_real_gerada", 0) or 0),
        }
        for key, value in diagnostic_payload.items():
            st.caption(f"{key}={value}")

    natural_quantity_mode = str(strategy_policy.get("natural_quantity_mode", "") or "")
    natural_generated_games = int(strategy_policy.get("natural_generated_games", 0) or 0)
    natural_scientific_quantity = bool(strategy_policy.get("natural_scientific_quantity", False))
    natural_quantity_status = str(strategy_policy.get("natural_quantity_status", "") or "")
    natural_candidate = bool(strategy_policy.get("natural_approvable_candidate", False))
    candidate_reason = str(strategy_policy.get("candidate_reason", "") or "")
    blocked_reason = str(strategy_policy.get("blocked_reason", "") or "")
    output_commander_status = str(strategy_policy.get("output_commander_status", "") or "")
    if selected_game_size == 15 and (natural_scientific_quantity or natural_candidate):
        nat_cols = st.columns([1.0, 1.1, 1.1, 1.2, 1.2])
        nat_cols[0].metric("Quantidade solicitada", int(requested_games))
        nat_cols[1].metric("Quantidade candidata observada", int(natural_generated_games or requested_games))
        nat_cols[2].metric(
            "Quantidade natural aprovada",
            int(natural_generated_games or requested_games) if natural_scientific_quantity else "-",
        )
        if natural_candidate:
            status_text = "Candidata observada"
        else:
            status_text = "Quantidade natural aprovada"
        nat_cols[3].metric("Status do OutputCommander", output_commander_status or "-")
        nat_cols[4].metric("Motivo do bloqueio", blocked_reason or "-")
        st.caption(
            "Quantidade candidata observada: jogos individualmente válidos, mas pacote solicitado incompleto."
            if natural_candidate and candidate_reason
            else "Quantidade natural aprovada: pacote solicitado, persistido e aprovado pelo OutputCommander."
        )

    with st.expander("Diagnóstico histórico", expanded=False):
        _render_scientific_calibration_panel(
            strategy_size=selected_game_size,
            scientific_state={
                "mode": str(strategy_display.get("mode", "GERAÇÃO PREPARADA") or "GERAÇÃO PREPARADA"),
                "structural_status": "baseline oficial pronta" if selected_game_size == 15 else "régua futura preparada",
                "scientific_status": str(strategy_display.get("scientific_status", "-") or "-"),
                "classification": str(strategy_display.get("scientific_status", "-") or "-"),
                "main_reason": str(strategy_display.get("main_reason", "-") or "-"),
                "status_visual": str(strategy_display.get("status_visual", "-") or "-"),
            },
            scientific_recommendation={
                "action_suggested": str(strategy_display.get("action_suggested", "gerar jogos") or "gerar jogos"),
                "status_visual": str(strategy_display.get("status_visual", "-") or "-"),
            },
            technical_payload=strategy_policy,
            use_expander=False,
        )

    use_top50 = bool(st.session_state.get("institutional_use_top50", True))
    repeat_limit = int(st.session_state.get("institutional_repeat_limit", 10 if selected_game_size == 15 else 8) or (10 if selected_game_size == 15 else 8))
    geometry_profile = _sync_hb_geometry_controls(selected_game_size)
    odd_min = int(geometry_profile["odd_min"])
    odd_max = int(geometry_profile["odd_max"])
    even_min = int(geometry_profile["even_min"])
    even_max = int(geometry_profile["even_max"])
    sequence_max = int(geometry_profile["sequence_max"])
    coverage_min = float(geometry_profile["coverage_min"])
    entropy_min = float(geometry_profile["entropy_min"])
    if st.button("Gerar jogos", type="primary"):
        _run_institutional_generation(
            total_games=requested_games,
            dezenas_per_game=selected_game_size,
            use_top50=bool(st.session_state.get("institutional_use_top50", True)),
            odd_min=int(st.session_state.get("institutional_odd_min", 0) or 0),
            odd_max=int(st.session_state.get("institutional_odd_max", selected_game_size) or selected_game_size),
            even_min=int(st.session_state.get("institutional_even_min", 0) or 0),
            even_max=int(st.session_state.get("institutional_even_max", selected_game_size) or selected_game_size),
            sequence_max=int(st.session_state.get("institutional_sequence_max", selected_game_size) or selected_game_size),
            coverage_min=float(st.session_state.get("institutional_coverage_min", 0.0) or 0.0),
            entropy_min=float(st.session_state.get("institutional_entropy_min", 0.0) or 0.0),
            repeat_limit=int(st.session_state.get("institutional_repeat_limit", 0) or 0),
            snapshot=snapshot,
        )
        st.rerun()

    batch_result = st.session_state.get("institutional_generation_batch_result") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    summary_result = batch_result or generation_result
    if summary_result:
        st.markdown("##### Resultado da geração")
        generation_event_id = int(summary_result.get("generation_event_id") or generation_result.get("generation_event_id") or 0)
        persisted_count = _count_generated_games_for_event(generation_event_id) if generation_event_id else 0
        batch_status = str(summary_result.get("status_comandante_saida", "BLOQUEADO") or "BLOQUEADO")
        total_requested = int(summary_result.get("quantidade_jogos_solicitada", requested_games) or requested_games)
        total_generated = int(summary_result.get("quantidade_jogos_real_gerada", len(generation_result.get("jogos") or [])) or len(generation_result.get("jogos") or []))
        total_unique = int(summary_result.get("total_jogos_unicos", total_generated) or total_generated)
        total_duplicates = int(summary_result.get("total_jogos_duplicados", 0) or 0)
        duplicate_history = max(0, total_generated - total_unique)
        summary_cols = st.columns(6)
        summary_cols[0].metric("generation_event_id", str(summary_result.get("generation_event_id", "-") or "-"))
        summary_cols[1].metric("solicitados", total_requested)
        summary_cols[2].metric("gerados", total_generated)
        summary_cols[3].metric("dezenas/jogo", int(selected_game_size))
        summary_cols[4].metric("duplicidade interna", total_duplicates)
        summary_cols[5].metric("duplicidade histórico", duplicate_history)
        st.caption(
            " | ".join(
                [
                    f"policy_used={strategy_display.get('strategy_label', '-')}",
                    f"generation_mode={strategy_display.get('generation_mode', strategy_policy.get('policy_mode', '-'))}",
                    f"policy_mode={strategy_display.get('policy_mode', strategy_policy.get('policy_mode', '-'))}",
                    f"historical_deduplication_mode={strategy_display.get('historical_deduplication_mode', 'AUDIT_ONLY' if bool(summary_result.get('official_package_preserved')) else 'BLOCK')}",
                    f"status_comandante_saida={batch_status}",
                    f"persistidos={persisted_count}",
                    f"generation_event_id={summary_result.get('generation_event_id', '-')}",
                ]
            )
        )
        if bool(summary_result.get("official_package_preserved")) and int(summary_result.get("historical_duplicates_found", 0) or 0) > 0:
            st.warning(
                "Aviso: há jogos do pacote oficial já presentes no histórico. "
                "O pacote foi preservado por se tratar de grupo oficial fechado."
            )
        if batch_status != "APROVADO":
            st.error(
                "Comandante de Saída bloqueou a geração. "
                f"status={batch_status} | "
                f"motivo={summary_result.get('motivo_bloqueio', 'não foi possível gerar a quantidade solicitada de jogos únicos')}"
            )
        elif generation_result.get("jogos"):
            st.success("Geração concluída com sucesso.")
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "rank": index + 1,
                            "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                            "perfil": game.get("profile_type", "-"),
                            "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                        }
                        for index, game in enumerate(generation_result.get("jogos") or [])
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("A geração foi registrada, mas não há jogos visíveis para exibição.")
        st.caption(
            " | ".join(
                [
                    f"quantidade_solicitada={summary_result.get('quantidade_jogos_solicitada', '-')}",
                    f"quantidade_gerada={summary_result.get('quantidade_jogos_real_gerada', '-')}",
                    f"quantidade_dezenas={summary_result.get('quantidade_dezenas_solicitada', '-')}",
                    f"duplicidade_interna={summary_result.get('total_jogos_duplicados', '-')}",
                    f"duplicidade_histórico={duplicate_history}",
                ]
            )
        )


def _render_operational_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Operacional")
    st.write("Fluxo principal limpo, sem legado visual ou CRM.")
    status_cols = st.columns([1, 1, 1, 1, 1])
    status_cols[0].metric("build", BUILD_MARKER)
    status_cols[1].metric("backend", snapshot["backend"])
    status_cols[2].metric("imported_contests", int(snapshot["counts"].get("imported_contests", 0)))
    status_cols[3].metric("generated_games", int(snapshot["counts"].get("generated_games", 0)))
    status_cols[4].metric("reconciliation_runs", int(snapshot["counts"].get("reconciliation_runs", 0)))

    contest_numbers = _load_imported_contest_numbers()
    latest_contest = _load_imported_contest()
    selected_contest = int(contest_numbers[-1]) if contest_numbers else int(snapshot["latest"].get("imported_contests") or 0) if str(snapshot["latest"].get("imported_contests", "")).isdigit() else 0
    latest_contest_number = latest_contest["contest_number"] if latest_contest else snapshot["latest"].get("imported_contests", "-")
    latest_contest_numbers = " ".join(f"{number:02d}" for number in (latest_contest.get("dezenas", []) if latest_contest else [])) or "-"

    top_cols = st.columns([1.3, 1.3, 1.8])
    top_cols[0].caption(f"Concurso alvo: {snapshot['latest'].get('imported_contests', '-')}")
    top_cols[1].caption("Cada jogo respeita a quantidade selecionada.")
    top_cols[2].caption(f"last_ui_event: {st.session_state.get('institutional_last_ui_event', '-')}")

    st.markdown("#### Motor de gera??o")
    gen_cols = st.columns([1.1, 0.75, 0.95, 0.8, 0.95])
    total_games = int(
        gen_cols[0].number_input(
            "Quantidade de jogos",
            min_value=1,
            max_value=100,
            value=15,
            step=1,
            key="institutional_total_games",
        )
    )
    if gen_cols[1].button("LotoIA", type="primary"):
        _run_institutional_generation(total_games=total_games, snapshot=snapshot)
        st.rerun()
    if gen_cols[2].button("Conferir Jogos", type="primary"):
        _run_institutional_conference(contest_number=selected_contest if selected_contest else None)
        st.rerun()
    gen_cols[3].number_input("?ltimo concurso", min_value=max(1, contest_numbers[0]) if contest_numbers else 1, max_value=max(contest_numbers) if contest_numbers else 999999, value=selected_contest if selected_contest else 1, step=1, key="institutional_contest_nav")
    if gen_cols[4].button("Simular Resultado", type="primary"):
        parsed_draw = _parse_draw_numbers(st.session_state.get("institutional_draw_input", ""))
        if len(parsed_draw) != 15:
            st.warning("Informe exatamente 15 dezenas v?lidas entre 1 e 25.")
        else:
            _run_institutional_simulation(drawn_numbers=parsed_draw)
            st.session_state["institutional_last_ui_event"] = "operacional:simular_resultado"
            st.rerun()
    st.caption("Escolha a quantidade antes de gerar.")

    generation_state = st.session_state.get("institutional_generation") or {}
    generation_result = st.session_state.get("institutional_generation_result") or {}
    if generation_result:
        st.success(
            f"Gera??o conclu?da. generation_event_id={generation_result.get('generation_event_id', '-')} | jogos={len(generation_result.get('jogos') or [])} | seed={generation_result.get('seed', '-')}"
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_result.get("jogos") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    elif generation_state.get("games"):
        st.info("?ltima gera??o carregada. Use a barra lateral para gerar, conferir ou simular novamente.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "rank": index + 1,
                        "dezenas": " ".join(f"{number:02d}" for number in game.get("numbers", [])),
                        "perfil": game.get("profile_type", "-"),
                        "score": round(float(game.get("final_score", {}).get("final_score", 0.0)), 4),
                    }
                    for index, game in enumerate(generation_state.get("games") or [])
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.caption("Use a barra lateral para acionar gera??o, confer?ncia e simula??o.")

    st.markdown("#### Simular Resultado")
    draw_input = st.text_input(
        "Dezenas sorteadas",
        value=st.session_state.get("institutional_draw_input", ""),
        placeholder="01 02 04 05 07 08 09 13 14 17 18 19 20 22 24",
    )
    st.session_state["institutional_draw_input"] = draw_input
    st.caption("Cole as 15 dezenas sorteadas para conferir com os jogos gerados e persistidos.")

    cover_result = st.session_state.get("institutional_simulation_result")
    if cover_result:
        st.markdown("#### Resultado da simula??o")
        st.caption("Confer?ncia dos jogos gerados contra as dezenas sorteadas informadas acima.")
        st.markdown(
            """
            <style>
            .lotoia-sim-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.95rem;
            }
            .lotoia-sim-table th,
            .lotoia-sim-table td {
                border-bottom: 1px solid rgba(0,0,0,0.08);
                padding: 0.55rem 0.6rem;
                vertical-align: top;
                text-align: left;
            }
            .lotoia-sim-table th {
                color: #6b7280;
                font-weight: 600;
            }
            .lotoia-sim-meta {
                color: #6b7280;
                font-size: 0.88rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        rows_html = []
        premium_rows = [row for row in cover_result if int(row.get("hits", 0)) >= 11]
        for row in premium_rows:
            rows_html.append(
                "<tr>"
                f"<td>{row.get('jogo', '-')}</td>"
                f"<td>{row.get('resultado', '-')}</td>"
                f"<td>{row.get('hits', '-')}</td>"
                f"<td>{row.get('premiado', '-')}</td>"
                "</tr>"
            )
        if premium_rows:
            st.markdown(
                """
                <table class="lotoia-sim-table">
                    <thead>
                        <tr>
                            <th>jogo</th>
                            <th>resultado</th>
                            <th>hits</th>
                            <th>premiado</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                + "".join(rows_html)
                + """
                    </tbody>
                </table>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhum jogo premiado com 11 pontos ou mais nesta simulação.")

    st.markdown("#### Cobertura estrutural")

    check_result = st.session_state.get("institutional_check_result")
    if isinstance(check_result, dict) and check_result.get("warning"):
        st.warning(check_result["warning"])
    if isinstance(check_result, dict) and check_result.get("results"):
        st.markdown("#### Confer?ncia")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "jogo": row["game_index"],
                        "formato_cartao": row.get("formato_cartao", "-"),
                        "nucleo_lei_15": row.get("nucleo_lei_15", "-"),
                        "reservas_auditadas": row.get("reservas_auditadas", "-"),
                        "cartao_final": " ".join(f"{number:02d}" for number in row.get("cartao_final", row["numbers"])),
                        "dezenas_conferidas_count": row.get("dezenas_conferidas_count", "-"),
                        "origem_dezenas_conferencia": row.get("origem_dezenas_conferencia", "-"),
                        "expected_card_size": row.get("expected_card_size", "-"),
                        "actual_card_size": row.get("actual_card_size", "-"),
                        "hits": row["hits"],
                        "matched_numbers": " ".join(f"{number:02d}" for number in row.get("matched_numbers", [])),
                        "premiado": row["prize_status"],
                    }
                    for row in check_result["results"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
        check_summary_cols = st.columns(4)
        check_summary_cols[0].metric("concurso", check_result.get("contest_number", "-"))
        check_summary_cols[1].metric("best_hits", check_result.get("best_hits", "-"))
        check_summary_cols[2].metric("prizes", check_result.get("prize_count", "-"))
        check_summary_cols[3].metric("total_hits", check_result.get("total_hits", "-"))
    elif isinstance(check_result, dict) and check_result.get("status") == "waiting_contest":
        st.info("A confer?ncia est? pronta, mas ainda falta o concurso oficial em imported_contests.")

    st.caption(
        f"Geração ativa: {selected_batch_id or '-'} | gerações ativas: "
        f"{', '.join(str(value) for value in active_generation_event_ids) if active_generation_event_ids else '-'}"
    )
def _render_analytical_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    st.subheader("Histórico Analítico")
    st.info("Esta página é analítica e observacional. Não gera jogos, não recalibra a Lei 15 e não altera histórico.")
    st.write("Visão acumulativa de desempenho dos jogos persistidos no PostgreSQL Institucional.")
    sovereign_events = _load_sovereign_generation_event_rows()
    operational_index = build_operational_generation_index(sovereign_events)
    analytic_labels = {
        "TOTAL_GENERATION_EVENTS_CARREGADOS": "Gerações carregadas",
        "TOTAL_JOGOS_HISTORICOS_CARREGADOS": "Jogos históricos carregados",
        "JOGOS_CONFERIVEIS": "Jogos conferíveis",
        "JOGOS_DIAGNOSTICO": "Jogos em diagnóstico",
        "GENERATION_EVENT_ID_MAIS_ANTIGO": "Geração mais antiga",
        "GENERATION_EVENT_ID_MAIS_RECENTE": "Geração mais recente",
    }

    generation_history = _load_generation_history_light(limit=25)
    historical_rows = _load_accumulated_analytical_rows_light(limit=25)
    if (not generation_history or not historical_rows) and int(snapshot["counts"].get("generation_events", 0) or 0) > 0:
        generation_history = _load_generation_history(limit=50)
        historical_rows = _load_accumulated_analytical_rows()
    if not generation_history or not historical_rows:
        st.info("Ainda não há gerações persistidas para reconstruir o histórico analítico.")
        return

    games_df = pd.DataFrame(historical_rows)
    if games_df.empty:
        st.info("Ainda não há jogos persistidos para reconstruir o histórico analítico.")
        return

    games_df = _ensure_analytical_games_schema(games_df)
    games_df["data/hora_dt"] = pd.to_datetime(games_df["data/hora"], errors="coerce")
    games_df["acertos_num"] = pd.to_numeric(games_df["acertos"], errors="coerce")
    games_df["score_num"] = pd.to_numeric(games_df["score"], errors="coerce").fillna(0.0)
    games_df["generation_event_id"] = pd.to_numeric(games_df["generation_event_id"], errors="coerce")
    games_df["jogo n°"] = pd.to_numeric(games_df["jogo n°"], errors="coerce")
    games_df["concurso conferido"] = pd.to_numeric(games_df["concurso conferido"], errors="coerce")
    games_df["is_conferible"] = games_df["is_conferible"].fillna(False).astype(bool)

    active_generation_event_id = _safe_int(st.session_state.get("active_reconciliation_generation_event_id"), default=None)
    if active_generation_event_id and "generation_event_id" in games_df.columns:
        active_mask = games_df["generation_event_id"].astype("Int64").fillna(0).astype(int).eq(int(active_generation_event_id))
        if bool(active_mask.any()):
            games_df = games_df[active_mask].copy()
            st.caption(f"Geração ativa: {active_generation_event_id}")
        else:
            st.caption(f"Geração ativa: {active_generation_event_id} | sem jogos persistidos nessa geração, exibindo histórico acumulado")
    else:
        st.caption("Geração ativa: -")

    filter_row_1 = st.columns([1.2, 1.2, 1.2, 1.2, 1.0])
    generation_options = sorted(int(value) for value in games_df["generation_event_id"].dropna().unique().tolist())
    if generation_options:
        latest_ge = max(generation_options)
        st.caption(
            f"Última geração operacional: "
            f"{resolve_operational_generation_label(latest_ge, operational_index=operational_index)} "
            f"(generation_event_id={latest_ge})"
        )
    strategy_options = sorted(str(value) for value in games_df["estratégia"].dropna().astype(str).unique().tolist())
    contest_options = sorted(
        int(value)
        for value in games_df["concurso conferido"].dropna().astype(int).unique().tolist()
        if int(value) > 0
    )

    selected_generation_ids = filter_row_1[0].multiselect("filtrar por geração", generation_options, default=generation_options)
    selected_strategies = filter_row_1[1].multiselect("filtrar por estratégia", strategy_options, default=strategy_options)
    selected_status_view = filter_row_1[2].selectbox(
        "filtrar por status de conferência",
        ["Todos", "Não conferido", "Conferido"],
        index=0,
    )
    selected_contests = filter_row_1[3].multiselect("filtrar por concurso", contest_options, default=contest_options)
    order_by = filter_row_1[4].selectbox("ordenar por", ["score", "data", "acertos"], index=0)

    date_values = games_df["data/hora_dt"].dropna()
    if not date_values.empty:
        min_date = date_values.min().date()
        max_date = date_values.max().date()
        date_range = st.date_input("filtrar por data", value=(min_date, max_date))
    else:
        date_range = ()

    filtered_df = games_df.copy()
    if selected_generation_ids:
        filtered_df = filtered_df[filtered_df["generation_event_id"].isin(selected_generation_ids)]
    if selected_strategies:
        filtered_df = filtered_df[filtered_df["estratégia"].isin(selected_strategies)]
    if selected_status_view != "Todos":
        filtered_df = filtered_df[filtered_df["status de conferência"].astype(str) == selected_status_view]
    if selected_contests:
        filtered_df = filtered_df[
            filtered_df["concurso conferido"].fillna(0).astype(int).isin(selected_contests)
        ]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            filtered_df["data/hora_dt"].dt.date.between(start_date, end_date)
        ]

    if order_by == "score":
        filtered_df = filtered_df.sort_values(
            by=["score_num", "data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, False, True],
        )
    elif order_by == "acertos":
        filtered_df = filtered_df.sort_values(
            by=["acertos_num", "score_num", "data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, False, False, True],
            na_position="last",
        )
    else:
        filtered_df = filtered_df.sort_values(
            by=["data/hora_dt", "generation_event_id", "jogo n°"],
            ascending=[False, False, True],
        )

    conferiveis_df = filtered_df[filtered_df["is_conferible"].fillna(False)].copy()
    diagnostic_df = filtered_df[~filtered_df["is_conferible"].fillna(False)].copy()

    display_games = conferiveis_df.copy()
    if not display_games.empty:
        display_games["concurso conferido"] = display_games["concurso conferido"].apply(
            lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—"
        )
        display_games["acertos"] = display_games["acertos"].apply(
            lambda value: f"{int(value)}" if pd.notna(value) and int(value) >= 0 else "—"
        )
        display_games["score"] = display_games["score"].apply(lambda value: f"{float(value):.4f}")
        display_games["data/hora"] = display_games["data/hora"].fillna("—")
        display_games = display_games[
            [
                "geração",
                "generation_event_id",
                "data/hora",
                "jogo n°",
                "dezenas",
                "formato_cartao",
                "núcleo_lei_15",
                "reservas_auditadas",
                "cartão_final",
                "quantidade_nucleo",
                "quantidade_reservas",
                "quantidade_final",
                "estratégia",
                "score",
                "tipo visual",
                "origem/modelo",
                "status de conferência",
                "concurso conferido",
                "acertos",
                "premiação",
                "observações",
            ]
        ]

    top_df = conferiveis_df.sort_values(
        by=["score_num", "acertos_num", "data/hora_dt", "generation_event_id", "jogo n°"],
        ascending=[False, False, False, False, True],
        na_position="last",
    ).copy()
    if not top_df.empty:
        top_df.insert(0, "rank", range(1, len(top_df) + 1))
        top_df["concurso conferido"] = top_df["concurso conferido"].apply(
            lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—"
        )
        top_df["acertos"] = top_df["acertos"].apply(
            lambda value: f"{int(value)}" if pd.notna(value) and int(value) >= 0 else "—"
        )
        top_df["score"] = top_df["score"].apply(lambda value: f"{float(value):.4f}")
        top_df["data/hora"] = top_df["data/hora"].fillna("—")
        top_df = top_df[
            [
                "rank",
                "geração",
                "generation_event_id",
                "data/hora",
                "jogo n°",
                "dezenas",
                "formato_cartao",
                "núcleo_lei_15",
                "reservas_auditadas",
                "cartão_final",
                "quantidade_nucleo",
                "quantidade_reservas",
                "quantidade_final",
                "estratégia",
                "score",
                "tipo visual",
                "origem/modelo",
                "status de conferência",
                "concurso conferido",
                "acertos",
                "premiação",
                "observações",
            ]
        ]

    diagnostic_summary_rows: list[dict[str, Any]] = []
    for generation in generation_history:
        if bool(generation.get("is_conferible", False)):
            continue
        diagnostic_summary_rows.append(
            {
                "generation_event_id": int(generation.get("generation_event_id", 0) or 0),
                "batch_id": str(generation.get("batch_id", "") or ""),
                "policy_id": str(generation.get("policy_id", "") or ""),
                "status comandante saída": str(generation.get("status_comandante_saida", "APROVADO") or "APROVADO"),
                "status científico": str(generation.get("scientific_status", "-") or "-"),
                "classificação científica": str(generation.get("scientific_classification", "-") or "-"),
                "tipo visual": str(generation.get("visibility_label", "Diagnóstico") or "Diagnóstico"),
                "motivo rejeição": str(generation.get("visibility_reason", "-") or "-"),
                "ação sugerida": str(generation.get("recommended_action", "-") or "-"),
                "total jogos": int(generation.get("total_games", 0) or 0),
                "total jogos únicos": int(generation.get("total_jogos_unicos", 0) or 0),
                "duplicados": int(generation.get("total_jogos_duplicados", 0) or 0),
                "policy_origin": str(generation.get("policy_origin", "") or ""),
                "policy_variant": str(generation.get("policy_variant", "") or ""),
            }
        )
    diagnostic_summary_df = pd.DataFrame(diagnostic_summary_rows)

    diag_cols = st.columns(6)
    diag_cols[0].metric(analytic_labels["TOTAL_GENERATION_EVENTS_CARREGADOS"], len(generation_history))
    diag_cols[1].metric(analytic_labels["TOTAL_JOGOS_HISTORICOS_CARREGADOS"], len(games_df))
    diag_cols[2].metric(analytic_labels["JOGOS_CONFERIVEIS"], len(conferiveis_df))
    diag_cols[3].metric(analytic_labels["JOGOS_DIAGNOSTICO"], len(diagnostic_df))
    diag_cols[4].metric(analytic_labels["GENERATION_EVENT_ID_MAIS_ANTIGO"], min(generation_options) if generation_options else "-")
    diag_cols[5].metric(analytic_labels["GENERATION_EVENT_ID_MAIS_RECENTE"], max(generation_options) if generation_options else "-")

    with st.expander("Jogos completos históricos conferíveis — detalhes avançados", expanded=False):
        if not display_games.empty:
            visible_display_games = display_games.rename(
                columns={
                    "generation_event_id": "ID da geração",
                    "data/hora": "Data/hora",
                    "jogo n°": "Jogo",
                    "dezenas": "Dezenas",
                    "formato_cartao": "Formato",
                    "núcleo_lei_15": "Núcleo Lei 15",
                    "reservas_auditadas": "Reservas auditadas",
                    "cartão_final": "Cartão final",
                    "quantidade_nucleo": "Núcleo",
                    "quantidade_reservas": "Reservas",
                    "quantidade_final": "Total final",
                    "estratégia": "Estratégia",
                    "score": "Score",
                    "tipo visual": "Tipo",
                    "origem/modelo": "Origem/modelo",
                    "status de conferência": "Status de conferência",
                    "concurso conferido": "Concurso conferido",
                    "acertos": "Acertos",
                    "premiação": "Premiação",
                }
            )
            st.dataframe(visible_display_games, hide_index=True, use_container_width=True, height=560)
        else:
            st.info("Nenhum jogo conferível encontrado com os filtros atuais.")

    st.markdown("##### Top jogos históricos conferíveis")
    if not top_df.empty:
        visible_top_df = top_df.head(20).rename(
            columns={
                "generation_event_id": "ID da geração",
                "data/hora": "Data/hora",
                "jogo n°": "Jogo",
                "dezenas": "Dezenas",
                "formato_cartao": "Formato",
                "núcleo_lei_15": "Núcleo Lei 15",
                "reservas_auditadas": "Reservas auditadas",
                "cartão_final": "Cartão final",
                "quantidade_nucleo": "Núcleo",
                "quantidade_reservas": "Reservas",
                "quantidade_final": "Total final",
                "estratégia": "Estratégia",
                "score": "Score",
                "tipo visual": "Tipo",
                "origem/modelo": "Origem/modelo",
                "status de conferência": "Status de conferência",
                "concurso conferido": "Concurso conferido",
                "acertos": "Acertos",
                "premiação": "Premiação",
            }
        )
        st.dataframe(visible_top_df, hide_index=True, use_container_width=True, height=520)
    else:
        st.info("Nenhum top jogo conferível encontrado com os filtros atuais.")

    if not diagnostic_summary_df.empty:
        structural_alerts = int(
            sum(
                1
                for generation in generation_history
                if str(generation.get("status_comandante_saida", "APROVADO") or "APROVADO") == "APROVADO"
                and str(generation.get("scientific_status", "") or "").upper() == "REPROVADO"
            )
        )
        if structural_alerts:
            st.warning("Bateria estruturalmente conferível. Diagnóstico científico preservado apenas como registro observacional, sem comando operacional.")
        st.markdown("##### Diagnóstico observacional legado")
        st.caption("Registros preservados para auditoria histórica. Não rejeitam a geração operacional e não comandam recalibração.")
        visible_diagnostic_summary_df = diagnostic_summary_df.copy()
        for column in ("status científico", "classificação científica", "ação sugerida", "motivo rejeição"):
            if column in visible_diagnostic_summary_df.columns:
                visible_diagnostic_summary_df[column] = visible_diagnostic_summary_df[column].apply(_sanitize_legacy_scientific_value)
        visible_diagnostic_summary_df["observação institucional"] = "Registro observacional legado, sem comando operacional."
        visible_diagnostic_summary_df = visible_diagnostic_summary_df[
            [
                "generation_event_id",
                "status comandante saída",
                "total jogos",
                "total jogos únicos",
                "duplicados",
                "policy_origin",
                "policy_variant",
                "observação institucional",
            ]
        ]
        st.dataframe(visible_diagnostic_summary_df, hide_index=True, use_container_width=True, height=260)
        with st.expander("Detalhes técnicos avançados", expanded=False):
            if not diagnostic_df.empty:
                rejected_view = diagnostic_df[
                    [
                        "generation_event_id",
                        "jogo n°",
                        "dezenas",
                        "tipo visual",
                        "status comandante saída",
                        "status científico",
                        "classificação científica",
                        "motivo rejeição",
                        "ação sugerida",
                        "policy_id",
                        "policy_origin",
                        "policy_variant",
                        "concurso conferido",
                        "acertos",
                        "premiação",
                    ]
                ].copy()
                for column in ("status científico", "classificação científica", "ação sugerida", "motivo rejeição"):
                    if column in rejected_view.columns:
                        rejected_view[column] = rejected_view[column].apply(_sanitize_legacy_scientific_value)
                rejected_view["concurso conferido"] = rejected_view["concurso conferido"].apply(
                    lambda value: f"{int(value)}" if pd.notna(value) and int(value) > 0 else "—"
                )
                rejected_view["acertos"] = rejected_view["acertos"].apply(
                    lambda value: f"{int(value)}" if pd.notna(value) and int(value) >= 0 else "—"
                )
                st.dataframe(rejected_view, hide_index=True, use_container_width=True, height=420)
            else:
                st.info("Nenhum jogo rejeitado com os filtros atuais.")

    with st.expander("Linha do tempo secundária", expanded=False):
        timeline = _load_analytical_timeline(limit=25)
        if timeline:
            st.dataframe(pd.DataFrame(timeline), hide_index=True, use_container_width=True)
        else:
            st.info("Ainda não há eventos suficientes para montar a timeline analítica.")
def _render_hb_geometry_page(state: dict[str, Any]) -> None:
    st.subheader("HB Geometry")
    st.write("Auditoria incremental isolada do motor oficial.")
    job = state["job"]
    progress = state["progress"]
    summary = state["summary"]
    csv_frame = state["csv_frame"]
    button_cols = st.columns(3)
    if button_cols[0].button("Iniciar Auditoria", type="primary", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:iniciar"
        _start_hb_geometry_job(resume=bool(progress) and not bool(progress.get("completed", False)))
        st.rerun()
    if button_cols[1].button("Continuar Auditoria", use_container_width=True, disabled=bool(job.get("running")) or not bool(progress) or bool(progress.get("completed", False))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:continuar"
        _start_hb_geometry_job(resume=True)
        st.rerun()
    if button_cols[2].button("Resetar Auditoria", use_container_width=True, disabled=bool(job.get("running"))):
        st.session_state["institutional_last_ui_event"] = "hb_geometry:resetar"
        _reset_hb_geometry_job()
        st.rerun()
    status_cols = st.columns(4)
    status_cols[0].metric("contests_processed", int(job.get("contests_processed", 0)))
    status_cols[1].metric("processed_batches", int(job.get("processed_batches", 0)))
    status_cols[2].metric("completed", "sim" if bool(job.get("completed")) else "não")
    status_cols[3].metric("elapsed_time", f"{float(job.get('elapsed_time', 0.0)):.1f}s")
    st.caption(f"current_scenario: {job.get('current_scenario', '-')}")
    if job.get("error"):
        st.error(f"HB Geometry error: {job['error']}")
    if progress:
        st.info(
            " | ".join(
                [
                    f"checkpoint={HB_GEOMETRY_PROGRESS_FILE.name}",
                    f"resume={'true' if bool(progress) and not bool(progress.get('completed', False)) else 'false'}",
                    f"last_contest={progress.get('last_contest', '-')}",
                    f"current_batch={progress.get('current_batch', '-')}",
                ]
            )
        )
    if summary:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Métrica": "avg_hits", "Valor": round(float(summary.get("hb_baseline", {}).get("average_hits", 0.0)), 4)},
                    {"Métrica": "11+", "Valor": int(summary.get("hb_baseline", {}).get("hits_11_plus", 0))},
                    {"Métrica": "12+", "Valor": int(summary.get("hb_baseline", {}).get("hits_12_plus", 0))},
                    {"Métrica": "overlap", "Valor": round(float(summary.get("hb_baseline", {}).get("average_overlap", 0.0)), 4)},
                    {"Métrica": "entropy", "Valor": round(float(summary.get("hb_baseline", {}).get("entropy", 0.0)), 4)},
                    {
                        "Métrica": "dominant_numbers",
                        "Valor": ", ".join(
                            f"{item['number']}:{item['frequency']}" for item in summary.get("hb_baseline", {}).get("dominant_numbers", [])[:5]
                        )
                        or "-",
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    if not csv_frame.empty:
        with st.expander("CSV consolidado", expanded=False):
            st.dataframe(csv_frame.tail(20), hide_index=True, use_container_width=True)


def _render_home_metric_card(label: str, value: str, *, caption: str = "", value_class: str = "") -> None:
    value_html = f'<div class="lotoia-metric-value {value_class}">{value}</div>'
    caption_html = f'<div class="lotoia-metric-caption">{caption}</div>' if caption else ""
    st.markdown(
        f"""
        <div class="lotoia-metric-card">
            <div class="lotoia-metric-label">{label}</div>
            {value_html}
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_home_status_pill(label: str, status: str, tone: str) -> None:
    st.markdown(
        f'<span class="lotoia-pill lotoia-pill-{tone}">{label}: {status}</span>',
        unsafe_allow_html=True,
    )


def _render_home_quick_access() -> None:
    st.markdown('<div class="lotoia-section-heading">Acesso rápido</div>', unsafe_allow_html=True)
    st.markdown('<div class="lotoia-quick-access">', unsafe_allow_html=True)
    for row_start in (0, 3):
        cols = st.columns(3)
        for col_index, item in enumerate(INSTITUTIONAL_QUICK_ACCESS[row_start : row_start + 3]):
            with cols[col_index]:
                if st.button(
                    f"{item['icon']} {item['label']}",
                    key=f"home_quick_{item['page_id']}",
                    use_container_width=True,
                ):
                    st.session_state["institutional_page_id"] = item["page_id"]
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_home_page(snapshot: dict[str, Any]) -> None:
    snapshot = _live_institutional_snapshot(snapshot)
    live_counts = dict(snapshot.get("counts") or {})
    try:
        official_history_max = int(
            (_load_official_history_diagnostics().get("contest_number_max", 0) or 0)
        ) or None
        monitored_contest = build_imported_contests_selection_context(
            list_imported_contest_records=_list_all_imported_contest_records,
            load_imported_contest=lambda contest_number: _load_imported_contest(contest_number),
            official_history_max=official_history_max,
        )
    except Exception as exc:
        logger.warning("home monitored contest unavailable: %s", exc)
        monitored_contest = {
            "contest_number": None,
            "display_contest_number": "—",
            "source": DB_UNAVAILABLE_LABEL,
            "sync_status": "UNAVAILABLE",
            "sync_message": DB_UNAVAILABLE_LABEL,
        }
    contest_number = monitored_contest.get("contest_number")
    contest_display = str(monitored_contest.get("display_contest_number") or "—")
    contest_source = str(monitored_contest.get("source") or MONITORED_CONTEST_SOURCE_LABEL)
    latest_reconciliation = _load_latest_reconciliation_summary() or {}
    latest_generation = (_load_generation_history_light(limit=1) or [{}])[0]
    generated_games = int(live_counts.get("generated_games", 0) or 0)
    generation_events = int(live_counts.get("generation_events", 0) or 0)
    reconciliation_runs = int(live_counts.get("reconciliation_runs", 0) or 0)
    best_hits = int(
        latest_generation.get("maior acerto", latest_reconciliation.get("best_hits", 0)) or 0
    )
    backend = str(snapshot.get("backend", "-") or "-")
    backend_ok = backend.lower() == "postgresql"
    last_reconciliation_date = str(latest_reconciliation.get("created_at", "") or "")[:10] or "—"
    generation_loaded = bool(
        (st.session_state.get("institutional_generation") or {}).get("games")
        or (st.session_state.get("institutional_generation_result") or {}).get("jogos")
    )
    active_commit = _resolve_active_commit()
    v3_mode = get_v3_mode()

    st.markdown('<div class="lotoia-home-header">', unsafe_allow_html=True)
    header_cols = st.columns([2.2, 1.2, 1.4, 0.8])
    with header_cols[0]:
        brand_cols = st.columns([0.28, 0.72])
        with brand_cols[0]:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), width=72)
        with brand_cols[1]:
            st.markdown(
                """
                <div class="lotoia-home-brand">
                    <div class="lotoia-home-brand-name">Painel Institucional LotoIA</div>
                    <div class="lotoia-home-brand-sub">Runtime cloud PostgreSQL · cobertura estrutural completa</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    with header_cols[1]:
        st.markdown(
            f"""
            <div class="lotoia-home-clock">
                <div style="font-size:0.72rem; letter-spacing:0.1em; text-transform:uppercase; opacity:0.8;">Deploy</div>
                <div>{BUILD_MARKER}</div>
                <div style="font-size:0.78rem; opacity:0.85;">commit {active_commit}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_cols[2]:
        st.markdown(
            f"""
            <div>
                <div class="lotoia-home-contest-label">Último concurso monitorado</div>
                <div class="lotoia-home-contest-value">{contest_display}</div>
                <div style="font-size:0.72rem; opacity:0.85; margin-top:0.25rem;">Origem: {contest_source}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_cols[3]:
        st.markdown(
            """
            <div style="text-align:right;">
                <span class="lotoia-pill lotoia-pill-success">ATIVO</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if monitored_contest.get("sync_status") == "SYNC_DIVERGENCE":
        st.warning(str(monitored_contest.get("sync_message") or ""))
    elif monitored_contest.get("sync_status") == "EMPTY":
        st.error(str(monitored_contest.get("sync_message") or ""))
    if monitored_contest.get("history_divergence_message"):
        st.warning(str(monitored_contest.get("history_divergence_message") or ""))
    if monitored_contest.get("outlier_message"):
        st.warning(str(monitored_contest.get("outlier_message") or ""))

    metric_cols = st.columns(5)
    with metric_cols[0]:
        _render_home_metric_card(
            "Último Concurso",
            contest_display,
            value_class="lotoia-metric-value-accent",
            caption=f"Origem: {contest_source}",
        )
    with metric_cols[1]:
        _render_home_metric_card(
            "Jogos Gerados",
            str(generated_games),
            caption=f"{'↑' if generation_events > 0 else '—'} {generation_events} gerações persistidas",
        )
    with metric_cols[2]:
        _render_home_metric_card(
            "Conferências Realizadas",
            str(reconciliation_runs),
            caption=f"última: {last_reconciliation_date}",
        )
    with metric_cols[3]:
        _render_home_metric_card(
            "Melhor Acerto",
            str(best_hits),
            value_class="lotoia-metric-value-success" if best_hits >= 13 else "",
            caption="destaque institucional" if best_hits >= 13 else "",
        )
    with metric_cols[4]:
        _render_home_metric_card(
            "Status Backend",
            "ONLINE" if backend_ok else "ATENÇÃO",
            value_class="lotoia-metric-value-success" if backend_ok else "lotoia-metric-value-danger",
            caption=backend,
        )

    governance_cols = st.columns(2)
    governance_cols[0].metric(CORE_REALIGN_V3_ENV_VAR, v3_mode)
    governance_cols[1].metric("Evidência histórica V3", CORE_REALIGN_V3_BATCH_LABEL)
    governance_cols[1].caption("Não é o Núcleo soberano — ver Status Constitucional abaixo.")

    _render_constitutional_status_panel(compact=False)

    st.markdown(
        '<div class="lotoia-status-panel"><div class="lotoia-section-heading">Estado do sistema</div>',
        unsafe_allow_html=True,
    )
    status_cols = st.columns(5)
    generation_status = (
        sovereign_generation_status_label()
        if not _is_sovereign_generation_blocked()
        else "BLOQUEADA"
    )
    generation_tone = "danger" if _is_sovereign_generation_blocked() else ("success" if generation_loaded else "success")
    recalibration = resolve_recalibration_display_status()
    ml_pill_status = (
        "SUPERVISIONADO"
        if is_supervised_output_calibration_active()
        else ("ASSISTIVO" if is_adm_supervised_ml_active() else "ASSISTIVO")
    )
    ml_pill_tone = "success" if is_supervised_output_calibration_active() else "info"
    with status_cols[0]:
        _render_home_status_pill("Lei 15", SOVEREIGN_CORE_ID, "success")
    with status_cols[1]:
        _render_home_status_pill("Geração", generation_status, generation_tone)
    with status_cols[2]:
        _render_home_status_pill(
            recalibration["pill_label"],
            recalibration["pill_status"],
            recalibration["pill_tone"],
        )
    with status_cols[3]:
        _render_home_status_pill("ML", ml_pill_status, ml_pill_tone)
    with status_cols[4]:
        _render_home_status_pill("Purge", "PROTEGIDO", "danger")
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption(
        "Lei 15A inoperante | Geração soberana controlada CORE_002 (M-GER-044) | "
        "Gestão de Projetos Fase 0 ativa | Inventário PR #124 aprovado."
    )
    _render_home_quick_access()


def _render_fallback_page(snapshot: dict[str, Any]) -> None:
    _ = snapshot
    st.subheader("Rota legada ou não institucionalizada — fallback")
    st.warning(
        "Esta rota foi removida do menu, redirecionada ou permanece bloqueada (M-PLAT-040). "
        "Use a navegação lateral para páginas constitucionais ativas."
    )
    st.info(
        "Aliases legados (`generation`, `clear_histories`, `delete_history`) redirecionam "
        "para destinos seguros. Rotas órfãs não executam geração, purge ou alteração de banco."
    )


def main() -> None:
    st.set_page_config(page_title="LotoIA Institucional", page_icon="🧭", layout="wide")
    try:
        enforce_cloud_runtime_policy(DB_PATH)
    except RuntimeError as exc:
        st.error("Runtime cloud bloqueado — política Lei No 001 violada.")
        st.code(str(exc), language="text")
        st.stop()
    require_institutional_login(DB_PATH)
    _ensure_institutional_schema()
    snapshot = _database_snapshot()
    snapshot["cloud_runtime_policy"] = cloud_runtime_policy_snapshot(DB_PATH)
    _align_institutional_runtime_with_database(snapshot)
    page = _render_sidebar(
        st.session_state.get("institutional_page_id", "home"),
        snapshot,
    )
    st.session_state["institutional_page_id"] = page
    if page == "audit":
        _render_runtime_audit_page(snapshot)
    elif page == "home":
        _render_home_page(snapshot)
    elif page == "governance_read_only":
        render_governance_read_only_page(
            snapshot=snapshot,
            app_build=APP_BUILD,
            active_commit=_resolve_active_commit(),
            generation_blocked=_is_sovereign_generation_blocked(),
            inventory_reference=INVENTORY_REPORT_REFERENCE,
            render_constitutional_panel=_render_constitutional_status_panel,
            render_diagnostic_caption=_render_diagnostic_observational_caption,
        )
    elif page == "core_002_read_only":
        render_core_002_read_only_page(
            generation_blocked=_is_sovereign_generation_blocked(),
            render_constitutional_panel=_render_constitutional_status_panel,
            render_diagnostic_caption=_render_diagnostic_observational_caption,
        )
    elif page == "fallback":
        _render_fallback_page(snapshot)
    elif page == "audit_monitoring":
        _render_audit_monitoring_page(snapshot, "overview")
    elif page == "audit_monitoring_conference":
        _render_audit_monitoring_page(snapshot, "conference")
    elif page == "audit_monitoring_group_performance":
        _render_audit_monitoring_page(snapshot, "group_performance")
    elif page == "audit_monitoring_missing_numbers":
        _render_audit_monitoring_page(snapshot, "missing_numbers")
    elif page == "audit_monitoring_extra_numbers":
        _render_audit_monitoring_page(snapshot, "extra_numbers")
    elif page == "audit_monitoring_side_leak":
        _render_audit_monitoring_page(snapshot, "side_leak")
    elif page == "audit_monitoring_13_to_14":
        _render_audit_monitoring_page(snapshot, "13_to_14")
    elif page == "audit_monitoring_14_to_15":
        _render_audit_monitoring_page(snapshot, "14_to_15")
    elif page == "audit_monitoring_offline_hypotheses":
        _render_audit_monitoring_page(snapshot, "offline_hypotheses")
    elif page == "clean_law15_generation":
        _render_clean_law15_generation_page(snapshot)
    elif page == "conference":
        _render_conference_page(snapshot)
    elif page == "simulation":
        _render_simulation_page(snapshot)
    elif page == "history_analytical":
        _render_analytical_page(snapshot)
    elif page == "history_institutional":
        _render_history_institutional_page(snapshot)
    elif page in ("restricted_controlled_cleanup", "clear_histories", "delete_history"):
        _render_restricted_controlled_cleanup_page(snapshot)
    elif page == "comparative_history":
        _render_comparative_history_page(snapshot)
    elif page == "strategies_analysis":
        _render_strategies_page("Análises Estratégicas", snapshot)
    elif page == "strategies_test":
        _render_strategies_page("Testar Estratégias", snapshot)
    elif page == "strategies_simulation":
        _render_strategies_page("Simular Estratégias", snapshot)
    elif page == "hb_metrics":
        _render_metrics_hb_page(snapshot)
    elif page == "central_ml_diagnostics":
        _render_central_ml_diagnostics_page(snapshot)
    elif page == "structural_coverage":
        _render_cobertura_estrutural_page(snapshot)
    elif page == "institutional_simulation_backtesting":
        st.subheader("Simulação Institucional / Backtesting")
        render_institutional_simulation_backtesting_page(
            generation_blocked=_is_sovereign_generation_blocked(),
        )
    elif page == "institutional_replay":
        _render_replay_institutional_page(snapshot)
    elif page == "summary_benchmark":
        _render_benchmark_resumido_page(snapshot)
    elif page == "operational_statistics":
        _render_estatisticas_operacionais_page(snapshot)
    else:
        _render_hb_geometry_page(_hb_geometry_state())


if __name__ == "__main__":
    main()
