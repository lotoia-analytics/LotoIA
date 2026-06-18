# M-ML-054 — Central ML como Motor de Calibração Supervisionada da Saída

| Campo | Valor |
|-------|-------|
| **Status** | `CONCLUIDA` |
| **Build ADM** | `institutional-adm-runtime-v34` |
| **Agentes** | agent_ml + agent_estatistico + agent_geracao + agent_dados + agent_governanca + agent_qualidade |
| **Pré-requisito** | M-ML-045, M-ML-VIS-053 |

## Objetivo

Transformar a Central ML de painel/diagnóstico em motor supervisionado de calibração da saída
gerada, aplicando ajustes automáticos de score/rerank subordinados ao CORE_002.

## Entregáveis

1. `src/lotoia/ml/supervised_output_calibration.py` — motor de calibração
2. Hook em `generate_best_games` antes de `compose_sovereign_gp`
3. Persistência em `context_json` (sem alteração de schema)
4. Painel Central ML com diagnóstico, ações, trace e 6 Bases
5. Testes unitários e integração ADM

## Regras constitucionais

- Permitido: ajustar score, reranquear, penalizar redundância, priorizar diversidade/cobertura
- Proibido: alterar LEI15_CORE_002, Lei 15, Lei 15A, public_app, schema, purge

## Veredicto

**M-ML-054 CONCLUÍDA — CENTRAL ML ATIVA COMO MOTOR DE CALIBRAÇÃO SUPERVISIONADA DA SAÍDA**
