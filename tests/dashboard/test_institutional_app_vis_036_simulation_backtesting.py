from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_simulation_backtesting as simulation_backtesting
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import ENV_GENERATION_ENABLED


def test_institutional_app_imports() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert institutional_app.APP_BUILD == "institutional-adm-runtime-v24"


def test_simulation_backtesting_module_imports() -> None:
    assert callable(simulation_backtesting.build_simulation_backtesting_snapshot)
    assert callable(simulation_backtesting.render_institutional_simulation_backtesting_page)


def test_simulation_backtesting_snapshot_has_temporal_cut_and_windows() -> None:
    payload = simulation_backtesting.build_simulation_backtesting_snapshot(generation_blocked=True)
    text_blob = str(payload)

    assert payload["execucao_backtest_automatica"] is False
    assert payload["geracao_real"] is False
    assert payload["generation_status"] == "BLOQUEADA"
    assert "X-1" in payload["temporal_cut_rule"]
    assert "walk-forward" in text_blob.lower() or "Walk-forward" in text_blob
    assert len(payload["walk_forward_windows"]) == 3
    assert len(payload["six_bases_backtesting"]) == 6
    assert simulation_backtesting.SIX_BASES_QUOTE in text_blob
    assert "Conferir Resultados" in text_blob
    assert "vazamento temporal" in text_blob.lower()


def test_simulation_backtesting_separates_flows_from_conference_and_generation() -> None:
    payload = simulation_backtesting.build_simulation_backtesting_snapshot(generation_blocked=True)
    flows = {row["fluxo"] for row in payload["flow_separation"]}

    assert "Conferir Resultados" in flows
    assert "Simular Resultados (session)" in flows
    assert "Simulação Institucional / Backtesting" in flows
    assert "Geração operacional" in flows
    conference = next(r for r in payload["flow_separation"] if r["fluxo"] == "Conferir Resultados")
    assert conference["geracao"] == "Não gera"


def test_simulation_backtesting_module_is_read_only_without_generation_or_purge() -> None:
    source = inspect.getsource(simulation_backtesting.render_institutional_simulation_backtesting_page)
    forbidden = (
        "_run_clean_law15_generation",
        "_run_institutional_simulation",
        "generate_best_games",
        "run_backtest",
        "execute_purge",
        "dry_run_history_cleanup",
        "st.button",
        "st.form",
    )
    for token in forbidden:
        assert token not in source


def test_simulation_page_references_institutional_backtesting_separation() -> None:
    source = inspect.getsource(institutional_app._render_simulation_page)
    assert "Simulação Institucional / Backtesting" in source
    assert "Conferir Resultados" in source
    assert "Session-only" in source


def test_institutional_simulation_backtesting_route_registered() -> None:
    assert "institutional_simulation_backtesting" in institutional_app.PAGE_TARGETS.values()
    assert (
        institutional_app.PAGE_TARGETS["Simulação Institucional / Backtesting"]
        == "institutional_simulation_backtesting"
    )


def test_m_vis_031_regression_blocks_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "0")
    result = institutional_app._run_clean_law15_generation(requested_count=5)
    assert result["blocked"] is True


def test_m_vis_035_regression_ml_assistive_module_exists() -> None:
    from dashboard import institutional_ml_assistive

    payload = institutional_ml_assistive.build_ml_assistive_snapshot()
    assert payload["ml_operacional"] is True


def test_m_vis_034_regression_structural_coverage_exists() -> None:
    from dashboard import institutional_structural_coverage

    assert len(
        institutional_structural_coverage.build_structural_coverage_snapshot(generation_blocked=True)[
            "six_bases_rows"
        ]
    ) == 6
