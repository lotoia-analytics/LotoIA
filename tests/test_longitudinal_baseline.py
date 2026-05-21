from __future__ import annotations

from pathlib import Path

from lotoia.experiments.longitudinal_baseline import run_longitudinal_baseline


def test_run_longitudinal_baseline_persists_checkpoints(tmp_path: Path, monkeypatch) -> None:
    def fake_run_benchmark(**kwargs):
        contests_value = kwargs["contests_analyzed"]
        contests_analyzed = len(contests_value) if isinstance(contests_value, list) else int(contests_value)
        base = float(contests_analyzed) / 10.0

        class _Result:
            def to_dict(self) -> dict[str, object]:
                return {
                    "contests_analyzed": contests_analyzed,
                    "strategies": {
                        "lotoia_engine": {
                            "average_hits": base,
                            "standard_deviation": base / 2,
                            "final_score_hit_correlation": 0.3,
                            "stability": {"windows": [{"standard_deviation": base / 4}]},
                            "hit_distribution": {"11": 0, "12": 0, "13": 0, "14": 0, "15": 0},
                        },
                        "filtered_random": {
                            "average_hits": base - 0.5,
                            "standard_deviation": base / 3,
                        },
                        "pure_random": {
                            "average_hits": base - 1.0,
                            "standard_deviation": base / 4,
                        },
                    },
                    "comparisons": {"lotoia_engine_vs_filtered_random": {"average_hit_difference": 0.5}},
                }

        return _Result()

    monkeypatch.setattr("lotoia.experiments.longitudinal_baseline.run_benchmark", fake_run_benchmark)

    result = run_longitudinal_baseline(seed=7, checkpoints=[10, 20], output_dir=tmp_path / "reports")

    payload = result.to_dict()
    report_file = tmp_path / "reports" / "baseline_hard_longitudinal.json"

    assert payload["baseline_mode"] == "hard"
    assert payload["seed"] == 7
    assert payload["checkpoints"] == [10, 20]
    assert len(payload["runs"]) == 2
    assert payload["summary"]["runtime_profile"] == "incremental_longitudinal"
    assert report_file.exists()
