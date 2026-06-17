# Política de Preservação de Histórico — LotoIA

| Campo | Valor |
|-------|-------|
| Registro | `POLITICA_PRESERVACAO_HISTORICO_LOTOIA_2026_06_17` |
| Agente | `agent_dados` |
| ADR | `ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002` |
| Auditoria origem | `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17` |
| Módulo | `src/lotoia/governance/history_preservation_policy.py` |

---

## Objetivo

Proteger a **memória institucional** da LotoIA contra purge genérico, `delete_history` do Painel ADM e resets operacionais sem filtro seguro por label.

Esta política **não autoriza limpeza**. Prepara limpeza operacional **controlada** em missão posterior.

---

## Princípios fail-closed

1. **Todo purge genérico é bloqueado** até limpeza controlada autorizada.
2. **Label desconhecido → preservar.**
3. **Label institucional → preservar.**
4. **GE ligado a ADR, EPOCH_001 ou relatório → preservar.**
5. **Dúvida → preservar.**
6. **Limpeza futura** só após: backup → congelamento → classificação → autorização dual → relatório → dry-run aprovado.

---

## Itens obrigatoriamente protegidos

| # | Item |
|---|------|
| 1 | GE **114** — CAND-A |
| 2 | GE **115** — CAND-D |
| 3 | Baseline **EPOCH_001** |
| 4 | `STRUCT_TEST_15D_001` |
| 5 | `STRUCT_REALIGN_V1_15D_001` |
| 6 | V2, V3, V4, CAND-001 (evidência histórica) |
| 7 | ADR-043 a ADR-047 |
| 8 | Relatórios 6 bases |
| 9 | Relatórios ML |
| 10 | Relatório Auditoria Constitucional |
| 11 | `imported_contests` |
| 12 | `lotofacil_official_history` |
| 13 | `scientific_institutional_memory` |
| 14 | `institutional_memory_*` |
| 15 | `FROZEN_LEGACY_LABELS` |
| 16 | Labels **SOBERANO**, **EVIDÊNCIA HISTÓRICA**, **LEGADO CONGELADO** |

---

## Classificações

| Classe | Protegido? | Exemplos |
|--------|------------|----------|
| **SOBERANO** | Sim | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| **EVIDÊNCIA HISTÓRICA** | Sim | V1, CAND-D, V2–V4, CDX |
| **LEGADO CONGELADO** | Sim | `STRUCT_TEST_15D_001`, `FROZEN_LEGACY_LABELS` |
| **INSTITUCIONAL DESCONHECIDO** | Sim | Label ausente ou não mapeado |
| **OPERACIONAL DESCARTÁVEL** | Somente com limpeza controlada futura | Nenhum liberado nesta fase |

---

## Tabelas

### Soberanas (Lei 001) — nunca purge genérico

- `imported_contests`
- `lotofacil_official_history`
- `scientific_institutional_memory`
- `institutional_memory_*`
- `benchmark_runs`, `backtest_runs`, `calibration_runs`
- `schema_migrations`

### Operacionais mistas — purge genérico bloqueado

- `generation_events`
- `generated_games`
- `reconciliation_*`
- `operational_logs`, `reset_events`
- `institutional_output_signatures`

---

## Guardas implementadas

| Superfície | Função | Efeito |
|------------|--------|--------|
| Painel `_purge_institutional_history_tables` | `assert_generic_institutional_purge_blocked` | **Bloqueado** |
| `InstitutionalResetService` | `assert_generic_institutional_purge_blocked` | **Bloqueado** |
| `lotoia_clean_zero` delete | `assert_table_generic_purge_blocked` | **Bloqueado** |
| Ops `purge_*_ge.py` | `assert_generation_event_deletion_allowed` | **Bloqueado** se evidência |

---

## Limpeza futura (sequência institucional)

```text
backup
  → congelamento
  → classificação por label
  → autorização agent_dados + agent_governanca
  → relatório de preservação
  → dry-run aprovado (scripts/ops/dry_run_history_cleanup_lotoia.py)
  → missão dedicada de limpeza (posterior)
```

---

## Ferramentas

| Artefato | Função |
|----------|--------|
| `history_preservation_policy.py` | Classificação + guardas |
| `dry_run_history_cleanup_lotoia.py` | Simulação read-only |
| `reports/history_preservation_audit_2026_06_17.json` | Export auditável |

---

## Referências

- `docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md`
- `docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md`
- `docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md`
