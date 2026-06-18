# M-ML-067 — Régua Format-Aware de Overlap e Quase Repetidos 15D–23D

**Status:** CONCLUÍDA  
**Build marker:** `institutional-adm-runtime-v55`  
**Missão:** `M-ML-067`

## Problema

A régua legada usava `overlap >= 13` fixo (`NEAR_DUPLICATE_OVERLAP = 13` em `card_structure.py`) para todos os formatos. Em lote **17D** com overlap máximo **15**, pares em atenção eram inflados como quase repetidos críticos (ex.: 50 de 190 pares).

## Régua legada (deprecated)

| Campo | Valor |
|-------|-------|
| Threshold | overlap >= 13 em qualquer formato |
| Problema | overlap 15 em 17D contado como crítico |
| Status | `deprecated_pre_m_ml_067` |

## Régua corrigida (M-ML-067)

Para formato **N**:

| Overlap | Classificação |
|---------|---------------|
| N | clone total / crítico |
| N-1 | quase clone / ruim |
| N-2 | atenção |
| N-3 ou menor | aceitável/bom |

**Quase repetidos críticos** = pares com overlap **N** + **N-1** apenas.  
**Pares em atenção** = overlap **N-2**.

## Implementação

| Componente | Arquivo |
|------------|---------|
| Memória ML unificada | `src/lotoia/ml/overlap_format_thresholds.py` |
| Cálculo de quase repetidos | `compute_gp_redundancy()` → `build_pair_overlap_distribution()` |
| Métricas Cobertura | `extract_operational_structural_metrics()` |
| Central ML / Cobertura | `coverage_evidence_interpreter.py`, cockpit, `institutional_app.py` |
| Veredito ML | `ml_operational_verdict.py` |
| Auditoria | `scripts/checks/m_ml_067_format_aware_overlap_audit.py` |

## Similaridade média por formato

Registrada em `FORMAT_SIMILARITY_THRESHOLDS` e `build_similarity_format_memory()` — faixas ideal, aceitável, atenção, alta redundância e crítico por formato 15D–23D.

## Testes

`tests/ml/test_m_ml_067_format_aware_overlap.py` — matriz 15D–23D, cenário 17D (overlap 15 = atenção), memória ML, métricas operacionais.

## Restrições respeitadas

- CORE_002, Lei 15, Lei 15A e `public_app` não alterados
- Sem purge de `imported_contests`
