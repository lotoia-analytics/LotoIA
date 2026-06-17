# M-VIS-033 — Pacote Núcleo Lei 15 no Painel ADM

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-033` |
| **Título** | Pacote Núcleo Lei 15 no Painel ADM |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Governança / Estatístico / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_visual` + `agent_governanca` + `agent_estatistico` + `agent_qualidade` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | Médio (visual/read-only); alto se tocar geração, banco ou Núcleo |

## Objetivo

Implementar no Painel ADM, em modo read-only, o Pacote Núcleo Lei 15 — consolidando
visualização institucional do LEI15_CORE_002, Matriz Soberana, papéis das dezenas,
Cobertura Estrutural orientada ao CORE_002 e leitura pelas 6 Bases.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-LEI15-003 em `main` | PR #131 — merge `6dea9e7` |
| Fechamento M-LEI15-003 | PR #132 — merge `ce15adb` |
| Geração bloqueada | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` |

## Escopo autorizado

- `dashboard/institutional_core_002.py` — pacote read-only CORE_002
- `dashboard/institutional_app.py` — menu/rota + banner Cobertura Estrutural
- `dashboard/institutional_build.py` — bump build marker v9
- testes em `tests/dashboard/test_institutional_app_core_002_read_only.py`
- documentação Gestão de Projetos

## Escopo proibido

- Liberar geração; alterar Núcleo; banco; purge; Lei 15A; ML operacional; public_app; deploy manual

## Entregáveis

1. Tela **Núcleo Lei 15 — CORE_002** (read-only)
2. Matriz Soberana 01–25 + papéis das dezenas
3. Leitura pelas 6 Bases (definições + histórico V1/CAND-D/baseline)
4. Evidências históricas reclassificadas
5. Orientação Cobertura Estrutural alinhada ao CORE_002
6. Textos institucionais (matriz ≠ cartão fixo; hit isolado ≠ veredicto)
7. Testes read-only + regressão M-VIS-031 / M-LEI15-003

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-vis-033-pacote-nucleo-lei15-cae6` |
| Build marker | `institutional-adm-runtime-v9` |

## Veredicto alvo

**M-VIS-033 CONCLUÍDA — PACOTE NÚCLEO LEI 15 READ-ONLY AGUARDANDO REVIEW**
