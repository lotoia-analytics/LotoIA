from __future__ import annotations

from dashboard.institutional_operational_battery import (
    build_battery_post_conference_memory,
    merge_battery_conference_results,
)


def test_battery_post_conference_memory_uses_aggregate_total_not_last_generation() -> None:
    merged = merge_battery_conference_results(
        [
            {
                "generation_event_id": 158,
                "battery_id": "BAT-159",
                "batch_id": "BAT-159",
                "total_games": 30,
                "contest_number": 3717,
                "results": [{"hits": 10}] * 5 + [{"hits": 11}] * 5 + [{"hits": 12}] * 20,
            },
            {
                "generation_event_id": 159,
                "battery_id": "BAT-159",
                "batch_id": "BAT-159",
                "total_games": 20,
                "contest_number": 3717,
                "results": [{"hits": 13}] * 2 + [{"hits": 12}] * 7 + [{"hits": 11}] * 0 + [{"hits": 10}] * 0 + [{"hits": 9}] * 11,
            },
        ]
    )

    memory = build_battery_post_conference_memory(
        merged,
        previous_memory={"generation_event_id": 159, "total_games": 20, "best_hit": 13},
    )

    assert memory["scope"] == "operational_battery"
    assert memory["generation_event_id"] == 159
    assert memory["generation_event_ids"] == [158, 159]
    assert memory["total_games"] == 50
    assert memory["total_games_checked"] == 50
    assert memory["best_hit"] == 13
    assert memory["count_13_exact"] == 2
    assert memory["count_12_exact"] == 27
    assert memory["count_11_plus"] == 34


def test_merge_battery_conference_results_counts_exact_and_plus() -> None:
    merged = merge_battery_conference_results(
        [
            {
                "generation_event_id": 159,
                "battery_id": "BAT-159",
                "batch_id": "BAT-159",
                "total_games": 5,
                "results": [
                    {"hits": 10},
                    {"hits": 11},
                    {"hits": 12},
                    {"hits": 13},
                    {"hits": 13},
                ],
            }
        ]
    )

    assert merged["total_games_checked"] == 5
    assert merged["count_10_exact"] == 1
    assert merged["count_11_exact"] == 1
    assert merged["count_12_exact"] == 1
    assert merged["count_13_exact"] == 2
    assert merged["count_11_plus"] == 4
    assert merged["count_13_plus"] == 2
