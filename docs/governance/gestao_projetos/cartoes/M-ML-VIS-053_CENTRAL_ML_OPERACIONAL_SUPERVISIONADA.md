# M-ML-VIS-053 — Ativar Painel Central ML Assistida / Operacional Supervisionada

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-ML-VIS-053` |
| **Título** | Ativar Painel Central ML Assistida / Operacional Supervisionada |
| **Projeto** | `P-ML-001` / `P-GOV-001` |
| **Tipo** | Visual / ML / Dados / Qualidade / Governança |
| **Data de abertura** | 2026-06-18 |
| **Agentes** | `agent_ml` + `agent_visual` + `agent_dados` + `agent_qualidade` + `agent_governanca` |
| **Status atual** | `CONCLUIDA` |
| **Prioridade / Risco** | Alta — painel inoperante ocultava ML supervisionado validado em PostgreSQL |

## Objetivo

Corrigir e ativar a página **Central ML — Operacional Supervisionada** para refletir o estado
real do ML operacional supervisionado sobre CORE_002 (M-ML-045), lendo `generation_events` e
`generated_games` no PostgreSQL — sem mock, sem session_state como fonte soberana.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-ML-045 concluída | ML supervisionado + trace PostgreSQL |
| M-GER-044 / M-DADOS-049 | Geração CORE_002 operacional |

## Escopo autorizado

- `dashboard/institutional_supervised_ml.py` — loader PostgreSQL operacional
- `dashboard/institutional_ml_assistive.py` — painel operacional supervisionado
- `dashboard/institutional_app.py` — rota `central_ml_diagnostics`
- Testes `tests/dashboard/test_institutional_app_ml_vis_053_operational_panel.py`
- Registro institucional + build marker

## Escopo proibido

- Alterar LEI15_CORE_002, generate_best_games, public_app, Lei 15A, schema, purge
- Geração pela Central ML; mock como dado real; session_state como fonte soberana

## Entregáveis

1. Painel PostgreSQL com últimos `generation_events` (`ml_enabled=True`, label CORE_002)
2. Exibição de decision trace, feature attribution e ML × 6 Bases (fallback controlado)
3. Bloqueios constitucionais BLK-* visíveis
4. Build marker `institutional-adm-runtime-v32`

## Veredicto

**M-ML-VIS-053 CONCLUÍDA — CENTRAL ML OPERACIONAL SUPERVISIONADA ATIVA SOBRE POSTGRESQL**
