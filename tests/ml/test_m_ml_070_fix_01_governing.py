"""M-ML-070-FIX-01 — Política Estrutural 15D governando o GP soberano por formato."""

from __future__ import annotations

import inspect
from pathlib import Path

import lotoia.generator.basic_generator as basic_generator
from lotoia.ml.structural_policy_15d import (
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_diagnosis,
    extract_structural_policy_application_from_context,
    validate_game_structural_policy_15d,
)

PREVIOUS = list(range(1, 16))
COMPLIANT_A = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]
COMPLIANT_B = [2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 16, 17, 18, 20, 22]
COMPLIANT_C = [1, 2, 3, 6, 7, 9, 10, 11, 13, 14, 16, 17, 19, 20, 22]
NON_COMPLIANT = list(range(1, 16))  # repetição 15 e sequência 15


def _game(numbers: list[int], score: float) -> dict:
    return {
        "numbers": numbers,
        "final_card_numbers": numbers,
        "profile_score": score,
        "final_score": {"final_score": score * 10},
    }


# --------------------------------------------------------------------------- #
# 1. Gate por formato, não por quantidade
# --------------------------------------------------------------------------- #
def test_gate_is_by_card_format_not_quantity() -> None:
    source = inspect.getsource(basic_generator.generate_best_games)
    assert "is_structural_policy_15d_format" in source
    assert "if count == 15:" not in source
    assert "_sovereign_card_size" in source


# --------------------------------------------------------------------------- #
# 2. A política governa: exclui não conformes quando há conformes suficientes
# --------------------------------------------------------------------------- #
def test_governance_excludes_non_compliant_when_compliant_available(tmp_path: Path) -> None:
    # Pré-condição: os três compliant são realmente conformes; o seq não é.
    assert validate_game_structural_policy_15d(COMPLIANT_A, previous_contest_numbers=PREVIOUS)["approved"]
    assert validate_game_structural_policy_15d(COMPLIANT_B, previous_contest_numbers=PREVIOUS)["approved"]
    assert validate_game_structural_policy_15d(COMPLIANT_C, previous_contest_numbers=PREVIOUS)["approved"]
    assert not validate_game_structural_policy_15d(NON_COMPLIANT, previous_contest_numbers=PREVIOUS)["approved"]

    selected = [_game(NON_COMPLIANT, 9.0), _game(COMPLIANT_A, 1.0)]  # GP colocou não conforme 1º
    pool = selected + [_game(COMPLIANT_B, 5.0), _game(COMPLIANT_C, 4.0)]

    final_games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=pool,
        history=[{"numbers": PREVIOUS}],
        required_count=2,
        db_path=tmp_path / "gov.db",
    )

    final_sigs = {tuple(sorted(g.get("final_card_numbers", g.get("numbers")))) for g in final_games}
    # Não conforme foi EXCLUÍDO (havia conformes suficientes).
    assert tuple(sorted(NON_COMPLIANT)) not in final_sigs
    assert all((g.get("structural_policy_15d_validation") or {}).get("approved") for g in final_games)
    assert bundle["structural_policy_applied"] is True
    assert bundle["games_non_compliant"] == 0
    assert bundle["policy_compliance_status"] == "compliant"
    assert bundle["lote_alterado"] is True


# --------------------------------------------------------------------------- #
# 3. Bundle expõe evidência completa de aplicação
# --------------------------------------------------------------------------- #
def test_bundle_exposes_all_evidence_fields(tmp_path: Path) -> None:
    selected = [_game(COMPLIANT_A, 2.0), _game(NON_COMPLIANT, 1.0)]
    _final, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=selected,
        history=[{"numbers": PREVIOUS}],
        required_count=2,
        db_path=tmp_path / "evid.db",
    )
    for key in (
        "structural_policy_memory_loaded",
        "structural_policy_format",
        "structural_policy_version",
        "structural_policy_applied",
        "structural_policy_application_mode",
        "policy_compliance_status",
        "policy_violations",
        "games_compliant",
        "games_non_compliant",
        "compliance_rate",
        "lote_alterado",
    ):
        assert key in bundle, key
    assert bundle["structural_policy_applied"] is True
    assert bundle["structural_policy_format"] == "15D"
    assert 0.0 <= bundle["compliance_rate"] <= 1.0


def test_extract_application_exposes_applied_flag() -> None:
    context = {
        "structural_policy_15d_bundle": {
            "structural_policy_memory_loaded": True,
            "structural_policy_format": "15D",
            "structural_policy_version": "M-ML-070-v1",
            "structural_policy_applied": True,
            "structural_policy_application_mode": "governing_by_compliance",
            "policy_compliance_status": "partial",
            "policy_violations": ["repeticao:fora_faixa_7_10:6"],
            "games_validated": 20,
            "games_compliant": 17,
            "games_non_compliant": 3,
            "compliance_rate": 0.85,
            "lote_alterado": True,
        }
    }
    application = extract_structural_policy_application_from_context(context)
    assert application["available"] is True
    assert application["structural_policy_applied"] is True
    assert application["games_non_compliant"] == 3
    assert application["compliance_rate"] == 0.85


# --------------------------------------------------------------------------- #
# 4. Integração no veredito/diagnóstico/plano
# --------------------------------------------------------------------------- #
def test_policy_feeds_diagnosis_when_violations_present() -> None:
    """A conformidade entra no diagnóstico/veredito via build_structural_policy_15d_diagnosis."""
    analysis = {
        "violations": ["repeticao:fora_faixa_7_10:6"],
        "diagnostics": [],
        "compliance_label": "REPROVADO",
        "games_total": 20,
        "games_compliant": 17,
    }
    issues = build_structural_policy_15d_diagnosis(analysis)
    assert issues
    issue = issues[0]
    assert issue.get("problema_detectado")
    assert issue.get("acao_recomendada")
    assert issue.get("violations")


def test_policy_diagnosis_compliant_when_no_violations() -> None:
    analysis = {
        "violations": [],
        "diagnostics": [],
        "compliance_label": "APROVADO",
        "games_total": 20,
        "games_compliant": 20,
    }
    issues = build_structural_policy_15d_diagnosis(analysis)
    assert issues
    assert issues[0].get("issue_type") == "structural_policy_15d_compliant"
