# M-VIS-037 — Conferir Resultados / Auditoria de Lotes Reais Persistidos

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-037` |
| **Título** | Conferir Resultados / Auditoria de Lotes Reais Persistidos |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Dados / Governança / Estatístico / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_visual` + `agent_dados` + `agent_governanca` + `agent_qualidade` + `agent_estatistico` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | Médio (read-only); alto/crítico se tocar geração, banco, Núcleo, purge ou public_app |

## Objetivo

Reorganizar Conferir Resultados como auditoria institucional de lotes reais persistidos
no PostgreSQL (Lei 001), separando conferência de simulação, session_state e geração.

## Frase obrigatória

Conferir Resultados é auditoria de produção gerada e persistida. Simular Resultados é
laboratório. Conferir não gera, não simula e não usa session_state como fonte soberana.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-VIS-036 em `main` | PR #138 — merge `240e3d0` |
| Geração bloqueada | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` |

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-vis-037-conferir-resultados-auditoria-cae6` |
| Build marker | `institutional-adm-runtime-v13` |

## Veredicto alvo

**M-VIS-037 CONCLUÍDA — CONFERIR RESULTADOS READ-ONLY AGUARDANDO REVIEW**
