from __future__ import annotations

import inspect

import pytest

import dashboard.institutional_app as institutional_app
import dashboard.institutional_ml_assistive as ml_assistive
import dashboard.institutional_supervised_ml as supervised_ml
import dashboard.public_app as public_app
import dashboard.public_surface as public_surface
from dashboard.institutional_build import BUILD_MARKER
from lotoia.governance.lei15_core_002_sovereign import BATCH_LABEL, ENV_GENERATION_ENABLED


def test_institutional_app_build_v19() -> None:
    assert institutional_app.APP_BUILD == BUILD_MARKER
    assert BUILD_MARKER == "institutional-adm-runtime-v24"


def test_supervised_ml_active_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, raising=False)
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    assert supervised_ml.is_ml_operational_enabled() is True
    assert supervised_ml.is_adm_supervised_ml_active() is True
    assert supervised_ml.supervised_ml_status_label() == supervised_ml.SUPERVISED_ML_STATUS_ACTIVE


def test_supervised_ml_blocked_when_env_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "0")
    monkeypatch.setenv(ENV_GENERATION_ENABLED, "1")
    assert supervised_ml.is_adm_supervised_ml_active() is False
    with pytest.raises(RuntimeError, match="ml_enabled=True rejeitado"):
        supervised_ml.resolve_adm_ml_enabled(ml_enabled=True, batch_label=BATCH_LABEL)


def test_ml_enabled_true_rejected_batch_label_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "1")
    with pytest.raises(RuntimeError, match="batch_label=None"):
        supervised_ml.resolve_adm_ml_enabled(ml_enabled=True, batch_label=None)


def test_ml_enabled_rejected_non_sovereign_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "1")
    with pytest.raises(RuntimeError, match="label não soberano"):
        supervised_ml.resolve_adm_ml_enabled(
            ml_enabled=True,
            batch_label="STRUCT_TEST_15D_001",
        )


