"""M-ML-070 — política estrutural soberana 15D."""

from __future__ import annotations

import inspect
from pathlib import Path

from dashboard.institutional_build import BUILD_MARKER
from lotoia.ml.structural_policy_15d import (
    COMPLIANCE_LABEL_APROVADO,
    COMPLIANCE_LABEL_ATENCAO,
    COMPLIANCE_LABEL_REPROVADO,
    MISSION_ID,
    POLICY_VERSION,
    analyze_batch_structural_policy_15d,
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_calibration_plan,
    build_structural_policy_15d_memory,
    is_structural_policy_15d_format,
    load_active_structural_policy_15d_memory,
    persist_structural_policy_15d_memory,
    resolve_policy_compliance_label,
    validate_game_structural_policy_15d,
)


def _compliant_numbers() -> list[int]:
    return [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]


def _previous_numbers() -> list[int]:
    return list(range(1, 16))


def test_format_gate_15d_only() -> None:
    assert is_structural_policy_15d_format(15) is True
    assert is_structural_policy_15d_format(16) is False
    assert is_structural_policy_15d_format(14) is False


def test_memory_persist_and_load(tmp_path: Path) -> None:
    db_path = tmp_path / "policy_15d.db"
    persisted = persist_structural_policy_15d_memory(db_path)
    assert persisted["mission_id"] == MISSION_ID
    assert persisted["policy_version"] == POLICY_VERSION
    loaded = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)
    assert loaded["mission_id"] == MISSION_ID
    assert loaded["policy_version"] == POLICY_VERSION
    assert loaded.get("memory_row_id")


def test_validation_repeat_range() -> None:
    numbers = _compliant_numbers()
    approved = validate_game_structural_policy_15d(
        numbers,
        previous_contest_numbers=_previous_numbers(),
    )
    assert approved["approved"] is True
    assert 7 <= int(approved["repeat_count"] or 0) <= 10

    low_repeat = validate_game_structural_policy_15d(
        [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 1, 2, 3, 4, 5],
        previous_contest_numbers=_previous_numbers(),
    )
    assert low_repeat["approved"] is False
    assert any("repeticao" in item for item in low_repeat["violations"])


def test_validation_parity_preference() -> None:
    numbers = _compliant_numbers()
    result = validate_game_structural_policy_15d(
        numbers,
        previous_contest_numbers=_previous_numbers(),
    )
    assert result["parity"] in ([7, 8], [8, 7])

    bad_parity = validate_game_structural_policy_15d(
        [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 2, 4],
        previous_contest_numbers=_previous_numbers(),
    )
    assert bad_parity["approved"] is False
    assert any("paridade" in item for item in bad_parity["violations"])


def test_validation_sequence_max() -> None:
    long_sequence = list(range(1, 16))
    result = validate_game_structural_policy_15d(
        long_sequence,
        previous_contest_numbers=_previous_numbers(),
    )
    assert result["approved"] is False
    assert any("sequencia" in item for item in result["violations"])
    assert int(result["largest_sequence"] or 0) > 6


def test_apply_structural_policy_bundle(tmp_path: Path) -> None:
    db_path = tmp_path / "policy_batch.db"
    previous = _previous_numbers()
    compliant = {
        "numbers": _compliant_numbers(),
        "final_card_numbers": _compliant_numbers(),
        "profile_score": 2.0,
        "final_score": {"final_score": 90.0},
    }
    pool = [compliant, {**compliant, "numbers": list(_compliant_numbers())}]
    games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        [compliant],
        pool_games=pool,
        history=[{"numbers": previous}],
        required_count=1,
        db_path=db_path,
    )
    assert len(games) == 1
    assert bundle["mission_id"] == MISSION_ID
    assert bundle["structural_policy_memory_loaded"] is True
    assert bundle["structural_policy_format"] == "15D"
    assert bundle.get("structural_policy_15d_memory")
    assert games[0].get("structural_policy_15d_validation", {}).get("approved") is True


def test_central_ml_exposes_structural_policy_15d_card() -> None:
    import dashboard.institutional_ml_calibration_cockpit as cockpit

    source = inspect.getsource(cockpit.render_ml_calibration_cockpit)
    card_source = inspect.getsource(cockpit._render_structural_policy_15d_card)
    assert "_render_structural_policy_15d_card" in source
    assert "M-ML-070" in card_source
    assert "structural_policy_15d_memory" in card_source


def test_build_marker_v59() -> None:
    assert BUILD_MARKER == "institutional-adm-runtime-v74"


def test_canonical_memory_catalog() -> None:
    memory = build_structural_policy_15d_memory()
    assert memory["formato"] == "15D"
    assert memory["repeticao_ultimo_concurso_min"] == 7
    assert memory["repeticao_ultimo_concurso_max"] == 10
    assert memory["sequencia_maxima"] == 6
    assert memory["paridade_preferencial"] == [[7, 8], [8, 7]]
    assert memory["paridade_permitida"] == [[7, 8], [8, 7]]


def test_resolve_policy_compliance_labels() -> None:
    assert resolve_policy_compliance_label(3, 3, []) == COMPLIANCE_LABEL_APROVADO
    assert resolve_policy_compliance_label(1, 3, ["repeticao:x"]) == COMPLIANCE_LABEL_ATENCAO
    assert resolve_policy_compliance_label(0, 3, ["repeticao:x"]) == COMPLIANCE_LABEL_REPROVADO


def test_batch_analysis_and_calibration_plan() -> None:
    previous = _previous_numbers()
    compliant = {
        "numbers": _compliant_numbers(),
        "final_card_numbers": _compliant_numbers(),
    }
    analysis = analyze_batch_structural_policy_15d(
        [compliant],
        previous_contest_numbers=previous,
        policy=build_structural_policy_15d_memory(),
    )
    assert analysis["games_total"] == 1
    assert analysis["compliance_label"] in {
        COMPLIANCE_LABEL_APROVADO,
        COMPLIANCE_LABEL_ATENCAO,
    }
    plan = build_structural_policy_15d_calibration_plan(analysis)
    assert "plan_items" in plan
    assert "parametros_sugeridos" in plan


def test_verdict_integration_policy_non_compliant() -> None:
    from lotoia.ml.ml_operational_verdict import evaluate_ml_operational_verdict

    payload = evaluate_ml_operational_verdict(
        {
            "policy_compliance_status": "non_compliant",
            "policy_compliance_label": COMPLIANCE_LABEL_REPROVADO,
            "policy_violations": ["repeticao:fora_faixa_7_10:3"],
            "formatos_analisados": [15],
        }
    )
    assert payload["ml_verdict"] in {"REPROVADO", "PRECISA CALIBRAR"}
    assert "structural_policy_15d_non_compliant" in list(
        (payload.get("trace") or {}).get("rule_triggers") or []
    )


def test_coverage_render_function_exists() -> None:
    from dashboard import institutional_structural_policy_coverage as module

    assert callable(module.render_structural_policy_15d_operational_block)
    assert callable(module.build_structural_policy_coverage_context)
