from __future__ import annotations

import ast
from pathlib import Path


ALLOWED_CALLS = {
    ("get_official_contest", "_load_official_history_contest"),
    ("get_latest_official_contest", "get_official_contest"),
    ("get_previous_official_contest", "get_official_contest"),
    ("get_previous_official_contest", "get_latest_official_contest"),
    ("_load_previous_contest_numbers_for_rfe", "get_official_contest"),
    ("_load_previous_contest_numbers_for_rfe", "get_latest_official_contest"),
    ("_run_institutional_conference", "_load_official_history_contest"),
    ("_render_audit_monitoring_page", "_load_official_history_contest"),
    ("_render_conference_page", "get_latest_official_contest"),
    ("_render_conference_page", "get_official_contest"),
    ("_run_clean_law15_generation", "get_latest_official_contest"),
}


def test_official_history_gateway_callsites_are_consolidated() -> None:
    source_path = Path(__file__).resolve().parents[1] / "dashboard" / "institutional_app.py"
    source = source_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)

    callsites: set[tuple[str, str]] = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.visit_FunctionDef(node)

        def visit_Call(self, node: ast.Call) -> None:
            if self.stack and isinstance(node.func, ast.Name):
                callee = node.func.id
                caller = self.stack[-1]
                if callee in {
                    "_load_official_history_contest",
                    "get_official_contest",
                    "get_latest_official_contest",
                    "get_previous_official_contest",
                }:
                    callsites.add((caller, callee))
            self.generic_visit(node)

    Visitor().visit(tree)

    assert callsites == ALLOWED_CALLS
