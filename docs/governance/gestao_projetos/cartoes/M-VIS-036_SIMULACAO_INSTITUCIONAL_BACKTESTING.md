# M-VIS-036 — Simulação Institucional / Backtesting

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-036` |
| **Título** | Simulação Institucional / Backtesting |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Estatístico / ML / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_estatistico` + `agent_ml` + `agent_visual` + `agent_governanca` + `agent_qualidade` |
| **Status atual** | `CONCLUIDA` |
| **Prioridade / Risco** | Médio (read-only); alto/crítico se tocar geração real, banco, Núcleo, purge, vazamento temporal ou public_app |

## Objetivo

Preparar no Painel ADM a área de Simulação Institucional / Backtesting em modo
read-only/diagnóstico, separando-a de Conferir Resultados e de geração operacional.

## Regra temporal (mandatória)

Concurso **X** usa apenas dados até **X-1**. Walk-forward obrigatório. Sem leakage.

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch implantação | `cursor/m-vis-036-simulacao-backtesting-cae6` |
| PR implantação | [#138](https://github.com/lotoia-analytics/LotoIA/pull/138) |
| Merge commit | `240e3d0cc5b1c332725d7bb53c5948441693c677` |
| Commit entrega | `43c081b2b98df0d76fb960d87164627efd8a1e29` |
| Build marker | `institutional-adm-runtime-v12` |

## Evidência de deploy

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Checkpoint | HTTP 200 + health `ok` (P1–P5 M-GOV-031) |

## Confirmação

- 64/64 testes passed
- Corte temporal X-1 documentado
- Separação Conferir / Simular session / Backtesting / Geração
- Sem geração real, purge, banco/schema, Núcleo, Lei 15A, ML operacional, public_app

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto institucional** | **M-VIS-036 ATIVA EM PRODUÇÃO — SIMULAÇÃO INSTITUCIONAL / BACKTESTING READ-ONLY VALIDADO** |
| **Veredicto de fechamento** | **M-VIS-036 CONCLUÍDA E ATIVA EM PRODUÇÃO — SIMULAÇÃO INSTITUCIONAL / BACKTESTING READ-ONLY VALIDADO** |

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `EM_EXECUCAO` | Autorizada pós M-VIS-035 | `agent_estatistico` |
| 2026-06-17 | `EM_EXECUCAO` | `AGUARDANDO_REVIEW` | PR #138 aberta | `agent_visual` |
| 2026-06-17 | `AGUARDANDO_REVIEW` | `INCORPORADA À MAIN` | Merge PR #138 | operador institucional |
| 2026-06-17 | `INCORPORADA À MAIN` | `CONCLUIDA` | Checkpoint proporcional | `agent_governanca` |
