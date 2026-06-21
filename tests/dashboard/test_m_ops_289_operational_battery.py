from __future__ import annotations

from dashboard.institutional_operational_battery import (
    build_operational_battery_groups,
    format_operational_battery_label,
    merge_battery_conference_results,
)


def test_build_operational_battery_groups_uses_batch_id_without_db_migration() -> None:
    groups = [
        {
            "generation_event_id": 67,
            "batch_id": "BAT-001",
            "total_games": 10,
            "games": [{"game_index": 1, "hits": 11}],
            "lot_operational_status": "approved_with_warning",
            "created_at": "2026-06-21T05:27:00",
        },
        {
            "generation_event_id": 68,
            "batch_id": "BAT-001",
            "total_games": 10,
            "games": [{"game_index": 2, "hits": 12}],
            "lot_operational_status": "approved_with_warning",
            "created_at": "2026-06-21T05:28:00",
        },
        {
            "generation_event_id": 76,
            "batch_id": "BAT-002",
            "total_games": 10,
            "games": [{"game_index": 1, "hits": 0}],
            "lot_operational_status": "pending_structural_review",
            "created_at": "2026-06-21T07:42:00",
        },
    ]

    batteries = build_operational_battery_groups(groups)

    bat_001 = next(row for row in batteries if row["battery_id"] == "BAT-001")
    assert bat_001["generation_event_ids"] == [67, 68]
    assert bat_001["total_generation_events"] == 2
    assert bat_001["total_games"] == 20
    assert len(bat_001["games"]) == 2
    assert bat_001["battery_scope"] == "operational_battery"


def test_battery_label_shows_total_generations_and_games() -> None:
    battery = {
        "battery_id": "BAT-001",
        "generation_event_ids": [67, 68],
        "total_games": 20,
        "lot_operational_status": "approved_with_warning",
        "created_at": "2026-06-21T05:28:00",
    }

    label = format_operational_battery_label(battery)

    assert "Bateria BAT-001" in label
    assert "2 gerações" in label
    assert "20 jogos" in label


def test_merge_battery_conference_results_consolidates_hits() -> None:
    result = merge_battery_conference_results(
        [
            {
                "generation_event_id": 67,
                "results": [
                    {"game_index": 1, "hits": 11},
                    {"game_index": 2, "hits": 9},
                ],
            },
            {
                "generation_event_id": 68,
                "results": [
                    {"game_index": 1, "hits": 12},
                ],
            },
        ]
    )

    assert result["scope"] == "operational_battery"
    assert result["generation_event_ids"] == [67, 68]
    assert result["total_games"] == 3
    assert result["best_hits"] == 12
    assert result["total_hits"] == 32
    assert result["prize_count"] == 2
