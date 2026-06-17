"""Decisão assistida ML — Núcleo Lei 15 candidato (interpretável, não preditivo).

Política: docs/governance/POLITICA_ML_ASSISTIVO.md
Papel ML: diagnose + structured fusion (V1 força + CAND-D controle)
Não substitui Lei 15 nem promove active automaticamente.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Final

ML_DECISION_REGISTRY: Final = "ML_LEI15_CORE_CANDIDATE_DECISION_2026_06_17"
CANDIDATE_ID: Final = "LEI15_CORE_CANDIDATE_002"
CANDIDATE_LABEL_PROPOSED: Final = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"

BASE_NAMES: Final = (
    "forca_acerto",
    "diversidade",
    "baixa_redundancia",
    "controle_prefixo_sufixo",
    "cobertura_dezenas_criticas",
    "estabilidade_multi_concurso",
)

# Evidências EPOCH_001 consolidadas (read-only, sem nova coleta)
CONSOLIDATED_EVIDENCE: Final = {
    "epoch": "EPOCH_001",
    "contests": list(range(3705, 3712)),
    "legacy_core": {
        "status": "baseline_congelado_read_only",
        "label": "STRUCT_TEST_15D_001",
        "verdict": "descartado_como_caminho_ativo",
    },
    "v1": {
        "label": "STRUCT_REALIGN_V1_15D_001",
        "best_hit": 14,
        "strong_avg": 13.07,
        "runs_13_plus": 75,
        "runs_14": 5,
        "contests_with_13_plus": 7,
        "contests_total": 7,
        "unique_cards_13_plus": 64,
        "v1_strong_pattern_pct": 85.9,
        "p3_123_gp_pct": 36.0,
        "p3_123_strong_pct": 32.8,
        "s3_222425_gp_pct": 25.1,
        "s3_222425_strong_pct": 46.9,
        "mean_overlap_13_plus": 10.83,
        "six_bases_strong_segment": {
            "forca_acerto": "forte",
            "diversidade": "parcial",
            "baixa_redundancia": "fraca",
            "controle_prefixo_sufixo": "parcial",
            "cobertura_dezenas_criticas": "parcial",
            "estabilidade_multi_concurso": "forte",
        },
    },
    "cand_d": {
        "label": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
        "ge_id": 115,
        "p3_123_pct": 4.0,
        "s3_222425_pct": 8.0,
        "relabeling": 0,
        "best_hit": 11,
        "avg_hits": 9.286,
        "runs_13_plus": 0,
        "six_bases": {
            "forca_acerto": "inconclusiva",
            "diversidade": "forte",
            "baixa_redundancia": "fraca",
            "controle_prefixo_sufixo": "forte",
            "cobertura_dezenas_criticas": "parcial",
            "estabilidade_multi_concurso": "inconclusiva",
        },
    },
    "failed_lanes": ["V2", "V3", "V4"],
    "complementarity": "V1_forca_CAND_D_controle",
}


@dataclass(frozen=True, slots=True)
class BaseContribution:
    source: str
    rating: str
    weight: float
    note: str


@dataclass(frozen=True, slots=True)
class SixBasesFusion:
    """Fusão interpretável V1 + CAND-D → proposta CAND-002."""

    ratings: dict[str, str]
    contributions: dict[str, list[BaseContribution]]
    projected_balance_score: float


@dataclass(frozen=True, slots=True)
class CoreCandidateArchitecture:
    candidate_id: str
    proposed_label: str
    mode: str
    layers: list[dict[str, Any]]
    preserve_from_v1: list[str]
    incorporate_from_cand_d: list[str]
    penalize_not_block: list[str]
    critical_digits: dict[str, Any]
    prefix_suffix_policy: dict[str, Any]
    anti_clone_policy: dict[str, Any]
    redundancy_policy: dict[str, Any]
    v1_strong_shield: dict[str, Any]
    lei15a_gate: dict[str, Any]


def _rating_score(r: str) -> float:
    return {"forte": 3.0, "parcial": 2.0, "inconclusiva": 1.0, "fraca": 0.0}.get(r, 0.0)


def fuse_six_bases(evidence: dict[str, Any]) -> SixBasesFusion:
    v1 = evidence["v1"]["six_bases_strong_segment"]
    cd = evidence["cand_d"]["six_bases"]

    contributions: dict[str, list[BaseContribution]] = {}
    projected: dict[str, str] = {}

    for base in BASE_NAMES:
        parts: list[BaseContribution] = []
        v1_r = v1.get(base, "inconclusiva")
        cd_r = cd.get(base, "inconclusiva")

        if base == "forca_acerto":
            parts.append(BaseContribution("V1", v1_r, 0.65, "Seleção/composição V1"))
            parts.append(BaseContribution("CAND-D", cd_r, 0.10, "Não substitui seleção V1"))
            projected[base] = "parcial" if v1_r == "forte" else "inconclusiva"
            if v1_r == "forte":
                projected[base] = "forte"
        elif base == "controle_prefixo_sufixo":
            parts.append(BaseContribution("V1", v1_r, 0.25, "Sufixos produtivos preservados"))
            parts.append(BaseContribution("CAND-D", cd_r, 0.55, "N-C1..N-C6 na geração"))
            projected[base] = "forte" if cd_r == "forte" else "parcial"
        elif base == "diversidade":
            parts.append(BaseContribution("V1", v1_r, 0.30, "Perfis mistos nos fortes"))
            parts.append(BaseContribution("CAND-D", cd_r, 0.50, "N-C4 quota + N-C3"))
            projected[base] = "forte" if cd_r == "forte" else "parcial"
        elif base == "baixa_redundancia":
            parts.append(BaseContribution("V1", v1_r, 0.20, "Overlap ~10.8 nos fortes"))
            parts.append(BaseContribution("CAND-D", "parcial", 0.35, "Anti-clone GP novo"))
            projected[base] = "parcial"
        elif base == "cobertura_dezenas_criticas":
            parts.append(BaseContribution("V1", v1_r, 0.35, "12/16/15/25 nos fortes"))
            parts.append(BaseContribution("CAND-D", cd_r, 0.40, "Blind spots N-C3"))
            projected[base] = "parcial"
        elif base == "estabilidade_multi_concurso":
            parts.append(BaseContribution("V1", v1_r, 0.70, "7/7 concursos com ≥13"))
            parts.append(BaseContribution("CAND-D", cd_r, 0.05, "Piloto único"))
            projected[base] = "forte" if v1_r == "forte" else "inconclusiva"

        contributions[base] = parts

    balance = sum(_rating_score(projected[b]) for b in BASE_NAMES)
    return SixBasesFusion(
        ratings=projected,
        contributions={k: [asdict(x) for x in v] for k, v in contributions.items()},
        projected_balance_score=balance,
    )


def build_architecture(evidence: dict[str, Any], fusion: SixBasesFusion) -> CoreCandidateArchitecture:
    return CoreCandidateArchitecture(
        candidate_id=CANDIDATE_ID,
        proposed_label=CANDIDATE_LABEL_PROPOSED,
        mode="shadow_test_only",
        layers=[
            {
                "order": 1,
                "name": "generation_cdx_d",
                "source": "CAND-D N-C1..N-C6",
                "role": "Pool diverso com controle prefixo/sufixo na origem",
            },
            {
                "order": 2,
                "name": "v1_selection_compose",
                "source": "V1 realignment",
                "role": "Seleção/composição preservando base_score e padrões V1-strong",
            },
            {
                "order": 3,
                "name": "v1_strong_shield",
                "source": "lei15_core_structural_payload",
                "role": "Reduz penalização estrutural em padrões V1-strong comprovados",
            },
            {
                "order": 4,
                "name": "anti_clone_gp",
                "source": "CAND-002 GP policy",
                "role": "Limita overlap e assinaturas duplicadas no GP final",
            },
            {
                "order": 5,
                "name": "critical_digit_layer",
                "source": "Auditoria V1≥13",
                "role": "Reforço 07/23; penalização contextual 15/25",
            },
        ],
        preserve_from_v1=[
            "composição/seleção V1 (realignment V1)",
            "shield padrões V1-strong (prefixos 01-02-03, 01-03-04; sufixos 22-24-25, 23-24-25, 18-24-25)",
            "estabilidade multi-concurso (evidência 7/7)",
            "distribuição por perfil recorrente/híbrido/caótico nos cartões fortes",
        ],
        incorporate_from_cand_d=[
            "N-C4 pool por quota de perfil",
            "N-C5 sem relabeling",
            "N-C1 cap overlap + penalização estrutural (não block cego prefix 123)",
            "N-C6 dampen recurrence",
            "N-C3 híbrido 4-7 + blind spots 06/16/17",
            "N-C2 cap sufixo alto com exceção sufixos produtivos V1-strong",
        ],
        penalize_not_block=[
            "prefixo 01-02-03 acima de 15% no GP (penalidade, não veto)",
            "sufixo 22-24-25 acima de cap configurável com shield V1-strong",
            "concentração de arquitetura (prefix+suffix) acima de 12% no GP",
            "dezenas 15/25 em excesso contextual (penalidade, não ausência)",
        ],
        critical_digits={
            "reinforce": {
                "digits": [7, 12, 16, 23],
                "rationale": "07 e 23 subcobertos nos V1≥13; 12/16 presentes nos fortes",
                "mechanism": "soft_boost_in_pool_sampling_min_presence",
                "target_min_presence_pct": 45,
            },
            "contextual_discourage": {
                "digits": [2, 4, 11, 15, 24, 25],
                "rationale": "15/25 aparecem em 87.5% dos V1≥13 — penalizar concentração, não vetar",
                "mechanism": "penalty_when_joint_presence_exceeds_threshold",
                "never_hard_block": [15, 24, 25],
            },
        },
        prefix_suffix_policy={
            "generation_soft_caps": {
                "prefix_01_02_03_max_pct": 15,
                "suffix_22_24_25_max_pct": 35,
            },
            "productive_suffixes_preserve": [
                "22-24-25",
                "23-24-25",
                "18-24-25",
                "21-24-25",
            ],
            "productive_prefixes_preserve_with_shield": [
                "01-02-03",
                "01-03-04",
                "01-03-06",
                "01-04-06",
            ],
            "relabeling": False,
            "compare_baseline": {"p3_legacy": 42.0, "s3_legacy": 53.0},
        },
        anti_clone_policy={
            "gp_max_pairwise_overlap": 10,
            "gp_max_same_architecture_pct": 12,
            "scope": "GP_final_only",
            "exempt": "cartões com padrão V1-strong comprovado no pool",
        },
        redundancy_policy={
            "tolerable_mean_overlap_strong_pool": 10.8,
            "block_clones_above_overlap": 11,
            "note": "Redundância tolerada no pool; anti-clone atua no GP",
        },
        v1_strong_shield={
            "enabled": True,
            "bias_reduction": 18,
            "patterns": "STRONG_V1_PREFIXES + STRONG_V1_SUFFIXES",
            "evidence": f"{evidence['v1']['v1_strong_pattern_pct']}% cartões ≥13",
        },
        lei15a_gate={
            "open_15a": False,
            "condition": "Núcleo Lei 15 candidato validado em teste limpo 15D multi-GE",
            "sequence": ["CAND-002 shadow_test", "gate 6 bases", "governança ADR", "15A posterior"],
        },
    )


def build_ml_decision(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    ev = evidence or CONSOLIDATED_EVIDENCE
    fusion = fuse_six_bases(ev)
    arch = build_architecture(ev, fusion)

    weak_count = sum(1 for r in fusion.ratings.values() if r == "fraca")
    inconclusive = sum(1 for r in fusion.ratings.values() if r == "inconclusiva")

    if fusion.projected_balance_score >= 14 and weak_count == 0:
        final_verdict = "NÚCLEO CANDIDATO DEFINIDO"
        governance_next = "NECESSITA GOVERNANÇA ANTES DE IMPLEMENTAR"
    elif fusion.projected_balance_score >= 12:
        final_verdict = "NÚCLEO CANDIDATO DEFINIDO"
        governance_next = "NECESSITA GOVERNANÇA ANTES DE IMPLEMENTAR"
    else:
        final_verdict = "NÚCLEO AINDA INDEFINIDO"
        governance_next = "NECESSITA GOVERNANÇA ANTES DE IMPLEMENTAR"

    risks = [
        "Fusão V1+CDX pode reintroduzir viço se shield falhar ou seleção V1 for enfraquecida",
        "Penalização insuficiente de 01-02-03 no GP geral pode manter p3~33% nos fortes",
        "Anti-clone agressivo demais pode eliminar cartões V1-strong legítimos",
        "Reforço 07/23 sem validação multi-GE pode não transferir força",
        "CAND-D pura ou V1 pura permanecem insuficientes — arquitetura híbrida obrigatória",
    ]

    clean_test_conditions = [
        "Modo shadow_test exclusivo; flag dedicada CAND-002",
        "Label STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        "Piloto 1 GE × 50 jogos antes de qualquer lote 20 GEs",
        "Reconcile 3705-3711 obrigatório",
        "Relatório 6 bases obrigatório pós-piloto",
        "Zero novo volume no núcleo legado STRUCT_TEST_15D_001",
        "Gate: equilíbrio 6 bases — hit isolado não basta",
        "Promoção active somente via ADR agent_governanca",
    ]

    return {
        "registry_id": ML_DECISION_REGISTRY,
        "ml_role": "diagnose",
        "ml_operational_effect": False,
        "policy": "POLITICA_ML_ASSISTIVO_FORMALIZADA",
        "six_bases_policy": "POLITICA_NUCLEO_LEI15_6_BASES_2026_06_17",
        "consolidated_evidence": ev,
        "matrix_summary": {
            "legacy_core": "descartado — baseline read-only",
            "v1_role": "força + estabilidade",
            "cand_d_role": "controle estrutural",
            "v2_v3_v4": "não resolveram",
            "hit_is_not_verdict": True,
        },
        "six_bases_reading": {
            "v1_strong_segment": ev["v1"]["six_bases_strong_segment"],
            "cand_d_pilot": ev["cand_d"]["six_bases"],
            "proposed_cand_002_projected": fusion.ratings,
            "fusion_contributions": fusion.contributions,
            "projected_balance_score": fusion.projected_balance_score,
        },
        "proposed_architecture": asdict(arch),
        "decision_rationale": (
            "ML assistivo recomenda arquitetura híbrida CAND-002: geração CDX-D (controle na "
            "origem) + seleção/composição V1 (força comprovada) + shield V1-strong + anti-clone "
            "GP + política contextual de dezenas. Decisão baseada no equilíbrio projetado das "
            "6 bases, não em hit isolado. V1 pura e CAND-D pura são insuficientes."
        ),
        "risks_known": risks,
        "clean_15d_test_minimum_conditions": clean_test_conditions,
        "lei15a_recommendation": {
            "open_now": False,
            "verdict": "NECESSITA 15A SOMENTE APÓS BASE LEI 15",
            "rationale": "15A consome núcleo Lei 15 como insumo; candidato Lei 15 deve ser validado primeiro",
        },
        "governance_handoff": {
            "next_agent": "agent_governanca",
            "action": "Registrar proposta CAND-002 como decisão institucional pendente de ADR",
            "implementation_agent_after_approval": "agent_geracao",
            "validation_agent": "agent_qualidade",
            "data_cleanup_agent": "agent_dados",
            "cleanup_timing": "Somente após implementação validada e backup autorizado",
        },
        "final_verdict": final_verdict,
        "governance_status": governance_next,
    }
