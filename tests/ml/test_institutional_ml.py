from __future__ import annotations

import sys
import types
from copy import deepcopy

import lotoia.ml as lotoia_ml

if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    pyplot = types.ModuleType("matplotlib.pyplot")
    pyplot.subplots = lambda *args, **kwargs: (type("Fig", (), {"add_axes": lambda *a, **k: type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: type("Tbl", (), {"auto_set_font_size": lambda *a, **k: None, "set_fontsize": lambda *a, **k: None, "scale": lambda *a, **k: None})()})(), "savefig": lambda *a, **k: None})(), type("Ax", (), {"axis": lambda *a, **k: None, "text": lambda *a, **k: None, "table": lambda *a, **k: None})())
    pyplot.close = lambda *args, **kwargs: None
    matplotlib.pyplot = pyplot  # type: ignore[attr-defined]
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.pyplot"] = pyplot

import dashboard.admin_app as admin_app


def _sample_game() -> dict[str, object]:
    return {
        "numbers": [1, 2, 3, 4, 5, 7, 9, 11, 13, 15, 18, 20, 22, 24, 25],
        "odd": 8,
        "even": 7,
        "sum": 204,
        "final_score": {"final_score": 81.0, "components": {}},
        "quadra_score": {"found_quadras": 4, "average_rank": 10.0},
        "hits": 11,
    }


def test_ml_helpers_keep_temporal_and_ranking_contracts() -> None:
    game = _sample_game()
    features = lotoia_ml.extract_score_ml_features(game)
    scorer = lotoia_ml.InterpretableLinearScoreML()
    result = scorer.score(game)
    reranked = lotoia_ml.supervised_rerank_games([deepcopy(game), deepcopy(game)], model=scorer)

    assert features
    assert result.score_ml >= 0
    assert set(result.features) == set(features)
    assert round(result.features["odd_balance"], 4) == round(features["odd_balance"], 4)
    assert len(reranked) == 2
    assert all("score_ml" in item for item in reranked)
    assert scorer.calibration is not None
    assert scorer.calibration["version"] == scorer.model_version


def test_ml_runtime_model_initializes_calibration() -> None:
    scorer = lotoia_ml.InterpretableLinearScoreML()

    assert scorer.calibration is not None
    assert scorer.calibration["status"] == "active"
    assert scorer.calibration["version"] == "historical_recalibrated_v2"


def test_ml_heartbeat_reports_active_runtime() -> None:
    state = lotoia_ml.ml_heartbeat()

    assert state["status"] == "active"
    assert state["engine_version"] == "historical_recalibrated_v2"


def test_walk_forward_splits_remain_temporally_safe() -> None:
    splits = admin_app.build_walk_forward_splits([1, 2, 3, 4, 5, 6], min_train_size=3, test_size=1, step_size=1)

    assert splits
    for split in splits:
        assert split.train_end < split.test_start


def test_ml_training_payload_has_governance_contract(monkeypatch) -> None:
    fake_game = _sample_game()
    fake_result = type(
        "FakeBacktest",
        (),
        {
            "contest_results": [
                {"contest": 1, "games": [deepcopy(fake_game)]},
                {"contest": 2, "games": [deepcopy(fake_game)]},
                {"contest": 3, "games": [deepcopy(fake_game)]},
                {"contest": 4, "games": [deepcopy(fake_game)]},
            ]
        },
    )()

    class _StubCalibration:
        model_version = "stub-v1"
        feature_schema_version = "stub-schema"
        training_summary = {}
        calibration = {}
        attribution = []

        def score(self, game):
            return type("ScoreResult", (), {"score_ml": 50.0, "features": {"odd_balance": 0.5, "sum_balance": 0.5}, "attribution": []})()

        def _weights(self):
            return {"odd_balance": 0.5, "sum_balance": 0.5}

    monkeypatch.setattr(admin_app, "_cached_backtest", lambda *args, **kwargs: fake_result)
    monkeypatch.setattr(lotoia_ml, "calibrate_linear_score_ml", lambda rows, target_field="target_hits": _StubCalibration())
    monkeypatch.setattr(lotoia_ml, "attach_score_ml", lambda game, model=None: {**game, "score_ml": 50.0, "score_ml_details": {"attribution": []}})
    monkeypatch.setattr(lotoia_ml, "supervised_rerank_games", lambda games, model=None: games)

    payload = admin_app._ml_training_result.__wrapped__()

    assert payload["validation_metrics"]["temporal_valid"] is True
    assert payload["payload"]["model_version"]
    assert payload["ml_snapshot"].exists()
    assert payload["ml_report_paths"]["json"].exists()
    assert payload["runtime"]["fallback_used"] is False
    assert payload["runtime"]["calibration_loaded"] is True


def test_ml_training_payload_does_not_require_model_attribution(monkeypatch) -> None:
    fake_game = _sample_game()
    fake_result = type(
        "FakeBacktest",
        (),
        {
            "contest_results": [
                {"contest": 1, "games": [deepcopy(fake_game)]},
                {"contest": 2, "games": [deepcopy(fake_game)]},
                {"contest": 3, "games": [deepcopy(fake_game)]},
                {"contest": 4, "games": [deepcopy(fake_game)]},
            ]
        },
    )()

    class _StubCalibration:
        model_version = "stub-v1"
        feature_schema_version = "stub-schema"
        training_summary = {}
        calibration = {}

        def score(self, game):
            return type(
                "ScoreResult",
                (),
                {"score_ml": 50.0, "features": {"odd_balance": 0.5, "sum_balance": 0.5}, "attribution": []},
            )()

        def _weights(self):
            return {"odd_balance": 0.5, "sum_balance": 0.5}

    monkeypatch.setattr(admin_app, "_cached_backtest", lambda *args, **kwargs: fake_result)
    monkeypatch.setattr(lotoia_ml, "calibrate_linear_score_ml", lambda rows, target_field="target_hits": _StubCalibration())
    monkeypatch.setattr(lotoia_ml, "attach_score_ml", lambda game, model=None: {**game, "score_ml": 50.0, "score_ml_details": {"attribution": []}})
    monkeypatch.setattr(lotoia_ml, "supervised_rerank_games", lambda games, model=None: games)

    payload = admin_app._ml_training_result.__wrapped__()

    assert payload["ml_snapshot"].exists()
    assert payload["payload"]["model_version"] == "stub-v1"
    assert payload["scored_games"][0]["score_ml_details"]["attribution"] == []
