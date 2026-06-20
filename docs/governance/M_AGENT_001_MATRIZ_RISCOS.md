# M-AGENT-001 — Matriz de Riscos (`agent_operador_ml`)

| Campo | Valor |
|-------|-------|
| **Missão** | M-AGENT-001 |
| **Agente** | `agent_operador_ml` |
| **Escala** | Probabilidade (B/Baixa · M/Média · A/Alta) × Impacto (1–5) |

---

## 1. Riscos estratégicos

| ID | Risco | P | I | Mitigação |
|----|-------|---|---|-----------|
| R01 | Agente substitui julgamento humano sem governança | M | 5 | Níveis de autonomia graduais; ADR por estágio |
| R02 | Confusão entre `agent_operador_ml` e `agent_ml` | A | 3 | Nomenclatura oficial; documentação; escopos separados |
| R03 | Autonomia prematura (N3+ sem benchmark) | M | 5 | Requisitos roadmap; kill-switch |
| R04 | Percepção de “predição de loteria” | M | 4 | Comunicação institucional; POLITICA_ML_ASSISTIVO |

---

## 2. Riscos operacionais

| ID | Risco | P | I | Mitigação |
|----|-------|---|---|-----------|
| R05 | Recomendação errada gera recalibração improdutiva | M | 4 | N1 somente recomenda; operador aprova |
| R06 | Promoção indevida de jogos `critical` | B | 5 | Regras M-OPS-078; proibição P9 |
| R07 | Loop de geração sem melhoria estrutural | M | 4 | `agent_observed_effect`; circuit breaker |
| R08 | Dependência de `session_state` | M | 3 | PostgreSQL soberano; proibição explícita |
| R09 | Ignorar veredito global do lote | B | 3 | Central ML mantém veredito; parcial ≠ ocultar |

---

## 3. Riscos técnicos

| ID | Risco | P | I | Mitigação |
|----|-------|---|---|-----------|
| R10 | Escrita acidental em produção (N0) | M | 5 | Testes read-only; code review `agent_qualidade` |
| R11 | Vazamento temporal em aprendizado | M | 5 | Walk-forward obrigatório N2+ |
| R12 | Trace incompleto (`agent_trace_id`) | M | 3 | Schema obrigatório §7.2 Constituição |
| R13 | Memória `agent_operational_learning` sem versionamento | M | 3 | `memory_kind` + versão + ADR |
| R14 | Conflito com matriz M-GOV-AGENTS-002 | B | 3 | Handoff `responsible_cursor_agent` |

---

## 4. Riscos de conformidade (soberania)

| ID | Risco | P | I | Mitigação |
|----|-------|---|---|-----------|
| R15 | Violação Lei 15 / CORE_002 | B | 5 | Proibições P5–P7; auditoria `agent_governanca` |
| R16 | Alteração de concursos oficiais | B | 5 | Proibição P1–P2 |
| R17 | Purge ou exclusão de jogos | B | 5 | Proibição P3 |
| R18 | Uso de hits em liberação estrutural | M | 4 | M-ML-076; auditoria trace |
| R19 | Alteração `public_app` | B | 4 | Fora do escopo; proibição P11 |
| R20 | Mascaramento de reprovações | M | 5 | Proibição P4; auditoria |

---

## 5. Riscos de adoção humana

| ID | Risco | P | I | Mitigação |
|----|-------|---|---|-----------|
| R21 | Operador não confia nas recomendações | M | 3 | Explicabilidade; métricas citadas |
| R22 | Sobrecarga de recomendações (ruído) | M | 3 | Severidade e priorização por `issue_type` |
| R23 | Responsável Cursor não indicado | A | 3 | Integração M-GOV-AGENTS-002 |

---

## 6. Mapa de calor (resumo)

| Impacto \ Probabilidade | Baixa | Média | Alta |
|-------------------------|-------|-------|------|
| **5 — Crítico** | R15–R17 | R01, R03, R10 | — |
| **4 — Alto** | R19 | R04–R08, R18, R20 | — |
| **3 — Médio** | R14 | R02, R12–R13, R21–R23 | — |
| **1–2 — Baixo** | R09 | — | — |

---

## 7. Resposta a incidentes (pré-implementação)

1. Desabilitar agente: `LOTOIA_AGENT_OPERADOR_ML_DISABLED=1`
2. Registrar incidente: `M-OPS-INC-*`
3. Downgrade autonomia para N0 via ADR emergencial
4. Auditoria `agent_governanca` + `agent_qualidade`
5. Sem purge — preservar traces para análise
