from __future__ import annotations

from pathlib import Path

from lotoia.experiments.behavioral_experiment import run_experiment_01


def test_run_experiment_01_generates_controlled_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = run_experiment_01(seeds=[7, 11], count=3, pool_size=6, report_dir=tmp_path / "reports")

    payload = result.to_dict()
    report_file = tmp_path / "reports" / "experiment_01_report.json"

    assert payload["experiment_id"] == "experiment_01_normalize_distribution"
    assert payload["baseline_mode"] == "hard"
    assert payload["experimental_mode"] == "medium"
    assert len(payload["baseline_runs"]) == 2
    assert len(payload["experimental_runs"]) == 2
    assert "summary" in payload
    assert report_file.exists()
