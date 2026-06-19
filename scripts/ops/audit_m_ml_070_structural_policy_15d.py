#!/usr/bin/env python3
"""M-ML-070-AUDIT-01 — Auditoria de aplicação efetiva da Política Estrutural 15D.

Audita, de forma empírica e read-only, se a Política Estrutural 15D (M-ML-070)
realmente governa o lote final entregue pelo GP soberano / CORE_002, ou se atua
apenas como memória/validação posterior/observabilidade.

Não altera CORE_002, Lei 15, Lei 15A nem public_app. Não executa purge. Não
força oficialização. Apenas gera lotes, inspeciona artefatos e mede conformidade.

Uso:
    python scripts/ops/audit_m_ml_070_structural_policy_15d.py
"""

from __future__ import annotations

import json
from typing import Any, Sequence

from lotoia.data.loader import load_draws_csv
from lotoia.generator.basic_generator import generate_best_games
from lotoia.ml.structural_policy_15d import (
    ALLOWED_PARITY_PAIRS,
    CORE_NUMBERS,
    DISCOURAGED_NUMBERS,
    PREFERRED_PARITY_PAIRS,
    POLICY_VERSION,
    apply_structural_policy_15d_to_sovereign_batch,
    build_structural_policy_15d_memory,
)

SOVEREIGN_BATCH_LABEL = "STRUCT_LEI15_CORE_CANDIDATE_002_15D_001"
POLICY_ARTIFACT_KEYS = (
    "structural_policy_memory_loaded",
    "structural_policy_format",
    "structural_policy_version",
    "structural_policy_applied",
    "policy_compliance_status",
    "structural_policy_15d_bundle",
)


def _max_sequence(numbers: Sequence[int]) -> int:
    ordered = sorted(set(int(n) for n in numbers))
    best = run = 1 if ordered else 0
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if cur == prev + 1 else 1
        best = max(best, run)
    return best


def _parity(numbers: Sequence[int]) -> tuple[int, int]:
    odd = sum(1 for n in numbers if int(n) % 2 != 0)
    return odd, len(numbers) - odd


def audit_game(numbers: Sequence[int], previous: set[int]) -> dict[str, Any]:
    nums = sorted(int(n) for n in numbers)
    repeat = len(set(nums) & previous)
    parity = _parity(nums)
    seq = _max_sequence(nums)
    core_present = sorted(set(nums) & set(CORE_NUMBERS))
    discouraged_present = sorted(set(nums) & set(DISCOURAGED_NUMBERS))
    violations: list[str] = []
    if not (7 <= repeat <= 10):
        violations.append(f"repeticao_fora_7_10({repeat})")
    if list(parity) not in [list(p) for p in ALLOWED_PARITY_PAIRS]:
        violations.append(f"paridade_nao_permitida({parity[0]}/{parity[1]})")
    if seq > 6:
        violations.append(f"sequencia_excede_6({seq})")
    return {
        "numbers": nums,
        "repeticao": repeat,
        "paridade": f"{parity[0]}/{parity[1]}",
        "paridade_preferencial": list(parity) in [list(p) for p in PREFERRED_PARITY_PAIRS],
        "maior_sequencia": seq,
        "core_presentes": core_present,
        "discouraged_presentes": discouraged_present,
        "violacoes": violations,
        "conforme": not violations,
    }


