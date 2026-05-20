from __future__ import annotations

import sys
import types
from contextlib import contextmanager

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app
from lotoia.models.draw import Draw


class _DummyColumn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def metric(self, *args, **kwargs):
        return None

    def write(self, *args, **kwargs):
        return None

    def download_button(self, *args, **kwargs):
        return None

    def text_input(self, *args, **kwargs):
        return ""

    def number_input(self, *args, **kwargs):
        return 1

    def radio(self, *args, **kwargs):
        return ""

    def selectbox(self, *args, **kwargs):
        return ""


@contextmanager
def _dummy_context():
    yield None


def _patch_streamlit(monkeypatch) -> None:
    monkeypatch.setattr(admin_app.st, "set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "plotly_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "stop", lambda *args, **kwargs: (_ for _ in ()).throw(SystemExit))
    monkeypatch.setattr(admin_app.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(admin_app.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st, "selectbox", lambda *args, **kwargs: "")
    monkeypatch.setattr(admin_app.st, "tabs", lambda labels: [_dummy_context() for _ in labels])
    monkeypatch.setattr(admin_app.st, "spinner", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app.st, "container", lambda *args, **kwargs: _dummy_context())
    monkeypatch.setattr(admin_app.st, "columns", lambda count: [_DummyColumn() for _ in range(count)])
    monkeypatch.setattr(admin_app.st, "radio", lambda *args, **kwargs: "geracao_jogos")
    monkeypatch.setattr(admin_app.st, "session_state", {})
    monkeypatch.setattr(admin_app.st.components, "v1", type("V1", (), {"html": lambda *args, **kwargs: None})())


def test_sidebar_navigation_includes_institutional_pages(monkeypatch) -> None:
    monkeypatch.setattr(admin_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(admin_app.st.sidebar, "radio", lambda *args, **kwargs: "observability")

    page = admin_app._sidebar_navigation()

    assert page == "observability"


def test_analytics_base_tables_accept_draw_objects(monkeypatch) -> None:
    monkeypatch.setattr(
        admin_app,
        "_load_draws",
        lambda: [
            Draw(contest=1, date=None, numbers=list(range(1, 16))),
            Draw(contest=2, date=None, numbers=list(range(2, 17))),
        ],
    )
    admin_app._historical_dataset.clear()
    admin_app._analytics_base_tables.clear()

    tables = admin_app._analytics_base_tables()

    assert not tables["history"].empty
    assert list(tables["history"]["concurso"]) == [1, 2]


def test_observability_and_reports_pages_render_safely(monkeypatch) -> None:
    _patch_streamlit(monkeypatch)
    success_messages = []
    monkeypatch.setattr(admin_app.st, "success", lambda message, *args, **kwargs: success_messages.append(message))
    monkeypatch.setattr(admin_app, "_observability_tables", lambda: {"logs": admin_app.pd.DataFrame(), "audit": admin_app.pd.DataFrame()})
    monkeypatch.setattr(admin_app, "_runtime_health", lambda: {
        "response_time_ms": 0.0,
        "total_runs": 0,
        "failures": 0,
        "avg_generation_ms": 0.0,
        "avg_check_ms": 0.0,
        "ml_events": 0,
        "report_events": 0,
        "snapshot_events": 0,
    })
    monkeypatch.setattr(admin_app, "_load_draws", lambda: [])
    monkeypatch.setattr(admin_app, "_sqlite_health_check", lambda: True)
    monkeypatch.setattr(admin_app, "_sidebar_navigation", lambda: "observability")

    admin_app.render_observability_page()
    admin_app.render_reports_engine_page()
    admin_app.main()
    assert "INSTITUTIONAL DASHBOARD ACTIVE" in success_messages
