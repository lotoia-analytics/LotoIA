from __future__ import annotations

import sys
import types

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app
import dashboard.app as cloud_app
import dashboard.labels as dashboard_labels
import dashboard.public_app as public_cloud_app


def test_streamlit_cloud_entrypoint_delegates_to_institutional_dashboard() -> None:
    assert cloud_app.main is admin_app.main
    assert public_cloud_app.main is admin_app.main


def test_institutional_sidebar_contains_full_navigation(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(admin_app.st.sidebar, "markdown", lambda *args, **kwargs: None)

    def _radio(label, options, **kwargs):
        captured["label"] = label
        captured["options"] = list(options)
        return "observability"

    monkeypatch.setattr(admin_app.st.sidebar, "radio", _radio)

    page = admin_app._sidebar_navigation()

    assert page == "observability"
    assert captured["label"] == "Navegao"
    assert captured["options"] == [
        "geracao_jogos",
        "conferir_jogos",
        "estatisticas_historicas",
        "historical_intelligence",
        "analytics_intelligence",
        "ml_intelligence",
        "jogo_expandido_experimental",
        "backtesting",
        "calibracao_experimental",
        "benchmark_cientifico",
        "historico_experimental",
        "relatorios",
        "ml_governance",
        "observability",
        "reports_engine",
    ]


def test_shared_dashboard_registry_contains_expansion_page() -> None:
    assert "jogo_expandido_experimental" in dashboard_labels.PAGES
    assert dashboard_labels.LABELS["jogo_expandido_experimental"] == "Jogo Expandido (Experimental)"
    assert admin_app.PAGES is dashboard_labels.PAGES
    assert admin_app.LABELS is dashboard_labels.LABELS
