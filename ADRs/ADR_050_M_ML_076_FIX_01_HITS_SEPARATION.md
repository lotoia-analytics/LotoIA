# ADR 050 — M-ML-076-FIX-01 Separação veredito estrutural vs hits 13/14/15

**Status:** Accepted  
**Data:** 2026-06-19  
**Missão:** M-ML-076-FIX-01

## Contexto

A auditoria M-ML-076-AUDIT-00 (classificação D) provou que a regra `captura_ausente_redundancia` em `evaluate_ml_operational_verdict` alterava `ml_verdict` e `official_release_allowed` com base em ausência de hits 13/14/15 quando a redundância estrutural era limítrofe (similaridade ≥ 0,55).

Mesma estrutura + zero hits → `PRECISA CALIBRAR` / liberação negada.  
Mesma estrutura + hits presentes → `APROVADO` / liberação permitida.

Isso viola a política institucional: veredito estrutural decide liberação; hits ficam apenas em Histórico Analítico, Conferir Resultados e Backtesting.

## Decisão

1. Remover a regra `captura_ausente_redundancia` do veredito operacional ML.
2. Remover bloco decisório `captura_13_14_ausente` e itens de plano com captura 13/14 da visão operacional principal.
3. Manter hits em `metrics_snapshot`, `build_historical_hit_analytics_summary` e card de Auditoria Técnica na Central ML.
4. Registrar rastreabilidade em `context_json` / payloads:
   - `structural_verdict_ignores_hits = true`
   - `hits_evaluation_scope = "historical_analytics_only"`
   - `hit_metrics_excluded_from_release = true`
   - `m_ml_076_fix_01_applied = true`

## Consequências

- Lotes com zero hits 13/14/15 não são penalizados estruturalmente por ausência de captura.
- Liberação operacional depende exclusivamente de indicadores estruturais (similaridade, overlap, diversidade, política 15D, cobertura, duplicidade).
- Hits permanecem visíveis em Histórico, Conferir, Backtesting e Auditoria Técnica.

## Alternativas rejeitadas

- Mascarar similaridade/overlap alto com hits positivos.
- Remover hits de Histórico/Conferir.
- Alterar thresholds estruturais ou geração Lei 15.
