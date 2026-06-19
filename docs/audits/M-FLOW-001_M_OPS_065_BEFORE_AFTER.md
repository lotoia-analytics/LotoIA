# M-FLOW-001 — Bateria GP:20 15D: evidência antes/depois M-OPS-065

**Veredito M-OPS-065:** promoção cautelosa com `promotion_bypass_reason=authorized_plan_consumed`  
**Veredito M-FLOW-001 pós-fix:** 81/100 ciclos OK (PRECISA CALIBRAR + plano); 19/100 REPROVADO bloqueados corretamente

## Comparativo agregado (100 ciclos)

| Métrica | Antes (pré M-OPS-065) | Depois (M-OPS-065) |
|---------|----------------------:|-------------------:|
| N persistidos | 100 | 100 |
| N+1 persistidos | 100 | 100 |
| Planos carregados/aplicados | 100 | 100 |
| Elegíveis Histórico | **0** | **81** |
| Elegíveis Conferir | **0** | **81** |
| Ciclos OK completos | **0** | **81** |
| Falha I (qualidade) | 100 (100%) | 19 (19%) |
| Falhas técnicas | 0 | 0 |

## Antes (baseline — `docs/audits/M-FLOW-001_battery_100x.json`)

- Falha dominante: **I — 100%** (`ml_verdict_precisa_calibrar_not_releasable`)
- Plano aplicado mas lote invisível em Histórico/Conferir

## Depois (`experiments/m_flow_001_after_m_ops_065/lotoia_m_flow_001_battery_20260619T211659Z.json`)

### Ciclo OK típico (PRECISA CALIBRAR + plano)

```json
{
  "ml_verdict_N1": "PRECISA CALIBRAR",
  "ml_verdict_after_authorized_plan": "PRECISA CALIBRAR",
  "lot_operational_status_N1": "approved_with_warning",
  "promotion_bypass_reason": "authorized_plan_consumed",
  "authorized_plan_applied_to_generation": true,
  "is_analytical_history_eligible": true,
  "in_analytical_history": true,
  "in_conferir_resultados": true,
  "failure_stage": "OK"
}
```

### Ciclo bloqueado típico (REPROVADO — sem bypass)

```json
{
  "ml_verdict_N1": "REPROVADO",
  "promotion_bypass_reason": "",
  "promotion_block_reason": "ml_verdict_reprovado_not_releasable",
  "lot_operational_status_N1": "pending_structural_review",
  "failure_stage": "I"
}
```

## Conclusão

M-OPS-065 resolve o gargalo identificado em M-FLOW-001 para veredito `PRECISA CALIBRAR` com plano consumido. `REPROVADO` permanece bloqueado (19 ciclos — comportamento esperado, sem mascaramento).

## Artefatos

| Artefato | Caminho |
|----------|---------|
| Script bateria | `scripts/audits/m_flow_001_generation_calibration_battery.py` |
| JSON antes | `docs/audits/M-FLOW-001_battery_100x.json` |
| JSON depois | `experiments/m_flow_001_after_m_ops_065/lotoia_m_flow_001_battery_20260619T211659Z.json` |
| ADR | `ADRs/ADR_049_M_OPS_065_AUTHORIZED_PLAN_PROMOTION_BYPASS.md` |

## Confirmações

- Sem purge
- Sem alteração de geração, ML, thresholds, Lei 15, `public_app`
- PostgreSQL operacional não alterado
