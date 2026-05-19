"""Governance council report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class GovernanceCouncilReport:
    decision_count: int
    approval_count: int
    consensus_reached: bool
    report_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def healthy(self) -> bool:
        return self.decision_count > 0 and self.approval_count > 0 and self.consensus_reached
