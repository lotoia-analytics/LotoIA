# M-VIS-036 — Simulação Institucional / Backtesting

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-036` |
| **Título** | Simulação Institucional / Backtesting |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Estatístico / ML / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_estatistico` + `agent_ml` + `agent_visual` + `agent_governanca` + `agent_qualidade` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | Médio (read-only); alto/crítico se tocar geração real, banco, Núcleo, purge, vazamento temporal ou public_app |

## Objetivo

Preparar no Painel ADM a área de Simulação Institucional / Backtesting em modo
read-only/diagnóstico, separando-a de Conferir Resultados e de geração operacional.

## Regra temporal (mandatória)

Concurso **X** usa apenas dados até **X-1**. Walk-forward obrigatório. Sem leakage.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-VIS-035 em `main` | PR #136 — merge `76031cb` |
| Geração bloqueada | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` |

## Escopo autorizado

- `dashboard/institutional_simulation_backtesting.py`
- Rota/menu **Simulação Institucional / Backtesting**
- Separação fluxos: Conferir / Simular session / Backtesting / Geração
- Janelas walk-forward 10/20/30
- Banner orientação em Simular Resultados
- Testes read-only + regressões

## Escopo proibido

- Geração real; backtest com geração; purge; Núcleo; banco/schema; Lei 15A; ML operacional; public_app

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-vis-036-simulacao-backtesting-cae6` |
| Build marker | `institutional-adm-runtime-v12` |

## Veredicto alvo

**M-VIS-036 CONCLUÍDA — SIMULAÇÃO INSTITUCIONAL / BACKTESTING READ-ONLY AGUARDANDO REVIEW**
