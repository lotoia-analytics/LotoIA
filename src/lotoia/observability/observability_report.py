"""Enterprise observability reports for dashboards and operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .metrics_registry import MetricSummary, MetricsRegistry
from .observability_alerts import ObservabilityAlert, ObservabilityAlertEngine
from .operational_monitoring import OperationalMonitoring, OperationalMonitoringSnapshot


@dataclass(frozen=True, slots=True)
class ObservabilityReport:
    """Structured enterprise observability report."""

    report_id: str
    created_at: datetime
    snapshot: OperationalMonitoringSnapshot
    metric_summaries: tuple[MetricSummary, ...]
    alerts: tuple[ObservabilityAlert, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        monitoring: OperationalMonitoring,
        metrics_registry: MetricsRegistry,
        alert_engine: ObservabilityAlertEngine,
        metadata: dict[str, Any] | None = None,
    ) -> "ObservabilityReport":
        """Collect metrics, evaluate alerts, and create an enterprise report."""

        snapshot = monitoring.collect()
        return cls(
            report_id=f"observability-report-{uuid4().hex}",
            created_at=datetime.now(UTC),
            snapshot=snapshot,
            metric_summaries=metrics_registry.summarize(),
            alerts=alert_engine.evaluate(snapshot.metrics),
            metadata={
                "layer": "enterprise_observability",
                "prometheus_ready": True,
                "opentelemetry_ready": True,
                **(metadata or {}),
            },
        )

    def summary_metrics(self) -> dict[str, float]:
        """Return report-level summary metrics."""

        return {
            **self.snapshot.metrics,
            "observability.alert_count": float(len(self.alerts)),
            "observability.critical_alert_count": float(
                sum(1 for alert in self.alerts if alert.severity == "critical")
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready report data."""

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
