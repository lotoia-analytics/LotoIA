# M-VIS-033 — Pacote Núcleo Lei 15 no Painel ADM

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-033` |
| **Título** | Pacote Núcleo Lei 15 no Painel ADM |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Governança / Estatístico / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_visual` + `agent_governanca` + `agent_estatistico` + `agent_qualidade` |
| **Status atual** | `CONCLUIDA` |
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
| Branch implantação | `cursor/m-vis-033-pacote-nucleo-lei15-cae6` |
| PR implantação | [#133](https://github.com/lotoia-analytics/LotoIA/pull/133) |
| Merge commit | `a2009cda458b2044020c5d9256693e0b19950e3b` |
| Commit entrega | `c5ce9ad259ce414b17500e04f4556cac0a973859` |
| Build marker | `institutional-adm-runtime-v9` |

## Evidência de deploy (Railway produção)

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker | `institutional-adm-runtime-v9` |
| Commit em produção | `a2009cda458b2044020c5d9256693e0b19950e3b` |
| Deploy Railway | 2026-06-17T19:55:04Z |
| Pendência de deploy | **NENHUMA** |
| Tipo de evidência | Textual/operacional (P1–P5) — M-GOV-031 |

## Confirmação textual/operacional em produção

- HTTP 200 em `/`
- Streamlit `/_stcore/health` → `ok`
- Deploy Railway recebido com SHA `a2009cd`
- Build `institutional-adm-runtime-v9`
- Testes 28/28 passed (core_002 + M-VIS-031 + M-LEI15-003)
- Tela `core_002_read_only` registrada
- Tela read-only — sem `st.button` operacional
- Sem chamada de geração/purge no módulo
- Geração **BLOQUEADA**
- `public_app` inalterado
- LEI15_CORE_002 inalterado

## Checklist de conformidade

```text
A Autorização:     [x] OK
B Documentação:    [x] OK
C Git:             [x] OK — PR #133 mergeada
D Qualidade:       [x] OK — 9 testes core_002 + regressão
E Deploy:          [x] OK — evidência leve produção (Railway 19:55:04Z)
F Bloqueios:       [x] OK — geração bloqueada; read-only confirmado
G Veredicto:       [x] OK
```

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto** | `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| **Data** | 2026-06-17 |
| **Emitido por** | `agent_governanca` + `agent_visual` + `agent_qualidade` |
| **Resumo** | PR #133 mergeada em `main`; Railway em `a2009cda` com build `institutional-adm-runtime-v9`; pacote Núcleo Lei 15 read-only confirmado. |
| **Veredicto institucional** | **M-VIS-033 ATIVA EM PRODUÇÃO POR EVIDÊNCIA PROPORCIONAL — NÚCLEO LEI 15 READ-ONLY VALIDADO** |
| **Veredicto de fechamento** | **M-VIS-033 FECHADA FORMALMENTE — NÚCLEO LEI 15 READ-ONLY VALIDADO EM PRODUÇÃO** |
| **Registro** | `REGISTRO_MISSOES_INSTITUCIONAL.md` — entrada M-VIS-033 |

## Próxima missão autorizável

`M-VIS-034` — Cobertura Estrutural + 6 Bases refinadas no Painel ADM

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `EM_EXECUCAO` | Autorizada pós M-LEI15-003 | `agent_visual` |
| 2026-06-17 | `EM_EXECUCAO` | `AGUARDANDO_REVIEW` | PR #133 aberta | `agent_visual` |
| 2026-06-17 | `AGUARDANDO_REVIEW` | `INCORPORADA À MAIN` | Merge PR #133 | operador institucional |
| 2026-06-17 | `INCORPORADA À MAIN` | `CONCLUIDA` | Deploy Railway + checkpoint produção validado | `agent_governanca` |
