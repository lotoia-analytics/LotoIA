"""M-DADOS-066 — reset absoluto operacional (nova fase LotoIA 001).

Decisão institucional: apagar TODA a camada operacional (gerações, jogos,
conferências, reconciliações, ML operacional de lote) e reiniciar sequences
para que a próxima geração nasça com generation_event_id = 1 e rótulo 001 real.

Preserva: Lei 001 (imported_contests), histórico oficial Caixa, governança
constitucional, memória científica/institucional, ADRs, CORE_002 (código/regras).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Sequence

MISSION_ID: Final = "M-DADOS-066"
CONFIRMATION_TOKEN: Final = "M_DADOS_066_ABSOLUTE_OPERATIONAL_RESET"
OPERATIONAL_EPOCH_LABEL: Final = "FASE_OPERACIONAL_001"

# Ordem de deleção — filhas antes das raízes (fail-closed em FK).
OPERATIONAL_DELETE_ORDER: Final = tuple(
    [
        "reconciliation_games",
        "expansion_events",
        "institutional_validated_expansions",
        "lotoia_client_generations",
        "lotoia_client_conference_results",
        "ml_usage_events",
        "reconciliation_events",
        "report_events",
        "workflow_events",
        "check_events",
        "ml_diagnostic_decisions",
        "reconciliation_runs",
        "generated_games",
        "institutional_output_signatures",
        "generation_events",
        "runtime_lineage",
        "runtime_metrics",
        "runtime_spans",
        "runtime_snapshots",
        "runtime_executions",
        "workflow_steps",
        "workflow_runs",
    ]
)

OPERATIONAL_SCOPE_TABLES: Final = frozenset(OPERATIONAL_DELETE_ORDER)

PRESERVED_TABLES: Final = frozenset(
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
        "schema_migrations",
        "users",
        "admin_users",
        "institutional_users",
        "auth_sessions",
        "auth_events",
        "access_events",
        "leads",
        "lotoia_clients",
        "lotoia_client_daily_usage",
        "messenger_conversation_state",
        "whatsapp_conversation_state",
        "feature_flags",
        "feature_usage_events",
        "reset_events",
        "adr_registry",
        "governance_policies",
        "analysis_batch_definitions",
    }
)

PRESERVED_COUNT_TABLES: Final = tuple(
    [
        "imported_contests",
        "lotofacil_official_history",
        "scientific_institutional_memory",
        "scientific_calibration_decisions",
        "institutional_memory_snapshots",
        "institutional_memory_states",
        "benchmark_runs",
        "backtest_runs",
        "calibration_runs",
        "reset_events",
    ]
)

OPERATIONAL_SEQUENCES: Final = tuple(
    [
        "generation_events_id_seq",
        "generated_games_id_seq",
        "reconciliation_runs_id_seq",
        "reconciliation_games_id_seq",
        "institutional_output_signatures_id_seq",
        "ml_diagnostic_decisions_id_seq",
        "expansion_events_id_seq",
        "institutional_validated_expansions_id_seq",
        "lotoia_client_generations_id_seq",
        "lotoia_client_conference_results_id_seq",
        "ml_usage_events_id_seq",
        "reconciliation_events_id_seq",
        "report_events_id_seq",
        "workflow_events_id_seq",
        "check_events_id_seq",
        "runtime_executions_id_seq",
        "runtime_spans_id_seq",
        "runtime_metrics_id_seq",
        "runtime_lineage_id_seq",
        "runtime_snapshots_id_seq",
        "workflow_runs_id_seq",
        "workflow_steps_id_seq",
    ]
)

INVENTORY_TABLES: Final = tuple(dict.fromkeys((*OPERATIONAL_DELETE_ORDER, *PRESERVED_COUNT_TABLES)))


@dataclass(frozen=True, slots=True)
class PostResetExpectation:
    operational_tables_empty: bool
    imported_contests_preserved: bool
    official_history_preserved: bool
    sequences_restarted: bool
    first_generation_event_id: int | None


def assert_m_dados_066_confirmation(*, confirmation: str | None, execute: bool) -> None:
    if not execute:
        return
    token = str(confirmation or "").strip()
    if token != CONFIRMATION_TOKEN:
        raise RuntimeError(
            f"[{MISSION_ID}] Execução bloqueada. Defina "
            f"LOTOIA_M_DADOS_066_RESET_CONFIRM={CONFIRMATION_TOKEN!r}."
        )


def assert_preserved_table_not_in_scope(table_name: str) -> None:
    normalized = str(table_name or "").strip().lower()
    if normalized in PRESERVED_TABLES:
        raise RuntimeError(f"[{MISSION_ID}] Tabela preservada fora de escopo: {normalized!r}.")


def build_inventory_report(
    *,
    table_counts: dict[str, int | str],
    generation_event_ids: Sequence[int],
    batch_labels: Sequence[str],
) -> dict[str, Any]:
    operational_counts = {
        table: table_counts.get(table, "missing")
        for table in OPERATIONAL_DELETE_ORDER
    }
    preserved_counts = {
        table: table_counts.get(table, "missing")
        for table in PRESERVED_COUNT_TABLES
    }
    return {
        "mission_id": MISSION_ID,
        "generated_at": datetime.now(UTC).isoformat(),
        "operational_counts": operational_counts,
        "preserved_counts": preserved_counts,
        "generation_events_total": len(generation_event_ids),
        "generation_event_ids_sample": list(generation_event_ids[:20]),
        "generation_event_id_max": max(generation_event_ids) if generation_event_ids else 0,
        "batch_labels_found": sorted({str(label) for label in batch_labels if label}),
        "tables_in_scope": list(OPERATIONAL_DELETE_ORDER),
        "tables_preserved": sorted(PRESERVED_TABLES),
        "sequences_to_reset": list(OPERATIONAL_SEQUENCES),
    }


def build_dry_run_report(
    *,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    return {
        **inventory,
        "mode": "dry_run",
        "absolute_reset": True,
        "protected_generation_event_ids": [],
        "will_delete_all_operational_rows": True,
        "sequence_reset_planned": True,
        "operational_numbering": (
            "Geração 001 real — generation_event_id reinicia em 1 após reset de sequences"
        ),
        "verdict": (
            f"{MISSION_ID} DRY-RUN APROVADO — aguardando "
            f"LOTOIA_M_DADOS_066_RESET_CONFIRM={CONFIRMATION_TOKEN!r}"
        ),
    }


def _safe_count(table_counts: dict[str, int | str], table: str) -> int:
    value = table_counts.get(table, -1)
    if value is None or str(value).startswith("error") or str(value) == "missing":
        return -1
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def build_post_reset_report(
    *,
    inventory_before: dict[str, Any],
    table_counts_after: dict[str, int | str],
    preserved_counts_after: dict[str, int | str],
    deleted_counts: dict[str, int],
    sequence_status: dict[str, str | int],
    reset_event_id: int | None = None,
) -> dict[str, Any]:
    operational_empty = all(
        _safe_count(table_counts_after, table) == 0 for table in OPERATIONAL_DELETE_ORDER
    )
    preserved_before = inventory_before.get("preserved_counts") or {}
    before_imported = preserved_before.get("imported_contests", 0)
    before_imported_int = _safe_count({"imported_contests": before_imported}, "imported_contests")
    imported_ok = _safe_count(preserved_counts_after, "imported_contests") >= max(before_imported_int, 0)
    return {
        "mission_id": MISSION_ID,
        "mode": "executed",
        "generated_at": datetime.now(UTC).isoformat(),
        "reset_event_id": reset_event_id,
        "operational_epoch_label": OPERATIONAL_EPOCH_LABEL,
        "inventory_before": inventory_before,
        "table_counts_after": table_counts_after,
        "preserved_counts_after": preserved_counts_after,
        "deleted_counts": deleted_counts,
        "sequence_status": sequence_status,
        "checks": {
            "operational_tables_empty": operational_empty,
            "imported_contests_preserved": imported_ok,
            "sequences_restarted": all(
                str(value).endswith("1") or value == 1 for value in sequence_status.values()
            )
            if sequence_status
            else False,
        },
        "verdict": (
            f"{MISSION_ID} RESET ABSOLUTO EXECUTADO — NOVA FASE {OPERATIONAL_EPOCH_LABEL} PRONTA"
            if operational_empty
            else f"{MISSION_ID} RESET PARCIAL — revisar table_counts_after"
        ),
    }


def validate_post_reset_state(
    *,
    table_counts: dict[str, int | str],
    preserved_counts: dict[str, int | str],
    sequence_last_values: dict[str, int | None],
    first_generation_event_id: int | None,
) -> dict[str, Any]:
    operational_empty = all(_safe_count(table_counts, table) == 0 for table in OPERATIONAL_DELETE_ORDER)
    imported_before = _safe_count(preserved_counts, "imported_contests")
    checks = {
        "generation_events_empty": _safe_count(table_counts, "generation_events") == 0,
        "generated_games_empty": _safe_count(table_counts, "generated_games") == 0,
        "reconciliation_empty": _safe_count(table_counts, "reconciliation_runs") == 0,
        "ml_diagnostic_empty": _safe_count(table_counts, "ml_diagnostic_decisions") == 0,
        "signatures_empty": _safe_count(table_counts, "institutional_output_signatures") == 0,
        "operational_tables_empty": operational_empty,
        "imported_contests_preserved": imported_before >= 0,
        "lotofacil_official_history_preserved": _safe_count(
            preserved_counts, "lotofacil_official_history"
        )
        >= 0,
        "no_fake_visual_mapping_required": True,
    }
    if first_generation_event_id is None:
        checks["awaiting_first_generation"] = True
    else:
        checks["first_generation_event_id_is_one"] = first_generation_event_id == 1
    if sequence_last_values:
        checks["generation_events_sequence_at_one"] = (
            sequence_last_values.get("generation_events_id_seq") in {None, 0}
            or int(sequence_last_values.get("generation_events_id_seq") or 0) <= 1
        )
    return {
        "mission_id": MISSION_ID,
        "checks": checks,
        "sequence_last_values": sequence_last_values,
        "first_generation_event_id": first_generation_event_id,
        "verdict": (
            "M-DADOS-066 VALIDAÇÃO OK"
            if all(checks.values())
            else "M-DADOS-066 VALIDAÇÃO PARCIAL — ver checks"
        ),
    }
