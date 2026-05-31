from __future__ import annotations

from lotoia.analytics.scientific_calibration_engine import (
    apply_supervised_calibration,
    evaluate_last_batch,
    generate_recalibration_policy,
    register_calibration_decision,
    recommend_next_strategy,
)
from lotoia.database.database import ScientificCalibrationDecision, create_database, get_session


def _contest(contest_number: int, numbers: list[int]) -> dict[str, object]:
    return {
        "contest_number": contest_number,
        "numbers": numbers,
        "draw_date": f"2026-05-{contest_number:02d}",
    }


def _build_weak_batch() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    reference_contests = [_contest(index + 1, list(range(1, 11)) + list(range(21, 26))) for index in range(10)]
    games: list[dict[str, object]] = []
    base_numbers = list(range(1, 11)) + [16, 17, 18, 19, 20]
    for index in range(20):
        games.append(
            {
                "game_index": index + 1,
                "numbers": base_numbers,
                "profile_type": "recorrente",
                "target_contest": 3698,
            }
        )
    return reference_contests, games


def test_scientific_calibration_recommends_recalibration_policy(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    reference_contests, games = _build_weak_batch()

    context = evaluate_last_batch(
        game_size=15,
        batch_id="batch-scientific-calibration",
        mode="OBSERVAÇÃO",
        contests=reference_contests,
        games=games,
        reference_contests=reference_contests,
        db_path=db_path,
    )

    policy = generate_recalibration_policy(context)
    recommendation = recommend_next_strategy(context)

    assert context["scientific_status"] == "REPROVADO"
    assert context["classification"] == "REPROVADA"
    assert policy["action"] == "recalibrate_frequency_distribution"
    assert policy["keep_rules"]["batch_size"] == 100
    assert policy["keep_rules"]["repeat_previous_min"] == 7
    assert policy["keep_rules"]["repeat_previous_max"] == 10
    assert policy["keep_rules"]["sequence_max"] == 6
    assert policy["keep_rules"]["unique_required"] is True
    assert recommendation["action_suggested"] == "recalibrate_frequency_distribution"
    assert recommendation["status_visual"] == "REPROVADO"


def test_register_scientific_calibration_decision_persists_memory(tmp_path) -> None:
    db_path = tmp_path / "lotoia.db"
    create_database(db_path)
    reference_contests, games = _build_weak_batch()

    context = evaluate_last_batch(
        game_size=15,
        batch_id="batch-scientific-calibration",
        mode="AUTONOMIA SUPERVISIONADA",
        contests=reference_contests,
        games=games,
        reference_contests=reference_contests,
        db_path=db_path,
    )
    decision = apply_supervised_calibration(
        context,
        approved_by="cientista@lotoia.local",
        notes="registro supervisionado",
        auto_apply=True,
    )
    saved = register_calibration_decision(context, decision=decision, db_path=db_path)

    with get_session(db_path) as session:
        stored = session.query(ScientificCalibrationDecision).all()

    assert saved["source_batch_id"] == "batch-scientific-calibration"
    assert saved["mode"] == "AUTONOMIA SUPERVISIONADA"
    assert saved["applied"] is False
    assert len(stored) == 1
    assert stored[0].source_batch_id == "batch-scientific-calibration"
    assert stored[0].mode == "AUTONOMIA SUPERVISIONADA"
    assert bool(stored[0].applied) is False
