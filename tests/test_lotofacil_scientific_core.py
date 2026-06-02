from __future__ import annotations

from lotoia.analytics.lotofacil_scientific_core import (
    LotofacilScientificCore,
    analyze_contest_transition,
    build_scientific_profile,
    build_batch_reconciliation_scientific_memory,
    build_post_reconciliation_scientific_memory,
    discover_scientific_generation_policy,
    get_scientific_generation_policy,
)
from lotoia.database.database import create_database


def _contest(contest_number: int, numbers: list[int]) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "numbers": numbers,
        "draw_date": f"2026-05-{contest_number:02d}",
        "source": "imported_contests",
    }


def test_lotofacil_scientific_core_builds_profile_with_frequency_windows_and_metrics() -> None:
    contests = [
        _contest(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        _contest(2, [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 24, 25, 2]),
        _contest(3, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24, 25, 1]),
        _contest(4, [1, 4, 5, 7, 8, 9, 10, 12, 14, 16, 18, 19, 21, 23, 25]),
    ]

    core = LotofacilScientificCore(contests=contests)
    profile = core.build_scientific_profile(window_size=4)
    transition = analyze_contest_transition(contests[0], contests[1])
    policy = get_scientific_generation_policy(15, contests=contests)

    assert profile["contest_count"] == 4
    assert profile["window_size"] == 4
    assert "full_history" in profile["frequency_windows"]
    assert "window_100" in profile["frequency_windows"]
    assert "delay_metrics" in profile
    assert "return_metrics" in profile
    assert profile["repeat_distribution"]
    assert profile["parity_distribution"]
    assert transition["previous_contest"] == 1
    assert transition["current_contest"] == 2
    assert isinstance(transition["overlap"], int)
    assert policy["repeat_min"] <= policy["repeat_max"]
    assert policy["preferred_parity_pairs"]
    assert all(sum(pair) == 15 for pair in policy["preferred_parity_pairs"])
    assert all(sum(pair) == 15 for pair in policy["allowed_parity_pairs"])
    assert policy["validation_threshold"] == 11
    assert policy["target_band"] == "11_to_15"
    assert policy["policy_mode"] == "hybrid_15_towards_12_plus"
    assert policy["current_target"] == "12_plus"
    assert policy["secondary_target"] == "13_plus"
    assert policy["memory_role"] == "strong_support"
    assert policy["dominant_memory"] == "conditional"
    assert policy["core_numbers_to_preserve"] == [1, 10, 18, 20, 9, 11, 6, 21]
    assert policy["controlled_support_numbers"] == [24, 15]
    assert policy["promote_numbers_for_12_plus"] == [17, 14, 7]
    assert policy["real_gap_number"] == 16
    assert policy["reduce_priority_numbers"] == [2, 3, 5, 8]
    assert len(policy["core_numbers"]) == 8
    assert all(isinstance(number, int) for number in policy["core_numbers"])
    assert len(policy["discouraged_numbers"]) == 6


def test_lotofacil_scientific_core_discovers_policy_with_metadata(tmp_path) -> None:
    contests = [
        _contest(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        _contest(2, [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 24, 25, 2]),
        _contest(3, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24, 25, 1]),
        _contest(4, [1, 4, 5, 7, 8, 9, 10, 12, 14, 16, 18, 19, 21, 23, 25]),
    ]

    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    discovery = discover_scientific_generation_policy(15, contests=contests, db_path=db_path)

    assert discovery["policy_origin"] == "automatic_scientific_discovery"
    assert discovery["candidate_count"] >= 20
    assert discovery["selection_reason"]
    assert discovery["policy"]["repeat_min"] <= discovery["policy"]["repeat_max"]
    assert discovery["policy"]["repeat_min"] >= 0
    assert discovery["policy"]["repeat_max"] <= 15
    assert len(discovery["candidates_tested"]) == discovery["candidate_count"]


def test_lotofacil_scientific_core_builds_post_reconciliation_memory_for_near_miss() -> None:
    contest = _contest(3699, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "game_index": 1},
    ]

    memory = build_post_reconciliation_scientific_memory(
        generation_event_id=340,
        batch_id="calibration-340",
        contest=contest,
        games=games,
        policy_before={
            "repeat_min": 7,
            "repeat_max": 10,
            "sequence_max": 6,
            "coverage_min": 0.4,
            "entropy_min": 0.45,
            "max_frequency_ratio": 0.7,
            "min_frequency_ratio": 0.2,
        },
        policy_after={
            "repeat_min": 7,
            "repeat_max": 10,
            "sequence_max": 6,
            "coverage_min": 0.4,
            "entropy_min": 0.45,
            "max_frequency_ratio": 0.7,
            "min_frequency_ratio": 0.2,
        },
    )

    assert memory["memory_kind"] == "scientific_reconciliation"
    assert memory["scientific_classification"] == "NEAR_MISS_LOCAL"
    assert memory["recommended_action"] == "recalibrate_from_near_miss_towards_15"
    assert memory["validation_threshold"] == 11
    assert memory["scientific_validation_zone_count"] == 0
    assert memory["policy_validation_status"] == "REPROVADO"
    assert memory["count_10"] == 1
    assert memory["cross_validation_summary"]["scientific_score_components"]["count_10"] == 1
    assert memory["generation_range"]["contest_number"] == 3699
    assert memory["policy_after"]["policy_origin"] == "scientific_reconciliation_memory"
    assert memory["policy_after"]["next_generation_policy_adjustments"]["max_frequency_ratio"] <= 0.7


