from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from lotoia.database.database import GenerationEvent, create_database, get_session
from lotoia.governance.analysis_batch_labels import build_batch_metadata

from dashboard.institutional_app import _coerce_analysis_batch_created_at, _persist_generation_snapshot


def test_persist_generation_snapshot_sanitizes_struct_test_batch_metadata(monkeypatch) -> None:
    db_path = Path("data/test_generation_event_json_safe_origin.db")
    if db_path.exists():
        db_path.unlink()
    create_database(db_path)
    monkeypatch.setattr("dashboard.institutional_app.DB_PATH", db_path, raising=False)

    batch_metadata = build_batch_metadata(
        "STRUCT_TEST_15D",
        game_size=15,
        created_by="ops/run_structural_test_15d",
    )
    games = [{"numbers": list(range(1, 16)), "profile_type": "HYBRID"}]

    snapshot = _persist_generation_snapshot(
        games=games,
        seed=1,
        target_contest=3707,
        batch_id="struct-test-15d",
        generation_context={
            **batch_metadata,
            "selected_15_group": "G50",
            "total_games": 50,
        },
        analysis_batch_label=batch_metadata.get("analysis_batch_label"),
        analysis_batch_type=batch_metadata.get("analysis_batch_type"),
        analysis_batch_created_by=batch_metadata.get("analysis_batch_created_by"),
        analysis_batch_created_at=_coerce_analysis_batch_created_at(
            batch_metadata.get("analysis_batch_created_at")
        ),
    )

    with get_session(db_path) as session:
        event = session.query(GenerationEvent).filter(GenerationEvent.id == snapshot["generation_event_id"]).one()

    json.dumps(event.context_json)
    json.dumps(event.generated_games)
    assert event.context_json["analysis_batch_label"] == "STRUCT_TEST_15D"
    assert isinstance(event.context_json["analysis_batch_created_at"], str)
    assert event.analysis_batch_created_at is not None

    if db_path.exists():
        db_path.unlink()
