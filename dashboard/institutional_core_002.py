"""Pacote Núcleo Lei 15 — LEI15_CORE_002 read-only no Painel ADM (M-VIS-033)."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import streamlit as st

from lotoia.governance.lei15_core_002_sovereign import (
    BATCH_LABEL as SOVEREIGN_BATCH_LABEL,
    REALIGNMENT_NAME as SOVEREIGN_CORE_ID,
)
from dashboard.institutional_lei15a_governance import LEI15A_FORMAL_STATUS
from lotoia.governance.lei15_core_six_bases_evaluation import (
    BASE_LABELS_PT,
    BASE_NAMES,
    CAND_D_ASSESSMENT,
    LEGACY_BASELINE_ASSESSMENT,
    V1_ASSESSMENT,
)

CORE_002_READ_ONLY_ALERT = (
    "Núcleo Lei 15 — read-only. Nenhuma geração, calibração, edição de matriz ou purge "
    "é executada nesta tela."
)

INSTITUTIONAL_MATRIX_QUOTE = (
    "O LEI15_CORE_002 é uma matriz soberana de papéis das dezenas 01–25, "
    "não um cartão fixo de 15 dezenas."
)

SIX_BASES_QUOTE = "Hit isolado não é veredicto. O Núcleo é avaliado pelas 6 bases."

ELIGIBLE_UNIVERSE = tuple(range(1, 26))

REINFORCE_DIGITS: frozenset[int] = frozenset({7, 12, 16, 23})
BLIND_SPOT_DIGITS: frozenset[int] = frozenset({6, 16, 17})
CONTEXTUAL_PENALTY_DIGITS: frozenset[int] = frozenset({2, 4, 11, 15, 24, 25})
NEVER_HARD_BLOCK_DIGITS: frozenset[int] = frozenset({15, 24, 25})
CONTROLLED_PREFIX_DIGITS: frozenset[int] = frozenset({1, 2, 3})
CONTROLLED_SUFFIX_DIGITS: frozenset[int] = frozenset({22, 23, 24, 25})

SIX_BASES_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "base": "Base 1 — Força de acerto",
        "mede": "Se a estrutura produz bons resultados cruzáveis (hits 12+/13+).",
        "importancia": "Hit é evidência, não veredicto final — cruzar com bases 2–6.",
        "status": "pendente de métrica operacional no painel",
    },
    {
        "base": "Base 2 — Diversidade suficiente",
        "mede": "Distribuição de perfis e assinaturas sem colapso em um único padrão.",
        "importancia": "Evita vício estrutural e concentração de clones no lote.",
        "status": "pendente de métrica operacional no painel",
    },
    {
        "base": "Base 3 — Baixa redundância",
        "mede": "Overlap e clones estruturais entre cartões do GP.",
        "importancia": "Redundância tolerada no pool; anti-clone atua no GP final.",
        "status": "pendente de métrica operacional no painel",
    },
    {
        "base": "Base 4 — Controle prefixo/sufixo",
        "mede": "Vícios dominantes nas faixas 01–03 e 22–25.",
        "importancia": "Penalização contextual — prefixo/sufixo produtivos preserváveis.",
        "status": "conceitual CORE_002 implantado (caps documentais ADR-046)",
    },
    {
        "base": "Base 5 — Cobertura das dezenas críticas",
        "mede": "Presença inteligente de reforços e blind spots (06/16/17, 07/12/23).",
        "importancia": "Cobertura ≠ contagem cega — papéis soberanos governam elegibilidade.",
        "status": "pendente de métrica operacional no painel",
    },
    {
        "base": "Base 6 — Estabilidade em vários concursos",
        "mede": "Sustentação estrutural em janelas walk-forward (10/20/30).",
        "importancia": "Performance de um concurso não invalida o Núcleo se o equilíbrio persiste.",
        "status": "pendente de métrica operacional no painel",
    },
)

HISTORICAL_EVIDENCE_ROWS: tuple[dict[str, str], ...] = (
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
        "variante": "Lei 15A (camada futura)",
        "classificacao": "Redefinida / inoperante",
        "soberano": "NÃO",
        "nota": "Subordinada ao CORE_002 — expansão 15+1/15+2 não reativada (M-GOV-038).",
    },
    {
        "variante": SOVEREIGN_CORE_ID,
        "classificacao": "Núcleo Soberano constitucional",
        "soberano": "SIM",
        "nota": f"Label operacional futuro: {SOVEREIGN_BATCH_LABEL} — geração bloqueada.",
    },
)


def _digit_roles(number: int) -> list[str]:
    roles: list[str] = ["elegível"]
    if number in REINFORCE_DIGITS:
        roles.append("reforço")
    if number in BLIND_SPOT_DIGITS:
        roles.append("blind spot")
    if number in CONTEXTUAL_PENALTY_DIGITS:
        roles.append("penalização contextual")
    if number in NEVER_HARD_BLOCK_DIGITS:
        roles.append("nunca hard-block")
    if number in CONTROLLED_PREFIX_DIGITS:
        roles.append("prefixo controlado/preservável")
    if number in CONTROLLED_SUFFIX_DIGITS:
        roles.append("sufixo controlado/preservável")
    return roles


def build_sovereign_matrix_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number in ELIGIBLE_UNIVERSE:
        roles = _digit_roles(number)
        rows.append(
            {
                "dezena": f"{number:02d}",
                "papeis": ", ".join(roles),
                "reforco": "sim" if number in REINFORCE_DIGITS else "—",
                "blind_spot": "sim" if number in BLIND_SPOT_DIGITS else "—",
                "penalizacao_contextual": "sim" if number in CONTEXTUAL_PENALTY_DIGITS else "—",
                "nunca_hard_block": "sim" if number in NEVER_HARD_BLOCK_DIGITS else "—",
            }
        )
    return rows


def build_core_002_snapshot(*, generation_blocked: bool) -> dict[str, Any]:
    """Snapshot read-only para testes — sem efeitos colaterais."""
    return {
        "read_only_alert": CORE_002_READ_ONLY_ALERT,
        "core_id": SOVEREIGN_CORE_ID,
        "batch_label": SOVEREIGN_BATCH_LABEL,
        "eligible_universe": "01–25",
        "matrix_quote": INSTITUTIONAL_MATRIX_QUOTE,
        "six_bases_quote": SIX_BASES_QUOTE,
        "reinforce_digits": sorted(REINFORCE_DIGITS),
        "blind_spot_digits": sorted(BLIND_SPOT_DIGITS),
        "contextual_penalty_digits": sorted(CONTEXTUAL_PENALTY_DIGITS),
        "never_hard_block_digits": sorted(NEVER_HARD_BLOCK_DIGITS),
        "controlled_prefix_digits": sorted(CONTROLLED_PREFIX_DIGITS),
        "controlled_suffix_digits": sorted(CONTROLLED_SUFFIX_DIGITS),
        "generation_status": "BLOQUEADA" if generation_blocked else "HABILITADA",
        "ml_status": "ASSISTIVO — sem efeito operacional automático",
        "lei15a_status": LEI15A_FORMAL_STATUS,
        "adm_path": "generate_best_games preparado (M-LEI15-003)",
        "public_app_scope": "fora do escopo desta missão",
        "matrix_rows": build_sovereign_matrix_rows(),
        "six_bases_definitions": [dict(row) for row in SIX_BASES_DEFINITIONS],
        "six_bases_historical": {
            "V1": V1_ASSESSMENT.as_dict(),
            "CAND-D": CAND_D_ASSESSMENT.as_dict(),
            "LEGACY-BASELINE": LEGACY_BASELINE_ASSESSMENT.as_dict(),
        },
        "historical_evidence": [dict(row) for row in HISTORICAL_EVIDENCE_ROWS],
        "coverage_guidance": (
            "Cobertura Estrutural no painel é leitura observacional. "
            "Referência constitucional: LEI15_CORE_002. "
            "Lotes V2/V3/V4 são evidência histórica — histórico não é núcleo soberano."
        ),
    }


def render_core_002_read_only_page(
    *,
    generation_blocked: bool,
    render_constitutional_panel: Callable[..., None],
    render_diagnostic_caption: Callable[[], None],
) -> None:
    """Renderiza Núcleo Lei 15 — CORE_002 (somente leitura)."""
    payload = build_core_002_snapshot(generation_blocked=generation_blocked)

    st.subheader("Núcleo Lei 15 — CORE_002")
    st.info(CORE_002_READ_ONLY_ALERT)
    st.markdown(f"*{INSTITUTIONAL_MATRIX_QUOTE}*")
    st.markdown(f"*{SIX_BASES_QUOTE}*")
    render_diagnostic_caption()

    tab_status, tab_matrix, tab_bases, tab_historico, tab_cobertura = st.tabs(
        [
            "Status do Núcleo",
            "Matriz Soberana 01–25",
            "Leitura pelas 6 Bases",
            "Evidências históricas",
            "Cobertura Estrutural",
        ]
    )

    with tab_status:
        render_constitutional_panel(compact=False)
        st.markdown("##### Status operacional (read-only)")
        cols = st.columns(2)
        cols[0].metric("Núcleo soberano", payload["core_id"])
        cols[1].metric("Label soberano", payload["batch_label"])
        cols[0].metric("Universo elegível", payload["eligible_universe"])
        cols[1].metric("Geração", payload["generation_status"])
        cols[0].metric("ML", "ASSISTIVO")
        cols[1].metric("Lei 15A", "INOPERANTE")
        st.caption(
            f"Path ADM preparado: `{payload['adm_path']}`. "
            f"`public_app`: {payload['public_app_scope']}."
        )
        st.warning(
            "Todas as dezenas 01–25 permanecem elegíveis. Reforço ≠ obrigatoriedade. "
            "Penalização contextual ≠ exclusão. Nunca hard-block = a dezena não deve ser "
            "proibida cegamente. O CORE_002 governa papéis, não fixa um jogo."
        )

    with tab_matrix:
        st.markdown("##### Matriz Soberana — papéis das dezenas")
        st.dataframe(
            pd.DataFrame(payload["matrix_rows"]),
            hide_index=True,
            use_container_width=True,
        )
        legend_cols = st.columns(3)
        legend_cols[0].markdown(
            f"**Reforços:** {', '.join(f'{d:02d}' for d in payload['reinforce_digits'])}"
        )
        legend_cols[1].markdown(
            f"**Blind spots:** {', '.join(f'{d:02d}' for d in payload['blind_spot_digits'])}"
        )
        legend_cols[2].markdown(
            "**Penalização contextual:** "
            + ", ".join(f"{d:02d}" for d in payload["contextual_penalty_digits"])
        )
        st.caption(
            f"Nunca hard-block: {', '.join(f'{d:02d}' for d in payload['never_hard_block_digits'])} | "
            f"Prefixo controlado: {', '.join(f'{d:02d}' for d in payload['controlled_prefix_digits'])} | "
            f"Sufixo controlado: {', '.join(f'{d:02d}' for d in payload['controlled_suffix_digits'])}"
        )

    with tab_bases:
        st.markdown("##### Leitura pelas 6 Bases (institucional)")
        st.dataframe(
            pd.DataFrame(payload["six_bases_definitions"]),
            hide_index=True,
            use_container_width=True,
        )
        st.markdown("##### Leituras históricas registradas (não soberanas)")
        for variant_key, assessment in payload["six_bases_historical"].items():
            with st.expander(f"{variant_key} — {assessment.get('batch_label', '-')}", expanded=False):
                for name in BASE_NAMES:
                    st.markdown(f"- **{BASE_LABELS_PT[name]}:** `{assessment.get(name, '-')}`")
                st.caption(assessment.get("institutional_reading", ""))
        st.info(
            f"Leitura operacional do {SOVEREIGN_CORE_ID} no painel: métricas walk-forward "
            "pendentes — avaliação constitucional pelas 6 bases permanece obrigatória antes "
            "de qualquer liberação de geração."
        )

    with tab_historico:
        st.markdown("##### Reclassificação de evidências históricas")
        st.dataframe(
            pd.DataFrame(payload["historical_evidence"]),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Histórico não é núcleo soberano. V1/CAND-D/V2/V3/V4/baseline = consulta apenas.")

    with tab_cobertura:
        st.markdown("##### Cobertura Estrutural — orientação CORE_002")
        st.write(payload["coverage_guidance"])
        st.markdown(
            "- Cobertura **não** é simples contagem de dezenas.\n"
            "- **Não** usar V3 como referência soberana.\n"
            "- **CORE_002** é a referência constitucional.\n"
            "- Evidências históricas podem aparecer como comparação secundária na página "
            "**Cobertura estrutural** — sempre rotuladas como histórico."
        )
        st.info(
            "Use o menu **Cobertura estrutural** para diagnósticos observacionais de lote. "
            "Esta aba não executa consultas — apenas orienta a leitura constitucional."
        )
