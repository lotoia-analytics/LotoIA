from __future__ import annotations

from itertools import combinations

from lotoia.analytics.lotofacil_scientific_core import _scientific_validation_rule
from lotoia.governance.scientific_commander import validate_scientific_batch


def _contest(contest_number: int, numbers: list[int]) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "numbers": numbers,
        "draw_date": f"2026-05-{contest_number:02d}",
    }


def test_scientific_commander_reproves_structural_batch_with_weak_hits() -> None:
    reference_contests = [_contest(index + 1, list(range(1, 11)) + list(range(21, 26))) for index in range(10)]
    tail_candidates = list(combinations(range(11, 21), 5))
    games = []
    for index, tail in enumerate(tail_candidates[:100], start=1):
        games.append({"numbers": list(range(1, 11)) + list(tail), "profile_type": "recorrente"})

    report = validate_scientific_batch(
        games,
        reference_contests,
        game_size=15,
        policy={
            "repeat_min": 7,
            "repeat_max": 10,
            "preferred_parity_pairs": [(7, 8), (8, 7)],
            "allowed_parity_pairs": [(7, 8), (8, 7), (6, 9), (9, 6)],
            "sequence_max": 6,
            "coverage_min": 0.40,
            "entropy_min": 0.45,
            "core_numbers": [7, 12, 16, 23],
            "discouraged_numbers": [2, 4, 11, 15, 24, 25],
            "max_frequency_ratio": 0.70,
            "min_frequency_ratio": 0.20,
            "preferred_profile_ratios": {(7, 8): 0.52, (8, 7): 0.48},
        },
        batch_id="batch-scientific-a",
    )

    assert report["total_jogos_solicitados"] == 100
    assert report["total_jogos_gerados"] == 100
    assert report["total_jogos_unicos"] == 100
    assert report["total_jogos_duplicados"] == 0
    assert report["best_hits"] == 10
    assert report["count_10_exact"] == 100
    assert report["count_11_exact"] == 0
    assert report["count_12_exact"] == 0
    assert report["count_13_exact"] == 0
    assert report["count_14_exact"] == 0
    assert report["count_15_exact"] == 0
    assert report["count_11_plus"] == 0
    assert report["count_11_plus"] == report["count_11_exact"] + report["count_12_exact"] + report["count_13_exact"] + report["count_14_exact"] + report["count_15_exact"]
    assert report["count_12_plus"] == report["count_12_exact"] + report["count_13_exact"] + report["count_14_exact"] + report["count_15_exact"]
    assert report["hit_histogram"]["10"] == 100
    assert report["scientific_validation_zone_count"] == 0
    assert report["policy_validation_status"] == "REPROVADO"
    assert report["status_comandante_cientifico"] == "REPROVADO"
    assert report["classificacao_cientifica"] == "APROVADA ESTRUTURALMENTE, REPROVADA CIENTIFICAMENTE"
    assert report["motivo_cientifico"] == "maior acerto < 11 e zona principal inexistente"


def test_scientific_validation_rule_by_game_size() -> None:
    assert _scientific_validation_rule(15)["validation_threshold"] == 11
    assert _scientific_validation_rule(15)["target_band"] == "11_to_15"
    assert _scientific_validation_rule(17)["validation_threshold"] == 12
    assert _scientific_validation_rule(17)["target_band"] == "12_to_15"
    assert _scientific_validation_rule(18)["validation_threshold"] == 13
    assert _scientific_validation_rule(18)["target_band"] == "13_to_15"


def test_scientific_commander_rejects_11_hits_for_17_dezenas() -> None:
    reference_contests = [_contest(index + 1, list(range(1, 12)) + list(range(18, 22))) for index in range(10)]
    games = [{"numbers": list(range(1, 12)) + list(range(12, 18)), "profile_type": "recorrente"} for _ in range(100)]

    report = validate_scientific_batch(
        games,
        reference_contests,
        game_size=17,
        policy={"repeat_min": 6, "repeat_max": 12, "sequence_max": 7, "max_frequency_ratio": 0.70, "min_frequency_ratio": 0.20},
        batch_id="batch-17z",
    )

    assert report["validation_threshold"] == 12
    assert report["target_band"] == "12_to_15"
    assert report["validation_zone_label"] == "Zona de validação científica: 12 a 15 acertos."
    assert report["best_hits"] == 11
    assert report["count_11_exact"] == 100
    assert report["count_12_exact"] == 0
    assert report["count_11_plus"] == 100
    assert report["count_12_plus"] == 0
    assert report["scientific_validation_zone_count"] == 0
    assert report["policy_validation_status"] == "REPROVADO"
    assert report["status_comandante_cientifico"] == "REPROVADO"


