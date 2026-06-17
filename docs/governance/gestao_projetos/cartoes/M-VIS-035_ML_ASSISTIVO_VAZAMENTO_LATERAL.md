# M-VIS-035 — ML Assistivo + Vazamento Lateral Constitucional

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-035` |
| **Título** | ML Assistivo + Vazamento Lateral Constitucional |
| **Projeto** | `P-GOV-001` / `P-ML-001` |
| **Tipo** | Visual / ML / Governança / Estatístico / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_ml` + `agent_visual` + `agent_governanca` + `agent_estatistico` + `agent_qualidade` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | Médio (read-only); alto/crítico se tocar geração, banco, Núcleo, purge, Lei 15A, ML operacional ou public_app |

## Objetivo

Reorganizar e reforçar no Painel ADM a leitura do ML como instrumento assistivo,
diagnóstico e governamental, junto com o bloco de Vazamento Lateral Constitucional,
em modo read-only.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-VIS-034 em `main` | PR #134 — merge `a533e61` |
| Geração bloqueada | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` |

## Escopo autorizado

- `dashboard/institutional_ml_assistive.py` — Central ML Assistiva + Vazamento Lateral
- Integração em `_render_central_ml_diagnostics_page` e `audit_monitoring_side_leak`
- Banners, matriz de separação, status ML, relação ML × 6 Bases
- Preparação conceitual M-VIS-036 (sem implementação)
- Testes read-only + regressões

## Escopo proibido

- ML operacional; geração; purge; Núcleo; banco; Lei 15A; public_app; deploy manual

## Entregáveis

1. Central ML Assistiva revisada (read-only governance header)
2. Vazamento Lateral Constitucional revisado
3. generation_cmd=False / recalibration_cmd=False explícitos
4. Frase Guardião Analítico Assistivo
5. Build marker v11

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-vis-035-ml-assistivo-vazamento-lateral-cae6` |
| Build marker | `institutional-adm-runtime-v11` |

## Veredicto alvo

**M-VIS-035 CONCLUÍDA — ML ASSISTIVO + VAZAMENTO LATERAL READ-ONLY AGUARDANDO REVIEW**
