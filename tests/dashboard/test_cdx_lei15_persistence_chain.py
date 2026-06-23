"""CDX — cadeia completa de persistência Lei 15 CORE_002 (15D, institucional)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL

import dashboard.institutional_app as institutional_app


@pytest.fixture
def sqlite_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "cdx_lei15_persistence.db"
    create_database(db_path)
    monkeypatch.setattr(institutional_app, "DB_PATH", db_path)
    monkeypatch.setattr(institutional_app.st, "session_state", {})
    monkeypatch.setattr(
        institutional_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(
        institutional_app,
        "_build_generation_previous_contest_context",
        lambda target: {
            "previous_contest_numbers": list(range(1, 16)),
            "rfe_previous_contest_found": True,
            "rfe_previous_contest_id": int(target or 3701) - 1,
            "rfe_previous_contest_numbers": " ".join(f"{n:02d}" for n in range(1, 16)),
            "rfe_previous_contest_message": "",
            "rfe_previous_contest_source": "official_lotofacil_history",
            "rfe_status": "OK",
        },
    )
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )
    return db_path


def _distinct_core_games(count: int) -> list[dict]:
    games: list[dict] = []
    for index in range(count):
        core = sorted((((number + index) % 25) + 1) for number in range(1, 16))
        games.append(
            {
                "numbers": core,
                "profile_type": "HYBRID",
                "generation_path": "LEI15_CORE_002",
            }
        )
    return games


def test_lei15_persistence_chain_with_manual_target_contest(
    sqlite_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    user_target = 3695
    games = _distinct_core_games(10)

    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": games,
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": False,
            "analysis_batch_label": BATCH_LABEL,
        },
    )

    result = institutional_app._run_clean_law15_generation(
        requested_count=10,
        selected_card_format=15,
        user_target_contest=user_target,
    )
    assert len(result.get("games") or []) == 10
    assert result["target_contest"] == user_target
    assert result["user_target_contest"] == user_target
    assert result["user_selected_target"] is True

    result["selected_card_format"] = 15
    persisted = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )

    assert not persisted.get("persistence_blocked"), persisted.get(
        "persistence_guard_status"
    )
    event_id = int(persisted["generation_event_id"])
    assert event_id > 0
    assert int(persisted["games_count"]) == 10
    assert persisted["target_contest"] == user_target
    assert persisted["user_target_contest"] == user_target
    assert persisted["user_selected_target"] is True

    with get_session(sqlite_db) as session:
        event = session.get(GenerationEvent, event_id)
        assert event is not None
        ctx = dict(event.context_json or {})
        json.dumps(ctx)
        games_count = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == event_id)
            .count()
        )
        sample = (
            session.query(GeneratedGame)
            .filter(GeneratedGame.generation_event_id == event_id)
            .first()
        )

    assert games_count == 10
    assert ctx.get("target_contest") == user_target
    assert ctx.get("user_target_contest") == user_target
    assert ctx.get("user_selected_target") is True
    assert ctx.get("generation_mode") == "LEI15_CORE_002_SOVEREIGN"
    assert sample is not None
    assert int(sample.target_contest) == user_target

    groups = institutional_app._load_persisted_generation_event_groups(
        generation_event_id=event_id,
        use_cache=False,
    )
    assert groups
    assert int(groups[0]["total_games"]) == 10
    assert int(groups[0]["target_contest"]) == user_target

    history = institutional_app._load_generation_history(limit=5)
    assert any(int(row["generation_event_id"]) == event_id for row in history)


def test_lei15_persistence_chain_automatic_target_contest(
    sqlite_db: Path,
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    games = _distinct_core_games(10)
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": games,
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": False,
            "analysis_batch_label": BATCH_LABEL,
        },
    )

    result = institutional_app._run_clean_law15_generation(
        requested_count=10,
        selected_card_format=15,
        user_target_contest=None,
    )
    assert result["target_contest"] == 3701
    assert result["user_selected_target"] is False

    persisted = institutional_app._persist_clean_law15_generation_history(
        result={**result, "selected_card_format": 15},
        selected_card_format=15,
    )
    assert int(persisted["generation_event_id"]) > 0
    assert persisted["target_contest"] == 3701
    assert persisted.get("user_selected_target") is False
