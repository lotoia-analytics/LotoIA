from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dashboard import institutional_app as admin_app
from lotoia.ingestion.result_sync_service import ResultSyncSummary


def test_history_number_frequency_reads_postgresql_not_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    admin_app._history_number_frequency.clear()

    def _forbidden_csv() -> list[object]:
        raise AssertionError("load_draws_csv must not be used as operational source")

    monkeypatch.setattr(admin_app, "load_draws_csv", _forbidden_csv)

    fake_row = SimpleNamespace(numbers="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    query = MagicMock()
    query.filter.return_value.order_by.return_value.all.return_value = [fake_row]
    session = MagicMock()
    session.query.return_value = query
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    monkeypatch.setattr(admin_app, "get_session", lambda _path: session_cm)

    frequencies = admin_app._history_number_frequency()
    assert frequencies[1] == 1
    assert frequencies[15] == 1


def test_sync_latest_official_result_now_requires_commit_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    summary = ResultSyncSummary(
        latest_contest=None,
        synced_contests=[],
        synced_contests_count=0,
        persisted_contests=0,
        provider_payload_count=0,
        contest_ids=[],
        db_backend="sqlite",
        engine_url="sqlite://",
        commit_state="failed",
        source="caixa",
        error_message="persist failed",
    )

    class _FakeService:
        client = SimpleNamespace(
            last_http_status=500,
            last_request_url="",
            last_request_headers={},
            last_response_headers={},
            last_response_preview="",
        )

        def sync_latest(self) -> ResultSyncSummary:
            return summary

    class _FakeRepository:
        def sync_official_history_from_imported_contests(self) -> int:
            return 0

        def get_latest_contest_record(self) -> None:
            return None

    monkeypatch.setattr(admin_app, "ContestRepository", lambda _path: _FakeRepository())
    monkeypatch.setattr(admin_app, "ResultSyncService", lambda repository: _FakeService())

    payload = admin_app._sync_latest_official_result_now()
    assert payload["status"] == "error"
    assert payload["commit_state"] == "failed"
    assert "persist failed" in str(payload.get("sync_error", ""))


def test_sync_latest_official_result_now_ok_on_commit_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    summary = ResultSyncSummary(
        latest_contest=3700,
        synced_contests=[3700],
        synced_contests_count=1,
        persisted_contests=1,
        provider_payload_count=1,
        contest_ids=[3700],
        db_backend="sqlite",
        engine_url="sqlite://",
        commit_state="ok",
        source="caixa",
    )

    class _FakeService:
        client = SimpleNamespace(
            last_http_status=200,
            last_request_url="",
            last_request_headers={},
            last_response_headers={},
            last_response_preview="",
        )

        def sync_latest(self) -> ResultSyncSummary:
            return summary

    class _FakeRepository:
        def sync_official_history_from_imported_contests(self) -> int:
            return 1

        def get_latest_contest_record(self) -> dict[str, object]:
            return {"contest_number": 3700, "dezenas": list(range(1, 16))}

        def get_all_contests(self) -> list[dict[str, object]]:
            return []

    monkeypatch.setattr(admin_app, "ContestRepository", lambda _path: _FakeRepository())
    monkeypatch.setattr(admin_app, "ResultSyncService", lambda repository: _FakeService())
    monkeypatch.setattr(admin_app, "_persist_official_sync_diagnostics", lambda _payload: None)
    monkeypatch.setattr(admin_app, "export_historical_csv", lambda _contests: None)

    payload = admin_app._sync_latest_official_result_now()
    assert payload["status"] == "ok"
    assert payload.get("sync_error") == ""


def test_get_latest_contest_is_db_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3701, "dezenas": list(range(1, 16)), "data": "01/06/2026"},
    )
    monkeypatch.setattr(admin_app, "_load_official_sync_contest_summary", lambda: None)
    monkeypatch.setattr(admin_app, "_load_imported_contest", lambda *_args, **_kwargs: None)

    result = admin_app._get_latest_contest()
    assert result is not None
    assert int(result.get("contest_number", 0) or 0) == 3701


def test_resolve_institutional_check_result_prefers_db(monkeypatch: pytest.MonkeyPatch) -> None:
    db_result = {
        "status": "checked",
        "source": "reconciliation_runs",
        "generation_results": [{"generation_event_id": 42, "results": []}],
        "contest_number": 3700,
        "best_hits": 13,
        "total_hits": 100,
        "prize_count": 2,
    }
    monkeypatch.setattr(admin_app, "_load_institutional_check_result_from_db", lambda **_: db_result)

    class _SessionState(dict):
        def get(self, key, default=None):
            return super().get(key, default)

    monkeypatch.setattr(
        admin_app.st,
        "session_state",
        _SessionState(
            {
                "institutional_check_result": {
                    "status": "checked",
                    "contest_number": 1,
                    "generation_results": [],
                }
            }
        ),
    )

    resolved = admin_app._resolve_institutional_check_result(generation_event_id=42)
    assert resolved is not None
    assert resolved.get("source") == "reconciliation_runs"
    assert resolved.get("contest_number") == 3700


def test_load_institutional_check_result_from_db_builds_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    run = SimpleNamespace(
        id=7,
        generation_event_id=42,
        contest_id=3700,
        best_hits=12,
        total_hits=180,
        prize_count=1,
        created_at=None,
    )
    game_row = SimpleNamespace(
        game_index=1,
        numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        hits=12,
        matched_numbers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        prize_status="premiado",
        prize_tier="faixa_12",
        context_json={},
    )
    event = SimpleNamespace(seed=99, created_at=None)

    session = MagicMock()
    session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = [run]
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [game_row]
    session.get.return_value = event

    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    monkeypatch.setattr(admin_app, "get_session", lambda _path: session_cm)
    official_row = SimpleNamespace(
        contest_number=3700,
        numbers="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
        draw_date="01/06/2026",
        numbers_signature="sig",
        source="caixa",
        is_valid=1,
        imported_at=None,
        validated_at=None,
    )
    session.query.return_value.filter.return_value.limit.return_value.one_or_none.return_value = official_row

    loaded = admin_app._load_institutional_check_result_from_db(generation_event_id=42)
    assert loaded is not None
    assert loaded["source"] == "reconciliation_runs"
    assert loaded["generation_results"][0]["generation_event_id"] == 42
    assert loaded["generation_results"][0]["results"][0]["origem_dezenas_conferencia"] == "cartao_final"