def test_scientific_commander_rejects_12_hits_for_18_dezenas() -> None:
    reference_contests = [_contest(index + 1, list(range(1, 13)) + list(range(19, 22))) for index in range(10)]
    games = [{"numbers": list(range(1, 13)) + list(range(13, 19)), "profile_type": "recorrente"} for _ in range(100)]

    report = validate_scientific_batch(
        games,
        reference_contests,
        game_size=18,
        policy={"repeat_min": 6, "repeat_max": 12, "sequence_max": 8, "max_frequency_ratio": 0.70, "min_frequency_ratio": 0.20},
        batch_id="batch-18z",
    )

    assert report["validation_threshold"] == 13
    assert report["target_band"] == "13_to_15"
    assert report["validation_zone_label"] == "Zona de validação científica: 13 a 15 acertos."
    assert report["best_hits"] == 12
    assert report["count_12_exact"] == 100
    assert report["count_13_exact"] == 0
    assert report["count_12_plus"] == 100
    assert report["count_13_plus"] == 0
    assert report["scientific_validation_zone_count"] == 0
    assert report["policy_validation_status"] == "REPROVADO"
    assert report["status_comandante_cientifico"] == "REPROVADO"


def test_scientific_commander_accepts_11_hits_for_15_dezenas() -> None:
    reference_contests = [_contest(index + 1, list(range(1, 16))) for index in range(10)]
    games = [{"numbers": list(range(1, 12)) + list(range(16, 20)), "profile_type": "recorrente"} for _ in range(100)]

    report = validate_scientific_batch(
        games,
        reference_contests,
        game_size=15,
        policy={"repeat_min": 6, "repeat_max": 12, "sequence_max": 7, "max_frequency_ratio": 0.70, "min_frequency_ratio": 0.20},
        batch_id="batch-15z",
    )

    assert report["validation_threshold"] == 11
    assert report["target_band"] == "11_to_15"
    assert report["validation_zone_label"] == "Zona de validação científica: 11 a 15 acertos."
    assert report["best_hits"] == 11
    assert report["count_11_exact"] == 100
    assert report["count_12_exact"] == 0
    assert report["scientific_validation_zone_count"] == 100
    assert report["policy_validation_status"] == "APROVADO"
    assert report["status_comandante_cientifico"] == "REPROVADO"


def test_scientific_commander_exposes_cross_product_backtest_summary() -> None:
    reference_contests = [
        _contest(1, list(range(1, 16))),
        _contest(2, list(range(11, 26))),
    ]
    games = [
        {"numbers": list(range(1, 16)), "profile_type": "recorrente"},
        {"numbers": list(range(11, 26)), "profile_type": "recorrente"},
        {"numbers": [1, 2, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17, 18, 19], "profile_type": "hibrido"},
    ]

    report = validate_scientific_batch(
        games,
        reference_contests,
        game_size=15,
        policy={"repeat_min": 6, "repeat_max": 12, "sequence_max": 7, "max_frequency_ratio": 0.70, "min_frequency_ratio": 0.20},
        batch_id="batch-cross-product",
    )

    assert report["contests_checked"] == 2
    assert report["games_per_contest"] == 3
    assert report["total_game_contest_checks"] == 6
    assert report["contests_with_11_plus"] == 2
    assert report["contests_with_12_plus"] == 2
    assert report["contests_with_13_plus"] == 2
    assert report["contests_with_14_plus"] == 2
    assert report["contests_with_15"] == 2
    assert report["aggregate_count_11_exact"] == 1
    assert report["aggregate_count_15_exact"] == 2
    assert report["aggregate_count_11_plus"] == 3
    assert report["backtest_aggregate"]["count_11_exact"] == 1
    assert report["backtest_aggregate"]["count_15_exact"] == 2
    assert report["backtest_aggregate"]["count_11_plus"] == 3
    assert report["backtest_aggregate"]["count_12_plus"] == 2
