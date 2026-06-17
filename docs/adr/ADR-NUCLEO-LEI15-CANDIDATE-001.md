# ADR-NUCLEO-LEI15-CANDIDATE-001

## Status

**SHADOW_TEST — CDX Núcleo Lei 15**

| Item | Estado |
|------|--------|
| Critério de avaliação | **6 bases institucionais** — `POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md` |
| Núcleo antigo legado | **BASELINE CONGELADO** |
| CDX Variante D piloto | **Executado** (GE 115) — leitura 6 bases registrada |
| Modo `active` | **BLOQUEADO** — exige equilíbrio 6 bases, não hit isolado |
| Novos lotes motor legado | **PROIBIDOS** |

## Correções N-C1..N-C6

| ID | Descrição | Variante |
|----|-----------|----------|
| N-C4 | Pool por `profile_quota` | A+ |
| N-C5 | Sem relabeling artificial | A+ |
| N-C1 | Cap overlap + soft block prefix 123 | B+ |
| N-C6 | Dampen recurrence scoring | C+ |
| N-C3 | Hybrid 4-7 + blind spots 06/16/17 | D |
| N-C2 | Cap sufixo alto em hot Recurrent | D |

Penalização estrutural leve (`structural_bias_penalty`) ativa em B+ — reduz score, não descarta padrões V1 fortes (shield).

## Payload obrigatório

- `perfil_origem_real`
- `perfil_label_final`
- `prefix_signature` / `suffix_signature`
- `structural_bias_score`
- `relabeling_applied` / `relabeling_reason`

## Evidência piloto D (2026-06-17)

| Métrica | Baseline legado | CAND-D |
|---------|-----------------|--------|
| prefixo 01-02-03 | 42.0% | 4.0% |
| sufixo 22-24-25 | 53.0% | 8.0% |
| melhor hit | 12 | 11 |
| runs 13+ | 0 | 0 |

## Relatórios

- `python scripts/ops/audit_lei15_core_cdx_report_15d.py`
- `python scripts/ops/report_core_cdx_pilot_d_final_15d.py`

## Governança

- `docs/adr/ADR-046-NUCLEO-LEI15-CANDIDATE-002.md` — **proposta síntese V1+CDX-D (sem implementação)**
- `docs/governance/POLITICA_AVALIACAO_NUCLEO_LEI15_6_BASES.md`
- `src/lotoia/governance/lei15_legacy_core_baseline.py`
- `docs/governance/RELATORIO_NUCLEO_ANTIGO_LEI15_BASELINE_CONGELADO_2026_06_17.md`
