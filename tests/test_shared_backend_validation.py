from __future__ import annotations

from pathlib import Path

import dashboard.admin_app as admin_app
import dashboard.user_app as user_app
from lotoia.database.adapter import resolve_institutional_adapter
from lotoia.database.database import create_database
from lotoia.database.public_repository import (
    save_check_event,
    save_expansion_event,
    save_generation_event,
    save_lead,
    save_reconciliation_event,
    save_report_event,
)


def test_shared_institutional_backend_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "shared_institutional.db"
    create_database(db_path)

    lead = save_lead(
        first_name="Maria Divina",
        whatsapp="65998895555",
        source="user",
        ip_hash="hash",
        user_agent="pytest",
        db_path=db_path,
    )

    generation = save_generation_event(
        lead_id=lead["id"],
        generated_games=[{"numbers": list(range(1, 16)), "profile_type": "balanced"}],
        ml_enabled=True,
        seed=42,
        strategy="shared_validation",
        ranking_score=91.5,
        execution_time_ms=7.5,
        target_contest=3691,
        origin="user",
        generation_mode="institutional_validation",
        context={"source": "phase_4_validation"},
        first_name="Maria Divina",
        whatsapp="65998895555",
        db_path=db_path,
    )

    check = save_check_event(
        lead_id=lead["id"],
        contest_id=3691,
        selected_numbers=list(range(1, 16)),
        hits=15,
        result_payload={"contest_id": 3691, "hits": 15},
        db_path=db_path,
    )

    report = save_report_event(
        lead_id=lead["id"],
        generation_event_id=generation["id"],
        report_type="usage_summary",
        generation_origin="user",
        runtime_origin="cloud",
        strategy_profile="balanced",
        payload={"source": "phase_4_validation"},
        db_path=db_path,
    )

    expansion = save_expansion_event(
        lead_id=lead["id"],
        generation_event_id=generation["id"],
        expansion_type="operational",
        expansion_size=5,
        runtime_origin="cloud",
        strategy_profile="balanced",
        payload={"source": "phase_4_validation"},
        db_path=db_path,
    )

    reconciliation = save_reconciliation_event(
        lead_id=lead["id"],
        generation_event_id=generation["id"],
        reconciliation_type="operational",
        hits=15,
        matched_numbers=list(range(1, 16)),
        runtime_origin="cloud",
        payload={"source": "phase_4_validation"},
        db_path=db_path,
    )

    adapter = resolve_institutional_adapter(db_path)
    metrics = adapter.fetch_usage_metrics()
    snapshot = adapter.fetch_latest_usage_snapshot()
    generation_events = adapter.fetch_generation_events(lead_id=lead["id"])

    assert metrics["leads"] == 1
    assert metrics["generation_events"] == 1
    assert metrics["ml_usage_events"] == 1
    assert metrics["check_events"] == 1
    assert metrics["report_events"] == 1
    assert metrics["expansion_events"] == 1
    assert metrics["reconciliation_events"] == 1
    assert snapshot["backend"] == "sqlite"
    assert snapshot["shared_cloud_ready"] is False
    assert snapshot["sqlite_path"].endswith("shared_institutional.db")
    assert generation_events and generation_events[0]["id"] == generation["id"]
    assert check["lead_id"] == lead["id"]
    assert report["lead_id"] == lead["id"]
    assert expansion["lead_id"] == lead["id"]
    assert reconciliation["lead_id"] == lead["id"]


def test_user_and_admin_share_the_same_institutional_database_contract(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    shared_db_path = Path("data/shared_backend_validation.db")
    monkeypatch.setattr(user_app, "USER_DB_PATH", shared_db_path, raising=False)
    monkeypatch.setattr(admin_app, "DB_PATH", shared_db_path, raising=False)
    create_database(shared_db_path)

    assert user_app.USER_DB_PATH == admin_app.DB_PATH

    user_adapter = resolve_institutional_adapter(user_app.USER_DB_PATH)
    admin_adapter = resolve_institutional_adapter(admin_app.DB_PATH)

    assert user_adapter.backend == "sqlite"
    assert admin_adapter.backend == "sqlite"
    assert user_adapter.sqlite_path == shared_db_path.resolve()
    assert admin_adapter.sqlite_path == shared_db_path.resolve()
    assert user_adapter.fetch_usage_metrics() == admin_adapter.fetch_usage_metrics()
