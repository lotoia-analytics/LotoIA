"""Adaptive Operational Governance engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .adaptive_change_control import AdaptiveChangeControl
from .adaptive_governance_report import AdaptiveGovernanceReport
from .governance_risk_analysis import GovernanceRiskAnalysis
from .operational_policy_guard import OperationalPolicyGuard
from .signal_approval_workflow import SignalApprovalWorkflow


@dataclass(frozen=True, slots=True)
class AdaptiveGovernanceConfig:
    """Configuration for adaptive governance execution."""

    persist_report: bool = True


class AdaptiveGovernanceEngine:
    """Run adaptive policy guard, risk analysis, approval, and change control."""

    def __init__(
        self,
        *,
        config: AdaptiveGovernanceConfig | None = None,
        policy_guard: OperationalPolicyGuard | None = None,
        risk_analysis: GovernanceRiskAnalysis | None = None,
        approval_workflow: SignalApprovalWorkflow | None = None,
        change_control: AdaptiveChangeControl | None = None,
    ) -> None:
        self.config = config or AdaptiveGovernanceConfig()
        self.policy_guard = policy_guard or OperationalPolicyGuard()
        self.risk_analysis = risk_analysis or GovernanceRiskAnalysis()
        self.approval_workflow = approval_workflow or SignalApprovalWorkflow()
        self.change_control = change_control or AdaptiveChangeControl()

    def run(
        self,
        *,
        metrics: dict[str, float],
        source_intelligence_id: str | None = None,
        experiment_id: str | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
        benchmark_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        store: Any | None = None,
    ) -> AdaptiveGovernanceReport:
        policy = self.policy_guard.evaluate(metrics)
        risk = self.risk_analysis.analyze(metrics=metrics, policy_result=policy)
        approval = self.approval_workflow.decide(policy_result=policy, risk_result=risk)
        control = self.change_control.decide(approval=approval, risk=risk)
        report = AdaptiveGovernanceReport.create(
            policy_result=policy,
            risk_result=risk,
            approval_decision=approval,
            change_control=control,
            source_intelligence_id=source_intelligence_id,
            experiment_id=experiment_id,
            model_name=model_name,
            model_version=model_version,
            benchmark_id=benchmark_id,
            metadata=metadata,
        )
        if self.config.persist_report and store is not None:
            report.persist(store)
        return report

    def run_from_intelligence(
        self,
        *,
        intelligence_report: Any,
        extra_metrics: dict[str, float] | None = None,
        store: Any | None = None,
    ) -> AdaptiveGovernanceReport:
        metrics = {
            key: float(value)
            for key, value in intelligence_report.summary_metrics().items()
            if isinstance(value, int | float | bool)
        }
        metrics.update(extra_metrics or {})
        return self.run(
            metrics=metrics,
            source_intelligence_id=intelligence_report.intelligence_id,
            experiment_id=intelligence_report.experiment_id,
            model_name=intelligence_report.model_name,
            model_version=intelligence_report.model_version,
            benchmark_id=intelligence_report.benchmark_id,
            metadata={"source": "operational_intelligence_center"},
            store=store,
        )
