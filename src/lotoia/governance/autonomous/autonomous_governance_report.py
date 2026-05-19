"""Autonomous governance report."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class AutonomousGovernanceReport:
    decision_count: int
    risk_score: float
    optimized_action: str
    report_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def healthy(self) -> bool:
        return self.decision_count > 0 and 0.0 <= self.risk_score <= 1.0 and bool(self.optimized_action)
