from __future__ import annotations

import subprocess
import sys


def test_workflow_package_import_is_lazy() -> None:
    code = """
import sys
import lotoia.workflows

blocked = [
    "lotoia.workflows.workflow_engine",
    "lotoia.workflows.workflow_scheduler",
    "lotoia.workflows.workflow_dashboard",
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

