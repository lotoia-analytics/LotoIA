"""Cobertura Estrutural governamental — 6 Bases read-only no Painel ADM (M-VIS-034)."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL as SOVEREIGN_BATCH_LABEL,
    REALIGNMENT_NAME as SOVEREIGN_CORE_ID,
)
from lotoia.governance.lei15_core_six_bases_evaluation import (
    BASE_LABELS_PT,
    BASE_NAMES,
    CAND_D_ASSESSMENT,
    LEGACY_BASELINE_ASSESSMENT,
    V1_ASSESSMENT,
)

STRUCTURAL_COVERAGE_READ_ONLY_ALERT = (
    "Cobertura Estrutural — read-only. Nenhuma geração, calibração, edição de matriz ou purge "
    "é executada nesta tela."
)

INSTITUTIONAL_ALERTS: tuple[str, ...] = (
    "Cobertura Estrutural não é promessa de acerto.",
    "A leitura pelas 6 Bases é diagnóstica e governamental.",
    "Nenhuma ação operacional é executada nesta tela.",
)

SIX_BASES_QUOTE = "Hit isolado não é veredicto. O Núcleo é avaliado pelas 6 bases."

METRIC_EXPECTATIONS: dict[str, str] = {
    "forca_acerto": "Média ponderada de hits 12+/13+ em janela walk-forward (10/20/30 concursos).",
    "diversidade": "Entropia / cobertura de perfis sem colapso estrutural no lote.",
    "baixa_redundancia": "Overlap e clones estruturais entre cartões do GP.",
    "controle_prefixo_sufixo": "Distribuição e vícios nas faixas 01–03 e 22–25.",
    "cobertura_dezenas_criticas": "Presença inteligente de reforços (07/12/16/23) e blind spots (06/16/17).",
    "estabilidade_multi_concurso": "Variância de métricas em janelas walk-forward comparáveis.",
}

HISTORICAL_VARIANTS: tuple[tuple[str, Any], ...] = (
    ("V1 — matriz histórica de força (não soberana)", V1_ASSESSMENT),
    ("CAND-D — matriz histórica de controle (não soberana)", CAND_D_ASSESSMENT),
    ("Baseline legado — controle histórico congelado (não soberano)", LEGACY_BASELINE_ASSESSMENT),
)

SOVEREIGN_HISTORICAL_ROWS: tuple[dict[str, str], ...] = (
    {
        "variante": "V1 (STRUCT_REALIGN_V1_15D_001)",
        "classificacao": "Evidência histórica — matriz de força",
        "soberano": "NÃO",
        "nota": "Força de acerto forte no segmento ≥13; não é Núcleo operacional.",
    },
    {
        "variante": "CAND-D (STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001)",
        "classificacao": "Evidência histórica — matriz de controle",
        "soberano": "NÃO",
        "nota": "Controle estrutural e diversidade; origem do pool L1 do CORE_002.",
    },
    {
        "variante": "V2 / V3 / V4",
        "classificacao": "Evidência histórica — realinhamentos",
        "soberano": "NÃO",
        "nota": "Comparativo EPOCH_001; não caminho de evolução atual.",
    },
    {
        "variante": "Baseline legado (STRUCT_TEST_15D_001)",
        "classificacao": "Controle histórico congelado",
        "soberano": "NÃO",
        "nota": "Read-only — não candidato ativo.",
    },
    {
        "variante": SOVEREIGN_CORE_ID,
        "classificacao": "Núcleo Soberano constitucional",
        "soberano": "SIM",
        "nota": f"Label operacional futuro: {SOVEREIGN_BATCH_LABEL} — geração bloqueada.",
    },
)


def _historical_evidence_for_base(base_name: str) -> str:
    parts: list[str] = []
    for label, assessment in HISTORICAL_VARIANTS:
        rating = getattr(assessment, base_name)
        parts.append(f"{label.split(' — ')[0]}={rating}")
    return "; ".join(parts)


def _pending_for_base(base_name: str) -> str:
    if base_name == "controle_prefixo_sufixo":
        return "Conceitual CORE_002 implantado — métrica walk-forward pendente no painel."
    return "Métrica operacional walk-forward pendente para LEI15_CORE_002."


def build_six_bases_governance_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name in BASE_NAMES:
        rows.append(
            {
                "base": BASE_LABELS_PT[name],
                "definicao": _base_definition(name),
                "metrica_esperada": METRIC_EXPECTATIONS[name],
                "evidencia_historica": _historical_evidence_for_base(name),
                "pendencia_core_002": _pending_for_base(name),
            }
        )
    return rows


def _base_definition(base_name: str) -> str:
    definitions = {
        "forca_acerto": "Se a estrutura produz bons resultados cruzáveis (hits 12+/13+).",
        "diversidade": "Distribuição de perfis e assinaturas sem colapso em um único padrão.",
        "baixa_redundancia": "Overlap e clones estruturais entre cartões do GP.",
        "controle_prefixo_sufixo": "Vícios dominantes nas faixas 01–03 e 22–25.",
        "cobertura_dezenas_criticas": "Presença inteligente de reforços e blind spots estruturais.",
        "estabilidade_multi_concurso": "Sustentação estrutural em janelas walk-forward (10/20/30).",
    }
    return definitions[base_name]


def build_structural_coverage_snapshot(*, generation_blocked: bool) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": STRUCTURAL_COVERAGE_READ_ONLY_ALERT,
        "institutional_alerts": list(INSTITUTIONAL_ALERTS),
        "six_bases_quote": SIX_BASES_QUOTE,
        "core_id": SOVEREIGN_CORE_ID,
        "batch_label": SOVEREIGN_BATCH_LABEL,
        "generation_status": "BLOQUEADA" if generation_blocked else "HABILITADA",
        "six_bases_rows": build_six_bases_governance_rows(),
        "historical_evidence": [dict(row) for row in SOVEREIGN_HISTORICAL_ROWS],
        "historical_assessments": {
            "V1": V1_ASSESSMENT.as_dict(),
            "CAND-D": CAND_D_ASSESSMENT.as_dict(),
            "LEGACY-BASELINE": LEGACY_BASELINE_ASSESSMENT.as_dict(),
        },
        "coverage_guidance": (
            "Cobertura Estrutural é leitura observacional e governamental. "
            "Referência constitucional: LEI15_CORE_002. "
            "Lotes V2/V3/V4 são evidência histórica — histórico não é núcleo soberano."
        ),
    }


def render_structural_coverage_governance_section(*, generation_blocked: bool) -> None:
    """Bloco institucional read-only — 6 Bases + separação soberano/histórico."""
    payload = build_structural_coverage_snapshot(generation_blocked=generation_blocked)

    st.info(STRUCTURAL_COVERAGE_READ_ONLY_ALERT)
    for alert in INSTITUTIONAL_ALERTS:
        st.warning(alert)
    st.markdown(f"*{SIX_BASES_QUOTE}*")

    ref_cols = st.columns(3)
    ref_cols[0].metric("Referência constitucional", payload["core_id"])
    ref_cols[1].metric("Label soberano", payload["batch_label"])
    ref_cols[2].metric("Geração", payload["generation_status"])

    st.markdown("##### Leitura pelas 6 Bases — governança CORE_002")
    st.caption(payload["coverage_guidance"])
    st.dataframe(
        pd.DataFrame(payload["six_bases_rows"]),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Evidência histórica por base (não soberana)")
    for label, assessment in HISTORICAL_VARIANTS:
        with st.expander(label, expanded=False):
            for name in BASE_NAMES:
                st.markdown(f"- **{BASE_LABELS_PT[name]}:** `{getattr(assessment, name)}`")
            st.caption(assessment.institutional_reading)

    st.markdown("##### Separação constitucional — soberano vs histórico")
    st.dataframe(
        pd.DataFrame(payload["historical_evidence"]),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "V1 é matriz histórica de força, não soberana. CAND-D é matriz histórica de controle, "
        "não soberana. V2/V3/V4 e baseline são históricos/legados. CORE_002 é referência constitucional."
    )
