"""M-GER-DADOS-051 — remoção controlada de generation_events específicos (fail-closed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Sequence

from lotoia.governance.m_dados_049_controlled_reset import (
    OPERATIONAL_DELETE_ORDER,
    PRESERVED_TABLES,
    assert_preserved_table_not_in_scope,
)

MISSION_ID: Final = "M-GER-DADOS-051"
CONFIRMATION_TOKEN: Final = "M_GER_DADOS_051_CONTROLLED_GE_REMOVAL"
CANCEL_CONFIRMATION_TOKEN: Final = "M_GER_DADOS_051_CANCEL_GE115_GE120"
REQUESTED_TARGET_IDS: Final = frozenset({114, 1115})
DIVERGENCE_CANDIDATE_ID: Final = 115


@dataclass(frozen=True, slots=True)
class GenerationEventAuditRow:
    id: int
    analysis_batch_label: str | None
    analysis_batch_type: str | None
    created_at: str | None
    ml_enabled: bool | None = None
    generated_games_count: int = 0
    reconciliation_runs_count: int = 0
    reconciliation_games_count: int = 0
    output_signatures_count: int = 0
    ml_usage_events_count: int = 0
    report_events_count: int = 0


def assert_m_ger_dados_051_confirmation(*, confirmation: str | None, execute: bool, token: str = CONFIRMATION_TOKEN) -> None:
    if not execute:
        return
    provided = str(confirmation or "").strip()
    if provided != token:
        raise RuntimeError(
            f"[{MISSION_ID}] Execução bloqueada. Defina "
            f"LOTOIA_M_GER_DADOS_051_RESET_CONFIRM={token!r}."
        )


def resolve_explicit_target_ids(
    requested_ids: Sequence[int],
    existing_ids: Sequence[int],
) -> tuple[list[int], dict[str, Any]]:
    """Remove somente IDs explicitamente solicitados que existem no banco."""
    requested = sorted({int(value) for value in requested_ids if int(value) > 0})
    existing = {int(value) for value in existing_ids if int(value) > 0}
    authorized = [ge_id for ge_id in requested if ge_id in existing]
    missing = [ge_id for ge_id in requested if ge_id not in existing]
    return authorized, {
        "requested_ids": requested,
        "existing_ids": sorted(existing),
        "authorized_ids": authorized,
        "missing_requested_ids": missing,
    }


def resolve_authorized_target_ids(
    existing_ids: Sequence[int],
    *,
    ge_115_exists: bool = False,
) -> tuple[list[int], dict[str, Any]]:
    """Resolve IDs autorizados — nunca remove 115 se operador pediu 1115 inexistente."""
    existing = {int(value) for value in existing_ids}
    notes: dict[str, Any] = {
        "requested_ids": sorted(REQUESTED_TARGET_IDS),
        "ge_114_exists": 114 in existing,
        "ge_1115_exists": 1115 in existing,
        "ge_115_exists": bool(ge_115_exists),
    }
    authorized: list[int] = []
    if 114 in REQUESTED_TARGET_IDS and 114 in existing:
        authorized.append(114)
    if 1115 in REQUESTED_TARGET_IDS:
        if 1115 in existing:
            authorized.append(1115)
        elif ge_115_exists:
            notes["divergence"] = (
                "GE 1115 não encontrado. GE 115 existe. "
                "Confirmar se deseja remover 115 — remoção automática bloqueada."
            )
            notes["ge_115_preserved_pending_confirmation"] = True
        else:
            notes["divergence"] = "GE 1115 não encontrado e GE 115 também não encontrado."
    return sorted(set(authorized)), notes


def build_dry_run_report(
    *,
    target_audits: Sequence[GenerationEventAuditRow],
    table_counts_before: dict[str, int | str],
    preserved_table_counts: dict[str, int | str],
    authorized_ids: Sequence[int],
    interpretation: dict[str, Any],
    requested_ids: Sequence[int] | None = None,
    confirmation_token: str = CONFIRMATION_TOKEN,
) -> dict[str, Any]:
    requested = sorted({int(value) for value in (requested_ids or REQUESTED_TARGET_IDS)})
    return {
        "mission_id": MISSION_ID,
        "mode": "dry_run",
        "generated_at": datetime.now(UTC).isoformat(),
        "requested_generation_event_ids": requested,
        "authorized_generation_event_ids": list(authorized_ids),
        "interpretation": interpretation,
        "confirmation_token": confirmation_token,
        "target_audits": [
            {
                "id": row.id,
                "exists": True,
                "analysis_batch_label": row.analysis_batch_label,
                "analysis_batch_type": row.analysis_batch_type,
                "created_at": row.created_at,
                "ml_enabled": row.ml_enabled,
                "generated_games": row.generated_games_count,
                "reconciliation_runs": row.reconciliation_runs_count,
                "reconciliation_games": row.reconciliation_games_count,
                "institutional_output_signatures": row.output_signatures_count,
                "ml_usage_events": row.ml_usage_events_count,
                "report_events": row.report_events_count,
            }
            for row in target_audits
        ],
        "missing_requested_ids": [
            ge_id
            for ge_id in requested
            if ge_id not in {row.id for row in target_audits}
        ],
        "table_counts_before": table_counts_before,
        "preserved_table_counts": preserved_table_counts,
        "tables_in_scope": list(OPERATIONAL_DELETE_ORDER),
        "tables_preserved": sorted(PRESERVED_TABLES),
        "verdict": (
            f"DRY-RUN APROVADO — aguardando confirmação {confirmation_token}"
            if authorized_ids
            else "DRY-RUN SEM REMOÇÃO — nenhum ID autorizado encontrado"
        ),
    }


def build_post_removal_report(
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
        "authorized_generation_event_ids_removed": dry_run.get("authorized_generation_event_ids"),
        "interpretation": dry_run.get("interpretation"),
        "table_counts_before": dry_run.get("table_counts_before"),
        "table_counts_after": table_counts_after,
        "deleted_counts": deleted_counts,
        "preserved_confirmed": dry_run.get("preserved_table_counts"),
        "verdict": "M-GER-DADOS-051 REMOÇÃO CONTROLADA EXECUTADA",
    }


def authorize_controlled_ge_removal(
    *,
    backup_confirmed: bool,
    dry_run_approved: bool,
    authorized_ids: Sequence[int],
) -> None:
    if not authorized_ids:
        raise RuntimeError(f"[{MISSION_ID}] Nenhum generation_event_id autorizado para remoção.")
    if not backup_confirmed:
        raise RuntimeError(f"[{MISSION_ID}] Backup não confirmado.")
    if not dry_run_approved:
        raise RuntimeError(f"[{MISSION_ID}] Dry-run não aprovado.")


def delete_operational_rows_for_generation_events(cur, target_ids: list[int]) -> dict[str, int]:
    if not target_ids:
        return {table: 0 for table in OPERATIONAL_DELETE_ORDER}

    id_list = ",".join(str(int(value)) for value in sorted(set(target_ids)))
    deleted: dict[str, int] = {}

    cur.execute(
        f"""
        DELETE FROM reconciliation_games
        WHERE reconciliation_run_id IN (
            SELECT id FROM reconciliation_runs
            WHERE generation_event_id IN ({id_list})
        )
        """
    )
    deleted["reconciliation_games"] = int(cur.rowcount)

    child_tables_with_ge = (
        "expansion_events",
        "institutional_validated_expansions",
        "lotoia_client_generations",
        "ml_usage_events",
        "reconciliation_events",
        "report_events",
        "reconciliation_runs",
        "generated_games",
        "institutional_output_signatures",
    )
    for table in child_tables_with_ge:
        assert_preserved_table_not_in_scope(table)
        cur.execute(f'DELETE FROM "{table}" WHERE generation_event_id IN ({id_list})')
        deleted[table] = int(cur.rowcount)

    assert_preserved_table_not_in_scope("generation_events")
    cur.execute(f'DELETE FROM generation_events WHERE id IN ({id_list})')
    deleted["generation_events"] = int(cur.rowcount)
    return deleted
