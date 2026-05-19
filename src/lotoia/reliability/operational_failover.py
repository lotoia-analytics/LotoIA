"""Operational failover foundation for benchmark and runtime services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .runtime_stability_monitor import StabilitySnapshot


@dataclass(frozen=True, slots=True)
class FailoverDecision:
    """Failover decision for operational degradation."""

    enabled: bool
    target: str | None
    reason: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class OperationalFailover:
    """Prepare failover decisions without binding to a specific cloud provider."""

    def decide(self, snapshot: StabilitySnapshot) -> FailoverDecision:
        """Decide whether failover mode should be activated."""

        if snapshot.stability_score >= 0.70:
            return FailoverDecision(
                enabled=False,
                target=None,
                reason="runtime_stable",
                metadata={"stability_score": snapshot.stability_score},
            )
        target = "benchmark_continuous_fallback" if not snapshot.scheduler_active else "runtime_secondary"
        return FailoverDecision(
            enabled=True,
            target=target,
            reason="runtime_degradation_detected",
            metadata={
                "degraded_services": snapshot.degraded_services,
                "stability_score": snapshot.stability_score,
            },
        )