def test_invoke_sovereign_path_uses_ml_when_operational(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate(**kwargs):
        captured.update(kwargs)
        games = [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002", "ml_enabled": True}]
        return {"games": games, "generation_path": "LEI15_CORE_002"}

    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "1")
    monkeypatch.setattr(
        "lotoia.generator.basic_generator.generate_best_games",
        _fake_generate,
    )

    payload = institutional_app._invoke_sovereign_adm_generate_best_games(
        requested_count=1,
        batch_label=BATCH_LABEL,
    )

    assert captured["batch_label"] == BATCH_LABEL
    assert captured["ml_enabled"] is True
    assert payload["ml_enabled"] is True


def test_run_clean_law15_generation_includes_ml_metadata(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "1")
    monkeypatch.setattr(
        institutional_app,
        "_invoke_sovereign_adm_generate_best_games",
        lambda **kwargs: {
            "games": [{"numbers": list(range(1, 16)), "generation_path": "LEI15_CORE_002"}],
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": True,
            "analysis_batch_label": BATCH_LABEL,
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
    assert "SUPERVISIONADO" in str(result.get("ml_operational_status", ""))


def test_persist_path_records_ml_trace(
    monkeypatch: pytest.MonkeyPatch,
    sovereign_generation_enabled,
) -> None:
    captured: dict[str, object] = {}

    def _fake_persist(**kwargs):
        captured.update(kwargs)
        return {"generation_event_id": 1001, "games_count": 1}

    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "1")
    monkeypatch.setattr(institutional_app, "_persist_generation_snapshot", _fake_persist)
    monkeypatch.setattr(institutional_app, "_load_latest_contest_summary", lambda: {"contest_number": 3700})
    monkeypatch.setattr(
        institutional_app,
        "validate_lei15_lei15a_runtime_contract",
        lambda **kwargs: {"persistence_allowed": True},
    )

    games = [
        {
            "numbers": list(range(1, 16)),
            "generation_path": "LEI15_CORE_002",
            "ml_enabled": True,
            "score_ml": 42.5,
            "score_ml_details": {
                "score_ml": 42.5,
                "model_version": "historical_recalibrated_v2",
                "feature_schema_version": "score-ml-features-v0.1.0",
                "attribution": [{"feature": "final_score_norm", "contribution": 1.0}],
                "features": {"final_score_norm": 0.8},
                "calibration": {"status": "active"},
            },
        }
    ]
    result = {
        "games": games,
        "requested_count": 1,
        "analysis_batch_label": BATCH_LABEL,
        "ml_enabled": True,
        "seed": 42,
        "batch_id": "ml-smoke",
        "fill_diagnostics": {"accepted_games": 1, "valid_candidates_found": 1, "attempts_used": 1, "fill_completed": True},
    }

    persisted = institutional_app._persist_clean_law15_generation_history(
        result=result,
        selected_card_format=15,
    )

    assert persisted["generation_event_id"] == 1001
    ctx = captured.get("generation_context") or {}
    assert ctx.get("ml_enabled") is True
    assert ctx.get("decision_trace")
    assert ctx.get("feature_attribution")
    assert ctx.get("ml_six_bases_reading")
    assert len(ctx.get("ml_six_bases_reading") or []) == 6


def test_ml_assistive_snapshot_operational_fields() -> None:
    payload = ml_assistive.build_ml_assistive_snapshot()
    assert payload["ml_operacional"] is True
    assert payload["decision_trace_enabled"] is True
    assert payload["feature_attribution_enabled"] is True
    assert payload["ml_six_bases_enabled"] is True
    assert payload["generation_cmd"] is False
    assert len(payload["ml_six_bases_relation"]) == 6


def test_ml_assistive_read_only_when_ml_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(supervised_ml.ENV_ML_OPERATIONAL_ENABLED, "0")
    payload = ml_assistive.build_ml_assistive_snapshot()
    assert payload["ml_operacional"] is False


def test_public_app_does_not_run_operational_ml(monkeypatch: pytest.MonkeyPatch) -> None:
    source = inspect.getsource(public_surface.render_public_app)
    assert "generate_best_games" not in source
    assert "institutional_supervised_ml" not in source
    monkeypatch.delenv("LOTOIA_DASHBOARD_MODE", raising=False)
    calls: list[str] = []
    monkeypatch.setattr(public_app, "_configure_public_page", lambda: None)
    monkeypatch.setattr(public_app, "_render_public_boot_marker", lambda: None)
    monkeypatch.setattr(public_app, "render_public_app", lambda **k: calls.append("public"))
    monkeypatch.setattr(public_app, "render_institutional_adm", lambda: calls.append("adm"))
    public_app.main()
    assert calls == ["public"]


def test_legacy_generate_direct_15_still_blocked() -> None:
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


def test_lei15a_has_no_operational_effect() -> None:
    from lotoia.governance.lei15_core_002_sovereign import lei15a_operational_gate

    gate = lei15a_operational_gate()
    assert gate["open_15a"] is False


def test_governance_mission_registry_includes_m_ml_045() -> None:
    from dashboard import institutional_governance

    mission_ids = {row["id"] for row in institutional_governance.MISSION_ROWS}
    assert "M-ML-045" in mission_ids


def test_activation_snapshot_documents_supervised_path() -> None:
    payload = supervised_ml.build_supervised_ml_activation_snapshot()
    assert payload["batch_label"] == BATCH_LABEL
    assert payload["ml_enabled_default"] is True
    assert payload["ml_operational_active"] is True


def test_m_ger_044_regression_sovereign_generation_still_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dashboard import institutional_sovereign_generation as sovereign_gen

    monkeypatch.delenv(ENV_GENERATION_ENABLED, raising=False)
    assert sovereign_gen.is_adm_sovereign_generation_active() is True


def test_m_lei15_003_regression_batch_label_none_rejected() -> None:
    with pytest.raises(RuntimeError, match="batch_label=None"):
        institutional_app._resolve_adm_sovereign_batch_label(None)
