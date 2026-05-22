from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dashboard.user_app import (
    ONLINE_MARKER,
    USER_DB_PATH,
    _build_light_report_pdf,
    _check_user_contest,
    _generate_user_games,
    _parse_numbers,
    _recent_history_dataframe,
    _render_sidebar,
    _user_indicator,
    render_generate_page,
    render_check_page,
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
    assert len(result["raw_games"]) == 3
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


def test_user_generation_persists_institutional_event(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _LeadCapture:
        lead = {"id": 21, "first_name": "Ana"}
        normalized_whatsapp = "5511999999999"

    class _LeadService:
        def __init__(self, db_path=None):
            captured["lead_db_path"] = db_path

        def capture(self, *_args, **_kwargs):
            return _LeadCapture()

    def _save_generation_event(**kwargs):
        captured["generation"] = kwargs
        return {"id": 77}

    monkeypatch.setattr("dashboard.user_app.LeadCaptureService", _LeadService)
    monkeypatch.setattr("dashboard.user_app.save_generation_event", _save_generation_event)
    monkeypatch.setattr("dashboard.user_app.st.header", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.caption", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.info", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.success", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.button", lambda *args, **kwargs: True)
    monkeypatch.setattr("dashboard.user_app.st.toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr("dashboard.user_app.st.number_input", lambda *args, **kwargs: 1)

    class _Column:
        def text_input(self, label, key=None):
            return "Ana" if "nome" in label.lower() else "5511999999999"

    monkeypatch.setattr("dashboard.user_app.st.columns", lambda count: [_Column() for _ in range(count)])
    monkeypatch.setattr("dashboard.user_app.st.session_state", {})
    monkeypatch.setattr("dashboard.user_app.st.write", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.error", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.radio", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.title", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.set_page_config", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.sidebar", type("Sidebar", (), {"title": lambda self, *a, **k: None, "success": lambda self, *a, **k: None, "radio": lambda self, *a, **k: "Gerar Jogos"})())
    monkeypatch.setattr(
        "dashboard.user_app._generate_user_games",
        lambda count, pool_size, ml_enabled: {
            "count": 1,
            "games": [{"ranking": 1, "numbers": list(range(1, 16)), "final_score": 80.0, "quadra_score": {}}],
            "raw_games": [{"numbers": list(range(1, 16)), "profile_type": "hibrido", "final_score": {"final_score": 80.0}, "quadra_score": {}}],
            "metadata": {"generated_at": "2026-05-22 00:00:00 UTC"},
        },
    )

    render_generate_page([])

    assert captured["lead_db_path"] == USER_DB_PATH
    assert captured["generation"]["origin"] == "user_panel"
    assert captured["generation"]["lead_id"] == 21
    assert len(captured["generation"]["generated_games"]) == 1
    assert "raw_games" not in captured["generation"]


def test_user_check_page_supports_smoke_validation(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("dashboard.user_app.st.header", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.success", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.write", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.error", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.caption", lambda *args, **kwargs: None)
    monkeypatch.setattr("dashboard.user_app.st.checkbox", lambda *args, **kwargs: True)
    monkeypatch.setattr("dashboard.user_app.st.text_input", lambda *args, **kwargs: "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15")
    monkeypatch.setattr("dashboard.user_app.st.button", lambda *args, **kwargs: True)
    monkeypatch.setattr("dashboard.user_app.st.session_state", {
        "user_last_generation": {
            "lead": {"id": 21, "first_name": "Ana"},
            "generation_event_id": 77,
            "raw_games": [
                {"numbers": list(range(1, 16)), "profile_type": "hibrido", "final_score": {"final_score": 80.0}, "quadra_score": {}},
                {"numbers": list(range(2, 17)), "profile_type": "recorrente", "final_score": {"final_score": 70.0}, "quadra_score": {}},
            ],
        }
    })
    monkeypatch.setattr(
        "dashboard.user_app.reconcile_smoke_validation",
        lambda **kwargs: {
            "generation_event_id": kwargs["generation_event_id"],
            "lead_id": kwargs["lead_id"],
            "contest_id": 0,
            "reconciled_games": [
                {
                    "game_index": 1,
                    "numbers": list(range(1, 16)),
                    "hits": 15,
                    "matched_numbers": list(range(1, 16)),
                    "prize_status": "premiado",
                    "prize_tier": "faixa_15",
                },
                {
                    "game_index": 2,
                    "numbers": list(range(2, 17)),
                    "hits": 14,
                    "matched_numbers": list(range(2, 16)),
                    "prize_status": "premiado",
                    "prize_tier": "faixa_14",
                },
            ],
            "prize_count": 2,
            "total_hits": 29,
            "best_hits": 15,
            "status": "reconciliado",
            "baseline_numbers": list(range(1, 16)),
            "source": "smoke_validation_baseline",
        },
    )
    monkeypatch.setattr(
        "dashboard.user_app.save_check_event",
        lambda **kwargs: captured.setdefault("check", kwargs) or {"id": 3},
    )

    render_check_page([])

    assert captured["check"]["contest_id"] == 0
    assert captured["check"]["hits"] == 15
    assert captured["check"]["result_payload"]["source"] == "smoke_validation_baseline"


def test_user_app_import_is_lightweight() -> None:
    result = subprocess.run(
        [sys.executable, "-c", "import dashboard.user_app"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
