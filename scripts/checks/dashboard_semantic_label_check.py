#!/usr/bin/env python3
"""Check institucional: rótulos semânticos Lei 15 / Lei 15A no dashboard."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_LABELS = (
    "16D–23D = núcleo operacional GP + reservas auditadas",
    "15D nasce do núcleo operacional GP",
)

REQUIRED_LABELS = (
    "16D–23D = cartão validado pela matriz GP da Lei 15A",
    "componentes próprios da Lei 15A",
    "cartão validado deve coincidir com o cartão final superior",
    "Cartão validado Lei 15A",
    "Reservas auditadas Lei 15",
)


def main() -> int:
    app_path = ROOT / "dashboard" / "institutional_app.py"
    text = app_path.read_text(encoding="utf-8")
    errors: list[str] = []

    for forbidden in FORBIDDEN_LABELS:
        if forbidden in text:
            errors.append(f"forbidden label still present: {forbidden}")

    for required in REQUIRED_LABELS:
        if required not in text:
            errors.append(f"required label missing: {required}")

    pytest_args = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_clean_app_formats.py",
        "-q",
        "-k",
        "semantic_label or column_labels_differentiate",
    ]
    result = subprocess.run(pytest_args, cwd=ROOT, check=False)
    if result.returncode != 0:
        errors.append("semantic label pytest subset failed")

    if errors:
        print("dashboard-semantic-label-check: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("dashboard-semantic-label-check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
