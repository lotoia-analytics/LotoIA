"""M-OPS-078-FIX-02 — Conferir Resultados respeita promoção parcial por jogo."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.operations.partial_game_promotion import (
    GAME_QUALITY_CRITICAL,
    apply_partial_promotion_to_payload_games,
    filter_conference_games,
)
from tests.operations.test_m_ops_078_partial_game_promotion import (
    _build_thirty_game_lot,
    _lot_context_with_policy,
    _mock_policy_audit,
    _policy_compliant_previous,
    _rejected_lot_context,
)


@pytest.fixture
def mock_policy_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lotoia.operations.partial_game_promotion.analyze_batch_structural_policy_15d",
        _mock_policy_audit,
    )


def _enriched_rejected_lot() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    games = _build_thirty_game_lot()
    enriched, patch = apply_partial_promotion_to_payload_games(
        games,
        generation_context=_lot_context_with_policy(generation_event_id=47),
        card_format=15,
        previous_contest_numbers=_policy_compliant_previous(),
    )
    return enriched, patch


def test_prepare_conference_group_accepts_rejected_lot_with_promoted_games(
    mock_policy_audit: None,
) -> None:
    enriched, patch = _enriched_rejected_lot()
    group = {
        "generation_event_id": 47,
        "context_json": {**_lot_context_with_policy(generation_event_id=47), **patch},
        "official_release_allowed": False,
        "is_official_conference_eligible": False,
        "games_promoted_to_conference": int(patch["games_promoted_to_conference"]),
        "games": enriched,
    }
    prepared = institutional_app._prepare_conference_group(group)
    assert prepared is not None
    assert int(prepared["generation_event_id"]) == 47
    assert len(prepared["games"]) == 27
    assert prepared["partial_conference_games"] is True
    assert all(game["game_quality_status"] != GAME_QUALITY_CRITICAL for game in prepared["games"])


def test_is_group_conference_selectable_without_whole_lot_approval(
    mock_policy_audit: None,
) -> None:
    enriched, patch = _enriched_rejected_lot()
    group = {
        "generation_event_id": 47,
        "context_json": {**_lot_context_with_policy(generation_event_id=47), **patch},
        "official_release_allowed": False,
        "is_official_conference_eligible": False,
        "games_promoted_to_conference": int(patch["games_promoted_to_conference"]),
        "games": enriched,
    }
    assert institutional_app._is_group_conference_selectable(group, page_load=True) is True
    assert institutional_app._is_group_conference_selectable(group, page_load=False) is True


def test_prepare_conference_group_excludes_critical_games(mock_policy_audit: None) -> None:
    enriched, patch = _enriched_rejected_lot()
    generation = {"context_json": {**_lot_context_with_policy(generation_event_id=47), **patch}}
    selected = filter_conference_games(generation, enriched)
    prepared = institutional_app._prepare_conference_group(
        {
            "generation_event_id": 47,
            "context_json": generation["context_json"],
            "games": enriched,
        }
    )
    assert prepared is not None
    assert len(prepared["games"]) == len(selected) == 27
    assert GAME_QUALITY_CRITICAL not in {game["game_quality_status"] for game in prepared["games"]}


def test_prepare_conference_group_returns_none_when_no_eligible_games() -> None:
    games = [
        {
            "game_index": 1,
            "numbers": list(range(1, 16)),
            "game_quality_status": GAME_QUALITY_CRITICAL,
            "game_conference_eligible": False,
            "context_json": {
                "game_quality_status": GAME_QUALITY_CRITICAL,
                "game_conference_eligible": False,
            },
        }
    ]
    group = {
        "generation_event_id": 99,
        "context_json": {
            **_rejected_lot_context(generation_event_id=99),
            "partial_promotion_enabled": True,
            "games_promoted_to_analytical": 1,
            "games_promoted_to_conference": 0,
        },
        "games": games,
    }
    assert institutional_app._prepare_conference_group(group) is None


def test_run_institutional_conference_does_not_gate_by_whole_lot_only() -> None:
    source = inspect.getsource(institutional_app._run_institutional_conference)
    assert "_prepare_conference_group" in source
    assert 'if bool(group.get("is_official_conference_eligible"' not in source


def test_run_institutional_conference_warns_when_analytical_without_conference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(institutional_app.st, "session_state", {}, raising=False)
    monkeypatch.setattr(
        institutional_app,
        "_resolve_latest_official_conference_contest",
        lambda: {"concurso": 3500, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(
        institutional_app,
        "_get_conference_contest_from_imported",
        lambda _: {"concurso": 3500, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(institutional_app, "_is_valid_conference_contest", lambda _: True)
    monkeypatch.setattr(
        institutional_app,
        "_load_persisted_generation_event_groups",
        lambda **_: [
            {
                "generation_event_id": 47,
                "context_json": {
                    **_rejected_lot_context(generation_event_id=47),
                    "partial_promotion_enabled": True,
                    "games_promoted_to_analytical": 3,
                    "games_promoted_to_conference": 0,
                },
                "games": [
                    {
                        "game_index": 1,
                        "numbers": list(range(1, 16)),
                        "game_quality_status": GAME_QUALITY_CRITICAL,
                        "game_conference_eligible": False,
                        "context_json": {
                            "game_quality_status": GAME_QUALITY_CRITICAL,
                            "game_conference_eligible": False,
                        },
                    }
                ],
            }
        ],
    )

    institutional_app._run_institutional_conference(generation_event_id=47)
    result = institutional_app.st.session_state.get("institutional_check_result") or {}
    assert "Histórico Analítico" in str(result.get("warning", ""))


def test_run_institutional_conference_uses_only_eligible_games(
    monkeypatch: pytest.MonkeyPatch,
    mock_policy_audit: None,
) -> None:
    enriched, patch = _enriched_rejected_lot()
    compared_games: list[list[dict[str, Any]]] = []

    def _capture_compare(*, generation_event_id: int, games: list[dict[str, Any]], contest: dict[str, Any]) -> dict[str, Any]:
        _ = generation_event_id, contest
        compared_games.append(list(games))
        return {
            "contest_number": 3500,
            "best_hits": 0,
            "total_hits": 0,
            "prize_count": 0,
            "results": [{"hits": 0} for _ in games],
            "diagnostics": {},
        }

    monkeypatch.setattr(institutional_app.st, "session_state", {}, raising=False)
    monkeypatch.setattr(
        institutional_app,
        "_resolve_latest_official_conference_contest",
        lambda: {"concurso": 3500, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(
        institutional_app,
        "_get_conference_contest_from_imported",
        lambda _: {"concurso": 3500, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(institutional_app, "_is_valid_conference_contest", lambda _: True)
    monkeypatch.setattr(
        institutional_app,
        "_load_persisted_generation_event_groups",
        lambda **_: [
            {
                "generation_event_id": 47,
                "context_json": {**_lot_context_with_policy(generation_event_id=47), **patch},
                "official_release_allowed": False,
                "is_official_conference_eligible": False,
                "games_promoted_to_conference": 27,
                "games": enriched,
                "batch_id": "GE-47",
                "seed": 1,
                "created_at": "2026-06-20T12:00:00",
            }
        ],
    )
    monkeypatch.setattr(institutional_app, "_compare_games_against_contest", _capture_compare)
    monkeypatch.setattr(
        institutional_app,
        "discover_scientific_generation_policy",
        lambda *args, **kwargs: {"policy": {}, "policy_before": {}, "policy_after": {}},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_post_reconciliation_scientific_memory",
        lambda **kwargs: {"memory": True},
    )
    monkeypatch.setattr(institutional_app, "_persist_scientific_reconciliation_memory", lambda payload: payload)
    monkeypatch.setattr(
        institutional_app,
        "persist_generation_event_conference_mark",
        lambda **kwargs: None,
    )

    institutional_app._run_institutional_conference(generation_event_id=47, contest_number=3500)
    assert compared_games
    assert len(compared_games[0]) == 27
    assert all(game["game_quality_status"] != GAME_QUALITY_CRITICAL for game in compared_games[0])
    assert institutional_app.st.session_state.get("active_reconciliation_generation_event_id") == 47


def test_official_conference_loader_uses_prepare_helper() -> None:
    source = inspect.getsource(institutional_app._load_official_conference_generation_groups)
    assert "_prepare_conference_group" in source
    assert "_is_group_conference_selectable" in source


def test_build_marker_unchanged_for_hotfix() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v84"


def test_governance_contract_check_passes() -> None:
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "checks" / "governance_contract_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
