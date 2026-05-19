"""Signal approval workflow for adaptive governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .governance_risk_analysis import GovernanceRiskResult
from .operational_policy_guard import PolicyGuardResult, PolicySeverity


class ApprovalStatus(StrEnum):
    """Approval workflow status."""

    AUTO_APPROVED = "auto_approved"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SignalApprovalDecision:
    """Approval decision for adaptive operational changes."""

    status: ApprovalStatus
    required_approver: str
    reason: str
    escalation_codes: tuple[str, ...]


class SignalApprovalWorkflow:
    """Create approval/escalation decisions from governance risk."""

    def decide(
        self,
        *,
        policy_result: PolicyGuardResult,
        risk_result: GovernanceRiskResult,
    ) -> SignalApprovalDecision:
        blocking_codes = tuple(
            violation.code
            for violation in policy_result.violations
            if violation.severity == PolicySeverity.BLOCKING
        )
        if blocking_codes:
            return SignalApprovalDecision(
                status=ApprovalStatus.BLOCKED,
                required_approver="governance_committee",
                reason="blocking_policy_violation",
                escalation_codes=blocking_codes,
            )
        if risk_result.risk_level in {"medium", "high"} or policy_result.violations:
            return SignalApprovalDecision(
                status=ApprovalStatus.REVIEW_REQUIRED,
                required_approver="operational_owner",
                reason=f"risk_level_{risk_result.risk_level}",
                escalation_codes=tuple(violation.code for violation in policy_result.violations),
            )
        return SignalApprovalDecision(
            status=ApprovalStatus.AUTO_APPROVED,
            required_approver="system",
            reason="within_adaptive_policy",
            escalation_codes=(),
        )
