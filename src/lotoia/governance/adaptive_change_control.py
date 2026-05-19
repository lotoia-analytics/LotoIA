"""Adaptive change control for operational governance."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .governance_risk_analysis import GovernanceRiskResult
from .signal_approval_workflow import ApprovalStatus, SignalApprovalDecision


class ChangeControlAction(StrEnum):
    """Allowed governance actions for adaptive changes."""

    APPLY = "apply"
    REVIEW = "review"
    BLOCK = "block"
    ROLLBACK = "rollback"


@dataclass(frozen=True, slots=True)
class AdaptiveChangeControlDecision:
    """Final adaptive change control decision."""

    action: ChangeControlAction
    approval_status: ApprovalStatus
    rollback_required: bool
    reason: str


class AdaptiveChangeControl:
    """Convert approval workflow and risk into operational control actions."""

    def decide(
        self,
        *,
        approval: SignalApprovalDecision,
        risk: GovernanceRiskResult,
    ) -> AdaptiveChangeControlDecision:
        if approval.status == ApprovalStatus.BLOCKED:
            return AdaptiveChangeControlDecision(
                action=ChangeControlAction.BLOCK,
                approval_status=approval.status,
                rollback_required=risk.risk_level == "high",
                reason=approval.reason,
            )
        if approval.status == ApprovalStatus.REVIEW_REQUIRED:
            return AdaptiveChangeControlDecision(
                action=ChangeControlAction.REVIEW,
                approval_status=approval.status,
                rollback_required=False,
                reason=approval.reason,
            )
        return AdaptiveChangeControlDecision(
            action=ChangeControlAction.APPLY,
            approval_status=approval.status,
            rollback_required=False,
            reason="adaptive_change_within_policy",
        )
