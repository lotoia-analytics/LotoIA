"""Performance — telas operacionais críticas (M-PERF-001)."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

MISSION_ID = "M-PERF-001"

# Limites padrão por tela (modo leve / operacional)
OPERATIONAL_EVENTS_LIMIT = 20
ANALYTICAL_EVENTS_LIMIT = 20
CONFERENCE_EVENTS_LIMIT = 20
CONFERENCE_SCAN_BUFFER = 50
CENTRAL_ML_EVENTS_LIMIT = 20
GENERATION_HISTORY_DEFAULT_LIMIT = 20

PERF_AUDIT_ENV = "LOTOIA_PERF_AUDIT"


@dataclass
class PerfScreenAudit:
    screen: str
    started_at: float = field(default_factory=time.perf_counter)
    ended_at: float = 0.0
    query_count: int = 0
    rows_loaded: int = 0
    notes: list[str] = field(default_factory=list)

    def finish(self) -> dict[str, Any]:
        self.ended_at = time.perf_counter()
        elapsed_ms = (self.ended_at - self.started_at) * 1000.0
        return {
            "mission_id": MISSION_ID,
            "screen": self.screen,
            "elapsed_ms": round(elapsed_ms, 2),
            "query_count": self.query_count,
            "rows_loaded": self.rows_loaded,
            "notes": list(self.notes),
        }


_perf_audit_active = os.getenv(PERF_AUDIT_ENV, "0").strip().lower() in {"1", "true", "yes", "on"}
_current_audit: PerfScreenAudit | None = None


def perf_audit_enabled() -> bool:
    return _perf_audit_active


@contextmanager
def perf_screen_audit(screen: str) -> Iterator[PerfScreenAudit]:
    global _current_audit
    audit = PerfScreenAudit(screen=screen)
    previous = _current_audit
    _current_audit = audit
    try:
        yield audit
    finally:
        audit.finish()
        _current_audit = previous


def perf_record_query(rows: int = 0, note: str = "") -> None:
    if _current_audit is None:
        return
    _current_audit.query_count += 1
    _current_audit.rows_loaded += max(0, int(rows))
    if note:
        _current_audit.notes.append(note)
