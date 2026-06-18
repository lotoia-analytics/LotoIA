from __future__ import annotations

import inspect

import dashboard.institutional_app as institutional_app
from dashboard.institutional_build import BUILD_MARKER


def test_institutional_app_build_v23() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_clean_runtime_page_source_excludes_prohibited_lei15a_phrases() -> None:
    source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    legacy_phrases = (
        "Leitura operacional Lei 15A",
        "Lei 15 + 1 reserva auditada",
        "15+1",
        "reserva auditada",
    )
    for phrase in legacy_phrases:
        assert phrase not in source, f"prohibited phrase present: {phrase!r}"


def test_clean_runtime_page_uses_operational_layout() -> None:
    source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    assert "render_generation_operation_block" in source
    assert "render_compact_status_chips" in source
