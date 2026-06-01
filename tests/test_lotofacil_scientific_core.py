from __future__ import annotations

from lotoia.analytics.lotofacil_scientific_core import (
    LotofacilScientificCore,
    analyze_contest_transition,
    build_scientific_profile,
    discover_scientific_generation_policy,
    get_scientific_generation_policy,
)


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
    assert len(policy["core_numbers"]) == 4
    assert all(isinstance(number, int) for number in policy["core_numbers"])
    assert len(policy["discouraged_numbers"]) == 6


def test_lotofacil_scientific_core_discovers_policy_with_metadata() -> None:
    contests = [
        _contest(1, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
        _contest(2, [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 24, 25, 2]),
        _contest(3, [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23, 24, 25, 1]),
        _contest(4, [1, 4, 5, 7, 8, 9, 10, 12, 14, 16, 18, 19, 21, 23, 25]),
    ]

    discovery = discover_scientific_generation_policy(15, contests=contests)

    assert discovery["policy_origin"] == "automatic_scientific_discovery"
    assert discovery["candidate_count"] >= 20
    assert discovery["selection_reason"]
    assert discovery["policy"]["repeat_min"] <= discovery["policy"]["repeat_max"]
    assert discovery["policy"]["repeat_min"] >= 0
    assert discovery["policy"]["repeat_max"] <= 15
    assert len(discovery["candidates_tested"]) == discovery["candidate_count"]
