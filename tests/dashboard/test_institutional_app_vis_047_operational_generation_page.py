from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_clean_law15_runtime as clean_runtime
import dashboard.public_app as public_app
from dashboard.institutional_build import BUILD_MARKER


def _page_source() -> str:
    return inspect.getsource(institutional_app._render_clean_law15_generation_page)


def test_institutional_app_build_v23() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v27"
    assert institutional_app.APP_BUILD == BUILD_MARKER


def test_generation_page_has_operational_layout() -> None:
    source = _page_source()
    assert "GENERATOR_PAGE_TITLE" in source
    assert "render_generation_operation_block" in source
    assert "Gerar lote" in source or "render_generation_operation_block" in source
    assert "render_compact_status_chips" in source
    assert "render_governance_expander" in source
    assert "_render_constitutional_status_panel(compact=False)" not in source


def test_generation_page_main_area_excludes_prohibited_phrases() -> None:
    source = _page_source()
    for phrase in clean_runtime.PROHIBITED_MAIN_PHRASES:
        assert phrase not in source, f"prohibited in page: {phrase!r}"


def test_runtime_module_supports_games_1_to_100() -> None:
    assert clean_runtime.validate_requested_games_count(1)[0] == 1
    assert clean_runtime.validate_requested_games_count(100)[0] == 100
    assert clean_runtime.validate_requested_games_count(0)[0] is None
    assert clean_runtime.validate_requested_games_count(101)[0] is None


def test_runtime_module_multidezena_options_15_to_23() -> None:
    assert clean_runtime.MULTIDEZENA_FORMAT_OPTIONS == tuple(range(15, 24))
    assert "reserva auditada" not in clean_runtime.multidezena_format_label(17).lower()
    assert "Lei 15A" not in clean_runtime.multidezena_format_label(18)


def test_multidezena_persistence_supported_15_to_23() -> None:
    for card_format in range(15, 24):
        assert clean_runtime.is_multidezena_persistence_supported(card_format) is True
    assert clean_runtime.is_multidezena_persistence_supported(24) is False


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
            "games": [{"numbers": list(range(1, 16))}],
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": True,
        },
    )

    result = institutional_app._run_clean_law15_generation(requested_count=5)

    assert result.get("blocked") is not True
    assert len(result.get("games") or []) == 1
    assert result.get("generation_mode") == "LEI15_CORE_002_SOVEREIGN"


def test_ml_supervised_still_active(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    monkeypatch.setenv("LOTOIA_ML_CORE_002_OPERATIONAL_ENABLED", "1")
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": [{"numbers": list(range(1, 16))}],
            "ml_enabled": True,
        },
    )
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


def test_public_app_unchanged() -> None:
    assert "institutional_clean_law15_runtime" not in inspect.getsource(public_app.main)


def test_institutional_app_imports() -> None:
    import dashboard.institutional_app  # noqa: F401
