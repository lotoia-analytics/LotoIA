# ADR 051 — M-AGENT-001 Constituição do Primeiro Agente de IA (`agent_operador_ml`)

**Status:** Accepted  
**Data:** 2026-06-20  
**Missão:** M-AGENT-001  
**Tipo:** Arquitetural — read-only (sem alteração funcional)

## Contexto

A LotoIA consolidou, até M-OPS-078, um ecossistema operacional maduro:

- geração soberana **CORE_002** / Lei 15;
- **Cobertura Estrutural** (6 bases);
- **Central ML** com hierarquia, veredito e calibração supervisionada;
- **Memória Institucional** (`scientific_institutional_memory`);
- **Histórico Analítico** e **Conferir Resultados** com promoção parcial por jogo (M-OPS-078);
- **8 agentes Cursor** documentais (`agent_governanca` … `agent_visual`) e matriz executável M-GOV-AGENTS-002.

Apesar disso, o ciclo **Diagnóstico → Decisão → Ação → Validação → Aprendizado** ainda depende predominantemente do operador humano para interpretar painéis, escolher correções e validar efeitos.

A auditoria M-GOV-AGENTS-001 confirmou que os agentes institucionais existem na governança documental, mas **não há um agente de IA executivo** que orquestre qualidade estrutural e operacional de ponta a ponta.

## Decisão

1. **Instituir formalmente o primeiro Agente de IA da LotoIA** com nome oficial:

   **`agent_operador_ml`**

2. **Definir missão institucional:**

   > Produzir gerações de jogos com máxima qualidade estrutural e operacional.

3. **Posicionamento arquitetural:**
   - O `agent_operador_ml` é o **cérebro executivo do ML operacional** — orquestrador de diagnóstico, recomendação, supervisão e (futuro) ação limitada.
   - É **distinto** de `agent_ml` (domínio de código/modelos), `agent_geracao` (Lei 15/CORE_002) e dos demais agentes Cursor (escopos de engenharia).
   - Subordina-se à **POLITICA_ML_ASSISTIVO**, Lei 15, Lei 15A (congelada), CORE_002 e Lei No 001 (PostgreSQL soberano).

4. **Escopo desta missão (M-AGENT-001):**
   - Apenas **constituição, limites, governança e roadmap** — documentados em `docs/governance/M_AGENT_001_*`.
   - **Nenhuma implementação runtime**, tabela nova, rotina automática ou alteração de produção.

5. **Níveis de autonomia (roadmap):**
   - Nível 0 (Observador) → Nível 4 (Autonomia institucional), com requisitos explícitos por estágio (ver `M_AGENT_001_ROADMAP_AUTONOMIA.md`).

6. **Memória proposta:**
   - Novo `memory_kind`: `agent_operational_learning` em `scientific_institutional_memory` — **especificado**, não implementado nesta missão.

7. **Rastreabilidade obrigatória de decisões futuras:**
   - `agent_trace_id`, `agent_reasoning_summary`, `agent_action`, `agent_expected_effect`, `agent_observed_effect`.

## Alternativas de nome consideradas

| Nome | Prós | Contras | Decisão |
|------|------|---------|---------|
| **`agent_operador_ml`** | Alinha ao papel operacional; distingue de `agent_ml`; português institucional | Pode soar “humano” | **Escolhido** |
| `agent_lotoia_ai` | Genérico, marca | Ambíguo; não diferencia domínio | Rejeitado |
| `agent_gp_orchestrator` | Descreve GP | Inglês; foco estreito em GP | Rejeitado |
| `agent_quality_operator` | Foco em qualidade | Inglês; omite ML institucional | Rejeitado |

## Consequências

- Existe referência normativa para a primeira implementação do agente (missão futura **M-AGENT-002** recomendada: Nível 0 Observador).
- Os 8 agentes Cursor permanecem responsáveis por **engenharia e governança**; o `agent_operador_ml` passa a ser a **persona executiva de IA** sobre o fluxo ML operacional.
- Qualquer promoção de autonomia (Nível ≥ 2) exigirá ADR complementar, testes e aprovação `agent_governanca`.

## Alternativas rejeitadas

- Implementar o agente nesta mesma missão (viola escopo read-only).
- Fundir `agent_operador_ml` com `agent_ml` (colapsa separação operador × domínio técnico).
- Conceder autonomia de alteração de Lei 15, CORE_002 ou dados oficiais (viola política assistiva).

## Referências

- `docs/governance/M_AGENT_001_CONSTITUICAO_AGENTE_OPERADOR_ML.md`
- `docs/governance/M_AGENT_001_ROADMAP_AUTONOMIA.md`
- `docs/governance/M_AGENT_001_MATRIZ_PERMISSOES.md`
- `docs/governance/M_AGENT_001_MATRIZ_RISCOS.md`
- `docs/governance/M_AGENT_001_MATRIZ_AUDITORIA.md`
- `docs/governance/M_GOV_AGENTS_001_AUDITORIA_AGENTES_FLUXO_ML.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `ADRs/ADR_009_POLITICA_ML_ASSISTIVO.md`

## Confirmações

| Item | Status |
|------|--------|
| Implementação do agente | **Não** — apenas constituição |
| Alteração de produção / geração / ML | **Nenhuma** |
| CORE_002, Lei 15, Lei 15A, `public_app` | **Intactos** |
| Purge | **Nenhum** |
| Tabelas novas | **Nenhuma** |
