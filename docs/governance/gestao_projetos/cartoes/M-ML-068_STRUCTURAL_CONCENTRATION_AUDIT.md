# M-ML-068 — Auditoria de Concentração Estrutural 17D

**Status:** CONCLUÍDA  
**Build marker:** `institutional-adm-runtime-v56`  
**Missão:** `M-ML-068`

## Contexto

Após M-ML-067, overlap crítico foi corrigido. Lotes 17D sem clones podem ainda apresentar similaridade média alta e diversidade baixa por **concentração estrutural** (prefixos, sufixos, bases, expansão).

## Escopo da auditoria

| Dimensão | Função |
|----------|--------|
| Prefixos/sufixos | `audit_prefix_suffix_concentration()` |
| Cobertura 01–25 | `audit_dezena_coverage()` |
| Base diversity | `audit_base_diversity()` |
| Expansão 17D | `audit_17d_expansion()` |
| Pool / rerank | `audit_pool_and_rerank()` |
| Restrições | `audit_restrictions()` |
| Causa raiz | `infer_root_cause()` |

## Implementação

- Módulo: `src/lotoia/ml/structural_concentration_audit.py`
- CLI: `scripts/checks/m_ml_068_structural_concentration_audit.py`
- Payload Central ML: `structural_concentration_audit` em `get_structural_coverage_evidence()`
- Testes: `tests/ml/test_m_ml_068_structural_concentration_audit.py`

## Limiares iniciais (auditoria)

- Prefixo/sufixo: ≤5/20 aceitável; 6–8 atenção; 9–11 alto; ≥12 crítico
- Dezenas 17D×20: média 13,6; <8 severa; 8–10 moderada; >20 excessiva severa
- Base: nenhuma base >4 jogos (20%) sem justificativa

## Restrições

- Sem alteração de gerador, CORE_002, Lei 15, Lei 15A, `public_app`
- Sem purge; sem alteração M-ML-067

## Próxima missão (recomendação)

Calibração para limitar prefixo dominante, diversificar núcleos 15D e pares de expansão 17D — **não implementada nesta missão**.
