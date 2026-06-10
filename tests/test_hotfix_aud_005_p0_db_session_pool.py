from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dashboard import institutional_app as admin_app


def test_load_official_history_contest_with_session_reuses_injected_session() -> None:
    row = SimpleNamespace(
        contest_number=3700,
        numbers="01 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
        draw_date="01/06/2026",
        numbers_signature="sig",
        source="caixa",
        is_valid=1,
        imported_at=None,
        validated_at=None,
    )
    session = MagicMock()
    session.query.return_value.filter.return_value.limit.return_value.one_or_none.return_value = row

    result = admin_app._load_official_history_contest_with_session(session, 3700)
    assert result is not None
    assert result["concurso"] == 3700
    assert len(result["dezenas"]) == 15
    session.query.assert_called_once()


def test_load_institutional_check_result_uses_single_db_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    session = MagicMock()
    session.query.return_value.order_by.return_value.filter.return_value.limit.return_value.all.return_value = [run]
    session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [game_row]
    session.get.return_value = event

    def _official_history_query(*_args, **_kwargs):
        query = MagicMock()
        query.filter.return_value.limit.return_value.one_or_none.return_value = official_row
        return query

    session.query.side_effect = lambda model: (
        _official_history_query()
        if model is admin_app.LotofacilOfficialHistory
        else MagicMock(
            order_by=MagicMock(
                return_value=MagicMock(
                    filter=MagicMock(
                        return_value=MagicMock(
                            limit=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[run])))
                        )
                    )
                )
            ),
            filter=MagicMock(
                return_value=MagicMock(
                    order_by=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[game_row])))
                )
            ),
        )
    )

    session_entries: list[int] = []

    def _tracked_get_session(_path):
        session_entries.append(1)
        session_cm = MagicMock()
        session_cm.__enter__.return_value = session
        session_cm.__exit__.return_value = False
        return session_cm

    monkeypatch.setattr(admin_app, "get_session", _tracked_get_session)

    def _forbidden_nested_contest_loader(_contest_number):
        raise AssertionError("_load_official_history_contest must not open nested session")

    monkeypatch.setattr(admin_app, "_load_official_history_contest", _forbidden_nested_contest_loader)

    loaded = admin_app._load_institutional_check_result_from_db(generation_event_id=42)
    assert loaded is not None
    assert loaded["source"] == "reconciliation_runs"
    assert loaded["contest_number"] == 3700
    assert len(loaded["dezenas"]) == 15
    assert len(session_entries) == 1


def test_conference_page_reload_does_not_open_nested_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_result = {
        "status": "checked",
        "source": "reconciliation_runs",
        "contest_number": 3700,
        "contest_date": "01/06/2026",
        "dezenas": list(range(1, 16)),
        "generation_results": [
            {
                "generation_event_id": 42,
                "results": [
                    {
                        "game_index": 1,
                        "hits": 12,
                        "matched_numbers": list(range(1, 13)),
                        "prize_status": "premiado",
                        "cartao_final": list(range(1, 16)),
                    }
                ],
            }
        ],
        "best_hits": 12,
        "total_hits": 12,
        "prize_count": 1,
        "formato_cartao": 15,
        "dezenas_conferidas_count": 15,
        "origem_dezenas_conferencia": "cartao_final",
        "expected_card_size": 15,
        "actual_card_size": 15,
        "results": [],
    }

    session_entries: list[int] = []

    def _tracked_get_session(_path):
        session_entries.append(1)
        session_cm = MagicMock()
        session_cm.__enter__.return_value = MagicMock()
        session_cm.__exit__.return_value = False
        return session_cm

    monkeypatch.setattr(admin_app, "get_session", _tracked_get_session)
    monkeypatch.setattr(
        admin_app,
        "_load_institutional_check_result_from_db",
        lambda **_: db_result,
    )

    resolved = admin_app._resolve_institutional_check_result(generation_event_id=42)
    assert resolved is not None
    assert resolved.get("source") == "reconciliation_runs"
    assert len(session_entries) == 0
