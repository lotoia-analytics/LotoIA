"""Enterprise metrics registry for operational observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class MetricType(StrEnum):
    """Supported operational metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass(frozen=True, slots=True)
class MetricSample:
    """One metric sample emitted by runtime, workers, APIs, or dashboards."""

    name: str
    value: float
    metric_type: MetricType
    labels: dict[str, str] = field(default_factory=dict)
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MetricSummary:
    """Aggregated metric summary for reports and alerting."""

    name: str
    count: int
    latest: float
    minimum: float
    maximum: float
    average: float
    labels: dict[str, str]


class MetricsRegistry:
    """In-memory metrics registry prepared for Prometheus/OpenTelemetry export."""

    def __init__(self) -> None:
        self._samples: list[MetricSample] = []

    def record(
        self,
        name: str,
        value: float,
        *,
        metric_type: MetricType = MetricType.GAUGE,
        labels: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MetricSample:
        """Record one metric sample."""

        sample = MetricSample(
            name=name,
            value=float(value),
            metric_type=metric_type,
            labels=labels or {},
            metadata=metadata or {},
        )
        self._samples.append(sample)
        return sample

    def increment(
        self,
        name: str,
        value: float = 1.0,
        *,
        labels: dict[str, str] | None = None,
    ) -> MetricSample:
        """Record a counter increment."""

        return self.record(name, value, metric_type=MetricType.COUNTER, labels=labels)

    def gauge(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> MetricSample:
        """Record a gauge value."""

        return self.record(name, value, metric_type=MetricType.GAUGE, labels=labels)

    def timing(
        self,
        name: str,
        milliseconds: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> MetricSample:
        """Record an operation latency metric."""

        return self.record(name, milliseconds, metric_type=MetricType.TIMER, labels=labels)

    def list_samples(self, *, name: str | None = None) -> tuple[MetricSample, ...]:
        """Return metric samples, optionally filtered by name."""

        if name is None:
            return tuple(self._samples)
        return tuple(sample for sample in self._samples if sample.name == name)

    def summarize(self) -> tuple[MetricSummary, ...]:
        """Aggregate metrics by metric name and labels."""

        groups: dict[tuple[str, tuple[tuple[str, str], ...]], list[MetricSample]] = {}
        for sample in self._samples:
            key = (sample.name, tuple(sorted(sample.labels.items())))
            groups.setdefault(key, []).append(sample)

        summaries = []
        for (name, labels_tuple), samples in groups.items():
            values = [sample.value for sample in samples]
            summaries.append(
                MetricSummary(
                    name=name,
                    count=len(samples),
                    latest=values[-1],
                    minimum=min(values),
                    maximum=max(values),
                    average=sum(values) / len(values),
                    labels=dict(labels_tuple),
                )
            )
        return tuple(sorted(summaries, key=lambda item: item.name))
