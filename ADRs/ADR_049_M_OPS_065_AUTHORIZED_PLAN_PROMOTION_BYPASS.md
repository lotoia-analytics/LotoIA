# ADR 049 — M-OPS-065 Promoção cautelosa N+1 com plano autorizado consumido

**Status:** Accepted  
**Data:** 2026-06-19  
**Missão:** M-OPS-065

## Contexto

A bateria M-FLOW-001 (100 ciclos GP:20 15D) demonstrou que o pipeline técnico N → plano PostgreSQL → N+1 funciona integralmente, mas **0/100** lotes N+1 alcançam Histórico/Conferir porque `ml_verdict=PRECISA CALIBRAR` bloqueia a promoção (`ml_verdict_precisa_calibrar_not_releasable`), mesmo com `authorized_plan_applied_to_generation=true`.

Isso confunde operação: o plano foi aplicado, mas o lote permanece invisível nas telas finais.

## Decisão

Para lotes **N+1 consumidores** de plano autorizado (`calibration_plan_loaded_from_db` + `calibration_plan_applied_to_generation`):

1. Promover para `approved_with_warning` quando `ml_verdict == PRECISA CALIBRAR`, desde que **não** seja `REPROVADO`, `BLOQUEADO` ou tier `REPROVADO`/`CRÍTICO`.
2. **Não** alterar veredito ML — `ml_verdict_after_authorized_plan` permanece honesto.
3. Registrar trace explícito:
   - `promotion_bypass_reason = "authorized_plan_consumed"`
   - `authorized_plan_promotion_bypass_mission_id = "M-OPS-065"`
   - `lot_operational_status = "approved_with_warning"`

Implementação soberana em `promote_post_calibration_consumer_lot_visibility()` / `_resolve_post_calibration_promoted_status()` (`lot_operational_status.py`). Telas leem flags persistidas — sem bypass duplicado em queries.

## Consequências

- Lotes N+1 com plano consumido sobem para Histórico/Conferir **com cautela**.
- `REPROVADO` após plano autorizado continua bloqueado (não mascarado).
- Requer testes M-OPS-065 + reexecução M-FLOW-001 para evidência antes/depois.

## Alternativas rejeitadas

- Bypass nas queries de Histórico/Conferir (duplicação de regra).
- Promover para `officialized` automático (plano ≠ aprovação estrutural).
- Alterar thresholds/geração para forçar `APROVADO`.
