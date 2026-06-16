# ADR-045 — LEI15_15A_CORE_REALIGNMENT_V3_BALANCED

**Status:** APROVADA PARA IMPLEMENTACAO EM SHADOW_TEST  
**Missão:** MISSAO_DA_VITORIA_REAVALIAR_NUCLEOS_LEI15_15A  
**Data:** 2026-06-16  
**Predecessora:** ADR-044 (V2) — evidência concluída, **rejeitada como candidata operacional**

---

## Contexto — o que a V2 provou

Lote oficial `STRUCT_CORE_REALIGN_V2_15D_001` (20 GEs × 50 jogos × 140 reconciliation_runs baseline 3705–3711):

| Dimensão | V1 | V2 | Leitura |
|---|---|---|---|
| Melhor hit | **14** | 11 | V2 perdeu força de acerto |
| Média hits | **12.143** | ~9.25 | Queda severa |
| Runs 14+ | **5** | 0 | Critério operacional falhou |
| Runs 13+ | **47** | 0 | Critério operacional falhou |
| Top prefixo_3 | 40.4% | **16.3%** | V2 “corrigiu demais” a estética |
| Top sufixo_3 | 26.7% | 15.6% | Estrutura OK |
| GP overlap | 9.717 | **9.558** | Estrutura OK |

**Conclusão:** a V2 validou a hipótese de que o pool pre-filter rígido + `max_prefix3_ratio=0.15` reduz concentração estrutural, mas **destrói a recorrência útil** herdada do último sorteio e **mata os hits**.

A V2 **não** deve ser promovida. Permanece como evidência EPOCH_001 para desenho da V3.

**Decisão ADM (2026-06-16):**

- Manter **V1** como melhor versão `shadow_test` até aqui.
- **Rejeitar V2** como candidata operacional.
- Usar V2 apenas como base de aprendizado para **V3 BALANCED**.

---

## Princípio da V3 — hits-first, estrutura equilibrada

A V3 **não** repete a lógica da V2:

> ❌ “quanto menor o prefixo, melhor”

A V3 adota:

> ✅ **melhorar prefixo/sufixo sem destruir hits**

### Prioridade (ordem obrigatória)

1. **Hits primeiro** — preservar ou superar patamar V1.
2. **Preservar ganhos do V1** — não regredir sufixo/GP overlap.
3. **Reduzir prefixo gradualmente** — vs V1, não vs piso artificial.
4. **Controlar sufixo** — manter controle já alcançado pelo V1.
5. **Reduzir redundância GP** — diversidade como freio, não destruição.
6. **Melhorar cobertura das dezenas críticas** — sem cortar herança boa.

---

## O que manter (governança — inalterável)

| Regra | Valor |
|---|---|
| Persistência | PostgreSQL obrigatório (Lei No 001) |
| Modo | `shadow_test` only |
| `active` | **Bloqueado** |
| Jogos inválidos | 0 |
| Rastreabilidade | Total (`realignment_metadata`, batch labels) |
| Comparativo | BASELINE + V1 + V3 |
| Avanço 16D | **Bloqueado** até 15D validado |
| ML | Auxiliar / guardião — **não** substitui Lei 15 |

---

## O que abandonar da V2

| V2 (rejeitado) | V3 (substituir) |
|---|---|
| `max_prefix3_ratio = 0.15` | alvo **30–35%** (redução gradual vs V1 ~40%) |
| Pool pre-filter rígido (`max_pool_prefix3_ratio=0.30`) | pre-filter **suave** — cap moderado, não esvaziar herança |
| Diversidade como objetivo primário | diversidade como **freio** pós-preservação combinatória |
| Corte duro de prefixo | **corrigir excesso**, não cortar a raiz |
| Critério “prefixo < 35%” isolado | prefixo **< V1 e >= 30%** (não artificialmente baixo) |

---

## Proposta técnica V3 BALANCED

