# Fluxograma Operacional do Agente de IA

Este documento descreve o fluxo de atuação do Agente de IA dentro do ecossistema LotoIA, operando nos Níveis 0 (Observador) e 1 (Recomendador).

## Fluxo de Observação e Recomendação

1. **Gatilho Operacional**
   - Um evento de geração é concluído (`generation_events`).
   - Ocorre uma reprovação de lote na Central ML.
   - O `agent_estatistico` identifica baixa diversidade estrutural.

2. **Fase de Observação (Leitura de Dados)**
   - O Agente de IA consulta o PostgreSQL (via `agent_dados`).
   - Analisa a tabela `generated_games` vinculada ao evento.
   - Lê as métricas da Cobertura Estrutural (prefixo, sufixo, sobreposição).
   - Consulta a `scientific_institutional_memory` para resgatar o histórico de aprendizado (`agent_operational_learning`).

3. **Fase de Análise e Raciocínio**
   - O agente avalia a conformidade estrutural contra os objetivos permanentes (ex: diversidade, cobertura das 25 dezenas).
   - Identifica anomalias (ex: concentração excessiva, falha na captura das bases 13/14).
   - Formula uma recomendação explicável.

4. **Fase de Registro e Recomendação (Ação)**
   - O agente não executa a alteração. Ele gera um payload de recomendação.
   - O payload contém: `agent_trace_id`, `agent_reasoning_summary`, `agent_action`, `agent_expected_effect`.
   - A recomendação é persistida na `scientific_institutional_memory` com o `memory_kind` = `agent_operational_learning`.
   - A recomendação é roteada para o agente institucional responsável (conforme ADR-048 - Matriz de Roteamento), por exemplo, para o `agent_ml` (calibração) ou `agent_geracao` (pool estrutural).

5. **Fase de Execução Supervisionada**
   - O agente responsável (humano ou institucional) analisa a recomendação.
   - Se aprovada, a ação é executada no sistema.

6. **Fase de Aprendizado (Feedback Loop)**
   - Após a execução, o resultado real é avaliado.
   - O campo `agent_observed_effect` é atualizado na memória institucional.
   - O Agente de IA utiliza este feedback para aprimorar recomendações futuras.
