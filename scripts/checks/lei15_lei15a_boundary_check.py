#!/usr/bin/env python3
"""Check institucional: fronteira Lei 15 / Lei 15A no runtime do painel."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PYTEST_ARGS = [
    sys.executable,
    "-m",
    "pytest",
    "tests/test_clean_app_formats.py",
    "-q",
    "-k",
    (
        "operational_read or component_boundary or runtime_contract or "
        "panel_sync or panel_semantic or normalize_dezenas or registration_card_remains"
    ),
]


def main() -> int:
    result = subprocess.run(PYTEST_ARGS, cwd=ROOT, check=False)
    if result.returncode == 0:
        print("lei15-lei15a-boundary-check: PASS")
        return 0
    print("lei15-lei15a-boundary-check: FAIL")
    return result.returncode or 1


if __name__ == "__main__":
    sys.exit(main())
