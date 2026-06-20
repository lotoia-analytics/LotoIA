# Roadmap de Níveis de Autonomia do Agente de IA

O Agente de IA da LotoIA evoluirá de forma gradual e supervisionada, garantindo a estabilidade institucional e a aderência à Lei 15. A progressão entre níveis exige a aprovação de ADRs específicos e o cumprimento de rigorosos requisitos de sucesso.

## Nível 0: Observador (Fase Atual)
**Objetivo:** Compreender o ecossistema e registrar métricas sem interferir no fluxo operacional.
**Capacidades:**
- Leitura passiva de `generation_events` e `generated_games`.
- Monitoramento de métricas na Central ML e Cobertura Estrutural.
- Registro de logs analíticos.
**Requisitos para avanço:**
- Demonstração de estabilidade na leitura de dados sem causar overhead no PostgreSQL.
- Capacidade de identificar anomalias estruturais com 95% de precisão.

## Nível 1: Recomendador (Fase Atual / Curto Prazo)
**Objetivo:** Propor ações corretivas baseadas em observações empíricas, sujeitas à aprovação humana ou de agentes institucionais.
**Capacidades:**
- Sugerir recalibração de parâmetros de geração.
- Recomendar mesclas estruturais para melhorar a diversidade.
- Persistir recomendações na `scientific_institutional_memory` (`agent_operational_learning`).
**Requisitos para avanço:**
- Taxa de aceitação das recomendações superior a 80%.
- Redução comprovada na necessidade de recalibrações sucessivas nos lotes em que o agente atuou.

## Nível 2: Supervisionado (Médio Prazo)
**Objetivo:** Executar ações corretivas menores em ambientes isolados (sandbox/simulação), aguardando veredicto final para promoção à produção.
**Capacidades:**
- Gerar lotes de teste com calibrações sugeridas.
- Submeter os lotes de teste à Central ML para avaliação automática.
- Preparar o payload final para o `agent_governanca` aprovar a integração.
**Requisitos para avanço:**
- Zero violações da Lei 15 ou do CORE_002 nos lotes gerados em sandbox.
- Capacidade comprovada de aumentar a taxa de promoção de jogos ao Histórico.

## Nível 3: Autonomia Limitada (Longo Prazo)
**Objetivo:** Executar calibrações dinâmicas e reordenação (reranking) em tempo real dentro de limites estritos pré-aprovados.
**Capacidades:**
- Ajustar pesos de calibração automaticamente, desde que dentro das margens definidas pela governança.
- Rejeitar autonomamente lotes que violem flagrantemente as métricas de diversidade, solicitando regeração imediata.
**Requisitos para avanço:**
- Auditoria constitucional completa (M-GOV-042 ou superior) sem apontamentos de risco.
- Explicabilidade em tempo real perfeitamente alinhada com os relatórios do `agent_estatistico`.

## Nível 4: Autonomia Institucional (Horizonte Futuro)
**Objetivo:** Atuar como o principal orquestrador da qualidade estrutural, gerenciando ativamente o ciclo de vida dos jogos, desde a geração até a promoção, sempre subordinado à Lei 15.
**Capacidades:**
- Gestão completa da `scientific_institutional_memory`.
- Otimização contínua do motor estrutural (dentro das regras do CORE_002).
- Atuação plena e integrada com os demais 8 agentes institucionais.
**Requisitos de manutenção:**
- Monitoramento contínuo de Anti-Leakage (walk-forward validation).
- Rastreabilidade ininterrupta via `agent_trace_id`.
