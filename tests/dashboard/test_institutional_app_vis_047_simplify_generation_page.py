from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_clean_law15_runtime as clean_runtime
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER


def _generation_page_source() -> str:
    page_source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    runtime_source = inspect.getsource(clean_runtime)
    return page_source + runtime_source


def test_institutional_app_build_v22() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert BUILD_MARKER == "institutional-adm-runtime-v22"


def test_generation_page_source_includes_required_operational_phrases() -> None:
    source = _generation_page_source()
    for phrase in clean_runtime.REQUIRED_RUNTIME_PHRASES:
        assert phrase in source, f"missing required phrase: {phrase!r}"


def test_generation_page_source_excludes_prohibited_phrases() -> None:
    page_source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    for phrase in clean_runtime.PROHIBITED_RUNTIME_PHRASES:
        assert phrase not in page_source, f"prohibited phrase in page: {phrase!r}"


def test_generation_page_uses_compact_layout_helpers() -> None:
    source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    assert "render_generation_compact_header" in source
    assert "render_generation_operation_block" in source
    assert "render_generation_result_summary" in source
    assert "render_governance_expander" in source
    assert "render_technical_expander" in source
    assert "render_six_bases_expander" in source
    assert "_render_constitutional_status_panel(compact=False)" not in source
    assert "render_lei15a_inoperative_notice" not in source
    assert "SOVEREIGN_GENERATION_STATUS_ACTIVE" not in source
    assert "Runtime Limpo ADM 15" not in source


def test_card_format_label_is_core_002_sovereign_only() -> None:
    assert clean_runtime.CARD_FORMAT_DISPLAY_LABEL == "15 dezenas — CORE_002 soberano"
    assert "Núcleo Lei 15" not in clean_runtime.CARD_FORMAT_DISPLAY_LABEL


def test_sovereign_generation_still_works(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    monkeypatch.setattr(institutional_app.st, "session_state", {})
    monkeypatch.setattr(
        institutional_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002"}],
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": True,
        },
    )

    result = institutional_app._run_clean_law15_generation(requested_count=1)

    assert result.get("blocked") is not True
    assert len(result.get("games") or []) == 1
    assert result.get("generation_mode") == "LEI15_CORE_002_SOVEREIGN"


def test_ml_supervised_still_active_on_generation_path(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "1")

    def _fake(**kwargs):
        return {
            "games": [{"numbers": list(range(1, 16))}],
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": True,
        }

    monkeypatch.setattr(institutional_app, "_invoke_sovereign_adm_generate_best_games", _fake)
    monkeypatch.setattr(institutional_app.st, "session_state", {})
    monkeypatch.setattr(
        institutional_app,
        "get_latest_official_contest",
        lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))},
    )
    monkeypatch.setattr(institutional_app, "load_all_output_signatures", lambda: [])
    monkeypatch.setattr(
        institutional_app,
        "output_commander_validate_games",
        lambda games, **kwargs: {
            "status_comandante_saida": "APROVADO",
            "quantidade_jogos_rejeitados": 0,
            "quantidade_jogos_aprovados": len(games),
            "quantidade_jogos_unicos": len(games),
        },
    )

    result = institutional_app._run_clean_law15_generation(requested_count=1)

    assert result.get("ml_enabled") is True


def test_lei15a_still_inoperative() -> None:
    from lotoia.governance.lei15_core_002_sovereign import lei15a_operational_gate

    gate = lei15a_operational_gate()
    assert gate["open_15a"] is False


def test_public_app_unchanged() -> None:
    source = inspect.getsource(public_app.main)
    assert "institutional_clean_law15_runtime" not in source


def test_institutional_app_imports_cleanly() -> None:
    import dashboard.institutional_app  # noqa: F401
