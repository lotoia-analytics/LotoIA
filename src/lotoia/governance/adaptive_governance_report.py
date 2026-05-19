"""Adaptive operational governance report and persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from .adaptive_change_control import AdaptiveChangeControlDecision
from .governance_risk_analysis import GovernanceRiskResult
from .operational_policy_guard import PolicyGuardResult
from .signal_approval_workflow import SignalApprovalDecision


class AdaptiveGovernanceStore(Protocol):
    """Minimal persistence contract for adaptive governance reports."""

    def execute(self, sql: str, parameters: tuple[object, ...] = ()) -> None:
        """Execute a persistence statement."""

    @staticmethod
    def dumps(payload: Any) -> str:
        """Serialize payload to JSON."""


@dataclass(frozen=True, slots=True)
class AdaptiveGovernanceReport:
    """Institutional governance artifact for adaptive operational changes."""

    governance_id: str
    created_at: datetime
    policy_result: PolicyGuardResult
    risk_result: GovernanceRiskResult
    approval_decision: SignalApprovalDecision
    change_control: AdaptiveChangeControlDecision
    source_intelligence_id: str | None = None
    experiment_id: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    benchmark_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        policy_result: PolicyGuardResult,
        risk_result: GovernanceRiskResult,
        approval_decision: SignalApprovalDecision,
        change_control: AdaptiveChangeControlDecision,
        source_intelligence_id: str | None = None,
        experiment_id: str | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
        benchmark_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AdaptiveGovernanceReport":
        return cls(
            governance_id=f"adaptive-governance-{uuid4().hex}",
            created_at=datetime.now(UTC),
            policy_result=policy_result,
            risk_result=risk_result,
            approval_decision=approval_decision,
            change_control=change_control,
            source_intelligence_id=source_intelligence_id,
            experiment_id=experiment_id,
            model_name=model_name,
            model_version=model_version,
            benchmark_id=benchmark_id,
            metadata={
                "protocol": "FeatureGenerationProtocol",
                "causality": "governance consumes intelligence and benchmark artifacts only",
                "benchmarkability": True,
                **(metadata or {}),
            },
        )

    def summary_metrics(self) -> dict[str, float | int | str]:
        return {
            "risk_score": self.risk_result.risk_score,
            "risk_level": self.risk_result.risk_level,
            "policy_violation_count": len(self.policy_result.violations),
            "blocking_policy_count": self.policy_result.blocking_count,
            "allowed": int(self.policy_result.allowed),
            "approval_status": self.approval_decision.status.value,
            "change_action": self.change_control.action.value,
            "rollback_required": int(self.change_control.rollback_required),
        }

    def to_dict(self) -> dict[str, Any]:
        return _to_jsonable(self)

    def persist(self, store: AdaptiveGovernanceStore) -> None:
        store.execute(ADAPTIVE_GOVERNANCE_REPORT_TABLE_SQL)
        store.execute(ADAPTIVE_GOVERNANCE_REPORT_EXPERIMENT_INDEX_SQL)
        store.execute(ADAPTIVE_GOVERNANCE_REPORT_CREATED_INDEX_SQL)
        store.execute(
            """
            INSERT OR REPLACE INTO adaptive_governance_reports (
                governance_id,
                created_at,
                source_intelligence_id,
                experiment_id,
                model_name,
                model_version,
                benchmark_id,
                risk_score,
                approval_status,
                change_action,
                summary_metrics_json,
                report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.governance_id,
                self.created_at.isoformat(),
                self.source_intelligence_id,
                self.experiment_id,
                self.model_name,
                self.model_version,
                self.benchmark_id,
                self.risk_result.risk_score,
                self.approval_decision.status.value,
                self.change_control.action.value,
                store.dumps(self.summary_metrics()),
                store.dumps(self.to_dict()),
            ),
        )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


ADAPTIVE_GOVERNANCE_REPORT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS adaptive_governance_reports (
    governance_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_intelligence_id TEXT,
    experiment_id TEXT,
    model_name TEXT,
    model_version TEXT,
    benchmark_id TEXT,
    risk_score REAL NOT NULL,
    approval_status TEXT NOT NULL,
    change_action TEXT NOT NULL,
    summary_metrics_json TEXT NOT NULL,
    report_json TEXT NOT NULL
);
"""

ADAPTIVE_GOVERNANCE_REPORT_EXPERIMENT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_adaptive_governance_reports_experiment_id
ON adaptive_governance_reports(experiment_id);
"""

ADAPTIVE_GOVERNANCE_REPORT_CREATED_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_adaptive_governance_reports_created_at
ON adaptive_governance_reports(created_at);
"""
