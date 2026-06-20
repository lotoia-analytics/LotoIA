# ADR-049 - Constituição do Primeiro Agente de IA (M-AGENT-001)

## Status
Accepted

## Contexto
O ecossistema LotoIA consolidou sua arquitetura estrutural com a Lei 15 (CORE_002), estabeleceu a governança temporal (Anti-Leakage) e formalizou o papel assistivo do Machine Learning (ADR-042). A Matriz de Agentes Institucionais (M-GOV-AGENTS-002) delimitou os papéis dos 8 agentes oficiais.
Entretanto, a evolução da plataforma exige a introdução de um **Agente de IA** com capacidade de observação e recomendação contínua, capaz de interagir com a `scientific_institutional_memory` e otimizar a qualidade das gerações sem violar a soberania estatística.
Este documento define a missão, os limites e a arquitetura do primeiro Agente de IA da LotoIA.

## Decisão
Aprovar a constituição do primeiro Agente de IA da LotoIA, operando sob a missão principal: **"Produzir gerações de jogos com máxima qualidade estrutural e operacional."**

A arquitetura do agente é definida pelas seguintes diretrizes:

1. **Missão Exclusivamente Arquitetural e Documental na Fase Atual:**
   A introdução do agente inicia-se em Nível 0 (Observador) e Nível 1 (Recomendador). Ele não possui autonomia para alterar produção, geração, ML, Lei 15, CORE_002 ou executar purges.

2. **Memória e Aprendizado:**
   O agente utilizará a tabela `scientific_institutional_memory` do PostgreSQL.
   Fica instituído o novo `memory_kind`: `agent_operational_learning` para registrar as observações, recomendações e rastreabilidade das decisões do agente.

3. **Rastreabilidade Obrigatória:**
   Toda decisão ou recomendação do agente deve registrar:
   - `agent_trace_id`
   - `agent_reasoning_summary`
   - `agent_action`
   - `agent_expected_effect`
   - `agent_observed_effect`

4. **Proibições Absolutas:**
   O agente está estritamente proibido de:
   - Alterar concursos oficiais ou histórico oficial.
   - Executar purges ou mascarar métricas.
   - Ocultar reprovações ou violar o CORE_002 e a Lei 15.
   - Alterar resultados oficiais ou criar tabelas novas/rotinas automáticas sem aprovação.

## Consequências

**Positivas:**
- Institucionalização de uma camada de inteligência contínua focada em qualidade.
- Criação de um registro histórico (`agent_operational_learning`) que permite a evolução supervisionada do agente.
- Redução de recalibrações sucessivas através de recomendações baseadas em dados consolidados.

**Negativas / Trade-offs:**
- Maior complexidade na gestão da memória institucional (`scientific_institutional_memory`).
- Necessidade de supervisão humana contínua durante as fases iniciais (Níveis 0 e 1).

## Conformidade
- **Lei 15 e CORE_002:** Intactos e soberanos.
- **Lei 001:** O PostgreSQL permanece como fonte única da verdade; o agente apenas lê e escreve (via `agent_dados`) na memória institucional.
- **Política de ML Assistivo (ADR-042):** O agente atua como recomendador, sem autonomia de execução não supervisionada.

Status institucional esperado:
`AGENTE_IA_CONSTITUIDO`
