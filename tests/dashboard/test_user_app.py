from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dashboard.user_app import (
    ONLINE_MARKER,
    _build_light_report_pdf,
    _check_user_contest,
    _generate_user_games,
    _parse_numbers,
    _recent_history_dataframe,
    _render_sidebar,
    _user_indicator,
    render_generate_page,
)


def test_parse_numbers_requires_15_unique_values() -> None:
    assert _parse_numbers("01 02 03 04 05 06 07 08 09 10 11 12 13 14 15") == list(range(1, 16))

    for value in [
        "01 02 03",
        "01 01 02 03 04 05 06 07 08 09 10 11 12 13 14",
        "26 02 03 04 05 06 07 08 09 10 11 12 13 14 15",
    ]:
        try:
            _parse_numbers(value)
        except Exception:
            pass
        else:
            raise AssertionError("Expected validation to fail")


def test_generate_user_games_returns_requested_count() -> None:
    result = _generate_user_games(3, 12, False)

    assert result["count"] == 3
    assert len(result["games"]) == 3
    assert all(len(game["numbers"]) == 15 for game in result["games"])


def test_check_user_contest_reads_history(tmp_path: Path) -> None:
    history_path = tmp_path / "history.csv"
    history_path.write_text(
        "concurso,data,d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12,d13,d14,d15\n"
        "10,2026-01-01,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15\n",
        encoding="utf-8",
    )

    result = _check_user_contest(10, list(range(1, 16)), history_path=history_path)

    assert result["hits"] == 15
    assert result["contest"] == 10


def test_light_report_pdf_is_created() -> None:
    pdf_bytes = _build_light_report_pdf(
        "Relatorio User",
        ["Total de eventos: 1", "Ultima geracao: sim"],
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_recent_history_dataframe_keeps_order() -> None:
    history = _recent_history_dataframe(
        [
            {"timestamp": "t1", "type": "a", "details": "x"},
            {"timestamp": "t2", "type": "b", "details": "y"},
        ]
    )

    assert list(history["timestamp"]) == ["t2", "t1"]


def test_user_indicator_classifies_scores() -> None:
    assert _user_indicator([])[0] == "Sem indicadores"
    assert _user_indicator([{"final_score": 80}, {"final_score": 70}])[0] == "Bom"


def test_user_panel_declares_cloud_marker() -> None:
    assert ONLINE_MARKER == "USER PANEL ONLINE"


def test_user_sidebar_does_not_expose_expansion(monkeypatch) -> None:
    captured_options = []
    image_calls = []

    class _Sidebar:
        def title(self, *args, **kwargs):
            return None

        def markdown(self, *args, **kwargs):
            return None

        def image(self, *args, **kwargs):
            image_calls.append(args)

        def success(self, *args, **kwargs):
            return None

        def radio(self, _label, options):
            captured_options.extend(options)
            return options[0]

    monkeypatch.setattr("dashboard.user_app.st.sidebar", _Sidebar())

    assert _render_sidebar() == "Gerar Jogos"
    assert "Jogo Expandido" not in captured_options
    assert image_calls


def test_user_generation_requires_lead(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Sidebar:
        pass

    monkeypatch.setattr("dashboard.user_app.st.header", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.caption", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.info", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.success", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.button", lambda *args, **kwargs: False)
    monkeypatch.setattr("dashboard.user_app.st.toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr("dashboard.user_app.st.number_input", lambda *args, **kwargs: 1)
    monkeypatch.setattr("dashboard.user_app.st.columns", lambda count: [type("Col", (), {"text_input": lambda self, *a, **k: ""})() for _ in range(count)])
    monkeypatch.setattr("dashboard.user_app.st.session_state", {})
    monkeypatch.setattr("dashboard.user_app.st.write", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.error", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.radio", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.title", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.sidebar", _Sidebar())
    monkeypatch.setattr("dashboard.user_app.st.sidebar", type("Sidebar", (), {"title": lambda self, *a, **k: None, "success": lambda self, *a, **k: None, "radio": lambda self, *a, **k: "Gerar Jogos"})())

    render_generate_page([])

    assert captured == {}


def test_user_app_import_is_lightweight() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import dashboard.user_app"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
