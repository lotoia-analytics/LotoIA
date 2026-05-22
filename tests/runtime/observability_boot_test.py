from __future__ import annotations

import subprocess
import sys


def test_observability_package_import_is_lazy() -> None:
    code = """
import sys
import lotoia.observability

blocked = [
    "lotoia.observability.live_telemetry",
    "lotoia.observability.operational_experience",
    "lotoia.observability.runtime_storytelling",
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

