from __future__ import annotations

import json

from lotoia.experiments.supervised_walk_forward import run_score_ml_walk_forward
from lotoia.models.draw import Draw


def make_draws(count: int = 10) -> list[Draw]:
    draws = []
    for contest in range(1, count + 1):
        start = ((contest - 1) % 10) + 1
        numbers = sorted({*range(1, 16), start})
        while len(numbers) < 15:
            numbers.append(len(numbers) + 1)
        draws.append(Draw(contest=contest, numbers=numbers[:15]))
    return draws


def test_score_ml_walk_forward_preserves_temporal_validity(tmp_path) -> None:
    result = run_score_ml_walk_forward(
        draws=make_draws(9),
        min_train_size=4,
        test_size=2,
        step_size=2,
        games_count=1,
        pool_size=1,
        history_window=3,
        seed=7,
        experiment_dir=tmp_path / "experiments",
        report_dir=tmp_path / "reports",
        update_registries=False,
    )
    report = json.loads((tmp_path / "reports" / "walk_forward_result.json").read_text())

    assert result.split_count == 2
    for split_result in report["split_results"]:
        split = split_result["split"]
        assert split["train_end"] < split["test_start"]
        assert split_result["training"]["feature_cutoff_max"] == split["train_end"]
        for contest_result in split_result["test"]["contest_results"]:
            assert contest_result["feature_cutoff_contest"] < contest_result["contest"]


def test_score_ml_walk_forward_is_reproducible_for_same_inputs(tmp_path) -> None:
    draws = make_draws(8)
    first = run_score_ml_walk_forward(
        draws=draws,
        min_train_size=4,
        test_size=1,
        step_size=1,
        games_count=1,
        pool_size=1,
        history_window=3,
        seed=11,
        experiment_dir=tmp_path / "first" / "experiments",
        report_dir=tmp_path / "first" / "reports",
        update_registries=False,
    )
    second = run_score_ml_walk_forward(
        draws=draws,
        min_train_size=4,
        test_size=1,
        step_size=1,
        games_count=1,
        pool_size=1,
        history_window=3,
        seed=11,
        experiment_dir=tmp_path / "second" / "experiments",
        report_dir=tmp_path / "second" / "reports",
        update_registries=False,
    )

    assert first.reproducibility_hash == second.reproducibility_hash
    assert first.average_hit_delta == second.average_hit_delta
