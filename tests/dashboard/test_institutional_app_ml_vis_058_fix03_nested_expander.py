"""M-ML-VIS-058-FIX-03 — Central ML sem expander aninhado.

Garante que _render_central_ml_observational_alerts não usa st.expander
(quando chamada dentro do expander observacional da página) e que a auditoria
de lotes excluídos permanece acessível via seção markdown.
"""

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


CENTRAL_ML_SOURCES = (
    inspect.getsource(institutional_app._render_central_ml_diagnostics_page),
    inspect.getsource(institutional_app._render_central_ml_observational_alerts),
    inspect.getsource(institutional_app._render_central_ml_observational_history),
    inspect.getsource(cockpit._render_technical_expanders),
    inspect.getsource(cockpit.render_ml_calibration_cockpit),
)


def test_central_ml_functions_have_no_intra_function_nested_expanders() -> None:
    for source in CENTRAL_ML_SOURCES:
        assert _nested_expander_functions(source) == []


def test_observational_alerts_has_no_expander() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_observational_alerts)
    assert "st.expander" not in source


def test_observational_alerts_keeps_excluded_batches_audit_section() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_observational_alerts)
    assert "Lotes excluídos da leitura ativa — auditoria técnica" in source
    assert "excluded_batches_audit" in source


def test_central_ml_page_wraps_observational_in_sibling_expander() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert 'st.expander("Diagnóstico ML observacional (alertas vazamento lateral)"' in source
    assert "_render_central_ml_observational_alerts" in source


def test_central_ml_page_still_uses_cockpit() -> None:
    source = inspect.getsource(institutional_app._render_central_ml_diagnostics_page)
    assert "render_ml_calibration_cockpit" in source


def test_build_marker_bumped_for_fix03() -> None:
    from dashboard.institutional_build import BUILD_MARKER, DEPRECATED_BUILD_MARKERS

    assert BUILD_MARKER == "institutional-adm-runtime-v50"
    assert "institutional-adm-runtime-v49" in DEPRECATED_BUILD_MARKERS
