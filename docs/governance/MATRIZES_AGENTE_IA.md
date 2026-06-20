# Matrizes do Agente de IA (Permissões, Riscos e Auditoria)

Este documento estabelece as diretrizes de controle, mitigação de riscos e auditoria para a atuação do Agente de IA na LotoIA.

## 1. Matriz de Permissões

A matriz abaixo define o nível de acesso do Agente de IA aos diferentes componentes da plataforma.

| Domínio / Componente | Nível de Acesso | Justificativa |
| :--- | :--- | :--- |
| `generation_events` | Leitura (Read-Only) | Necessário para observar eventos de geração e resultados. |
| `generated_games` | Leitura (Read-Only) | Necessário para analisar a estrutura dos jogos gerados. |
| `scientific_institutional_memory` | Leitura e Escrita (Append-Only) | Leitura para aprendizado; Escrita para registrar `agent_operational_learning`. |
| Central ML (Métricas) | Leitura (Read-Only) | Necessário para diagnosticar a qualidade dos lotes. |
| CORE_002 (Motor de Geração) | Negado (No Access) | O núcleo gerador é soberano e inalterável pelo Agente de IA. |
| Lei 15 (Regras) | Negado (No Access) | As regras estruturais são fixas e imutáveis. |
| Histórico Oficial (Concursos) | Leitura (Read-Only) | Necessário para análise de performance (walk-forward). |
| Painel ADM (`public_app`) | Negado (No Access) | A interface de usuário não deve ser manipulada pelo Agente. |
| Purge / Deleção de Dados | Negado (No Access) | O Agente não tem permissão para excluir registros institucionais. |

## 2. Matriz de Riscos

A matriz de riscos identifica potenciais ameaças decorrentes da introdução do Agente de IA e as respectivas estratégias de mitigação.

| Risco Identificado | Impacto | Probabilidade | Estratégia de Mitigação |
| :--- | :--- | :--- | :--- |
| **R1:** Violar a Lei 15 ou o CORE_002. | Crítico | Baixa | Bloqueio de acesso a escrita nos módulos geradores. Auditoria rigorosa nos Níveis 0 e 1. |
| **R2:** Corromper a `scientific_institutional_memory`. | Alto | Média | Implementação de escrita Append-Only. Validação estrutural do payload de recomendação antes da persistência. |
| **R3:** Loop infinito de recomendações (Recalibração excessiva). | Médio | Alta | Limitação de recomendações por evento de geração. Inclusão do campo `agent_observed_effect` para interromper ciclos falhos. |
| **R4:** Vazamento Temporal (Anti-Leakage violation). | Crítico | Baixa | Restrição de leitura de dados futuros durante a formulação de recomendações (Walk-Forward Validation obrigatório). |
| **R5:** Perda de Explicabilidade (Efeito Caixa-Preta). | Alto | Média | Exigência obrigatória dos campos `agent_trace_id` e `agent_reasoning_summary` em toda ação. |

## 3. Matriz de Auditoria

A matriz de auditoria define como as ações do Agente de IA serão rastreadas e verificadas para garantir a conformidade institucional.

| Evento Auditável | Ponto de Verificação | Responsável pela Auditoria | Frequência |
| :--- | :--- | :--- | :--- |
| Geração de Recomendação | Registro na tabela `scientific_institutional_memory` (`memory_kind` = `agent_operational_learning`). | `agent_governanca` / Humano | Por Lote (Tempo Real) |
| Conformidade Estrutural | Verificação de que a recomendação não sugere alteração do CORE_002 ou Lei 15. | `agent_qualidade` | Diária |
| Rastreabilidade (`trace_id`) | Confirmação de que 100% das recomendações possuem `agent_trace_id` único e explicável. | `agent_dados` | Semanal |
| Eficácia da Recomendação | Análise do `agent_expected_effect` versus `agent_observed_effect`. | `agent_estatistico` | Mensal |
| Integridade do PostgreSQL | Verificação de que o Agente não realizou operações de Purge ou deleção. | `agent_dados` | Contínua (Triggers) |
