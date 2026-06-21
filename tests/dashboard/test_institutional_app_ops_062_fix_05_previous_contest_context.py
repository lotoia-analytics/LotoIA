"""M-OPS-062-FIX-05 — concurso anterior injetado no caminho soberano para promoção parcial."""

from __future__ import annotations

import pytest

from dashboard import institutional_app as admin_app
from lotoia.governance.structural_rfe import RFEPreviousContestReference
from lotoia.operations.partial_game_promotion import GAME_QUALITY_ACCEPTABLE

_POLICY_PREVIOUS = sorted([2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 1, 3, 5])
_POLICY_COMPLIANT_GAME = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]


def _previous_reference(contest_id: int = 3716) -> RFEPreviousContestReference:
    return RFEPreviousContestReference(
        found=True,
        contest_id=contest_id,
        numbers=list(_POLICY_PREVIOUS),
        source="official_lotofacil_history",
        message=None,
    )


def test_build_generation_previous_contest_context_from_rfe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_previous_contest_numbers_for_rfe",
        lambda target: _previous_reference(int(target or 0) - 1),
    )
    ctx = admin_app._build_generation_previous_contest_context(3717)
    assert ctx["rfe_previous_contest_found"] is True
    assert ctx["previous_contest_numbers"] == list(_POLICY_PREVIOUS)
    assert ctx["rfe_previous_contest_id"] == 3716
    assert "01 02 03" in str(ctx["rfe_previous_contest_numbers"])


def test_sovereign_generation_result_carries_previous_contest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "0")
    monkeypatch.setattr(
        admin_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3716, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(admin_app, "_load_previous_contest_numbers_for_rfe", lambda _t: _previous_reference())
    monkeypatch.setattr(
        admin_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002"}],
            "generation_path": "LEI15_CORE_002",
        },
    )
    monkeypatch.setattr(admin_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        admin_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )
    monkeypatch.setattr(admin_app.st, "session_state", {})

    result = admin_app._run_clean_law15_generation(requested_count=1)

    assert result["target_contest"] == 3717
    assert result["rfe_previous_contest_found"] is True
    assert list(result["previous_contest_numbers"]) == list(_POLICY_PREVIOUS)
    assert result["rfe_status"] == "OK"
    assert "not_applicable_sovereign_path" not in str(result.get("rfe_previous_contest_source") or "")


def test_persist_partial_promotion_uses_previous_contest_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_persist(**kwargs):
        captured.update(kwargs)
        return {"generation_event_id": 1001, "games_count": 1}

    monkeypatch.setattr(admin_app, "_persist_generation_snapshot", _fake_persist)
    monkeypatch.setattr(admin_app, "_attach_operational_generation_label", lambda snapshot: snapshot)
    monkeypatch.setattr(
        admin_app,
        "validate_lei15_lei15a_runtime_contract",
        lambda **kwargs: {"persistence_allowed": True},
    )
    monkeypatch.setattr(admin_app, "get_latest_official_contest", lambda: {"contest_number": 3716, "dezenas": list(range(1, 16))})
    monkeypatch.setattr(admin_app, "_load_previous_contest_numbers_for_rfe", lambda _t: _previous_reference())
    monkeypatch.setattr(admin_app.st, "session_state", {})

    games = [{"numbers": list(_POLICY_COMPLIANT_GAME), "final_card_numbers": list(_POLICY_COMPLIANT_GAME), "game_index": 1}]
    result = {
        "games": games,
        "requested_count": 1,
        "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
        "ml_enabled": False,
        "seed": 7,
        "batch_id": "prev-ctx-smoke",
        "target_contest": 3717,
        "previous_contest_numbers": list(_POLICY_PREVIOUS),
        "rfe_previous_contest_found": True,
        "rfe_previous_contest_id": 3716,
        "rfe_previous_contest_numbers": " ".join(f"{n:02d}" for n in _POLICY_PREVIOUS),
        "rfe_previous_contest_source": "official_lotofacil_history",
        "rfe_status": "OK",
        "commander_report": {"status_comandante_saida": "APROVADO"},
        "fill_diagnostics": {"fill_completed": True, "accepted_games": 1},
    }

    persisted = admin_app._persist_clean_law15_generation_history(result=result, selected_card_format=15)

    assert persisted.get("generation_event_id") == 1001
    ctx = dict(captured.get("generation_context") or {})
    assert list(ctx.get("previous_contest_numbers") or []) == list(_POLICY_PREVIOUS)
    assert int(ctx.get("games_promoted_to_conference", 0) or 0) >= 1
    snapshot_games = list(captured.get("games") or [])
    assert snapshot_games
    assert str(snapshot_games[0].get("game_quality_status") or "") == GAME_QUALITY_ACCEPTABLE
