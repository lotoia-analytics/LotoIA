# ADR-048 — M-ML-073b: Hierarquia ML como classificador de qualidade (não gate de entrega)

**Status:** APROVADO  
**Data:** 2026-06-19  
**Missões:** M-ML-073b (classificador), M-ML-073 (observabilidade), M-ML-074 (recuperação pré-GP)

## Contexto

A investigação M-ML-074-DIAG-00 provou que **M-ML-073** introduziu o primeiro comportamento de **0 jogos entregues** quando `gp_closure_allowed=False` (etapas 1–3 reprovadas). M-ML-072, M-STAT-002 e M-ML-074 alimentam/recuperam o pool mas não criam o bloqueio de entrega.

O operador institucional precisa receber **GP:N sempre** (10/20/100/200), com a ML classificando qualidade — não impedindo entrega por problemas que a própria hierarquia tenta corrigir.

## Decisão

1. **M-ML-073 deixa de ser gate de entrega** e passa a ser **classificador de qualidade** (`M-ML-073b`).
2. Após avaliação das etapas 1–3, o pipeline **sempre** executa calibração pré-final e `compose_sovereign_gp`, salvo bloqueio crítico.
3. Novo campo **`gp_quality_tier`**: `APROVADO` | `ATENÇÃO` | `REPROVADO`.
4. **`gp_closure_allowed`** permanece como metadado de conformidade das etapas 1–3 (observabilidade / trace).
5. **`gp_delivery_blocked`** bloqueia entrega apenas em falhas críticas:
   - pool vazio
   - overlap crítico multidezena (corrupção estrutural)
   - falha em `compose_sovereign_gp` (< N jogos)
   - erros internos / violação soberana crítica

### Mapeamento de tiers

| Tier | Condição |
|------|----------|
| APROVADO | Etapas 1–3 aprovadas |
| ATENÇÃO | Exatamente 1 etapa reprovada (diversidade ou cobertura; conformidade não crítica) |
| REPROVADO | 2+ etapas reprovadas ou conformidade com overlap crítico |

### Preservação de inteligência M-ML-073

Mantidos sem remoção: `diversity_score`, similaridade média, trinca dominante, cobertura, `stage_results`, roteamento de agentes, M-ML-074 recovery loop.

## Consequências

- Dashboard e Central ML exibem **GP entregue + qualidade** em vez de `hierarchy_blocked` com 0 jogos.
- `MlOperationalHierarchyBlockedError` restrito a `gp_delivery_blocked=True`.
- M-ML-074 considera sucesso de recuperação quando `gp_quality_tier == APROVADO`.
- Build marker: `institutional-adm-runtime-v69`.

## Alternativas rejeitadas

- Abaixar limiar de diversidade (0.55) sem ADR — rejeitado.
- Remover etapas 1–3 — rejeitado (perde observabilidade construída).
