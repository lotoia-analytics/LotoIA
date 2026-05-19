"""Enterprise observability alert rules and evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ObservabilityAlertRule:
    """One threshold rule for operational observability metrics."""

    metric_name: str
    warning_threshold: float
    critical_threshold: float
    direction: str = "above"
    description: str = ""

    def evaluate(self, value: float) -> str | None:
        """Return alert severity for a metric value."""

        if self.direction == "below":
            if value <= self.critical_threshold:
                return "critical"
            if value <= self.warning_threshold:
                return "warning"
            return None
        if value >= self.critical_threshold:
            return "critical"
        if value >= self.warning_threshold:
            return "warning"
        return None


@dataclass(frozen=True, slots=True)
class ObservabilityAlert:
    """One operational alert produced by observability rules."""

    metric_name: str
    value: float
    severity: str
    description: str
    alert_id: str = field(default_factory=lambda: f"observability-alert-{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class ObservabilityAlertEngine:
    """Evaluate enterprise alert rules against operational metrics."""

    def __init__(self, rules: tuple[ObservabilityAlertRule, ...] | None = None) -> None:
        self.rules = rules or default_observability_rules()

    def evaluate(self, metrics: dict[str, float]) -> tuple[ObservabilityAlert, ...]:
        """Evaluate all rules against a metric dictionary."""

        alerts: list[ObservabilityAlert] = []
        for rule in self.rules:
            if rule.metric_name not in metrics:
                continue
            value = float(metrics[rule.metric_name])
            severity = rule.evaluate(value)
            if severity is None:
                continue
            alerts.append(
                ObservabilityAlert(
                    metric_name=rule.metric_name,
                    value=value,
                    severity=severity,
                    description=rule.description,
                    metadata={"direction": rule.direction},
                )
            )
        return tuple(alerts)


def default_observability_rules() -> tuple[ObservabilityAlertRule, ...]:
    """Default enterprise alert thresholds for initial operation."""

    return (
        ObservabilityAlertRule(
            metric_name="execution.failure_rate",
            warning_threshold=0.10,
            critical_threshold=0.25,
            description="Execution failure rate is elevated.",
        ),
        ObservabilityAlertRule(
            metric_name="execution.queue_depth",
            warning_threshold=50.0,
            critical_threshold=200.0,
            description="Execution queue depth is elevated.",
        ),
        ObservabilityAlertRule(
            metric_name="worker.available_count",
            warning_threshold=1.0,
            critical_threshold=0.0,
            direction="below",
            description="Worker availability is degraded.",
        ),
        ObservabilityAlertRule(
            metric_name="api.route_count",
            warning_threshold=1.0,
            critical_threshold=0.0,
            direction="below",
            description="Operational API routes are not available.",
        ),
    )
