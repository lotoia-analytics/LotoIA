"""M-DADOS-066-FIX-01 — scripts ops psycopg-only (Railway console)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESET_SCRIPT = ROOT / "scripts/ops/m_dados_066_absolute_operational_reset.py"
VALIDATION_SCRIPT = ROOT / "scripts/ops/m_dados_066_post_reset_validation.py"


def _imports_lotoia_package(source: str) -> list[str]:
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("lotoia"):
            offenders.append(node.module)
    return offenders


def test_reset_script_does_not_import_lotoia_packages() -> None:
    source = RESET_SCRIPT.read_text(encoding="utf-8")
    assert _imports_lotoia_package(source) == []
    assert "importlib.util" in source


def test_validation_script_does_not_import_lotoia_packages() -> None:
    source = VALIDATION_SCRIPT.read_text(encoding="utf-8")
    assert _imports_lotoia_package(source) == []


def test_emergency_sql_exists() -> None:
    sql = (ROOT / "scripts/ops/m_dados_066_emergency_reset.sql").read_text(encoding="utf-8")
    assert "DELETE FROM generation_events" in sql
    assert "RESTART WITH 1" in sql
    assert "imported_contests" not in sql.split("DELETE")[1].split("COMMIT")[0]
