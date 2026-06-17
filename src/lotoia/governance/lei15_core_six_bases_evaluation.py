"""Avaliação institucional do Núcleo Lei 15 pelas 6 bases.

Política: docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md
Registro: POLITICA_NUCLEO_LEI15_6_BASES_2026_06_17

Hit não é veredicto final — é evidência da Base 1 (força de acerto).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

BaseRating = Literal["forte", "parcial", "fraca", "inconclusiva"]

POLICY_REGISTRY_ID: Final = "POLITICA_NUCLEO_LEI15_6_BASES_2026_06_17"

BASE_NAMES: Final = (
    "forca_acerto",
    "diversidade",
    "baixa_redundancia",
    "controle_prefixo_sufixo",
    "cobertura_dezenas_criticas",
    "estabilidade_multi_concurso",
)

BASE_LABELS_PT: Final = {
    "forca_acerto": "Base 1 — Força de acerto",
    "diversidade": "Base 2 — Diversidade suficiente",
    "baixa_redundancia": "Base 3 — Baixa redundância",
    "controle_prefixo_sufixo": "Base 4 — Controle prefixo/sufixo",
    "cobertura_dezenas_criticas": "Base 5 — Cobertura das dezenas críticas",
    "estabilidade_multi_concurso": "Base 6 — Estabilidade em vários concursos",
}


@dataclass(frozen=True, slots=True)
class SixBasesAssessment:
    """Leitura institucional de uma variante pelas 6 bases."""

    variant_id: str
    batch_label: str
    forca_acerto: BaseRating
    diversidade: BaseRating
    baixa_redundancia: BaseRating
    controle_prefixo_sufixo: BaseRating
    cobertura_dezenas_criticas: BaseRating
    estabilidade_multi_concurso: BaseRating
    institutional_reading: str

    def as_dict(self) -> dict[str, str]:
        return {
            "variant_id": self.variant_id,
            "batch_label": self.batch_label,
            **{name: getattr(self, name) for name in BASE_NAMES},
            "institutional_reading": self.institutional_reading,
        }

    def format_report_lines(self) -> list[str]:
        lines = [f"Leitura 6 bases — {self.variant_id} ({self.batch_label})"]
        for name in BASE_NAMES:
            rating = getattr(self, name)
            lines.append(f"  {BASE_LABELS_PT[name]}: {rating}")
        lines.append(f"  Leitura institucional: {self.institutional_reading}")
        return lines


# Leituras registradas EPOCH_001 (3705–3711) — agent_governanca + agent_qualidade
CAND_D_ASSESSMENT = SixBasesAssessment(
    variant_id="CAND-D",
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001",
    forca_acerto="fraca",
    diversidade="forte",
    baixa_redundancia="parcial",
    controle_prefixo_sufixo="forte",
    cobertura_dezenas_criticas="inconclusiva",
    estabilidade_multi_concurso="inconclusiva",
    institutional_reading=(
        "Avanço forte em controle estrutural, diversidade e redução de vício; "
        "equilíbrio insuficiente em força de acerto, cobertura crítica auditada "
        "e estabilidade multi-ciclo. Não descartar por hit isolado; não promover "
        "por estrutura isolada."
    ),
)

V1_ASSESSMENT = SixBasesAssessment(
    variant_id="V1",
    batch_label="STRUCT_REALIGN_V1_15D_001",
    forca_acerto="forte",
    diversidade="inconclusiva",
    baixa_redundancia="inconclusiva",
    controle_prefixo_sufixo="parcial",
    cobertura_dezenas_criticas="inconclusiva",
    estabilidade_multi_concurso="parcial",
    institutional_reading=(
        "Força de acerto e estabilidade inicial demonstradas; auditoria fina "
        "pendente em diversidade, redundância, controle prefixo e cobertura "
        "crítica. Não aprovar como Núcleo pleno apenas por hits."
    ),
)

LEGACY_BASELINE_ASSESSMENT = SixBasesAssessment(
    variant_id="LEGACY-BASELINE",
    batch_label="STRUCT_TEST_15D_001",
    forca_acerto="parcial",
    diversidade="fraca",
    baixa_redundancia="fraca",
    controle_prefixo_sufixo="fraca",
    cobertura_dezenas_criticas="fraca",
    estabilidade_multi_concurso="parcial",
    institutional_reading=(
        "Baseline congelado read-only. Evidência histórica e controle negativo — "
        "não candidato ativo de evolução."
    ),
)

REGISTERED_ASSESSMENTS: Final = {
    CAND_D_ASSESSMENT.batch_label: CAND_D_ASSESSMENT,
    V1_ASSESSMENT.batch_label: V1_ASSESSMENT,
    LEGACY_BASELINE_ASSESSMENT.batch_label: LEGACY_BASELINE_ASSESSMENT,
}


def get_registered_assessment(batch_label: str | None) -> SixBasesAssessment | None:
    normalized = str(batch_label or "").strip().upper()
    return REGISTERED_ASSESSMENTS.get(normalized)


def count_strong_bases(assessment: SixBasesAssessment) -> int:
    return sum(1 for name in BASE_NAMES if getattr(assessment, name) == "forte")


def has_critical_weakness(assessment: SixBasesAssessment) -> bool:
    """True se alguma base essencial está fraca (não apenas inconclusiva)."""
    structural = (
        assessment.diversidade,
        assessment.controle_prefixo_sufixo,
        assessment.baixa_redundancia,
    )
    return assessment.forca_acerto == "fraca" or any(r == "fraca" for r in structural)


def may_advance_as_nucleus_candidate(assessment: SixBasesAssessment) -> bool:
    """Gate ampliado: equilíbrio progressivo — nunca hit ou estrutura isolados."""
    ratings = [getattr(assessment, name) for name in BASE_NAMES]
    if "fraca" in ratings:
        return False
    if ratings.count("inconclusiva") > 2:
        return False
    if assessment.forca_acerto not in {"forte", "parcial"}:
        return False
    if assessment.controle_prefixo_sufixo not in {"forte", "parcial"}:
        return False
    return count_strong_bases(assessment) >= 2
