from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_clean_law15_runtime as clean_runtime
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label
from lotoia.governance.m_ger_dados_051_controlled_ge_removal import resolve_authorized_target_ids


def test_build_marker_v28() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v32"


def test_persist_blocked_when_commander_rejects() -> None:
    result = {
        "games": [{"numbers": list(range(1, 16)), "final_score": {}}],
        "requested_count": 1,
        "commander_report": {
            "status_comandante_saida": "BLOQUEADO",
            "motivo_bloqueio": "duplicidade_na_bateria",
        },
    }
    snapshot = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )
    assert snapshot.get("persistence_blocked") is True
    assert "duplicidade" in str(snapshot.get("persistence_guard_status") or "")


@pytest.mark.parametrize("card_format", list(range(15, 24)))
def test_multidezena_persistence_supported_15_to_23(card_format: int) -> None:
    assert clean_runtime.is_multidezena_persistence_supported(card_format) is True


def test_multidezena_batch_labels_core_002_derived() -> None:
    assert resolve_core_002_batch_label(15) == "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
    assert resolve_core_002_batch_label(17) == "STRUCT_LEI15_CORE_CANDIDATE_002_17D_001"
    assert resolve_core_002_batch_label(23) == "STRUCT_LEI15_CORE_CANDIDATE_002_23D_001"


def test_ge_1115_divergence_preserves_115() -> None:
    authorized, notes = resolve_authorized_target_ids([114], ge_115_exists=True)
    assert authorized == [114]
    assert notes.get("ge_115_preserved_pending_confirmation") is True
    assert "1115" in str(notes.get("divergence") or "")


def test_validate_multidezena_persistence_guard() -> None:
    games = institutional_app._expand_generation_games_for_format(
        [{"numbers": list(range(1, 16))}],
        17,
    )
    contract = institutional_app._validate_core_002_multidezena_persistence_allowed(
        formatted_games=games,
        selected_card_format=17,
    )
    assert contract.get("persistence_allowed") is True


def test_persist_multidezena_uses_final_card_numbers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "multi.db"
    captured: dict[str, object] = {}

    def _fake_persist(**kwargs):
        captured.update(kwargs)
        games = list(kwargs.get("games") or [])
        return {
            "generation_event_id": 901,
            "games_count": len(games),
            "analysis_batch_label": kwargs.get("analysis_batch_label"),
        }

    monkeypatch.setattr(institutional_app, "DB_PATH", db_path)
    monkeypatch.setattr(institutional_app, "_persist_generation_snapshot", _fake_persist)
    monkeypatch.setattr(
        institutional_app,
        "_load_latest_contest_summary",
        lambda: {"contest_number": 3712},
    )
    monkeypatch.setattr(
        institutional_app,
        "build_supervised_ml_persistence_bundle",
        lambda games, **kw: {"decision_trace": [], "feature_attribution": [], "generation_lineage": []},
    )

    result = {
        "games": [{"numbers": list(range(1, 16)), "final_score": {}}],
        "requested_count": 1,
        "ml_enabled": True,
        "analysis_batch_label": resolve_core_002_batch_label(17),
    }
    snapshot = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=17,
    )
    assert snapshot.get("generation_event_id") == 901
    games = list(captured.get("games") or [])
    assert len(games[0]["numbers"]) == 17
    assert captured.get("analysis_batch_label") == "STRUCT_LEI15_CORE_CANDIDATE_002_17D_001"


def test_analytical_row_includes_batch_label_and_format() -> None:
    row = institutional_app._analytical_row_from_game(
        generation={
            "generation_event_id": 42,
            "created_at": "2026-06-18T00:00:00+00:00",
            "strategy": "institutional_clean_hb",
            "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_002_17D_001",
            "ml_enabled": True,
            "status_comandante_saida": "APROVADO",
            "is_conferible": True,
        },
        game={
            "game_index": 1,
            "numbers": list(range(1, 18)),
            "score": 0.5,
            "origin": "institutional",
            "generation_context": {
                "selected_card_format": 17,
                "core_numbers": list(range(1, 16)),
                "audited_reserve_numbers": [16, 17],
                "final_card_numbers": list(range(1, 18)),
                "quantidade_final": 17,
            },
        },
        operational_index={42: 1},
    )
    assert row["formato_cartao"] == 17
    assert row["analysis_batch_label"] == "STRUCT_LEI15_CORE_CANDIDATE_002_17D_001"
    assert row["ml_enabled"] is True
    assert len(row["dezenas"].split()) == 17
