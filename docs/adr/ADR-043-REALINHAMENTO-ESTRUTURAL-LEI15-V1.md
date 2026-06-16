# ADR-043 — Realinhamento Estrutural Lei 15 V1

## Status

AUTORIZADO_PELO_ADM — shadow_test ativo em EPOCH_001

## Contexto

A auditoria completa da EPOCH_001 (lotes STRUCT_TEST_15D_001 a STRUCT_TEST_20D_001)
confirmou viés estrutural sistemático no GP:

| Problema | Evidência EPOCH_001 |
|---|---|
| Prefixo `01-02-03` concentrado | 42–63 % dos jogos em todos os lotes |
| Sufixo `22-24-25` concentrado | 53–66 % dos jogos em todos os lotes |
| Dezenas 07, 16, 17, 19, 20, 23 ausentes | <15 % de cobertura no GP |
| Similaridade média GP | 0.799–0.838 (alvo: ≤ 0.75) |
| Pares quase-idênticos (overlap ≥ size-2) | centenas por lote |

Os problemas são consistentes entre 15D e 20D, indicando causa estrutural
na composição do GP e não no gerador de cartão individual.

## Decisão

Implementar **Realinhamento Estrutural V1** como camada de composição de GP
controlada por feature flag, com modo inicial `shadow_test`:

1. **`law15_structural_realignment_v1.py`** (governança) — thresholds auditáveis,
   feature flag (`LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1`), referência ao ADR.

2. **`structural_realignment_v1.py`** (geração) — scoring de diversidade GP,
   penalidades por concentração de prefixo/sufixo, bônus de cobertura de
   dezenas ausentes, composição gulosa diversificada.

3. **Feature flag** com três modos:
   - `off` — comportamento atual intacto (default)
   - `shadow_test` — metrics logadas, seleção inalterada
   - `active` — composição diversificada ativada

4. **Novos labels de lote** para fase comparativa:
   - `STRUCT_REALIGN_V1_15D_001` a `STRUCT_REALIGN_V1_18D_001`

## Consequências

### O que muda
- `basic_generator.generate_best_games` chama o hook de realinhamento
  quando a flag está em `shadow_test` ou `active`.
- Em `shadow_test`: cada jogo recebe `realignment_metadata` (apenas metadado).
- Em `active`: `compose_diverse_gp` substitui `_compose_profiled_games`.
- `analysis_batch_labels` aceita `STRUCT_REALIGN_V1_*` como labels válidos.

### O que NÃO muda
- Lei 15 e Lei 15A — geração individual de cartão intacta.
- Pesos, filtros e regras de validação existentes.
- `_is_valid_game`, `_generate_profile_candidate`, rerank ML (auxiliar).
- Persistência e esquema do banco de dados.
- Lotes EPOCH_001 — são apenas baseline de referência.

### Rollback
Definir `LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1=off` ou remover a variável.
Nenhuma migração de banco necessária.

## Critérios de aprovação para promoção de shadow_test → active

- Reduzir concentração do prefixo `01-02-03` de ~55 % para ≤ 25 % do GP.
- Reduzir concentração do sufixo `22-24-25` de ~60 % para ≤ 25 % do GP.
- Reduzir frequência das faltantes 16 e 06 (de ~90 % dos jogos para ≤ 50 %).
- Reduzir similaridade média GP de ~0.82 para ≤ 0.75.
- Não piorar taxa de 14/15 hits.
- Não gerar jogos inválidos (validação `_is_valid_game` intacta).
- Comparativo baseado nos lotes `STRUCT_REALIGN_V1_*` vs baseline `STRUCT_TEST_*_001`.

## Log institucional

```
2026-06-16  ADM autorizou realinhamento estrutural V1.
            Missão: IMPLEMENTAR_REALINHAMENTO_ESTRUTURAL_LEI15_V1
            Base: EPOCH_001 audit (15D–20D).
            Modo inicial: shadow_test.
            Feature flag: LOTOIA_LAW15_STRUCTURAL_REALIGNMENT_V1
```

## Referências

- ADR-042 — Política ML Assistivo (ML não substitui Lei 15)
- Relatório EPOCH_001: `reports/epoch_001_structural_results_15d_20d.md`
- Evidências: lotes `STRUCT_TEST_15D_001` a `STRUCT_TEST_20D_001` no Railway PostgreSQL
