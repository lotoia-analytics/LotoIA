"""M-ML-070-AUDIT-01 — auditoria da aplicação efetiva da Política Estrutural 15D.

Estes testes CODIFICAM os achados da auditoria (comportamento atual verificado
empiricamente), servindo como evidência reproduzível e guarda de regressão:

- a memória da política existe e bate com o catálogo M-ML-070-v1;
- a validação por jogo detecta violações de repetição/paridade/sequência;
- PORÉM a aplicação no lote soberano é APENAS OBSERVACIONAL: quando o GP já
  entrega `required_count` jogos, `apply_structural_policy_15d_to_sovereign_batch`
  mantém os jogos originais (mesma ordem) e NÃO remove os não conformes;
- o bundle não expõe `structural_policy_applied` (artefato esperado ausente).

Se a M-ML-070 for evoluída para aplicação efetiva (reordenar/bloquear não
conformes), estes testes devem ser revisados junto com nova auditoria.
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


def test_application_is_observational_not_governing(tmp_path: Path) -> None:
    """Achado central: o lote final NÃO é alterado e os não conformes permanecem."""
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

    selected_sigs = [tuple(sorted(g["final_card_numbers"])) for g in selected]
    final_sigs = [tuple(sorted(g.get("final_card_numbers", g.get("numbers")))) for g in final_games]
    # Lote final inalterado (mesma composição e ordem da seleção original do GP).
    assert final_sigs == selected_sigs
    # Não conforme permanece no lote (não houve bloqueio/remoção).
    assert any(
        not (g.get("structural_policy_15d_validation") or {}).get("approved")
        for g in final_games
    )
    # Compliance é apenas medido/anotado.
    assert bundle["policy_compliance_status"] == "partial"
    assert bundle["games_compliant"] == 1
    assert bundle["games_validated"] == 2


def test_bundle_lacks_structural_policy_applied_flag(tmp_path: Path) -> None:
    """Critério #2 da auditoria espera structural_policy_applied=true — ausente."""
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
    assert "structural_policy_applied" not in bundle
    # O bundle expõe memory_loaded, mas não o flag de aplicação efetiva.
    assert bundle["structural_policy_memory_loaded"] is True
