# M-AGENT-001 — Matriz de Permissões (`agent_operador_ml`)

| Campo | Valor |
|-------|-------|
| **Missão** | M-AGENT-001 |
| **Agente** | `agent_operador_ml` |
| **Legenda** | ✅ Permitido · ⚠️ Condicional · ❌ Proibido · 👁️ Somente leitura |

---

## 1. Matriz por domínio e nível de autonomia

| Domínio / Recurso | N0 Observador | N1 Recomendador | N2 Supervisionado | N3 Autonomia limitada | N4 Institucional |
|-------------------|:-------------:|:---------------:|:-----------------:|:---------------------:|:----------------:|
| `generation_events` (read) | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| `generation_events` (write `context_json`) | ❌ | ❌ | ⚠️ trace only | ⚠️ | ⚠️ |
| `generated_games` (read) | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| `generated_games` (write qualidade) | ❌ | ❌ | ⚠️ reclassificação | ⚠️ | ⚠️ |
| Concursos oficiais | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| Alterar concursos oficiais | ❌ | ❌ | ❌ | ❌ | ❌ |
| Central ML — veredito | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| Alterar veredito ML | ❌ | ❌ | ❌ | ❌ | ❌ |
| Calibração supervisionada | 👁️ | ⚠️ recomendar | ⚠️ plano autorizado | ⚠️ | ⚠️ |
| Geração CORE_002 / Lei 15 | 👁️ | ⚠️ recomendar regen | ❌ executar | ⚠️ batch soberano | ⚠️ |
| Purge / delete jogos | ❌ | ❌ | ❌ | ❌ | ❌ |
| Histórico Analítico | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| Promoção analítica parcial | 👁️ | ⚠️ recomendar | ⚠️ | ⚠️ auto elegíveis | ⚠️ |
| Conferir Resultados | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| Promoção conferência (`critical`) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `scientific_institutional_memory` (read) | 👁️ | 👁️ | 👁️ | 👁️ | 👁️ |
| `agent_operational_learning` (write) | ❌ | ❌ | ⚠️ | ⚠️ | ✅ |
| `public_app` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Thresholds globais / ADR weights | ❌ | ❌ | ❌ | ❌ | ❌ |
| Mascarar métricas | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 2. Matriz ação × classificação

| Classificação | Persistência | Aprovação humana | ADR extra |
|---------------|:------------:|:----------------:|:---------:|
| Observável (§5.1) | Opcional log | Não | Não |
| Recomendável (§5.2) | Trace recomendação | Sim | Não |
| Supervisionada (§5.3) | `context_json` + memória | Plano pré-autorizado | Nível 2 |
| Autônoma futura (§5.4) | Completa | Exceção / kill-switch | Nível 3+ |

---

## 3. Matriz de handoff para agentes Cursor

| `issue_type` / problema | Agente Cursor primário | `agent_operador_ml` pode |
|-------------------------|------------------------|----------------------------|
| Pool insuficiente | `agent_geracao` | Recomendar expansão; não gerar |
| Diversidade / overlap | `agent_estatistico` | Recomendar mescla / top-slice |
| Calibração / veredito | `agent_ml` | Recomendar ou aplicar plano autorizado |
| Persistência / trace | `agent_dados` | Solicitar registro memória |
| UI Central ML | `agent_visual` | Solicitar card de recomendação |
| Runtime / API | `agent_plataforma` | Solicitar endpoint observador |
| Testes / regressão | `agent_qualidade` | Submeter evidência |
| ADR / Lei 15 | `agent_governanca` | Escalar bloqueio normativo |

*Roteamento alinhado a `institutional_agent_routing_matrix` (M-GOV-AGENTS-002).*

---

## 4. Condições transversais (todas as permissões ⚠️)

1. `agent_trace_id` obrigatório.
2. `agent_autonomy_level` explícito.
3. Rollback documentado para writes.
4. Sem uso de hits 13/14/15 em decisão estrutural.
5. PostgreSQL soberano — sem `session_state` como fonte de verdade.

---

## 5. Revogação de permissões

`agent_governanca` pode revogar qualquer nível via:

- ADR de suspensão;
- variável `LOTOIA_AGENT_OPERADOR_ML_DISABLED=1`;
- downgrade forçado para N0 em incidente (M-OPS-INC-*).
