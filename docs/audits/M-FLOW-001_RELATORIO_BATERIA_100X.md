# M-FLOW-001 — Bateria GP:20 15D (100 ciclos)

**Executado em:** 2026-06-19T20:59:40Z  
**Veredito:** M-FLOW-001 CONCLUÍDA — BATERIA 100x IDENTIFICOU ONDE O FLUXO GERAÇÃO → CALIBRAÇÃO → REENTRADA FALHA

## Pergunta central

Em 100 ciclos do fluxo geração → calibração → reentrada, **quantos completam corretamente** e **onde falham os demais**?

**Resposta:** 0/100 ciclos completam até Histórico/Conferir. **100/100** falham na etapa **I — liberação por qualidade** (`ml_verdict` / promoção), não em persistência nem em plano autorizado.

## Resumo agregado

| Métrica | Valor |
|---------|------:|
| Total ciclos | 100 |
| N persistidos | 100 |
| Planos criados | 100 |
| N+1 persistidos | 100 |
| Planos carregados | 100 |
| Planos aplicados | 100 |
| Promoções avaliadas | 100 |
| Elegíveis Histórico | 0 |
| Elegíveis Conferir | 0 |
| Visíveis Histórico | 0 |
| Visíveis Conferir | 0 |
| Não liberados por qualidade | 100 |
| Falhas técnicas | 0 |
| Ciclos OK completos | 0 |

## Tabela por falha

| Falha | Quantidade | Percentual | Exemplo GE | Causa provável |
|-------|----------:|-----------:|-----------:|----------------|
| I — N+1 não liberado por qualidade | 100 | 100.0% | 2 | `ml_verdict=PRECISA CALIBRAR` impede promoção; `promotion_block_reason=ml_verdict_precisa_calibrar_not_releasable` |

## Exemplo de ciclo típico (ciclo 1)

| Campo | Valor |
|-------|-------|
| generation_event_id_N | 1 |
| generation_event_id_N1 | 2 |
| generated_games_count_N / N1 | 20 / 20 |
| calibration_plan_created | true |
| calibration_plan_loaded_from_db | true |
| calibration_plan_applied_to_generation | true |
| post_calibration_promotion_evaluated | true |
| lot_operational_status_N1 | needs_calibration |
| ml_verdict_N1 | PRECISA CALIBRAR |
| official_release_allowed_N1 | false |
| promotion_block_reason | ml_verdict_precisa_calibrar_not_releasable |
| in_coverage (Cobertura) | true |
| in_central_ml | true |
| in_analytical_history | false |
| in_conferir_resultados | false |

## Causa dominante

**I — N+1 não liberado por qualidade (100%)**

O pipeline técnico N → plano → N+1 **funciona integralmente** (persistência, memória autorizada, aplicação, avaliação de promoção). O bloqueio ocorre **depois**: o veredito ML na N+1 permanece `PRECISA CALIBRAR`, impedindo `is_analytical_history_eligible` e `is_official_conference_eligible`.

## Recomendação objetiva

1. **Não tratar como falha de persistência ou de plano** — 100% dos planos carregam e aplicam na N+1.
2. **Separar semanticamente** “plano autorizado aplicado” de “lote liberado para Histórico/Conferir” (M-ML-075-FIX-02).
3. **Revisar política de promoção pós-plano** quando `ml_verdict` na N+1 ainda é `PRECISA CALIBRAR` apesar do plano consumido — hoje `promote_post_calibration_consumer_lot_visibility` avalia mas bloqueia com `ml_verdict_precisa_calibrar_not_releasable`.
4. **GP mockado** na bateria: pool soberano simulado para velocidade; persistência/plano/loaders são reais.

## Artefatos

- Script: `scripts/audits/m_flow_001_generation_calibration_battery.py`
- JSON: `experiments/m_flow_001/lotoia_m_flow_001_battery_20260619T205230Z.json`
- CSV: `experiments/m_flow_001/lotoia_m_flow_001_battery_20260619T205230Z.csv`
- DBs isolados (não versionados): `experiments/m_flow_001/cycle_dbs/cycle_XXX.db`

## Confirmações

- Sem purge
- Sem alteração de geração, ML, thresholds, Lei 15, `public_app`
- PostgreSQL operacional não alterado (SQLite efêmero por ciclo)