def test_lotofacil_scientific_core_uses_threshold_by_game_size_for_17_and_18() -> None:
    contest_17 = _contest(3700, list(range(1, 18)))
    games_17 = [
        {"numbers": list(range(1, 12)) + list(range(18, 24)), "game_index": 1},
    ]
    memory_17 = build_post_reconciliation_scientific_memory(
        generation_event_id=341,
        batch_id="calibration-341",
        contest=contest_17,
        games=games_17,
        policy_before={},
        policy_after={},
    )

    contest_18 = _contest(3701, list(range(1, 19)))
    games_18 = [
        {"numbers": list(range(1, 13)) + list(range(19, 25)), "game_index": 1},
    ]
    memory_18 = build_post_reconciliation_scientific_memory(
        generation_event_id=342,
        batch_id="calibration-342",
        contest=contest_18,
        games=games_18,
        policy_before={},
        policy_after={},
    )

    assert memory_17["validation_threshold"] == 12
    assert memory_17["target_band"] == "12_to_15"
    assert memory_17["scientific_validation_zone_count"] == 0
    assert memory_17["policy_validation_status"] == "REPROVADO"
    assert memory_17["best_hit"] == 11

    assert memory_18["validation_threshold"] == 13
    assert memory_18["target_band"] == "13_to_15"
    assert memory_18["scientific_validation_zone_count"] == 0
    assert memory_18["policy_validation_status"] == "REPROVADO"
    assert memory_18["best_hit"] == 12


def test_lotofacil_scientific_core_uses_reconciliation_results_for_count_10() -> None:
    contest = _contest(3699, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    games = [
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "game_index": 1},
        {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 11], "game_index": 2},
    ]
    reconciliation_results = [
        {"game_index": 1, "hits": 10},
        {"game_index": 2, "hits": 9},
    ]

    memory = build_post_reconciliation_scientific_memory(
        generation_event_id=350,
        batch_id="calibration-350",
        contest=contest,
        games=games,
        reconciliation_results=reconciliation_results,
        policy_before={},
        policy_after={},
    )

    assert memory["count_10"] == 1
    assert memory["cross_validation_summary"]["scientific_score_components"]["count_10"] == 1


def test_lotofacil_scientific_core_builds_strong_near_miss_memory() -> None:
    contest = _contest(3699, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    generation_results = [
        {
            "generation_event_id": 351,
            "batch_id": "calibration-351",
            "total_games": 10,
            "best_hits": 10,
            "total_hits": 98,
            "prize_count": 0,
            "results": [{"hits": 10} for _ in range(9)] + [{"hits": 9}],
            "games": [{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} for _ in range(10)],
        },
        {
            "generation_event_id": 354,
            "batch_id": "calibration-354",
            "total_games": 10,
            "best_hits": 10,
            "total_hits": 97,
            "prize_count": 0,
            "results": [{"hits": 10} for _ in range(8)] + [{"hits": 9}, {"hits": 8}],
            "games": [{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} for _ in range(10)],
        },
    ]

    memory = LotofacilScientificCore(contests=[]).build_strong_near_miss_scientific_memory(
        batch_id="calibration",
        contest=contest,
        generation_results=generation_results,
    )

    assert memory["memory_kind"] == "scientific_strong_near_miss"
    assert memory["scientific_classification"] == "NEAR_MISS_FORTE"
    assert memory["recommended_action"] == "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
    assert memory["generation_range"]["best_generation_event_id"] in {351, 354}
    assert memory["generation_range"]["best_generation_count_10"] >= 8


def test_lotofacil_scientific_core_builds_batch_reconciliation_memory() -> None:
    contest = _contest(3699, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])
    generation_results = []
    for generation_event_id in range(351, 361):
        generation_results.append(
            {
                "generation_event_id": generation_event_id,
                "batch_id": "calibration-20260601200630-98e210b",
                "total_games": 10,
                "best_hits": 10,
                "total_hits": 95 + (generation_event_id % 3),
                "prize_count": 0,
                "results": [{"hits": 10} for _ in range(5)] + [{"hits": 9} for _ in range(5)],
                "games": [{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} for _ in range(10)],
                "contest_number": 3699,
                "contest_date": "2026-06-01",
            }
        )

    memory = build_batch_reconciliation_scientific_memory(
        batch_id="calibration-20260601200630-98e210b",
        contest=contest,
        generation_results=generation_results,
    )

    assert memory["memory_kind"] == "scientific_batch_reconciliation"
    assert memory["scientific_classification"] == "STRONG_NEAR_MISS_BATCH"
    assert memory["recommended_action"] == "recalibrate_from_strong_near_miss_towards_11_plus_and_15"
    assert memory["generation_range"]["first_generation_event_id"] == 351
    assert memory["generation_range"]["last_generation_event_id"] == 360
    assert memory["generation_range"]["total_generations"] == 10
    assert memory["generation_range"]["total_games_checked"] == 100
    assert memory["generation_range"]["global_best_hits"] == 10
    assert memory["generation_range"]["global_count_10"] == 50
    assert memory["generation_range"]["global_count_11_plus"] == 0
    assert len(memory["near_miss_generation_ranking"]) == 10
