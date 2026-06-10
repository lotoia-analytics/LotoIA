#!/usr/bin/env python3
"""Check institucional: contratos de governança LotoIA presentes e formalizados."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = (
    "AGENTS.md",
    "docs/governance/POLITICA_ML_ASSISTIVO.md",
    "docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md",
    "docs/governance/LEI_15_NUCLEO_OPERACIONAL_15D.md",
    "docs/governance/ADR_LEI15_NUCLEO_15D_CONGELADO.md",
    "docs/governance/BRANCH_PROTECTION_MAIN.md",
    ".github/CODEOWNERS",
    ".github/workflows/governance-gate.yml",
    "dashboard/institutional_app.py",
)

REQUIRED_MARKERS = {
    "AGENTS.md": ("LotoIA", "Law 15", "Walk-forward"),
    "docs/governance/POLITICA_ML_ASSISTIVO.md": ("POLITICA_ML_ASSISTIVO_FORMALIZADA",),
    "docs/governance/ADR_LEI15A_CARTAO_REGISTRO_APOSTA.md": ("governanca_soberana", "Lei 15A"),
}


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_PATHS:
        path = ROOT / relative
        if not path.exists():
            errors.append(f"missing required path: {relative}")

    for relative, markers in REQUIRED_MARKERS.items():
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative} missing marker: {marker}")

    if errors:
        print("governance-contract-check: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("governance-contract-check: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
