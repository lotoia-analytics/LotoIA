"""Operational monitoring for runtime, workers, queues, APIs, and governance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from .metrics_registry import MetricSample, MetricsRegistry


class RegistryLike(Protocol):
    """Dependency registry contract used by observability."""

    def has(self, name: str) -> bool:
        """Return whether a dependency exists."""

    def resolve(self, name: str) -> Any:
        """Resolve a dependency."""


@dataclass(frozen=True, slots=True)
class OperationalMonitoringSnapshot:
    """Point-in-time operational monitoring snapshot."""

    created_at: datetime
    metrics: dict[str, float]
    metric_samples: tuple[MetricSample, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


class OperationalMonitoring:
    """Collect operational signals without coupling to scientific domain internals."""

    def __init__(self, *, registry: RegistryLike, metrics: MetricsRegistry) -> None:
        self.registry = registry
        self.metrics = metrics

    def collect(self) -> OperationalMonitoringSnapshot:
        """Collect enterprise monitoring metrics from runtime services."""

        values: dict[str, float] = {}
        values.update(self._runtime_metrics())
        values.update(self._execution_metrics())
        values.update(self._api_metrics())
        values.update(self._dashboard_metrics())
        values.update(self._governance_metrics())
        samples = tuple(
            self.metrics.gauge(name, value, labels={"source": "operational_monitoring"})
            for name, value in sorted(values.items())
        )
        return OperationalMonitoringSnapshot(
            created_at=datetime.now(UTC),
            metrics=values,
            metric_samples=samples,
            metadata={"collector": "operational_monitoring"},
        )

    def _runtime_metrics(self) -> dict[str, float]:
        return {
            "runtime.dependency_count": float(len(self.registry.resolve("runtime_context").describe()))
            if self.registry.has("runtime_context")
            else 0.0,
        }

    def _execution_metrics(self) -> dict[str, float]:
        metrics: dict[str, float] = {
            "execution.queue_depth": 0.0,
            "execution.failure_rate": 0.0,
            "execution.retry_count": 0.0,
            "worker.available_count": 0.0,
        }
        if self.registry.has("execution_queue"):
            metrics["execution.queue_depth"] = float(self.registry.resolve("execution_queue").pending_count())
        if self.registry.has("worker_registry"):
            metrics["worker.available_count"] = float(
                len([worker for worker in self.registry.resolve("worker_registry").list() if worker.enabled])
            )
        if self.registry.has("execution_monitor"):
            summary = self.registry.resolve("execution_monitor").summary()
            terminal = summary.succeeded + summary.failed
            metrics["execution.failure_rate"] = (
                float(summary.failed) / float(terminal) if terminal else 0.0
            )
            metrics["execution.retry_count"] = float(summary.retry_scheduled)
        return metrics

    def _api_metrics(self) -> dict[str, float]:
        if not self.registry.has("operational_router"):
            return {"api.route_count": 0.0}
        return {"api.route_count": float(len(self.registry.resolve("operational_router").route_names()))}

    def _dashboard_metrics(self) -> dict[str, float]:
        names = (
            "executive_dashboard",
            "operational_health_dashboard",
            "operational_intelligence_dashboard",
        )
        return {
            "dashboard.registered_count": float(sum(1 for name in names if self.registry.has(name))),
        }

    def _governance_metrics(self) -> dict[str, float]:
        return {
            "governance.available": 1.0 if self.registry.has("operational_governance") else 0.0,
        }
