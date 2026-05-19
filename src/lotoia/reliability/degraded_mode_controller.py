"""Degraded mode controller for resilient operational continuity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .runtime_stability_monitor import StabilitySnapshot


@dataclass(frozen=True, slots=True)
class DegradedModeDecision:
    """Decision to enter or leave degraded operation."""

    active: bool
    level: str
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class DegradedModeController:
    """Control degraded mode for operational SaaS stability."""

    def decide(self, snapshot: StabilitySnapshot) -> DegradedModeDecision:
        """Return degraded mode decision."""

        if snapshot.stability_score >= 0.85:
            return DegradedModeDecision(
                active=False,
                level="normal",
                reason="runtime_stable",
                metadata={"stability_score": snapshot.stability_score},
            )
        if snapshot.stability_score >= 0.60:
            return DegradedModeDecision(
                active=True,
                level="watch",
                reason="partial_degradation",
                metadata={"degraded_services": snapshot.degraded_services},
            )
        return DegradedModeDecision(
            active=True,
            level="critical",
            reason="severe_degradation",
            metadata={"degraded_services": snapshot.degraded_services},
        )
