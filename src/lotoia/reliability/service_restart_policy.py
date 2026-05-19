"""Service restart policy for continuous SaaS resilience."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True, slots=True)
class RestartDecision:
    """Decision for one service restart attempt."""

    service_name: str
    should_restart: bool
    reason: str
    next_allowed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class ServiceRestartPolicy:
    """Institutional restart policy with bounded retries and cooldown."""

    def __init__(
        self,
        *,
        max_restarts: int = 3,
        cooldown_seconds: int = 10,
    ) -> None:
        self.max_restarts = max_restarts
        self.cooldown_seconds = cooldown_seconds
        self._restart_counts: dict[str, int] = {}
        self._last_restart_at: dict[str, datetime] = {}

    def decide(
        self,
        *,
        service_name: str,
        status: str,
        now: datetime | None = None,
    ) -> RestartDecision:
        """Decide whether a service should be restarted."""

        checked_at = now or datetime.now(UTC)
        if status in {"running", "registered"}:
            return RestartDecision(
                service_name=service_name,
                should_restart=False,
                reason="service_healthy",
                next_allowed_at=checked_at,
            )

        count = self._restart_counts.get(service_name, 0)
        last = self._last_restart_at.get(service_name)
        next_allowed = (
            last + timedelta(seconds=self.cooldown_seconds)
            if last is not None
            else checked_at
        )
        if checked_at < next_allowed:
            return RestartDecision(
                service_name=service_name,
                should_restart=False,
                reason="restart_cooldown_active",
                next_allowed_at=next_allowed,
                metadata={"restart_count": count},
            )
        if count >= self.max_restarts:
            return RestartDecision(
                service_name=service_name,
                should_restart=False,
                reason="restart_limit_reached",
                next_allowed_at=checked_at,
                metadata={"restart_count": count},
            )
        return RestartDecision(
            service_name=service_name,
            should_restart=True,
            reason="service_degraded",
            next_allowed_at=checked_at,
            metadata={"restart_count": count},
        )

    def record_restart(self, service_name: str, *, now: datetime | None = None) -> None:
        """Record that a restart was attempted."""

        self._restart_counts[service_name] = self._restart_counts.get(service_name, 0) + 1
        self._last_restart_at[service_name] = now or datetime.now(UTC)

    def restart_count(self, service_name: str) -> int:
        """Return restart attempts for a service."""

        return self._restart_counts.get(service_name, 0)