**Nome:** `LEI15_15A_CORE_REALIGNMENT_V3_BALANCED`  
**Flag (proposta):** `LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3`  
**Label (proposta):** `STRUCT_CORE_REALIGN_V3_BALANCED_15D_001`

### Camadas (conceito)

1. **Preservar força combinatória Lei 15** — perfis Recurrent/Hybrid mantêm herança útil do último sorteio.
2. **Redução gradual de excesso** — penalidades de concentração mais próximas do V1, não V2.
3. **Pool pre-filter suave** — limitar outliers extremos de prefixo, não homogeneizar o pool.
4. **ML Guardião (auxiliar)** — escolher núcleo candidato / sinalizar excesso; nunca mutar Lei 15 soberana.
5. **Composição V1+** — base `compose_diverse_gp` V1 com ajustes balanceados, não substituição agressiva.

### Parâmetros iniciais (proposta — calibrar em shadow_test)

| Parâmetro | V1 ref | V2 (rejeitado) | V3 proposta |
|---|---|---|---|
| `max_prefix3_ratio` | ~0.25 | 0.15 | **0.30–0.35** |
| `max_pool_prefix3_ratio` | — | 0.30 | **0.40–0.45** (suave) |
| `min_pool_size_after_filter` | — | 30 | **40** (menos fallback destrutivo) |
| Objetivo prefixo | reduzir | minimizar | **reduzir vs V1, manter >= 30%** |

---

## Critérios mínimos de aprovação V3 (shadow_test 15D)

Comparativo oficial: **20 GEs × 7 concursos = 140 reconciliation_runs** (dedupe 3711).

### Obrigatórios (hits — espelho V1)

| Critério | Mínimo |
|---|---|
| Melhor hit | **>= 14** |
| Média hits | **>= 12.143** |
| Runs 14+ | **>= 5** |
| Runs 13+ | **>= 47** |

### Estrutura (equilibrada — não agressiva)

| Critério | Regra |
|---|---|
| Top prefixo_3 | **< V1 (40.4%)** e **>= 30%** (não artificial) |
| Top sufixo_3 | **<= V1 (26.7%)** — manter controle |
| GP overlap | **<= V1 (9.717)** — não piorar |
| Jogos inválidos | **0** |
| Fallback V1 total | **0** ou justificado e rastreado |

---

## Status V2 pós-lote

| Item | Estado |
|---|---|
| ADR-044 V2 | Implementada — evidência coletada |
| V2 operacional | **Rejeitada** |
| V1 shadow_test | **Vencedora atual** |
| V3 BALANCED | **Implementada shadow_test 15D** — aguarda lote `STRUCT_CORE_REALIGN_V3_BALANCED_15D_001` |
| 16D | **Bloqueado** |

---

## Referências

- ADR-044 — V2 (pool pre-filter + thresholds agressivos)
- ADR-043 — V1 structural realignment
- Lote V2 evidência: `STRUCT_CORE_REALIGN_V2_15D_001` (GE 52–71)
- Lote V3: `STRUCT_CORE_REALIGN_V3_BALANCED_15D_001`

### Implementação (shadow_test 15D)

| Componente | Caminho |
|---|---|
| Flag / config | `src/lotoia/governance/lei15_15a_core_realignment_v3.py` |
| Composição BALANCED | `src/lotoia/generation/core_realignment_v3.py` |
| Hook gerador | `src/lotoia/generator/basic_generator.py` |
| Label | `STRUCT_CORE_REALIGN_V3_BALANCED_15D_001` |
| Env | `LOTOIA_LEI15_15A_CORE_REALIGNMENT_V3=shadow_test` |

### Sequência ops

```powershell
python scripts/ops/run_core_realign_v3_test_15d.py --generations 1
python scripts/ops/run_core_realign_v3_test_15d.py --validate-only
python scripts/ops/run_core_realign_v3_test_15d.py --target-total 20
python scripts/ops/reconcile_core_realign_v3_baseline_contests.py
python scripts/ops/compare_core_realign_4way_15d.py
```
