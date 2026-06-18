"""M-DADOS-049 — reset controlado de gerações operacionais antigas (fail-closed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Sequence

from lotoia.governance.history_preservation_policy import (
    PROTECTED_GENERATION_EVENT_IDS,
    SOVEREIGN_DATA_TABLES,
    assert_controlled_cleanup_authorized,
    is_protected_generation_event_id,
)
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL as SOVEREIGN_BATCH_LABEL

MISSION_ID: Final = "M-DADOS-049"
CONFIRMATION_TOKEN: Final = "M_DADOS_049_CONTROLLED_RESET"

PRESERVED_TABLES: Final = frozenset(SOVEREIGN_DATA_TABLES) | frozenset(
    {
        "schema_migrations",
        "users",
        "admin_users",
        "leads",
        "adr_registry",
        "governance_policies",
        "analysis_batch_definitions",
        "reset_events",
    }
)

# Ordem de deleção — filhas antes das raízes operacionais.
OPERATIONAL_DELETE_ORDER: Final = tuple(
    [
        "reconciliation_games",
        "expansion_events",
        "institutional_validated_expansions",
        "lotoia_client_generations",
        "ml_usage_events",
        "reconciliation_events",
        "report_events",
        "reconciliation_runs",
        "generated_games",
        "institutional_output_signatures",
        "generation_events",
    ]
)

OPERATIONAL_SCOPE_TABLES: Final = frozenset(OPERATIONAL_DELETE_ORDER)


@dataclass(frozen=True, slots=True)
class GenerationEventRow:
    id: int
    analysis_batch_label: str | None
    analysis_batch_type: str | None
    created_at: str | None
    ml_enabled: bool | None = None

    @property
    def protected(self) -> bool:
        """M-DADOS-049: preserva apenas IDs institucionais explícitos (114/115)."""
        return is_protected_generation_event_id(self.id)

    @property
    def deletable(self) -> bool:
        return not self.protected


def assert_m_dados_049_confirmation(*, confirmation: str | None, execute: bool) -> None:
    if not execute:
        return
    token = str(confirmation or "").strip()
    if token != CONFIRMATION_TOKEN:
        raise RuntimeError(
            f"[{MISSION_ID}] Execução bloqueada. Defina "
            f"LOTOIA_M_DADOS_049_RESET_CONFIRM={CONFIRMATION_TOKEN!r}."
        )


def assert_preserved_table_not_in_scope(table_name: str) -> None:
    normalized = str(table_name or "").strip().lower()
    if normalized in PRESERVED_TABLES:
        raise RuntimeError(
            f"[{MISSION_ID}] Tabela preservada fora de escopo: {normalized!r}."
        )


def partition_generation_events(rows: Sequence[GenerationEventRow]) -> dict[str, list[dict[str, Any]]]:
    protected: list[dict[str, Any]] = []
    deletable: list[dict[str, Any]] = []
    for row in rows:
        payload = {
            "id": row.id,
            "analysis_batch_label": row.analysis_batch_label,
            "analysis_batch_type": row.analysis_batch_type,
            "created_at": row.created_at,
            "ml_enabled": row.ml_enabled,
            "protected": row.protected,
            "reason": (
                f"GE protegido id={row.id} (EPOCH_001 evidência)"
                if is_protected_generation_event_id(row.id)
                else "Operacional — elegível para reset M-DADOS-049"
            ),
        }
        if row.protected:
            protected.append(payload)
        else:
            deletable.append(payload)
    return {"protected": protected, "deletable": deletable}


def build_dry_run_report(
    *,
    table_counts_before: dict[str, int | str],
    generation_events: Sequence[GenerationEventRow],
    batch_labels: Sequence[str],
    preserved_table_counts: dict[str, int | str],
) -> dict[str, Any]:
    partitioned = partition_generation_events(generation_events)
    deletable_ids = [int(row["id"]) for row in partitioned["deletable"]]
    protected_ids = sorted(PROTECTED_GENERATION_EVENT_IDS)

    return {
        "mission_id": MISSION_ID,
        "mode": "dry_run",
        "generated_at": datetime.now(UTC).isoformat(),
        "sovereign_batch_label": SOVEREIGN_BATCH_LABEL,
        "protected_generation_event_ids": protected_ids,
        "table_counts_before": table_counts_before,
        "preserved_table_counts": preserved_table_counts,
        "batch_labels_found": sorted({str(label) for label in batch_labels if label}),
        "generation_events_total": len(generation_events),
        "generation_events_protected": partitioned["protected"],
        "generation_events_deletable": partitioned["deletable"],
        "deletable_generation_event_ids": deletable_ids,
        "tables_in_scope": sorted(OPERATIONAL_SCOPE_TABLES),
        "tables_preserved": sorted(PRESERVED_TABLES),
        "will_delete": {
            table: (
                "rows ligadas a GEs deletáveis"
                if table != "generation_events"
                else f"{len(deletable_ids)} generation_events deletáveis"
            )
            for table in OPERATIONAL_DELETE_ORDER
        },
        "will_preserve": {
            "imported_contests": preserved_table_counts.get("imported_contests"),
            "scientific_institutional_memory": preserved_table_counts.get("scientific_institutional_memory"),
            "scientific_calibration_decisions": preserved_table_counts.get("scientific_calibration_decisions"),
            "protected_generation_events": protected_ids,
        },
        "sequence_reset_planned": False,
        "operational_numbering": "001/002 via rótulo operacional — IDs internos PostgreSQL preservados",
        "verdict": "DRY-RUN APROVADO — aguardando confirmação M_DADOS_049_CONTROLLED_RESET",
    }


def build_post_reset_report(
    *,
    dry_run: dict[str, Any],
    table_counts_after: dict[str, int | str],
    deleted_counts: dict[str, int],
    reset_event_id: int | None = None,
) -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "mode": "executed",
        "generated_at": datetime.now(UTC).isoformat(),
        "reset_event_id": reset_event_id,
        "table_counts_before": dry_run.get("table_counts_before"),
        "table_counts_after": table_counts_after,
        "deleted_counts": deleted_counts,
        "batch_labels_removed": dry_run.get("batch_labels_found"),
        "deletable_generation_event_ids_removed": dry_run.get("deletable_generation_event_ids"),
        "preserved_confirmed": dry_run.get("will_preserve"),
        "operational_epoch_batch_label": SOVEREIGN_BATCH_LABEL,
        "verdict": "M-DADOS-049 RESET CONTROLADO EXECUTADO — NOVA FASE OPERACIONAL PRONTA",
    }


def authorize_controlled_reset(
    *,
    backup_confirmed: bool,
    dry_run_approved: bool,
    agent_dados_authorized: bool,
    agent_governanca_authorized: bool,
    preservation_report_path: str | None,
) -> None:
    assert_controlled_cleanup_authorized(
        backup_confirmed=backup_confirmed,
        dry_run_approved=dry_run_approved,
        agent_dados_authorized=agent_dados_authorized,
        agent_governanca_authorized=agent_governanca_authorized,
        preservation_report_path=preservation_report_path,
    )
