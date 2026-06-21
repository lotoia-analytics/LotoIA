"""M-OPS-289A — conferência por bateria operacional."""

from __future__ import annotations

from dashboard.institutional_operational_battery import (
    OPERATIONAL_BATTERY_ALL_ID,
    build_operational_battery_aggregate,
    build_operational_battery_groups,
    format_operational_battery_label,
    merge_battery_conference_results,
)


def test_build_operational_battery_groups_groups_by_batch_id() -> None:
    groups = [
        {"generation_event_id": 10, "batch_id": "BAT-001", "total_games": 10, "lot_operational_status": "approved_with_warning"},
        {"generation_event_id": 11, "batch_id": "BAT-001", "total_games": 10, "lot_operational_status": "approved_with_warning"},
        {"generation_event_id": 5, "batch_id": "BAT-002", "total_games": 20, "lot_operational_status": "officialized"},
    ]
    batteries = build_operational_battery_groups(groups)
    assert len(batteries) == 2
    bat_001 = next(row for row in batteries if row["battery_id"] == "BAT-001")
    assert bat_001["generation_event_ids"] == [10, 11]
    assert bat_001["total_games"] == 20
    assert bat_001["generations_count"] == 2
    assert len(bat_001["groups"]) == 2


def test_format_operational_battery_label() -> None:
    label = format_operational_battery_label(
        {
            "battery_id": "BAT-001",
            "generation_event_ids": [10, 11],
            "total_games": 20,
            "lot_operational_status": "approved_with_warning",
            "created_at": "2026-06-21",
        }
    )
    assert "Bateria BAT-001" in label
    assert "2 gerações" in label
    assert "20 jogos" in label


def test_merge_battery_conference_results_consolidates_all_generations() -> None:
    per_generation = [
        {
            "generation_event_id": 1,
            "battery_id": "BAT-001",
            "batch_id": "BAT-001",
            "total_games": 10,
            "best_hits": 12,
            "total_hits": 120,
            "prize_count": 2,
            "results": [{"hits": 12}, {"hits": 11}],
            "contest_number": 3717,
            "contest_date": "2026-01-01",
        },
        {
            "generation_event_id": 2,
            "battery_id": "BAT-001",
            "batch_id": "BAT-001",
            "total_games": 10,
            "best_hits": 13,
            "total_hits": 130,
            "prize_count": 3,
            "results": [{"hits": 13}, {"hits": 10}],
            "contest_number": 3717,
            "contest_date": "2026-01-01",
        },
    ]
    merged = merge_battery_conference_results(per_generation)
    assert merged["scope"] == "operational_battery"
    assert merged["generation_event_ids"] == [1, 2]
    assert merged["best_hits"] == 13
    assert merged["total_hits"] == 46
    assert merged["prize_count"] == 3
    assert merged["total_games_checked"] == 20
    assert len(merged["results"]) == 4


def test_build_operational_battery_aggregate_for_todos() -> None:
    batteries = build_operational_battery_groups(
        [
            {"generation_event_id": 1, "batch_id": "BAT-001", "total_games": 10},
            {"generation_event_id": 2, "batch_id": "BAT-001", "total_games": 10},
            {"generation_event_id": 3, "batch_id": "BAT-002", "total_games": 10},
        ]
    )
    aggregate = build_operational_battery_aggregate(batteries)
    assert aggregate["battery_id"] == OPERATIONAL_BATTERY_ALL_ID
    assert aggregate["generations_count"] == 3
    assert aggregate["total_games"] == 30
