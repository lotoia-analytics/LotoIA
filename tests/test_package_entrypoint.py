from __future__ import annotations

import sys

from lotoia import __main__ as lotoia_main


def test_package_entrypoint_dispatches_institutional_analytics(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        lotoia_main.cli,
        "run_institutional_analytics_cli",
        lambda argv=None: calls.append(tuple(argv or [])),
    )
    monkeypatch.setattr(sys, "argv", ["lotoia", "institutional-analytics"])

    lotoia_main.main()

    assert calls == [()]


def test_package_entrypoint_passes_institutional_arguments(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        lotoia_main.cli,
        "run_institutional_analytics_cli",
        lambda argv=None: calls.append(tuple(argv or [])),
    )
    monkeypatch.setattr(sys, "argv", ["lotoia", "institutional-analytics", "--report-dir", "custom/reports"])

    lotoia_main.main()

    assert calls == [("--report-dir", "custom/reports")]


def test_package_entrypoint_dispatches_observational_stabilization(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        lotoia_main.cli,
        "run_observational_stabilization_cli",
        lambda argv=None: calls.append(tuple(argv or [])),
    )
    monkeypatch.setattr(sys, "argv", ["lotoia", "observational-stabilization", "--db-path", "data/lotoia.db"])

    lotoia_main.main()

    assert calls == [("--db-path", "data/lotoia.db")]


def test_package_entrypoint_dispatches_adaptive_intelligence(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        lotoia_main.cli,
        "run_adaptive_institutional_intelligence_cli",
        lambda argv=None: calls.append(tuple(argv or [])),
    )
    monkeypatch.setattr(sys, "argv", ["lotoia", "adaptive-intelligence", "--report-dir", "custom/reports"])

    lotoia_main.main()

    assert calls == [("--report-dir", "custom/reports")]
