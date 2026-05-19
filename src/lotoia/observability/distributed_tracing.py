"""Distributed tracing foundation for runtime, workers, APIs, and dashboards."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Iterator
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class TraceSpan:
    """One distributed tracing span."""

    name: str
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    status: str = "running"
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        """Return span duration in milliseconds."""

        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds() * 1000.0


class DistributedTracer:
    """In-memory tracer prepared for OpenTelemetry adapters."""

    def __init__(self) -> None:
        self._spans: dict[str, TraceSpan] = {}

    def start_span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Start a tracing span."""

        span = TraceSpan(
            name=name,
            trace_id=trace_id or f"trace-{uuid4().hex}",
            span_id=f"span-{uuid4().hex}",
            parent_span_id=parent_span_id,
            attributes=attributes or {},
        )
        self._spans[span.span_id] = span
        return span

    def finish_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """Finish an existing span."""

        span = self._spans[span_id]
        updated = replace(
            span,
            finished_at=datetime.now(UTC),
            status=status,
            attributes={**span.attributes, **(attributes or {})},
        )
        self._spans[span_id] = updated
        return updated

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[TraceSpan]:
        """Context manager for tracing one operation."""

        trace_span = self.start_span(
            name,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            attributes=attributes,
        )
        try:
            yield trace_span
        except Exception:
            self.finish_span(trace_span.span_id, status="error")
            raise
        else:
            self.finish_span(trace_span.span_id, status="ok")

    def list_spans(self) -> tuple[TraceSpan, ...]:
        """Return all spans."""

        return tuple(self._spans.values())
