from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v33"
    assert institutional_app.SOVEREIGN_BATCH_LABEL == BATCH_LABEL


def test_resolve_adm_sovereign_batch_label_rejects_none() -> None:
    with pytest.raises(RuntimeError, match="batch_label=None rejeitado"):
        institutional_app._resolve_adm_sovereign_batch_label(None)


def test_resolve_adm_sovereign_batch_label_rejects_empty() -> None:
    with pytest.raises(RuntimeError, match="batch_label=None rejeitado"):
        institutional_app._resolve_adm_sovereign_batch_label("   ")


def test_resolve_adm_sovereign_batch_label_rejects_non_sovereign() -> None:
    with pytest.raises(RuntimeError, match="Label ADM inválido"):
        institutional_app._resolve_adm_sovereign_batch_label("STRUCT_TEST_15D_001")


def test_resolve_adm_sovereign_batch_label_accepts_sovereign() -> None:
    assert institutional_app._resolve_adm_sovereign_batch_label(BATCH_LABEL) == BATCH_LABEL


def test_generate_direct_15_games_is_legacy_blocked() -> None:
    with pytest.raises(RuntimeError, match="BLK-LEGACY-GEN-001"):
        institutional_app._generate_direct_15_games(
            total_games=1,
            seed=1,
            history_frequency={},
            latest_numbers=set(),
            batch_number_usage={},
            batch_profile_usage={},
            batch_total_games=1,
            core_numbers=[],
            discouraged_numbers=[],
            max_frequency_ratio=1.0,
            min_frequency_ratio=0.0,
            preferred_profile_ratios={},
            odd_min=5,
            odd_max=10,
            even_min=5,
            even_max=10,
            sequence_max=15,
            coverage_min=0.0,
            entropy_min=0.0,
            repeat_min=0,
            repeat_max=15,
            preferred_parity_pairs=[],
            allowed_parity_pairs=[],
        )


def test_run_clean_law15_generation_blocked_with_flag_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    result = institutional_app._run_clean_law15_generation(requested_count=10)

    assert result["blocked"] is True
    assert result["games"] == []
    assert result["analysis_batch_label"] == BATCH_LABEL
    assert result["fill_diagnostics"]["sovereign_generation_path"] == "generate_best_games"
    assert "SOVEREIGN_GENERATION_BLOCKED" in str(result["commander_report"]["motivo_bloqueio"])


def test_run_clean_law15_generation_uses_generate_best_games_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_best_games(**kwargs):
        captured.update(kwargs)
        return {
            "games": [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002"}],
            "generation_path": "LEI15_CORE_002",
        }

    monkeypatch.setattr(institutional_app, "_invoke_sovereign_adm_generate_best_games", _fake_generate_best_games)
    monkeypatch.setattr(institutional_app, "get_latest_official_contest", lambda: {"contest_number": 3700, "dezenas": list(range(1, 16))})
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
    monkeypatch.setattr(institutional_app.st, "session_state", {})

    result = institutional_app._run_clean_law15_generation(requested_count=1)

    assert captured["batch_label"] == BATCH_LABEL
    assert captured["requested_count"] == 1
    assert result["sovereign_generation_path"] == "generate_best_games"
    assert result["generation_mode"] == "LEI15_CORE_002_SOVEREIGN"
    assert len(result["games"]) == 1


def test_orphan_generation_page_not_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    sidebar_calls: list[str] = []
    monkeypatch.setattr(institutional_app.st, "session_state", {})
    monkeypatch.setattr(institutional_app, "_apply_institutional_styles", lambda: None)
    monkeypatch.setattr(institutional_app, "_render_sidebar_logo", lambda: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "divider", lambda *args, **kwargs: None)
    monkeypatch.setattr(institutional_app.st.sidebar, "expander", lambda *args, **kwargs: institutional_app.st.sidebar)
    monkeypatch.setattr(
        institutional_app.st.sidebar,
        "button",
        lambda label, **kwargs: sidebar_calls.append(str(label)),
    )
    monkeypatch.setattr(institutional_app, "_resolve_active_commit", lambda: "test")
    monkeypatch.setattr(institutional_app, "_render_constitutional_status_panel", lambda **kwargs: None)

    page = institutional_app._render_sidebar("generation", {"counts": {}, "latest": {}})

    assert page == "clean_law15_generation"


def test_run_clean_law15_generation_source_uses_sovereign_helper() -> None:
    source = inspect.getsource(institutional_app._run_clean_law15_generation)
    assert "_invoke_sovereign_adm_generate_best_games" in source
    assert "_generate_direct_15_games" not in source


def test_run_institutional_generation_source_uses_sovereign_helper() -> None:
    source = inspect.getsource(institutional_app._run_institutional_generation)
    assert "_invoke_sovereign_adm_generate_best_games" in source
    assert "_generate_direct_15_games" not in source


def test_m_vis_031_constitutional_status_blocked_when_env_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    lines = institutional_app._constitutional_status_lines()

    assert lines["core_id"] == "LEI15_CORE_002"
    assert lines["batch_label"] == BATCH_LABEL
    assert lines["generation_status"] == "BLOQUEADA"
    assert "REDEFINIDA" in lines["lei15a_status"]
    assert "ASSISTIVO" in lines["ml_status"]
    assert lines["history_status"] == "PROTEGIDO"

    source = inspect.getsource(institutional_app._render_delete_history_page)
    assert "Apagar historico persistido" not in source
    assert "_purge_institutional_history_tables" not in source
