from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from sqlalchemy import delete

from lotoia.database.adapter import resolve_institutional_adapter
from lotoia.database.database import (
    DEFAULT_DATABASE_PATH,
    AccessEvent,
    AuthEvent,
    AuthSession,
    CheckEvent,
    ExpansionEvent,
    FeatureFlag,
    FeatureUsageEvent,
    GenerationEvent,
    GeneratedGame,
    MlUsageEvent,
    ReconciliationEvent,
    ReconciliationGame,
    ReconciliationRun,
    ReportEvent,
    WorkflowEvent,
    WorkflowRun,
    WorkflowStep,
    get_session,
)


class ResetScope(StrEnum):
    visual = "visual"
    operational = "operational"
    telemetry = "telemetry"
    full_operational = "full_operational"


@dataclass(frozen=True, slots=True)
class ResetResult:
    reset_type: str
    triggered_by: str
    timestamp: str
    affected_tables: list[str]
    removed_rows: dict[str, int]
    status: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "reset_type": self.reset_type,
            "triggered_by": self.triggered_by,
            "timestamp": self.timestamp,
            "affected_tables": self.affected_tables,
            "removed_rows": self.removed_rows,
            "status": self.status,
            "notes": self.notes,
        }


class InstitutionalResetService:
    def __init__(self, db_path: Path = DEFAULT_DATABASE_PATH) -> None:
        self.db_path = db_path
        self.adapter = resolve_institutional_adapter(db_path)

    def reset_operational_history(
        self,
        *,
        scope: ResetScope,
        triggered_by: str,
        confirm_token: str,
        payload: dict[str, Any] | None = None,
    ) -> ResetResult:
        if confirm_token.strip().lower() != "confirmar":
            raise ValueError("confirm_token inválido; use 'confirmar' para prosseguir.")

        affected_tables = self._scope_tables(scope)
        if affected_tables:
            from lotoia.governance.history_preservation_policy import assert_generic_institutional_purge_blocked

            assert_generic_institutional_purge_blocked(
                source=f"InstitutionalResetService.reset_operational_history scope={scope.value}",
                tables=list(affected_tables.keys()),
            )
        removed_rows: dict[str, int] = {}
        with get_session(self.db_path) as session:
            for table_name, model in affected_tables.items():
                removed_rows[table_name] = int(session.execute(delete(model)).rowcount or 0)
            session.commit()

        result = ResetResult(
            reset_type=scope.value,
            triggered_by=triggered_by,
            timestamp=datetime.now(UTC).isoformat(),
            affected_tables=list(affected_tables.keys()),
            removed_rows=removed_rows,
            status="completed",
            notes="histórico operacional limpo com isolamento científico preservado",
        )
        self.adapter.save_reset_event(
            reset_type=scope.value,
            triggered_by=triggered_by,
            affected_tables=result.affected_tables,
            payload=payload or {},
            status=result.status,
            notes=result.notes,
        )
        return result

    def _scope_tables(self, scope: ResetScope) -> dict[str, Any]:
        if scope == ResetScope.visual:
            return {}
        if scope == ResetScope.operational:
            return {
                "generated_games": GeneratedGame,
                "ml_usage_events": MlUsageEvent,
                "reconciliation_games": ReconciliationGame,
                "report_events": ReportEvent,
                "expansion_events": ExpansionEvent,
                "reconciliation_events": ReconciliationEvent,
                "check_events": CheckEvent,
                "reconciliation_runs": ReconciliationRun,
                "workflow_steps": WorkflowStep,
                "workflow_events": WorkflowEvent,
                "workflow_runs": WorkflowRun,
                "generation_events": GenerationEvent,
            }
        if scope == ResetScope.telemetry:
            return {
                "generated_games": GeneratedGame,
                "feature_usage_events": FeatureUsageEvent,
                "access_events": AccessEvent,
                "auth_events": AuthEvent,
                "auth_sessions": AuthSession,
                "feature_flags": FeatureFlag,
                "ml_usage_events": MlUsageEvent,
                "reconciliation_games": ReconciliationGame,
                "report_events": ReportEvent,
                "expansion_events": ExpansionEvent,
                "reconciliation_events": ReconciliationEvent,
                "check_events": CheckEvent,
                "reconciliation_runs": ReconciliationRun,
                "workflow_steps": WorkflowStep,
                "workflow_events": WorkflowEvent,
                "workflow_runs": WorkflowRun,
                "generation_events": GenerationEvent,
            }
        if scope == ResetScope.full_operational:
            return {
                "generated_games": GeneratedGame,
                "feature_usage_events": FeatureUsageEvent,
                "access_events": AccessEvent,
                "auth_events": AuthEvent,
                "auth_sessions": AuthSession,
                "feature_flags": FeatureFlag,
                "ml_usage_events": MlUsageEvent,
                "reconciliation_games": ReconciliationGame,
                "report_events": ReportEvent,
                "expansion_events": ExpansionEvent,
                "reconciliation_events": ReconciliationEvent,
                "check_events": CheckEvent,
                "reconciliation_runs": ReconciliationRun,
                "workflow_steps": WorkflowStep,
                "workflow_events": WorkflowEvent,
                "workflow_runs": WorkflowRun,
                "generation_events": GenerationEvent,
            }
        raise ValueError(f"unsupported reset scope: {scope}")
