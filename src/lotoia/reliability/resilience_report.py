"""Resilience report for operational recovery actions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .degraded_mode_controller import DegradedModeDecision
from .operational_failover import FailoverDecision
from .runtime_stability_monitor import StabilitySnapshot
from .service_restart_policy import RestartDecision


@dataclass(frozen=True, slots=True)
class ResilienceReport:
    """Institutional resilience report."""

    snapshot: StabilitySnapshot
    restart_decisions: tuple[RestartDecision, ...]
    restarted_services: tuple[str, ...]
    failover: FailoverDecision
    degraded_mode: DegradedModeDecision
    report_id: str = field(default_factory=lambda: f"resilience-report-{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def recovered(self) -> bool:
        """Whether recovery actions were applied or runtime is stable."""

        return self.snapshot.stability_score >= 0.85 or bool(self.restarted_services)

    def summary_metrics(self) -> dict[str, float]:
        """Return numeric resilience metrics."""

        return {
            "runtime.stability_score": self.snapshot.stability_score,
            "runtime.degraded_service_count": float(len(self.snapshot.degraded_services)),
            "runtime.restarted_service_count": float(len(self.restarted_services)),
            "runtime.degraded_mode_active": 1.0 if self.degraded_mode.active else 0.0,
            "runtime.failover_enabled": 1.0 if self.failover.enabled else 0.0,
            "runtime.recovered": 1.0 if self.recovered else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready report."""

        return _to_jsonable(self)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value
