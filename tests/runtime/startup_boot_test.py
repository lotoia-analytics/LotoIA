from __future__ import annotations

import subprocess
import sys


def test_user_entrypoint_boot_without_generator_cascade() -> None:
    code = """
import sys
import dashboard.user_app

blocked = [
    "lotoia.generator.basic_generator",
    "lotoia.backtesting.backtester",
    "lotoia.benchmark.benchmark_engine",
    "lotoia.ml.rerank",
]

assert not [module for module in blocked if module in sys.modules], sorted(
    module for module in blocked if module in sys.modules
)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
