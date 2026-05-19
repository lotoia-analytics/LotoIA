"""Release governance orchestration."""

from __future__ import annotations

from typing import Any

_MISSING_RELEASE_GOVERNANCE_MESSAGE = (
    "release governance dependencies are not available in the current LotoIA namespace"
)


class ReleaseGovernanceEngine:
    """Run release approval, risk analysis, rollback simulation, audit, and observability."""

    def __init__(
        self,
        *,
        container: Any,
        audit: Any | None = None,
    ) -> None:
        try:
            from lotoia.releases import (
                DeploymentRiskAnalysis,
                ReleaseApprovalWorkflow,
                ReleaseAuditRegistry,
                RollbackOrchestrator,
            )
        except ModuleNotFoundError as exc:
            raise RuntimeError(_MISSING_RELEASE_GOVERNANCE_MESSAGE) from exc

        self.container = container
        self.audit = audit or ReleaseAuditRegistry()
        self.risk_analysis = DeploymentRiskAnalysis()
        self.approvals = ReleaseApprovalWorkflow(self.audit)
        self.rollback = RollbackOrchestrator(self.audit)

    def evaluate(
        self,
        release: Any,
        *,
        validation_passed: bool,
        deployment_ready: bool,
        actor_id: str | None = None,
        manual_approval: bool = False,
    ) -> Any:
        """Evaluate institutional release governance gates."""
        try:
            from lotoia.releases import ReleaseGovernanceReport
        except ModuleNotFoundError as exc:
            raise RuntimeError(_MISSING_RELEASE_GOVERNANCE_MESSAGE) from exc

        observability = self.container.resolve("observability_report")
        risk = self.risk_analysis.analyze(
            release,
            validation_passed=validation_passed,
            deployment_ready=deployment_ready,
            observability_active=bool(observability.summary_metrics()),
        )
        decision = self.approvals.decide(
            release,
            risk,
            actor_id=actor_id,
            manual_approval=manual_approval,
        )
        rollback_plan = self.rollback.simulate(release)
        report = ReleaseGovernanceReport(
            release_id=release.release_id,
            approved=decision.approved,
            risk_score=risk.risk_score,
            rollback_ready=rollback_plan.ready,
            audit_events=len(self.audit.list(release_id=release.release_id)),
            metadata={
                "approval_status": decision.status.value,
                "approval_reason": decision.reason,
                "risk_level": risk.risk_level,
                "rollback_status": rollback_plan.status.value,
                "runtime_id": self.container.context.runtime_id,
            },
        )
        metrics = self.container.resolve("metrics_registry")
        for name, value in report.summary_metrics().items():
            metrics.gauge(name, value, labels={"source": "release_governance"})
        self.container.resolve("structured_logger").info(
            "release governance evaluated",
            source="release_governance_engine",
            metadata=report.to_dict(),
        )
        return report
