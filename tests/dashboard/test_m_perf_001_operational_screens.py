"""M-PERF-001 — otimização telas operacionais críticas."""

from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_light_mode import (
    ANALYTICAL_PAGE_SIZE,
    CONFERENCE_EVENTS_LIMIT,
    OPERATIONAL_EVENTS_LIMIT,
    SESSION_LOAD_ANALYTICAL,
    SESSION_LOAD_CENTRAL_ML,
    SESSION_LOAD_CONFERENCE,
)
from dashboard.institutional_operational_structural_coverage import load_operational_core_002_generations


def test_build_marker_v73() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v83"


def test_operational_generations_accepts_limit(tmp_path) -> None:
    from lotoia.database.database import create_database

    db_path = tmp_path / "perf-limit.db"
    create_database(db_path)
    rows = load_operational_core_002_generations(db_path, limit=5)
    assert isinstance(rows, list)
    assert len(rows) <= 5


def test_persisted_groups_supports_limit_and_summary_only(monkeypatch) -> None:
    calls: list[dict] = []

    def _fake_uncached(**kwargs):
        calls.append(dict(kwargs))
        return []

    monkeypatch.setattr(
        institutional_app,
        "_load_persisted_generation_event_groups_uncached",
        lambda *args, **kwargs: _fake_uncached(**kwargs),
    )
    institutional_app._load_persisted_generation_event_groups(
        conference_eligible_only=True,
        limit=CONFERENCE_EVENTS_LIMIT,
        summary_only=True,
        use_cache=False,
    )
    assert calls
    assert calls[0]["summary_only"] is True
    assert calls[0]["limit"] == CONFERENCE_EVENTS_LIMIT


def test_main_uses_light_snapshot_resolver() -> None:
    source = inspect.getsource(institutional_app.main)
    assert "_resolve_database_snapshot()" in source
    assert "snapshot = _database_snapshot()" not in source


def test_analytical_page_has_lazy_gate() -> None:
    source = inspect.getsource(institutional_app._render_analytical_page)
    assert "SESSION_LOAD_ANALYTICAL" in source
    assert "render_lazy_load_gate" in source
    assert "ANALYTICAL_PAGE_SIZE" in source


def test_conference_page_has_lazy_gate_and_summary_load() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "SESSION_LOAD_CONFERENCE" in source
    assert "page_load=True" in source
    assert "SESSION_CONFERENCE_SELECTED_GE" in source
    assert "read_cached_conference_result" in source


def test_central_ml_page_has_lazy_gate() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "SESSION_LOAD_CENTRAL_ML" in source


def test_cobertura_uses_cached_operational_loader() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "_load_operational_generations_cached" in source
    assert "OPERATIONAL_EVENTS_LIMIT" in source


def test_scientific_indexes_cached() -> None:
    source = inspect.getsource(institutional_app._load_scientific_context_indexes)
    assert "_cached_scientific_context_indexes" in source
