# ADR-048 - Matriz de Roteamento dos Agentes Institucionais

## Status

Accepted

## Contexto

A auditoria M-GOV-AGENTS-001 confirmou que os 8 agentes oficiais LotoIA estao
formalizados em `.cursor/rules/`, governanca documental e cartoes de missao, mas
**nao estavam integrados ao pipeline decisorio ML** (diagnosticos, calibracao,
hierarquia operacional, snapshot e `context_json`).

Sem `responsible_agent` estruturado, o cockpit Central ML e a Cobertura Estrutural
indicavam problemas e acoes recomendadas sem ownership institucional auditavel.

## Decisao

Adotar a **Matriz Executavel de Roteamento dos Agentes Institucionais**
(`src/lotoia/governance/institutional_agent_routing_matrix.py`) como contrato
normativo M-GOV-AGENTS-002, versao `M-GOV-AGENTS-002-v1`.

A matriz define roteamento por:

- `issue_type` (diagnosticos estruturais / calibracao)
- `stage_id` (hierarquia operacional M-ML-073)
- `corrective_action` (remediacoes automaticas do pool)

Campos obrigatorios em payloads enriquecidos:

- `responsible_agent`
- `support_agents`
- `routing_reason`
- `agent_routing_matrix_version`
- `agent_routing_mission_id` (`M-GOV-AGENTS-002`)

Integracao obrigatoria:

1. `coverage_evidence_interpreter` — `decision_blocks`, `calibration_plan`, evidencia agregada
2. `ml_operational_hierarchy` — `stage_results` e trace hierarquico
3. `basic_generator` — payload de geracao soberana CORE_002
4. `context_json` — persistencia PostgreSQL via painel ADM
5. Central ML / Cobertura — card "Agente responsavel" e etapas com ownership

## Mapeamento resumido

| Dominio | Agente principal |
|---------|------------------|
| Conformidade / pool estrutural | `agent_geracao` |
| Diversidade / cobertura / overlap | `agent_estatistico` |
| Calibracao / veredito ML | `agent_ml` |
| Render cockpit / painel | `agent_visual` + `agent_plataforma` |
| Politica Lei 15 / ADR | `agent_governanca` |
| Persistencia trace | `agent_dados` |

## Consequencias

Positivas:

- handoff auditavel entre dominios institucionais;
- cockpit ML com ownership visivel por problema e etapa;
- rastreabilidade em `context_json` sem alterar Lei 15 ou CORE_002.

Negativas / trade-offs:

- payloads ML maiores (matriz versionada em memoria institucional);
- novos `issue_type` exigem atualizacao da matriz + ADR se alterar contrato.

## Conformidade

- Lei 15 / Lei 15A permanecem soberanas — a matriz **nao altera** regras de geracao.
- ML continua auxiliar (ADR-042).
- `agent_core` inexistente — correto e mantido.

Status institucional esperado:

`INSTITUTIONAL_AGENT_ROUTING_MATRIX_ACTIVE`
