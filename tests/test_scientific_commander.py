from __future__ import annotations

from itertools import combinations

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
    assert report["count_11_plus"] == 0
    assert report["status_comandante_cientifico"] == "REPROVADO"
    assert report["classificacao_cientifica"] == "APROVADA ESTRUTURALMENTE, REPROVADA CIENTIFICAMENTE"
    assert report["motivo_cientifico"] == "maior acerto <= 10 e 11+ inexistente"
