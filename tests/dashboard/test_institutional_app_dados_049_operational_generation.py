from __future__ import annotations

import inspect

import dashboard.institutional_clean_law15_runtime as clean_runtime
import dashboard.institutional_app as institutional_app
import dashboard.institutional_operational_generation as operational_generation
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL


def test_build_marker_v25() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v25"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_operational_generation_number_format() -> None:
    assert operational_generation.format_operational_generation_number(1) == "001"
    assert operational_generation.format_operational_generation_number(12) == "012"


def test_operational_index_for_sovereign_batch_only() -> None:
    events = [
        {"id": 114, "analysis_batch_label": "STRUCT_LEI15_CORE_CANDIDATE_001_15D_001", "created_at": "2026-01-01"},
        {"id": 200, "analysis_batch_label": BATCH_LABEL, "created_at": "2026-06-01"},
        {"id": 201, "analysis_batch_label": BATCH_LABEL, "created_at": "2026-06-02"},
    ]
    index = operational_generation.build_operational_generation_index(events)
    assert index[200] == 1
    assert index[201] == 2
    assert 114 not in index
    assert operational_generation.resolve_operational_generation_label(200, operational_index=index) == "001"
    assert operational_generation.resolve_operational_generation_label(201, operational_index=index) == "002"


def test_generation_result_summary_shows_operational_label() -> None:
    source = inspect.getsource(clean_runtime.render_generation_result_summary)
    runtime_source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    assert "Geração operacional" in source
    assert "operational_generation_label" in source
    assert "_attach_operational_generation_label" in runtime_source


def test_analytical_page_reads_postgresql_not_session_only() -> None:
    source = inspect.getsource(institutional_app._render_analytical_page)
    assert "_load_generation_history_light" in source or "_load_generation_history(" in source
    assert "build_operational_generation_index" in source
    assert "session_state" not in source.split("generation_history =")[0]


def test_structural_coverage_reads_postgresql() -> None:
    source = inspect.getsource(institutional_app._render_cobertura_estrutural_page)
    assert "_cached_card_structure_diagnostics_from_db" in source
    assert "postgresql" in source.lower()


def test_public_app_unchanged() -> None:
    assert "m_dados_049" not in inspect.getsource(public_app.main).lower()
