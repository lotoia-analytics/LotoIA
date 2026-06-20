"""M-OPS-078-FIX-01 — event_context antes do loop em _load_generation_history."""

from __future__ import annotations

from pathlib import Path

import pytest

import dashboard.institutional_app as institutional_app
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session


@pytest.fixture
def history_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "m_ops_078_fix_01.db"
    create_database(db_path)
    monkeypatch.setattr(institutional_app, "DB_PATH", db_path)
    monkeypatch.setattr(institutional_app, "_load_scientific_context_indexes", lambda: ({}, {}))
    return db_path


def test_load_generation_history_light_with_games(history_db: Path) -> None:
    with get_session(history_db) as session:
        event = GenerationEvent(
            seed=1,
            strategy="test",
            ml_enabled=0,
            generated_games=[{"numbers": list(range(1, 16))}],
            ranking_score=0.0,
            execution_time_ms=0.0,
            context_json={
                "batch_id": "FIX-01",
                "lot_operational_status": "rejected",
                "partial_promotion_enabled": True,
                "ml_verdict": "REPROVADO",
            },
        )
        session.add(event)
        session.flush()
        session.add(
            GeneratedGame(
                generation_event_id=int(event.id or 0),
                game_index=1,
                numbers=list(range(1, 16)),
                origin="institutional",
                generation_mode="hb_baseline",
                context_json={
                    "game_quality_status": "acceptable",
                    "game_analytical_eligible": True,
                    "game_conference_eligible": True,
                },
            )
        )
        session.commit()

    rows = institutional_app._load_generation_history_light(limit=1)
    assert len(rows) == 1
    assert rows[0]["games"][0]["game_quality_status"] == "acceptable"
    assert rows[0]["context_json"]["batch_id"] == "FIX-01"


def test_load_generation_history_event_without_games(history_db: Path) -> None:
    with get_session(history_db) as session:
        session.add(
            GenerationEvent(
                seed=2,
                strategy="empty",
                ml_enabled=0,
                generated_games=[],
                ranking_score=0.0,
                execution_time_ms=0.0,
                context_json={"batch_id": "FIX-01-EMPTY"},
            )
        )
        session.commit()

    rows = institutional_app._load_generation_history(limit=1)
    assert len(rows) == 1
    assert rows[0]["total_games"] == 0
    assert rows[0]["games"] == []
    assert rows[0]["context_json"]["batch_id"] == "FIX-01-EMPTY"


def test_accumulated_analytical_rows_do_not_raise(history_db: Path) -> None:
    with get_session(history_db) as session:
        event = GenerationEvent(
            seed=3,
            strategy="analytical",
            ml_enabled=0,
            generated_games=[{"numbers": list(range(1, 16))}],
            ranking_score=0.0,
            execution_time_ms=0.0,
            context_json={
                "lot_operational_status": "rejected",
                "partial_promotion_enabled": True,
                "ml_verdict": "REPROVADO",
            },
        )
        session.add(event)
        session.flush()
        session.add(
            GeneratedGame(
                generation_event_id=int(event.id or 0),
                game_index=1,
                numbers=list(range(1, 16)),
                origin="institutional",
                generation_mode="hb_baseline",
                context_json={
                    "game_quality_status": "acceptable",
                    "game_analytical_eligible": True,
                },
            )
        )
        session.commit()

    rows = institutional_app._load_accumulated_analytical_rows_light(limit=1)
    assert isinstance(rows, list)
