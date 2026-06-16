from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session

from dashboard.institutional_app import _json_safe, _persist_generation_snapshot


def test_json_safe_converts_non_serializable_types() -> None:
    created_at = datetime(2026, 6, 16, 12, 30, tzinfo=UTC)
    payload = {
        "created_at": created_at,
        "draw_date": date(2026, 6, 16),
        "score": Decimal("12.50"),
        "batch_id": UUID("12345678-1234-5678-1234-567812345678"),
        "tags": {"tuple_key": (1, 2), "set_values": {3, 4}},
        "items": [{"nested": created_at}],
    }

    sanitized = _json_safe(payload)

    json.dumps(sanitized)
    assert sanitized["created_at"] == created_at.isoformat()
    assert sanitized["draw_date"] == "2026-06-16"
    assert sanitized["score"] == 12.5
    assert sanitized["batch_id"] == "12345678-1234-5678-1234-567812345678"
    assert sanitized["tags"]["tuple_key"] == [1, 2]
    assert sorted(sanitized["tags"]["set_values"]) == [3, 4]
    assert sanitized["items"][0]["nested"] == created_at.isoformat()


def test_persist_generation_snapshot_sanitizes_datetime_in_json_fields(monkeypatch) -> None:
    db_path = Path("data/test_generation_event_json_safe.db")
    if db_path.exists():
        db_path.unlink()
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)

    created_at = datetime(2026, 6, 16, 4, 33, 3, tzinfo=UTC)
    games = [
        {
            "numbers": list(range(1, 16)),
            "profile_type": "HYBRID",
            "final_score": {"total": Decimal("1.25")},
            "diagnostic_at": created_at,
        }
    ]
    generation_context = {
        "analysis_batch_label": "STRUCT_TEST_15D",
        "analysis_batch_type": "STRUCTURAL_COVERAGE_TEST",
        "analysis_batch_created_by": "ops/run_structural_test_15d",
        "analysis_batch_created_at": created_at,
        "operational_effect": False,
        "selected_15_group": "G50",
        "total_games": 50,
    }

    snapshot = _persist_generation_snapshot(
        games=games,
        seed=621977,
        target_contest=3707,
        batch_id="struct-test-15d-sample",
        generation_context=generation_context,
    )

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == snapshot["generation_event_id"]).one()
        generated_game = session.query(GeneratedGame).filter(GeneratedGame.generation_event_id == event.id).one()

    assert event.context_json["analysis_batch_label"] == "STRUCT_TEST_15D"
    assert event.context_json["analysis_batch_created_at"] == created_at.isoformat()
    assert isinstance(event.generated_games[0]["diagnostic_at"], str)
    assert event.generated_games[0]["final_score"]["total"] == 1.25

    json.dumps(event.context_json)
    json.dumps(event.generated_games)
    json.dumps(generated_game.context_json)

    assert "datetime" not in json.dumps(event.context_json)
    assert "datetime" not in json.dumps(event.generated_games)

    if db_path.exists():
        db_path.unlink()
