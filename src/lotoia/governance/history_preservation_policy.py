"""Política de preservação de histórico institucional — fail-closed (ADR-047).

Registro: POLITICA_PRESERVACAO_HISTORICO_LOTOIA_2026_06_17
Agente: agent_dados

Regras:
  - purge genérico bloqueado;
  - label desconhecido → preservar;
  - label institucional → preservar;
  - limpeza futura só com backup + dry-run + autorização dual.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final, Iterable, Sequence

REGISTRY_ID: Final = "POLITICA_PRESERVACAO_HISTORICO_LOTOIA_2026_06_17"
ADR_REFERENCE: Final = "ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002"
AUDIT_REFERENCE: Final = "AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17"

# Evidência CDX EPOCH_001 — GE 114 removido (M-GER-DADOS-051); GE 115 removível por ordem explícita
PROTECTED_GENERATION_EVENT_IDS: Final = frozenset()

# Tabelas soberanas Lei 001 — nunca DELETE genérico
SOVEREIGN_DATA_TABLES: Final = frozenset(
    {
        "imported_contests",
        "lotofacil_official_history",
        "scientific_institutional_memory",
        "scientific_calibration_decisions",
        "institutional_memory_snapshots",
        "institutional_memory_states",
        "institutional_memory_lineage",
        "institutional_memory_replay",
        "benchmark_runs",
        "backtest_runs",
        "calibration_runs",
        "ml_diagnostic_decisions",
        "schema_migrations",
    }
)

# Tabelas operacionais — purge genérico bloqueado (contêm evidência mista por label)
OPERATIONAL_HISTORY_TABLES: Final = frozenset(
    {
        "generation_events",
        "generated_games",
        "reconciliation_runs",
        "reconciliation_games",
        "reconciliation_events",
        "operational_logs",
        "reset_events",
        "institutional_output_signatures",
    }
)

GENERIC_PURGE_BLOCKED_TABLES: Final = frozenset(
    SOVEREIGN_DATA_TABLES | OPERATIONAL_HISTORY_TABLES
)

# Relatórios filesystem preservados (referência institucional)
PRESERVED_REPORT_ARTIFACTS: Final = frozenset(
    {
        "reports/lei15_core_6_bases_comparative_2026_06_17.json",
        "reports/ml_lei15_core_candidate_decision_2026_06_17.json",
        "reports/auditoria_constitucional_lotoia_2026_06_17.json",
        "reports/history_preservation_audit_2026_06_17.json",
        "reports/adr_047_transicao_constitucional_lei15_core002_2026_06_17.json",
        "reports/lei15_v1_strong_cards_6_bases_audit_2026_06_17.json",
        "reports/lei15_core_002_implantation_2026_06_17.json",
    }
)

PRESERVED_ADR_ARTIFACTS: Final = frozenset(
    {
        "docs/adr/ADR-043-REALINHAMENTO-ESTRUTURAL-LEI15-V1.md",
        "docs/adr/ADR-044-REAVALIACAO-NUCLEOS-LEI15-15A.md",
        "docs/adr/ADR-045-CORE-REALIGNMENT-V3-BALANCED.md",
        "docs/adr/ADR-046-NUCLEO-LEI15-CANDIDATE-002.md",
        "docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md",
        "docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md",
    }
)

_LABEL_PREFIX_PATTERNS: Final = (
    re.compile(r"^STRUCT_TEST_\d+D(?:_\d+)?$"),
    re.compile(r"^STRUCT_REALIGN_V\d+_\d+D_\d+$"),
    re.compile(r"^STRUCT_CORE_REALIGN_V\d+(?:_[A-Z_]+)?_\d+D_\d+$"),
    re.compile(r"^STRUCT_LEI15_CORE_V\d+(?:_\d+)?(?:_[A-Z0-9_]+)?_\d+D_\d+$"),
    re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_001(?:_[ABCD])?_\d+D_\d+$"),
    re.compile(r"^STRUCT_LEI15_CORE_CANDIDATE_002_\d+D_\d+$"),
)


class PreservationClass(StrEnum):
    SOVEREIGN = "SOBERANO"
    HISTORICAL_EVIDENCE = "EVIDÊNCIA HISTÓRICA"
    FROZEN_LEGACY = "LEGADO CONGELADO"
    INSTITUTIONAL_UNKNOWN = "INSTITUCIONAL DESCONHECIDO"
    OPERATIONAL_DISPOSABLE = "OPERACIONAL DESCARTÁVEL"


class DataTier(StrEnum):
    INSTITUTIONAL = "institucional"
    OPERATIONAL = "operacional"
    DISPOSABLE = "descartavel"
    INCONCLUSIVE = "inconclusivo"


@dataclass(frozen=True, slots=True)
class LabelPreservation:
    label: str | None
    preservation_class: PreservationClass
    protected: bool
    data_tier: DataTier
    reason: str


@dataclass(frozen=True, slots=True)
class PurgeGuardResult:
    allowed: bool
    blocked: bool
    reason: str
    registry: str = REGISTRY_ID


def _normalize_label(batch_label: str | None) -> str:
    return str(batch_label or "").strip().upper()


def get_protected_batch_labels() -> frozenset[str]:
    """Lista institucional consolidada de labels preservados."""
    from lotoia.governance.analysis_batch_labels import ALLOWED_BATCH_LABELS, LEGACY_BATCH_LABELS
    from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL as SOVEREIGN_LABEL
    from lotoia.governance.lei15_legacy_core_baseline import (
        CDX_CANDIDATE_LABEL_A,
        CDX_CANDIDATE_LABEL_D,
        FROZEN_LEGACY_LABELS,
        V1_EVIDENCE_LABEL,
    )

    labels: set[str] = set(ALLOWED_BATCH_LABELS) | set(LEGACY_BATCH_LABELS) | set(FROZEN_LEGACY_LABELS)
    labels.update({SOVEREIGN_LABEL, V1_EVIDENCE_LABEL, CDX_CANDIDATE_LABEL_A, CDX_CANDIDATE_LABEL_D})
    return frozenset(labels)


def _matches_institutional_prefix(normalized: str) -> bool:
    return any(pattern.match(normalized) for pattern in _LABEL_PREFIX_PATTERNS)


def classify_batch_label(batch_label: str | None) -> LabelPreservation:
    """Classifica label para preservação — fail-closed."""
    normalized = _normalize_label(batch_label)
    protected_labels = get_protected_batch_labels()

    if not normalized:
        return LabelPreservation(
            label=None,
            preservation_class=PreservationClass.INSTITUTIONAL_UNKNOWN,
            protected=True,
            data_tier=DataTier.INCONCLUSIVE,
            reason="Label ausente — dúvida preserva (fail-closed)",
        )

    from lotoia.governance.lei15_core_002_sovereign import is_sovereign_core_label
    from lotoia.governance.lei15_legacy_core_baseline import (
        FROZEN_LEGACY_LABELS,
        is_cdx_candidate_label,
        is_legacy_core_frozen_label,
    )

    if is_sovereign_core_label(normalized):
        return LabelPreservation(
            label=normalized,
            preservation_class=PreservationClass.SOVEREIGN,
            protected=True,
            data_tier=DataTier.INSTITUTIONAL,
            reason="LEI15_CORE_002 soberano (ADR-046/047)",
        )

    if normalized in FROZEN_LEGACY_LABELS or is_legacy_core_frozen_label(normalized):
        return LabelPreservation(
            label=normalized,
            preservation_class=PreservationClass.FROZEN_LEGACY,
            protected=True,
            data_tier=DataTier.INSTITUTIONAL,
            reason="FROZEN_LEGACY_LABELS / baseline EPOCH_001",
        )

    if normalized == "STRUCT_REALIGN_V1_15D_001" or normalized.startswith("STRUCT_REALIGN_V1_"):
        return LabelPreservation(
            label=normalized,
            preservation_class=PreservationClass.HISTORICAL_EVIDENCE,
            protected=True,
            data_tier=DataTier.INSTITUTIONAL,
            reason="V1 evidência histórica EPOCH_001",
        )

    if is_cdx_candidate_label(normalized):
        return LabelPreservation(
            label=normalized,
            preservation_class=PreservationClass.HISTORICAL_EVIDENCE,
            protected=True,
            data_tier=DataTier.INSTITUTIONAL,
            reason="CDX CAND-001 evidência (GE 114/115)",
        )

    if normalized in protected_labels or _matches_institutional_prefix(normalized):
        return LabelPreservation(
            label=normalized,
            preservation_class=PreservationClass.HISTORICAL_EVIDENCE,
            protected=True,
            data_tier=DataTier.INSTITUTIONAL,
            reason="Label institucional registrado ou padrão STRUCT_*",
        )

    return LabelPreservation(
        label=normalized,
        preservation_class=PreservationClass.INSTITUTIONAL_UNKNOWN,
        protected=True,
        data_tier=DataTier.INCONCLUSIVE,
        reason="Label desconhecido — preservar (fail-closed)",
    )


def is_protected_generation_event_id(generation_event_id: int | None) -> bool:
    if generation_event_id is None:
        return True
    return int(generation_event_id) in PROTECTED_GENERATION_EVENT_IDS


def is_protected_generation_event(
    *,
    generation_event_id: int | None,
    batch_label: str | None,
) -> bool:
    if is_protected_generation_event_id(generation_event_id):
        return True
    return classify_batch_label(batch_label).protected


def assert_table_generic_purge_blocked(*, table_name: str, source: str) -> None:
    """Bloqueia DELETE genérico em tabelas institucionais ou operacionais mistas."""
    normalized = str(table_name or "").strip().lower()
    if normalized not in GENERIC_PURGE_BLOCKED_TABLES:
        return
    raise RuntimeError(
        f"[{REGISTRY_ID}] Purge genérico bloqueado para tabela={normalized!r} "
        f"(origem={source!r}). Evidência institucional protegida conforme {ADR_REFERENCE}. "
        f"Use scripts/ops/dry_run_history_cleanup_lotoia.py e autorização "
        f"agent_dados + agent_governanca após backup."
    )


def assert_generic_institutional_purge_blocked(*, source: str, tables: Sequence[str] | None = None) -> None:
    """Fail-closed: proíbe purge/delete_history/reset sem filtro seguro por label."""
    target_tables = list(tables) if tables else list(OPERATIONAL_HISTORY_TABLES)
    for table in target_tables:
        assert_table_generic_purge_blocked(table_name=table, source=source)
    raise RuntimeError(
        f"[{REGISTRY_ID}] Purge institucional genérico bloqueado (origem={source!r}). "
        f"PostgreSQL contém evidência EPOCH_001 (GE 114/115, baseline, V1, CDX). "
        f"Limpeza futura exige: backup → congelamento → classificação por label → "
        f"autorização agent_dados + agent_governanca → dry-run aprovado. "
        f"Referência: {ADR_REFERENCE}."
    )


def assert_generation_event_deletion_allowed(
    *,
    generation_event_id: int | None,
    batch_label: str | None,
    source: str,
) -> None:
    """Bloqueia DELETE de generation_event protegido."""
    if is_protected_generation_event(
        generation_event_id=generation_event_id,
        batch_label=batch_label,
    ):
        classification = classify_batch_label(batch_label)
        raise RuntimeError(
            f"[{REGISTRY_ID}] DELETE bloqueado para GE id={generation_event_id!r} "
            f"label={batch_label!r} classificação={classification.preservation_class.value} "
            f"(origem={source!r}). {classification.reason}."
        )


def assert_controlled_cleanup_authorized(
    *,
    backup_confirmed: bool,
    dry_run_approved: bool,
    agent_dados_authorized: bool,
    agent_governanca_authorized: bool,
    preservation_report_path: str | None,
) -> None:
    """Pré-requisitos para limpeza controlada futura — ainda não autoriza purge real nesta missão."""
    missing: list[str] = []
    if not backup_confirmed:
        missing.append("backup")
    if not dry_run_approved:
        missing.append("dry_run_aprovado")
    if not agent_dados_authorized:
        missing.append("autorizacao_agent_dados")
    if not agent_governanca_authorized:
        missing.append("autorizacao_agent_governanca")
    if not preservation_report_path:
        missing.append("relatorio_preservacao")
    if missing:
        raise RuntimeError(
            f"[{REGISTRY_ID}] Limpeza controlada não autorizada. Faltam: {', '.join(missing)}."
        )


def evaluate_generation_events_for_cleanup(
    rows: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Dry-run: classifica GEs sem apagar."""
    protected: list[dict[str, Any]] = []
    potentially_disposable: list[dict[str, Any]] = []
    inconclusive: list[dict[str, Any]] = []

    for row in rows:
        ge_id = row.get("id")
        label = row.get("analysis_batch_label")
        info = classify_batch_label(label)
        payload = {
            "id": ge_id,
            "analysis_batch_label": label,
            "preservation_class": info.preservation_class.value,
            "protected": info.protected,
            "data_tier": info.data_tier.value,
            "reason": info.reason,
            "explicit_protected_id": is_protected_generation_event_id(ge_id),
        }
        if info.protected or is_protected_generation_event_id(ge_id):
            protected.append(payload)
        elif info.data_tier == DataTier.OPERATIONAL and info.preservation_class == PreservationClass.OPERATIONAL_DISPOSABLE:
            potentially_disposable.append(payload)
        else:
            inconclusive.append(payload)

    return {
        "registry": REGISTRY_ID,
        "protected_count": len(protected),
        "potentially_disposable_count": len(potentially_disposable),
        "inconclusive_count": len(inconclusive),
        "protected": protected,
        "potentially_disposable": potentially_disposable,
        "inconclusive": inconclusive,
        "generic_purge_allowed": False,
        "fail_closed": True,
    }


