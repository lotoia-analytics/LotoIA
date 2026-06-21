"""M-OPS-066-FIX-01 — Conferir Resultados não quebra ao resolver generation_event_id."""

from __future__ import annotations

import inspect

import pytest

from dashboard import institutional_app as admin_app
from dashboard.institutional_build import BUILD_MARKER
from dashboard.institutional_conference_runtime import (
    OPS_FIX_MISSION_ID,
    SESSION_CONFERENCE_SELECTED_BATTERY,
    SESSION_CONFERENCE_SELECTED_GE,
    ensure_conference_session_defaults,
    is_valid_resolved_battery_id,
    read_conference_selected_battery,
    sync_conference_battery_selection,
)


def test_session_constant_defined() -> None:
    assert SESSION_CONFERENCE_SELECTED_BATTERY == "conference_selected_battery_id"


def test_build_marker_bumped() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v100"


def test_run_conference_does_not_write_widget_session_key() -> None:
    source = inspect.getsource(admin_app._run_institutional_conference)
    assert "st.session_state[SESSION_CONFERENCE_SELECTED_BATTERY]" not in source
    assert "is_valid_resolved_battery_id" in source


def test_is_valid_resolved_battery_id() -> None:
    assert is_valid_resolved_battery_id("BAT-001")
    assert not is_valid_resolved_battery_id(None)
    assert not is_valid_resolved_battery_id("")
    assert not is_valid_resolved_battery_id("GE-1")


def test_ensure_conference_session_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    session: dict[str, object] = {}
    monkeypatch.setattr(
        "dashboard.institutional_conference_runtime.st.session_state",
        session,
        raising=False,
    )
    ensure_conference_session_defaults(default_battery_id="BAT-001")
    assert session[SESSION_CONFERENCE_SELECTED_BATTERY] == "BAT-001"


def test_sync_conference_battery_selection_aligns_invalid_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session: dict[str, object] = {SESSION_CONFERENCE_SELECTED_BATTERY: "BAT-999"}
    monkeypatch.setattr(
        "dashboard.institutional_conference_runtime.st.session_state",
        session,
        raising=False,
    )
    selected = sync_conference_battery_selection(
        selectable_battery_ids=["BAT-001", "BAT-002"],
        default_battery_id="BAT-001",
    )
    assert selected == "BAT-001"
    assert session[SESSION_CONFERENCE_SELECTED_BATTERY] == "BAT-001"


def test_read_conference_selected_battery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "dashboard.institutional_conference_runtime.st.session_state",
        {SESSION_CONFERENCE_SELECTED_BATTERY: "BAT-002"},
        raising=False,
    )
    assert read_conference_selected_battery() == "BAT-002"


def test_run_conference_rejects_invalid_explicit_battery_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session: dict[str, object] = {}
    monkeypatch.setattr(admin_app.st, "session_state", session, raising=False)
    monkeypatch.setattr(admin_app, "_is_valid_conference_contest", lambda _contest: True)
    monkeypatch.setattr(
        admin_app,
        "_get_conference_contest_from_imported",
        lambda _contest: {"concurso": 3713, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(admin_app, "_load_official_conference_generation_groups", lambda **_kwargs: [])

    admin_app._run_institutional_conference(
        contest_number=3713,
        battery_id="invalid",
        conference_all_official=False,
    )

    result = session["institutional_check_result"]
    assert result["status"] == "waiting_lot"
    assert "inválido" in str(result["warning"]).lower()


def test_run_conference_succeeds_without_touching_widget_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session: dict[str, object] = {SESSION_CONFERENCE_SELECTED_BATTERY: "BAT-001"}
    monkeypatch.setattr(admin_app.st, "session_state", session, raising=False)
    monkeypatch.setattr(admin_app, "_is_valid_conference_contest", lambda _contest: True)
    monkeypatch.setattr(
        admin_app,
        "_get_conference_contest_from_imported",
        lambda _contest: {"concurso": 3713, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(
        admin_app,
        "_load_official_conference_generation_groups",
        lambda **_kwargs: [
            {
                "generation_event_id": 35,
                "total_games": 20,
                "official_release_allowed": True,
                "is_official_conference_eligible": True,
                "games": [{"numbers": list(range(1, 16)), "game_index": 1}],
                "batch_id": "batch-35",
            }
        ],
    )
    monkeypatch.setattr(admin_app, "_prepare_conference_group", lambda group: dict(group))
    monkeypatch.setattr(
        admin_app,
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
        admin_app,
        "discover_scientific_generation_policy",
        lambda *_args, **_kwargs: {"policy": {}, "policy_before": {}, "policy_after": {}},
    )
    monkeypatch.setattr(
        admin_app,
        "build_post_reconciliation_scientific_memory",
        lambda **_kwargs: {"memory_id": 1},
    )
    monkeypatch.setattr(admin_app, "_persist_scientific_reconciliation_memory", lambda payload: payload)
    monkeypatch.setattr(admin_app, "build_strong_near_miss_scientific_memory", lambda **_kwargs: {})
    monkeypatch.setattr(admin_app, "build_batch_reconciliation_scientific_memory", lambda **_kwargs: {})
    monkeypatch.setattr(admin_app, "persist_generation_event_conference_mark", lambda **_kwargs: True)

    admin_app._run_institutional_conference(
        contest_number=3713,
        battery_id="BAT-001",
        conference_all_official=False,
    )

    assert session[SESSION_CONFERENCE_SELECTED_BATTERY] == "BAT-001"
    result = session["institutional_check_result"]
    assert result["status"] == "checked"
    assert result.get("battery_id") == "BAT-001"


def test_mission_id_declared() -> None:
    assert OPS_FIX_MISSION_ID == "M-OPS-066-FIX-01"
