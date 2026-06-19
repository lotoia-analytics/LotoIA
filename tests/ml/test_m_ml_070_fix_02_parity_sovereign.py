"""M-ML-070-FIX-02 — Paridade soberana 15D alinhada (somente 7/8 e 8/7)."""

from __future__ import annotations

import inspect
from pathlib import Path

from dashboard import institutional_ml_calibration_cockpit as cockpit
from dashboard import institutional_structural_policy_coverage as coverage
from lotoia.ml.structural_policy_15d import (
    ALLOWED_PARITY_PAIRS,
    NON_COMPLIANT_PARITY_PAIRS,
    PREFERRED_PARITY_PAIRS,
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_memory,
    load_active_structural_policy_15d_memory,
    memory_needs_parity_alignment,
    normalize_structural_policy_15d_memory,
    persist_structural_policy_15d_memory,
    validate_game_structural_policy_15d,
)

PREVIOUS = list(range(1, 16))
COMPLIANT = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]
PARITY_6_9 = [1, 3, 5, 7, 9, 11, 2, 4, 6, 8, 10, 12, 14, 16, 18]
PARITY_9_6 = [1, 3, 5, 7, 9, 17, 19, 21, 23, 2, 4, 6, 8, 10, 16]


def _game(numbers: list[int], score: float = 2.0) -> dict:
    return {
        "numbers": numbers,
        "final_card_numbers": numbers,
        "profile_score": score,
        "final_score": {"final_score": score * 10},
    }


def test_memory_catalog_excludes_non_compliant_parity_pairs() -> None:
    memory = build_structural_policy_15d_memory()
    assert memory["paridade_preferencial"] == [[7, 8], [8, 7]]
    assert memory["paridade_permitida"] == [[7, 8], [8, 7]]
    assert [6, 9] not in memory["paridade_permitida"]
    assert [9, 6] not in memory["paridade_permitida"]
    assert ALLOWED_PARITY_PAIRS == PREFERRED_PARITY_PAIRS
    assert NON_COMPLIANT_PARITY_PAIRS == ((6, 9), (9, 6))


def test_legacy_memory_is_normalized_on_load(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_parity.db"
    legacy = build_structural_policy_15d_memory()
    legacy["paridade_permitida"] = [[7, 8], [8, 7], [6, 9], [9, 6]]
    assert memory_needs_parity_alignment(legacy) is True
    persist_structural_policy_15d_memory(db_path, legacy)
    loaded = load_active_structural_policy_15d_memory(db_path, persist_if_missing=False)
    assert loaded["paridade_permitida"] == [[7, 8], [8, 7]]
    assert [6, 9] not in loaded["paridade_permitida"]
    assert normalize_structural_policy_15d_memory(legacy)["paridade_permitida"] == [[7, 8], [8, 7]]


def test_cobertura_displays_only_compliant_parity() -> None:
    source = inspect.getsource(coverage.render_structural_policy_15d_operational_block)
    assert "Paridade conforme" in source
    assert "Paridade permitida" not in source
    assert "NON_COMPLIANT_PARITY_PAIRS" not in source


def test_central_ml_displays_compliant_and_violation_parity() -> None:
    source = inspect.getsource(cockpit._render_structural_policy_15d_card)
    assert "**Conforme:**" in source
    assert "**Violação:**" in source
    assert "NON_COMPLIANT_PARITY_PAIRS" in source
    assert "6/9" not in source or "NON_COMPLIANT_PARITY_PAIRS" in source


def test_parity_6_9_counts_as_violation() -> None:
    result = validate_game_structural_policy_15d(
        PARITY_6_9,
        previous_contest_numbers=PREVIOUS,
    )
    assert result["parity"] == [6, 9]
    assert result["approved"] is False
    assert any("paridade:fora_preferencial_7_8:6_9" == item for item in result["violations"])


def test_parity_9_6_counts_as_violation() -> None:
    result = validate_game_structural_policy_15d(
        PARITY_9_6,
        previous_contest_numbers=PREVIOUS,
    )
    assert result["parity"] == [9, 6]
    assert result["approved"] is False
    assert any("paridade:fora_preferencial_7_8:9_6" == item for item in result["violations"])


from itertools import combinations


def _compliant_variants(count: int) -> list[dict]:
    found: list[dict] = []
    for combo in combinations(range(1, 26), 15):
        numbers = list(combo)
        result = validate_game_structural_policy_15d(
            numbers,
            previous_contest_numbers=PREVIOUS,
        )
        if result["approved"]:
            found.append(_game(numbers, float(len(found) + 1)))
            if len(found) >= count:
                break
    if len(found) < count:
        raise AssertionError(f"expected {count} compliant variants, found {len(found)}")
    return found


def test_gp20_15d_bundle_keeps_structural_policy_applied(tmp_path: Path) -> None:
    pool = _compliant_variants(24)
    selected = pool[:20]
    _final, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=pool,
        history=[{"numbers": PREVIOUS}],
        required_count=20,
        db_path=tmp_path / "gp20.db",
    )
    assert bundle["structural_policy_applied"] is True
    assert bundle["structural_policy_format"] == "15D"
    assert bundle["games_validated"] == 20
    memory = dict(bundle.get("structural_policy_15d_memory") or {})
    assert memory.get("paridade_permitida") == [[7, 8], [8, 7]]


def test_bundle_does_not_treat_6_9_or_9_6_as_allowed(tmp_path: Path) -> None:
    non_compliant = _game(PARITY_6_9, 9.0)
    selected = [non_compliant]
    _final, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=selected,
        history=[{"numbers": PREVIOUS}],
        required_count=1,
        db_path=tmp_path / "bundle_parity.db",
    )
    validation = dict((_final[0].get("structural_policy_15d_validation") or {}))
    assert validation.get("approved") is False
    violations = list(validation.get("violations") or bundle.get("policy_violations") or [])
    assert any("paridade" in item for item in violations)
    memory = dict(bundle.get("structural_policy_15d_memory") or {})
    assert [6, 9] not in memory.get("paridade_permitida", [])
    assert [9, 6] not in memory.get("paridade_permitida", [])
