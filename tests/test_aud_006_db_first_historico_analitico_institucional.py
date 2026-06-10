from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dashboard import institutional_app as app
from lotoia.database.institutional_read_repository import (
    InstitutionalReadRepository,
    count_generated_games_for_event,
    get_analytical_snapshot,
    get_generation_event_with_games,
    get_institutional_snapshot,
    get_latest_official_contest,
    get_latest_reconciliation_for_generation,
    get_reconciliation_run_with_items,
)
from lotoia.governance.db_first_guards import (
    build_db_export_metadata,
    detect_session_truth,
    evaluate_analytical_guard,
    evaluate_history_guard,
    evaluate_institutional_guard,
)


def test_history_loads_from_postgresql_not_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    app._history_number_frequency.clear()

    def _forbidden_csv() -> list[object]:
        raise AssertionError("load_draws_csv must not be used as operational source")

    monkeypatch.setattr(app, "load_draws_csv", _forbidden_csv)

    fake_row = SimpleNamespace(numbers="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    query = MagicMock()
    query.filter.return_value.order_by.return_value.all.return_value = [fake_row]
    session = MagicMock()
    session.query.return_value = query
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    monkeypatch.setattr(app, "get_session", lambda _path: session_cm)

    frequencies = app._history_number_frequency()
    assert frequencies[1] == 1
    assert frequencies[15] == 1


def test_analytics_loads_from_reconciliation_items(monkeypatch: pytest.MonkeyPatch) -> None:
    run = SimpleNamespace(id=9, generation_event_id=42, contest_id=3700, best_hits=12, total_hits=120, prize_count=1)
    item = SimpleNamespace(game_index=1, hits=12, matched_numbers=[1, 2, 3], prize_status="premiado", prize_tier="faixa_12", contest_id=3700)
    session = MagicMock()
    session.get.side_effect = lambda model, pk: run if pk == 9 else None
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [item]
    session.query.return_value.filter.return_value.order_by.return_value.first.return_value = run

    guard = evaluate_analytical_guard(session, reconciliation_run_id=9)
    assert guard["allowed"] is True
    assert guard["reconciliation_run_id"] == 9
    assert guard["items_count"] == 1
    assert guard["db_table"] == "reconciliation_games"

    monkeypatch.setattr(app, "_load_institutional_check_result_from_db", lambda **_: {"source": "reconciliation_runs"})
    monkeypatch.setattr(app.st, "session_state", {"institutional_check_result": {"status": "checked", "contest_number": 1}})
    conflict = app._resolve_institutional_check_result(generation_event_id=42)
    assert conflict is not None
    assert conflict.get("source") == "reconciliation_runs"


def test_institutional_panel_loads_from_snapshots_or_audit_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    guard = {
        "allowed": True,
        "snapshot": {
            "source": "institutional_memory_snapshots",
            "memory_id": "mem-1",
            "db_table": "institutional_memory_snapshots",
        },
    }
    monkeypatch.setattr(app, "_evaluate_db_first_institutional_guard", lambda: guard)
    monkeypatch.setattr(app, "_load_official_sync_contest_summary", lambda: {"contest_number": 3700, "sync_timestamp": "2026-06-01"})
    monkeypatch.setattr(app.st, "session_state", {"institutional_last_official_sync_summary": {"contest_number": 1}})

    sync_from_db = app._load_official_sync_contest_summary() or {}
    assert int(sync_from_db.get("contest_number", 0) or 0) == 3700
    assert app._evaluate_db_first_institutional_guard()["allowed"] is True
    assert app._evaluate_db_first_institutional_guard()["snapshot"]["source"] == "institutional_memory_snapshots"


def test_exports_are_db_derived() -> None:
    metadata = build_db_export_metadata(
        db_table="reconciliation_games",
        event_id=42,
        run_id=9,
        snapshot_id="snap-1",
        commit_hash="abc123",
    )
    payload = app._build_db_derived_export_payload(
        [{"generation_event_id": 42, "acertos": 12}],
        db_table="reconciliation_games",
        event_id=42,
        run_id=9,
        snapshot_id="snap-1",
    )
    assert payload["metadata"]["db_table"] == "reconciliation_games"
    assert payload["metadata"]["generation_event_id"] == "42"
    assert payload["metadata"]["reconciliation_run_id"] == "9"
    assert payload["metadata"]["snapshot_id"] == "snap-1"
    assert "commit_hash" in payload["metadata"]
    assert metadata["export_origin"] == "postgresql"


def test_no_csv_operational_sources_remaining_in_history_render(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def _tracked_csv() -> list[object]:
        calls.append("load_draws_csv")
        return []

    monkeypatch.setattr(app, "load_draws_csv", _tracked_csv)
    monkeypatch.setattr(
        app,
        "_load_hai_latest_contest_summary",
        lambda: {"contest_number": 3700, "source": "lotofacil_official_history"},
    )
    monkeypatch.setattr(app, "_load_latest_generated_games", lambda: {})
    monkeypatch.setattr(app, "_load_latest_reconciliation_summary", lambda: {})
    monkeypatch.setattr(app, "_load_official_sync_contest_summary", lambda: {})
    monkeypatch.setattr(app, "_load_official_history_diagnostics", lambda: {})
    monkeypatch.setattr(app, "_history_number_frequency", lambda: {1: 1})
    app._institutional_source_map({"counts": {}, "latest": {}})
    assert "load_draws_csv" not in calls


def test_no_session_truth_after_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    conflict = detect_session_truth(
        {"status": "checked", "contest_number": 1, "generation_results": []},
        None,
    )
    assert conflict["conflict"] is True
    assert conflict["reason"] == "session_truth_detectado"

    monkeypatch.setattr(app, "_load_institutional_check_result_from_db", lambda **_: None)
    monkeypatch.setattr(app.st, "session_state", {"institutional_check_result": {"status": "checked", "contest_number": 1}})
    resolved = app._resolve_institutional_check_result(generation_event_id=42)
    assert resolved is not None
    assert resolved.get("status") == "blocked_session_truth"


def test_no_nested_db_session_in_dashboard_reload(monkeypatch: pytest.MonkeyPatch) -> None:
    session_open_count = {"count": 0}

    class _SessionContext:
        def __enter__(self):
            session_open_count["count"] += 1
            session = MagicMock()
            session.query.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return session

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(app, "get_session", lambda _path: _SessionContext())
    monkeypatch.setattr(app, "_load_scientific_context_indexes", lambda: ({}, {}))

    history = app._load_generation_history(limit=1)
    assert history == []
    assert session_open_count["count"] == 1


def test_repository_helpers_use_injected_session() -> None:
    official_session = MagicMock()
    official = SimpleNamespace(contest_number=3700)
    official_session.query.return_value.order_by.return_value.first.return_value = official
    assert get_latest_official_contest(official_session) is official

    generation_session = MagicMock()
    event = SimpleNamespace(id=42)
    game = SimpleNamespace(game_index=1)
    generation_session.get.return_value = event
    generation_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [game]
    loaded_event, games = get_generation_event_with_games(generation_session, 42)
    assert loaded_event is event
    assert games == [game]

    reconciliation_session = MagicMock()
    run = SimpleNamespace(id=7, generation_event_id=42)
    reconciliation_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = run
    reconciliation_session.get.return_value = run
    reconciliation_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    loaded_run, items = get_latest_reconciliation_for_generation(reconciliation_session, 42)
    assert loaded_run is run
    assert items == []

    count_session = MagicMock()
    count_session.query.return_value.filter.return_value.count.return_value = 3
    assert count_generated_games_for_event(count_session, 42) == 3

    repo = InstitutionalReadRepository()
    repo.get_latest_official_contest(session=official_session)


def test_history_guard_blocks_missing_generation_event_id() -> None:
    session = MagicMock()
    blocked = evaluate_history_guard(session, None)
    assert blocked["allowed"] is False
    assert blocked["reason"] == "historico_sem_generation_event_id"


def test_institutional_guard_blocks_without_db_state() -> None:
    session = MagicMock()
    session.query.return_value.order_by.return_value.first.return_value = None
    session.query.return_value.limit.return_value.count.return_value = 0
    blocked = evaluate_institutional_guard(session)
    assert blocked["allowed"] is False
    assert blocked["reason"] == "institucional_sem_snapshot_ou_audit_log"
