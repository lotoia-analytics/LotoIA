from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from dashboard.institutional_operational_structural_coverage import (
    load_agent_routing_coverage_summary,
    load_ml_operational_hierarchy_coverage_summary,
    load_pre_final_pool_coverage_summary,
    load_pre_gp_recovery_coverage_summary,
    load_structural_15d_pool_coverage_summary,
)
from lotoia.database.database import GeneratedGame, GenerationEvent, create_database, get_session
from lotoia.governance.lei15_core_002_sovereign import resolve_core_002_batch_label


@pytest.fixture
def sqlite_db_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOTOIA_DATABASE_URL", raising=False)
    monkeypatch.delenv("STREAMLIT_DATABASE_URL", raising=False)


def _seed_core_event(db_path: Path, *, card_format: int, index: int) -> int:
    numbers = list(range(1, int(card_format) + 1))
    with get_session(db_path) as session:
        event = GenerationEvent(
            first_name="institutional",
            whatsapp="",
            generated_games=[{"numbers": numbers[:15]}],
            context_json={
                "generation_mode": "LEI15_CORE_002_SOVEREIGN",
                "active_reading_scope": True,
                "operational_status": "pending_structural_review",
                "pre_final_pool_ml_calibration": {"pre_final_pool_ml_enabled": True, "pre_final_pool_size": 50 + index},
                "ml_structural_15d_pool": {"structural_pool_applied": True, "structural_pool_size": 60 + index},
                "ml_operational_hierarchy": {"ml_hierarchy_status": "active", "current_stage": f"stage_{index}"},
                "pre_gp_recovery": {"recovery_applied": True, "recovered_candidates": index},
                "responsible_agents": ["core_002"],
                "primary_responsible_agent": "core_002",
            },
            ml_enabled=1,
            seed=42 + index,
            strategy="institutional_clean_hb",
            ranking_score=0.0,
            execution_time_ms=1.0,
            analysis_batch_label=resolve_core_002_batch_label(card_format),
            analysis_batch_type="LEI15_CORE_002_SOVEREIGN",
            analysis_batch_created_at=datetime.now(UTC),
        )
        session.add(event)
        session.flush()
        ge_id = int(event.id)
        session.add(
            GeneratedGame(
                generation_event_id=ge_id,
                target_contest=3712,
                origin="institutional",
                generation_mode="hb_baseline",
                game_index=1,
                numbers=numbers if card_format == 15 else numbers[:15],
                profile_type="HYBRID",
                final_score={},
                quadra_score={},
                context_json={"selected_card_format": card_format, "final_card_numbers": numbers},
            )
        )
        session.commit()
        return ge_id


def test_aggregate_analytics_layers_do_not_fallback_to_single_generation(
    tmp_path: Path,
    sqlite_db_env: None,
) -> None:
    db_path = tmp_path / "operational_layers_all.db"
    create_database(db_path)
    ge_15 = _seed_core_event(db_path, card_format=15, index=1)
    ge_17 = _seed_core_event(db_path, card_format=17, index=2)

    loaders = [
        load_pre_final_pool_coverage_summary,
        load_structural_15d_pool_coverage_summary,
        load_ml_operational_hierarchy_coverage_summary,
        load_pre_gp_recovery_coverage_summary,
        load_agent_routing_coverage_summary,
    ]
    for loader in loaders:
        payload = loader(db_path, 0)
        assert payload["aggregate_mode"] is True
        assert payload["generation_events_count"] == 2
        assert set(payload["generation_event_ids"]) == {ge_15, ge_17}
        assert payload["summary"]["total_generations_analyzed"] == 2
