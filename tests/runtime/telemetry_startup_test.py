from __future__ import annotations

import ast
from pathlib import Path


def test_dashboard_admin_boot_does_not_import_heavy_modules_at_top_level() -> None:
    source = Path("dashboard/admin_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    top_level_modules = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            top_level_modules.append(node.module)

    blocked = {
        "lotoia.generator.basic_generator",
        "lotoia.backtesting.backtester",
        "lotoia.benchmark.benchmark_engine",
    }

    assert not blocked.intersection(top_level_modules)
