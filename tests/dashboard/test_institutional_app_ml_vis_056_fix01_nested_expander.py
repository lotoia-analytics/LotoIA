from __future__ import annotations

import ast
import inspect

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_calibration_cockpit as cockpit


def _nested_expander_functions(source: str) -> list[str]:
    tree = ast.parse(source)
    offenders: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self._expander_depth = 0
            self._current_function: str | None = None

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            previous_function = self._current_function
            previous_depth = self._expander_depth
            self._current_function = node.name
            self._expander_depth = 0
            self.generic_visit(node)
            self._current_function = previous_function
            self._expander_depth = previous_depth

        def visit_With(self, node: ast.With) -> None:
            is_expander = any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(getattr(item.context_expr.func, "attr", None), str)
                and item.context_expr.func.attr == "expander"
                for item in node.items
            )
            if is_expander:
                self._expander_depth += 1
                if self._expander_depth > 1 and self._current_function:
                    offenders.append(self._current_function)
            self.generic_visit(node)
            if is_expander:
                self._expander_depth -= 1

    Visitor().visit(tree)
    return sorted(set(offenders))


def test_central_ml_page_has_no_nested_expanders() -> None:
    sources = [
        inspect.getsource(institutional_app._render_central_ml_diagnostics_page),
        inspect.getsource(institutional_app._render_central_ml_observational_alerts),
        inspect.getsource(institutional_app._render_central_ml_observational_history),
    ]
    sources.append(inspect.getsource(cockpit._render_technical_expanders))
    for source in sources:
        assert _nested_expander_functions(source) == []


def test_central_ml_page_uses_sibling_expanders() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "Detalhes técnicos adicionais" in source
    assert "Histórico de decisões ADM (observacional)" in source
    assert "_render_central_ml_observational_history" in source
    assert "_render_central_ml_observational_expander" not in source


def test_central_ml_page_still_uses_cockpit() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "render_ml_calibration_cockpit" in source