def institutional_preservation_summary() -> dict[str, Any]:
    """Snapshot read-only da política (sem DB)."""
    labels = sorted(get_protected_batch_labels())
    return {
        "registry": REGISTRY_ID,
        "adr": ADR_REFERENCE,
        "audit": AUDIT_REFERENCE,
        "protected_generation_event_ids": sorted(PROTECTED_GENERATION_EVENT_IDS),
        "protected_batch_labels_count": len(labels),
        "protected_batch_labels_sample": labels[:20],
        "sovereign_tables": sorted(SOVEREIGN_DATA_TABLES),
        "operational_history_tables": sorted(OPERATIONAL_HISTORY_TABLES),
        "generic_purge_blocked": True,
        "mandatory_preservation": {
            "ge_114": "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001 (CAND-A)",
            "ge_115": "STRUCT_LEI15_CORE_CANDIDATE_001_D_15D_001 (CAND-D)",
            "baseline": "STRUCT_TEST_15D_001 / EPOCH_001",
            "v1": "STRUCT_REALIGN_V1_15D_001",
            "sovereign": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        },
        "filesystem_artifacts": {
            "reports": sorted(PRESERVED_REPORT_ARTIFACTS),
            "adrs": sorted(PRESERVED_ADR_ARTIFACTS),
        },
        "future_cleanup_sequence": [
            "backup",
            "congelamento",
            "classificacao_por_label",
            "autorizacao_agent_dados_agent_governanca",
            "relatorio_preservacao",
            "dry_run_aprovado",
        ],
    }
