from __future__ import annotations

import ast
from pathlib import Path


def _top_level_imports(source: str) -> list[str]:
    tree = ast.parse(source)
    imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_streamlit_entrypoints_do_not_eagerly_import_heavy_layers() -> None:
    entrypoints = [
        Path("dashboard/app.py"),
        Path("dashboard/public_app.py"),
        Path("dashboard/user_app.py"),
        Path("dashboard/admin_app.py"),
    ]
    blocked_imports = {
        "lotoia.generator.basic_generator",
        "lotoia.backtesting",
        "lotoia.benchmark",
        "lotoia.generator",
        "lotoia.backtesting.backtester",
        "lotoia.benchmark.benchmark_engine",
    }

    for entrypoint in entrypoints:
        source = entrypoint.read_text(encoding="utf-8")
        for imported in _top_level_imports(source):
            assert imported not in blocked_imports, f"{imported} found at top level in {entrypoint}"