def consolidate(audited: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(audited)
    conformes = sum(1 for g in audited if g["conforme"])
    by_rule: dict[str, list[int]] = {}
    for idx, g in enumerate(audited, start=1):
        for v in g["violacoes"]:
            key = v.split("(")[0]
            by_rule.setdefault(key, []).append(idx)
    return {
        "total_jogos": total,
        "jogos_conformes": conformes,
        "jogos_com_violacao": total - conformes,
        "taxa_conformidade": round(conformes / total, 4) if total else 0.0,
        "violacoes_por_regra": {k: len(v) for k, v in by_rule.items()},
        "jogos_afetados_por_regra": by_rule,
    }


def _artifact_presence(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: (key in payload) for key in POLICY_ARTIFACT_KEYS}


def _generate(count: int) -> dict[str, Any]:
    return dict(
        generate_best_games(
            count=count,
            pool_size=max(60, count * 3),
            ml_enabled=True,
            batch_label=SOVEREIGN_BATCH_LABEL,
        )
    )


def main() -> int:
    history = load_draws_csv()
    previous_numbers = sorted(int(n) for n in history[-1].numbers)
    previous_contest = history[-1].contest
    previous_set = set(previous_numbers)

    print("=" * 72)
    print("M-ML-070-AUDIT-01 — Política Estrutural 15D — Aplicação efetiva")
    print("=" * 72)
    memory = build_structural_policy_15d_memory()
    print(f"Política (memória canônica): versão={memory['policy_version']} formato={memory['formato']}")
    print(f"  repetição={memory['repeticao_ultimo_concurso_min']}-{memory['repeticao_ultimo_concurso_max']} "
          f"sequência_max={memory['sequencia_maxima']} core={memory['core_numbers']} discouraged={memory['discouraged_numbers']}")
    print(f"Concurso anterior (history[-1]): {previous_contest} -> {previous_numbers}")
    print()

    report: dict[str, Any] = {"policy_version": POLICY_VERSION, "previous_contest": previous_contest, "scenarios": {}}

    for count, label in ((20, "GP:20 (cenário auditado)"), (15, "GP:15 (gate count==15)")):
        print("-" * 72)
        print(f"CENÁRIO {label} — generate_best_games(count={count}, 15 dezenas, ml_enabled=True)")
        payload = _generate(count)
        games = [g.get("final_card_numbers", g.get("numbers")) for g in (payload.get("games") or [])]
        presence = _artifact_presence(payload)
        print(f"  jogos gerados: {len(games)} | card_size: {len(games[0]) if games else 0}")
        print("  artefatos da política no payload:")
        for key, present in presence.items():
            print(f"    - {key}: {'PRESENTE' if present else 'AUSENTE'}"
                  + (f" = {payload.get(key)!r}" if present and key != 'structural_policy_15d_bundle' else ""))
        audited = [audit_game(g, previous_set) for g in games]
        summary = consolidate(audited)
        print(f"  compliance: conformes={summary['jogos_conformes']}/{summary['total_jogos']} "
              f"taxa={summary['taxa_conformidade']} violações_por_regra={summary['violacoes_por_regra']}")
        report["scenarios"][f"count_{count}"] = {
            "n_games": len(games),
            "card_size": len(games[0]) if games else 0,
            "artifact_presence": presence,
            "compliance": summary,
            "games": audited,
        }
        print()

    # Teste de efeito no lote final: a política reordena/bloqueia ou só anota?
    print("-" * 72)
    print("TESTE DE EFEITO NO LOTE FINAL (apply_structural_policy_15d_to_sovereign_batch)")
    base = _generate(20)
    selected = list(base.get("games") or [])
    selected_sigs = [tuple(sorted(g.get("final_card_numbers", g.get("numbers")))) for g in selected]
    final_games, bundle = apply_structural_policy_15d_to_sovereign_batch(
        selected,
        pool_games=selected,
        history=history,
        required_count=len(selected),
    )
    final_sigs = [tuple(sorted(g.get("final_card_numbers", g.get("numbers")))) for g in final_games]
    lote_alterado = selected_sigs != final_sigs
    print(f"  required_count={len(selected)} | selected={len(selected)} | final={len(final_games)}")
    print(f"  ordem/composição do lote final ALTERADA pela política? {lote_alterado}")
    print(f"  bundle.policy_compliance_status={bundle.get('policy_compliance_status')} "
          f"games_compliant={bundle.get('games_compliant')}/{bundle.get('games_validated')}")
    report["lot_alteration_test"] = {
        "required_count": len(selected),
        "lote_alterado": lote_alterado,
        "policy_compliance_status": bundle.get("policy_compliance_status"),
        "games_compliant": bundle.get("games_compliant"),
        "games_validated": bundle.get("games_validated"),
    }

    # Classificação final
    gp20 = report["scenarios"]["count_20"]["artifact_presence"]
    classificacao = "NAO_APLICADA"
    if gp20.get("structural_policy_15d_bundle"):
        classificacao = "APLICADA_EFETIVAMENTE" if lote_alterado else "APENAS_OBSERVACIONAL"
    else:
        # GP:20 não recebe a política; gate é por count==15 (quantidade), não por formato 15D.
        classificacao = "NAO_APLICADA_NO_CENARIO_GP20"
    report["classificacao_final"] = classificacao
    print()
    print("=" * 72)
    print(f"CLASSIFICAÇÃO FINAL (GP:20 15D): {classificacao}")
    print("=" * 72)

    print("\nJSON_REPORT_BEGIN")
    print(json.dumps(report, ensure_ascii=False, default=str))
    print("JSON_REPORT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
