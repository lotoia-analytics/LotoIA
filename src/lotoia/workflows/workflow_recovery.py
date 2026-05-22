from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from lotoia.reliability import ServiceRestartPolicy


@dataclass(frozen=True, slots=True)
class WorkflowRecoveryAction:
    workflow_id: str
    step_name: str
    status: str
    should_retry: bool
    reason: str
    next_allowed_at: datetime
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "step_name": self.step_name,
            "status": self.status,
            "should_retry": self.should_retry,
            "reason": self.reason,
            "next_allowed_at": self.next_allowed_at.isoformat(),
            "metadata": self.metadata,
        }


class WorkflowRecoveryEngine:
    """Bounded retry and recovery policy for workflow steps."""

    def __init__(self, *, max_retries: int = 3, cooldown_seconds: int = 30) -> None:
        self.restart_policy = ServiceRestartPolicy(max_restarts=max_retries, cooldown_seconds=cooldown_seconds)

    def decide(self, *, workflow_id: str, step_name: str, status: str, service_name: str | None = None, now: datetime | None = None) -> WorkflowRecoveryAction:
        checked_at = now or datetime.now(UTC)
        service = service_name or step_name
        decision = self.restart_policy.decide(service_name=service, status=status, now=checked_at)
        return WorkflowRecoveryAction(
            workflow_id=workflow_id,
            step_name=step_name,
            status=status,
            should_retry=decision.should_restart,
            reason=decision.reason,
            next_allowed_at=decision.next_allowed_at,
            metadata=dict(decision.metadata),
        )
