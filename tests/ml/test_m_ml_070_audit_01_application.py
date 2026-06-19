"""M-ML-070-AUDIT-01 — auditoria da Política Estrutural 15D (atualizada por M-ML-070-FIX-01).

A auditoria original constatou que a política era APENAS OBSERVACIONAL. A
correção M-ML-070-FIX-01 fez a política GOVERNAR o lote final por conformidade.
Estes testes refletem o comportamento corrigido:

- a memória da política existe e bate com o catálogo M-ML-070-v1;
- a validação por jogo detecta violações de repetição/paridade/sequência;
- o bundle expõe `structural_policy_applied = True`;
- não conformes só permanecem quando não há conformes suficientes (rastreado).
"""

from __future__ import annotations

from pathlib import Path

from lotoia.ml.structural_policy_15d import (
    POLICY_VERSION,
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_memory,
    validate_game_structural_policy_15d,
)

PREVIOUS = list(range(1, 16))
COMPLIANT = [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 16, 17, 18, 20, 22]
NON_COMPLIANT_SEQ = list(range(1, 16))  # repetição 15 e sequência 15 → não conforme


def test_policy_memory_catalog_matches_spec() -> None:
    memory = build_structural_policy_15d_memory()
    assert memory["policy_version"] == POLICY_VERSION == "M-ML-070-v1"
    assert memory["formato"] == "15D"
    assert memory["repeticao_ultimo_concurso_min"] == 7
    assert memory["repeticao_ultimo_concurso_max"] == 10
    assert memory["sequencia_maxima"] == 6
    assert memory["core_numbers"] == [7, 12, 16, 23]
    assert memory["discouraged_numbers"] == [2, 4, 11, 15, 24, 25]


def test_validation_flags_violations() -> None:
    ok = validate_game_structural_policy_15d(COMPLIANT, previous_contest_numbers=PREVIOUS)
    assert ok["approved"] is True
    bad = validate_game_structural_policy_15d(NON_COMPLIANT_SEQ, previous_contest_numbers=PREVIOUS)
    assert bad["approved"] is False
    assert any("sequencia" in v for v in bad["violations"])


def test_non_compliant_kept_only_when_insufficient_compliant(tmp_path: Path) -> None:
    """Pós-FIX-01: não conforme só permanece quando faltam conformes (rastreado)."""
    db_path = tmp_path / "audit_070.db"
    compliant = {"numbers": COMPLIANT, "final_card_numbers": COMPLIANT, "profile_score": 2.0,
                 "final_score": {"final_score": 90.0}}
    non_compliant = {"numbers": NON_COMPLIANT_SEQ, "final_card_numbers": NON_COMPLIANT_SEQ,
                     "profile_score": 5.0, "final_score": {"final_score": 99.0}}
    selected = [compliant, non_compliant]

    final_games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=selected,
        history=[{"numbers": PREVIOUS}],
        required_count=len(selected),
        db_path=db_path,
    )

    # Há só 1 conforme para 2 vagas → o não conforme entra para completar.
    assert any(
        not (g.get("structural_policy_15d_validation") or {}).get("approved")
        for g in final_games
    )
    assert bundle["policy_compliance_status"] == "partial"
    assert bundle["games_compliant"] == 1
    assert bundle["games_non_compliant"] == 1
    assert bundle["non_compliant_kept_reason"] == "insufficient_compliant_pool"


def test_bundle_exposes_structural_policy_applied(tmp_path: Path) -> None:
    """Pós-FIX-01: o bundle comprova aplicação efetiva (structural_policy_applied=True)."""
    db_path = tmp_path / "audit_070_flag.db"
    compliant = {"numbers": COMPLIANT, "final_card_numbers": COMPLIANT, "profile_score": 1.0,
                 "final_score": {"final_score": 50.0}}
    _final, bundle = apply_structural_policy_15d_to_sovereign_batch(
        [compliant],
        pool_games=[compliant],
        history=[{"numbers": PREVIOUS}],
        required_count=1,
        db_path=db_path,
    )
    assert bundle["structural_policy_applied"] is True
    assert bundle["structural_policy_application_mode"] == "governing_by_compliance"
    assert bundle["structural_policy_memory_loaded"] is True
