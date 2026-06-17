# Relatório agent_dados — Rodada Multiagente

**Veredicto:** **CONCLUÍDO — LEI 001 AUDITADA; PURGE BLOQUEADO; LIMPEZA FUTURA PLANEJADA**

---

## Proteção de histórico

Módulo: `src/lotoia/governance/history_preservation_policy.py`

- `assert_generic_institutional_purge_blocked` — fail-closed
- Tabelas soberanas + operacionais protegidas
- GE 114/115 e labels `STRUCT_*` preservados

---

## Painel ADM

- `delete_history`: UI bloqueada (M-VIS-031)
- `_purge_institutional_history_tables`: guard antes de DELETE

---

## Tabelas sensíveis mapeadas

`generation_events`, `generated_games`, `imported_contests`, `scientific_institutional_memory`,
`institutional_output_signatures`, `ml_diagnostic_decisions`, cadeia reconciliation.

---

## Gaps

| Gap | Risco |
|-----|-------|
| `lotoia_clean_zero.py` UI purge ainda expõe botão (guard runtime) | Médio |
| `test_institutional_reset_service` pode divergir de guard atual | Baixo (teste) |

---

## Limpeza Controlada futura

Requer: backup, dry-run, `agent_dados` + `agent_governanca`, missão específica — **não executada**.

---

## Confirmações

- Purge: **não executado**
- Banco/schema: **não alterado**

---

## Próximo passo

**M-DADOS-033** (proposta): Alinhar testes reset + bloquear UI `lotoia_clean_zero` read-only.
