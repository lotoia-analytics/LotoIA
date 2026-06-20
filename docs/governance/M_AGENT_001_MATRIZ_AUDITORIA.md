# M-AGENT-001 — Matriz de Auditoria (`agent_operador_ml`)

| Campo | Valor |
|-------|-------|
| **Missão** | M-AGENT-001 |
| **Agente** | `agent_operador_ml` |
| **Responsável** | `agent_governanca` (aprovação) · `agent_qualidade` (execução) |

---

## 1. Objetivos de auditoria

1. Verificar que o agente **não viola** proibições absolutas (Constituição §6).
2. Verificar **rastreabilidade completa** de cada ciclo decisório.
3. Verificar **alinamento** com POLITICA_ML_ASSISTIVO, Lei 15, CORE_002.
4. Verificar **eficácia** dos critérios de sucesso (Constituição §9).

---

## 2. Matriz de controles

| ID | Controle | Frequência | Evidência | Responsável |
|----|----------|------------|-----------|-------------|
| A01 | Ausência de writes em N0 | Por release | Testes read-only | `agent_qualidade` |
| A02 | Campos `agent_*` presentes | Por decisão | `context_json` / memória | `agent_ml` |
| A03 | Sem purge em ações do agente | Contínuo | Logs PostgreSQL | `agent_dados` |
| A04 | Veredito lote preservado | Por lote | Central ML | `agent_visual` |
| A05 | `critical` fora de Conferir | Por lote | M-OPS-078 tests | `agent_qualidade` |
| A06 | Hits fora de liberação estrutural | Por veredito | M-ML-076 trace | `agent_ml` |
| A07 | Handoff `responsible_cursor_agent` | Por recomendação | decision_block | `agent_governanca` |
| A08 | Rollback testado | Por promoção Nível | ADR + testes | `agent_qualidade` |
| A09 | Walk-forward em aprendizado | Por ciclo N2+ | `agent_operational_learning` | `agent_ml` |
| A10 | Kill-switch funcional | Trimestral | Env `DISABLED` | `agent_plataforma` |

---

## 3. Checklist por nível de autonomia

### Nível 0 — Observador

- [ ] Zero `INSERT`/`UPDATE`/`DELETE` em tabelas operacionais pelo módulo agente
- [ ] Relatório gerado com `agent_trace_id`
- [ ] Fontes §4 da Constituição cobertas
- [ ] CORE_002, Lei 15, `public_app` não alterados

### Nível 1 — Recomendador

- [ ] Todos os itens N0
- [ ] Recomendações com `agent_reasoning_summary` e métricas citadas
- [ ] Nenhuma execução sem flag de aprovação humana
- [ ] Card UI somente leitura até aprovação

### Nível 2 — Supervisionado

- [ ] Todos os itens N1
- [ ] Plano de calibração `authorized_ml_calibration_plan` referenciado
- [ ] `agent_expected_effect` vs `agent_observed_effect` preenchidos
- [ ] Rollback documentado e testado

### Nível 3–4

- [ ] ADR de autonomia vigente
- [ ] Benchmark temporal anexo
- [ ] Circuit breaker e kill-switch validados
- [ ] Auditoria `agent_governanca` assinada

---

## 4. Evidências obrigatórias por ciclo

| Evidência | Local | Retenção |
|-----------|-------|----------|
| `agent_trace_id` | `context_json` / log | Permanente |
| Métricas de entrada | Snapshot Central ML | Por `generation_event_id` |
| Ação executada | `agent_action` | Permanente |
| Efeito esperado / observado | Trace agente | Permanente |
| Roteamento Cursor | `responsible_cursor_agent` | Por decisão |
| Comparativo estrutural | Relatório / memória | Por ciclo N+1 |

---

## 5. Queries de auditoria sugeridas (read-only)

```sql
-- Lotes com trace do agente (futuro)
SELECT id, created_at,
       context_json->>'agent_trace_id' AS trace,
       context_json->>'agent_action' AS action,
       context_json->>'agent_autonomy_level' AS level
FROM generation_events
WHERE context_json->>'agent_mission_id' LIKE 'M-AGENT-%'
ORDER BY created_at DESC
LIMIT 50;
```

```sql
-- Memória de aprendizado (futuro)
SELECT id, memory_kind, strategy_name, created_at
FROM scientific_institutional_memory
WHERE memory_kind = 'agent_operational_learning'
ORDER BY created_at DESC
LIMIT 20;
```

---

## 6. Auditorias relacionadas (baseline)

| Auditoria | Relação |
|-----------|---------|
| M-GOV-AGENTS-001 | Lacuna agentes no fluxo ML |
| M-GOV-AGENTS-002 | Matriz executável de roteamento |
| M-AUDIT-077 | Promoção por lote vs. parcial |
| M-ML-076-AUDIT-00 | Separação hits vs. estrutural |
| M-OPS-078 | Promoção parcial por jogo |

---

## 7. Veredito de auditoria (template)

```
AUDITORIA agent_operador_ml — [MISSÃO] — [DATA]
Nível de autonomia avaliado: N_
Controles A01–A10: [PASS/FAIL]
Proibições P1–P13: [NENHUMA VIOLAÇÃO / VIOLAÇÕES LISTADAS]
Recomendação: [APROVAR NÍVEL / MANTER / REVOGAR]
Assinatura: agent_governanca + agent_qualidade
```

---

## 8. Confirmações M-AGENT-001

| Item | Resultado auditoria constitucional |
|------|-----------------------------------|
| Implementação runtime | **Ausente** (conforme escopo) |
| Código de produção alterado | **Não** |
| Purge | **Não** |
| Documentação constitucional | **Completa** |

**M-AGENT-001 — auditoria constitucional: PASS (read-only)**
