from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_clean_law15_runtime as clean_runtime
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_build_v21() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert BUILD_MARKER == "institutional-adm-runtime-v21"


def test_clean_runtime_page_source_excludes_prohibited_lei15a_phrases() -> None:
    source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    for phrase in clean_runtime.PROHIBITED_RUNTIME_PHRASES:
        assert phrase not in source, f"prohibited phrase present: {phrase!r}"
    assert "format_func=_clean_law15_format_label" not in source
    assert "OFFICIAL_CARD_FORMATS" not in source
    assert '_render_institutional_matrix_reading_section' not in source


def test_clean_runtime_page_source_includes_required_constitutional_phrases() -> None:
    source = inspect.getsource(institutional_app._render_clean_law15_generation_page)
    assert "render_lei15a_inoperative_notice" in source
    assert "render_sovereign_runtime_format_panel" in source
    assert "ADM_RUNTIME_ACTIVE_CARD_FORMAT" in source
    assert "SOVEREIGN_RUNTIME_FORMAT_LABEL" in source
    assert "Gerar CORE_002 (15D)" in source


def test_clean_runtime_module_documents_15d_only() -> None:
    assert clean_runtime.ADM_RUNTIME_ACTIVE_CARD_FORMAT == 15
    assert BATCH_LABEL in clean_runtime.SOVEREIGN_RUNTIME_FORMAT_LABEL


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


def test_public_app_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(public_app.main)
    assert "institutional_clean_law15_runtime" not in source


def test_m_gov_038_regression_lei15a_governance_module_exists() -> None:
    from dashboard import institutional_lei15a_governance

    assert "INOPERANTE" in institutional_lei15a_governance.LEI15A_FORMAL_STATUS


def test_m_ger_044_regression_generation_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    assert institutional_app._is_sovereign_generation_blocked() is False
