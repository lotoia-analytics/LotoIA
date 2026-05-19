"""Structured logging foundation for enterprise operation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class LogLevel(StrEnum):
    """Institutional structured log levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class StructuredLogEvent:
    """One JSON-ready structured log event."""

    message: str
    level: LogLevel = LogLevel.INFO
    service: str = "lotoia"
    source: str = "runtime"
    event_id: str = field(default_factory=lambda: f"log-{uuid4().hex}")
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trace_id: str | None = None
    span_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-ready event data."""

        return _to_jsonable(self)

    def to_json(self) -> str:
        """Return a compact JSON log line."""

        return json.dumps(self.to_dict(), sort_keys=True)


class StructuredLogger:
    """In-memory structured logger ready for stdout/ELK/OpenSearch adapters."""

    def __init__(self, *, service: str = "lotoia") -> None:
        self.service = service
        self._events: list[StructuredLogEvent] = []

    def log(
        self,
        message: str,
        *,
        level: LogLevel = LogLevel.INFO,
        source: str = "runtime",
        trace_id: str | None = None,
        span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StructuredLogEvent:
        """Record one structured log event."""

        event = StructuredLogEvent(
            message=message,
            level=level,
            service=self.service,
            source=source,
            trace_id=trace_id,
            span_id=span_id,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def info(self, message: str, **kwargs: Any) -> StructuredLogEvent:
        """Record an info event."""

        return self.log(message, level=LogLevel.INFO, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> StructuredLogEvent:
        """Record a warning event."""

        return self.log(message, level=LogLevel.WARNING, **kwargs)

    def error(self, message: str, **kwargs: Any) -> StructuredLogEvent:
        """Record an error event."""

        return self.log(message, level=LogLevel.ERROR, **kwargs)

    def list_events(self) -> tuple[StructuredLogEvent, ...]:
        """Return recorded structured log events."""

        return tuple(self._events)


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    return value
