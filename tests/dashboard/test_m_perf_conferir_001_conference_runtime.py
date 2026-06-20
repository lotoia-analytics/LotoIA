"""M-PERF-CONFERIR-001 — Conferir Resultados sem travar sessão."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_conference_runtime import (
    MISSION_ID,
    SESSION_CONFERENCE_CACHE,
    SESSION_CONFERENCE_SELECTED_GE,
    conference_cache_key,
    default_conference_generation_event_id,
    format_conference_lot_label,
    paginate_conference_lots,
    read_cached_conference_result,
    store_cached_conference_result,
)


def test_build_marker_v81_conference_perf() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v83"


def test_conference_page_loads_summary_only_with_limit() -> None:
    source = inspect.getsource(institutional_app._load_official_conference_generation_groups)
    assert "summary_only=True" in source
    assert "CONFERENCE_EVENTS_LIMIT" in source


def test_conference_page_single_lot_on_demand() -> None:
    source = inspect.getsource(institutional_app._render_conference_page)
    assert "Conferir lote selecionado" in source
    assert "SESSION_CONFERENCE_SELECTED_GE" in source
    assert "st.spinner" in source
    assert "conference_all_official=True" not in source
    assert "read_cached_conference_result" in source


def test_run_institutional_conference_does_not_load_unbounded_groups() -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "limit=None" not in source
    assert "generation_event_id=resolved_ge_id" in source or "generation_event_id=" in source


def test_latest_contest_uses_limited_cached_query() -> None:
    source = inspect.getsource(institutional_app._load_recent_imported_contest_records)
    assert ".limit(" in source
    assert inspect.getsource(institutional_app._resolve_latest_official_conference_contest).count(
        "_cached_latest_official_conference_contest"
    ) >= 1


def test_persisted_groups_support_generation_event_id_filter() -> None:
    source = inspect.getsource(institutional_app._load_persisted_generation_event_groups_uncached)
    assert "generation_event_id" in source
    assert "GenerationEvent.id ==" in source


def test_paginate_conference_lots() -> None:
    groups = [{"generation_event_id": index, "total_games": 20} for index in range(25, 0, -1)]
    page, pages, idx = paginate_conference_lots(groups, page_index=0, page_size=10)
    assert len(page) == 10
    assert pages == 3
    assert idx == 0


def test_default_conference_generation_event_id_picks_latest() -> None:
    groups = [
        {"generation_event_id": 33, "total_games": 20},
        {"generation_event_id": 35, "total_games": 20},
        {"generation_event_id": 31, "total_games": 20},
    ]
    assert default_conference_generation_event_id(groups) == 35


def test_format_conference_lot_label() -> None:
    label = format_conference_lot_label(
        {"generation_event_id": 35, "total_games": 20, "lot_operational_status": "officialized", "batch_id": "CORE"}
    )
    assert "GE 35" in label
    assert "20 jogos" in label


def test_conference_cache_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    session: dict = {}
    monkeypatch.setattr(
        "dashboard.institutional_conference_runtime.st.session_state",
        session,
        raising=False,
    )
    store_cached_conference_result(
        generation_event_id=35,
        contest_number=3713,
        check_result={"status": "checked", "generation_event_id": 35, "contest_number": 3713},
    )
    assert conference_cache_key(generation_event_id=35, contest_number=3713) in session[SESSION_CONFERENCE_CACHE]
    cached = read_cached_conference_result(generation_event_id=35, contest_number=3713)
    assert cached is not None
    assert cached["generation_event_id"] == 35


def test_run_institutional_conference_single_lot_only(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def _fake_load(**kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("summary_only"):
            return [{"generation_event_id": 35, "total_games": 20, "official_release_allowed": True}]
        return [
            {
                "generation_event_id": 35,
                "total_games": 20,
                "official_release_allowed": True,
                "is_official_conference_eligible": True,
                "context_json": {"lot_operational_status": "officialized"},
                "games": [{"numbers": list(range(1, 16)), "game_index": 1}],
                "batch_id": "batch-35",
            }
        ]

    monkeypatch.setattr(institutional_app, "_load_persisted_generation_event_groups", _fake_load)
    monkeypatch.setattr(
        institutional_app,
        "_get_conference_contest_from_imported",
        lambda _contest: {"concurso": 3713, "dezenas": list(range(1, 16)), "data": "2026-01-01"},
    )
    monkeypatch.setattr(institutional_app, "_is_valid_conference_contest", lambda _contest: True)
    monkeypatch.setattr(
        institutional_app,
        "_compare_games_against_contest",
        lambda **_: {
            "results": [{"hits": 11, "game_index": 1, "numbers": list(range(1, 16)), "prize_status": "premiado"}],
            "best_hits": 11,
            "total_hits": 11,
            "prize_count": 1,
            "contest_number": 3713,
            "contest_date": "2026-01-01",
            "diagnostics": {},
        },
    )
    monkeypatch.setattr(
        institutional_app,
        "discover_scientific_generation_policy",
        lambda *_args, **_kwargs: {"policy": {}, "policy_before": {}, "policy_after": {}},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_post_reconciliation_scientific_memory",
        lambda **_kwargs: {"memory_id": 1},
    )
    monkeypatch.setattr(institutional_app, "_persist_scientific_reconciliation_memory", lambda payload: payload)
    monkeypatch.setattr(institutional_app, "build_strong_near_miss_scientific_memory", lambda **_kwargs: {})
    monkeypatch.setattr(institutional_app, "build_batch_reconciliation_scientific_memory", lambda **_kwargs: {})
    monkeypatch.setattr(institutional_app, "persist_generation_event_conference_mark", lambda **_kwargs: True)
    monkeypatch.setattr(institutional_app.st, "session_state", {}, raising=False)

    institutional_app._run_institutional_conference(
        contest_number=3713,
        generation_event_id=35,
        conference_all_official=False,
    )

    full_loads = [call for call in calls if not call.get("summary_only")]
    assert full_loads
    assert full_loads[-1].get("generation_event_id") == 35
    result = institutional_app.st.session_state.get("institutional_check_result")
    assert isinstance(result, dict)
    assert int(result.get("generation_event_id", 0) or 0) == 35


def test_mission_id_declared() -> None:
    assert MISSION_ID == "M-PERF-CONFERIR-001"
