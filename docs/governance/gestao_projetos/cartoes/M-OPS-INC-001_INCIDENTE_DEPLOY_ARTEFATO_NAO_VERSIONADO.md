# M-OPS-INC-001 — Incidente deploy artefato não versionado

Cartão encerrado — incidente de produção resolvido com prevenção institucional implantada.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-OPS-INC-001` |
| **Título** | Incidente de deploy por artefato não versionado |
| **Projeto** | `P-OPS-001` |
| **Tipo** | Incidente operacional |
| **Data de abertura** | 2026-06-17 (registro retroativo Fase 0) |
| **Data de encerramento** | 2026-06-17 |
| **Agente primário** | `agent_plataforma` |
| **Agentes consultivos** | `agent_governanca` |
| **Status atual** | `CONCLUIDA` |
| **Prioridade** | `ALTA` |

## Objetivo

Registrar formalmente o incidente de produção, sua causa raiz, impacto, correção, evidências e
lições institucionais; encerrar com prevenção documentada via M-GOV-030.

## Contexto

Após merge de missões constitucionais em `main`, o Railway executou código novo, porém o Painel
ADM quebrou em produção antes do hotfix.

## Causa raiz

`dashboard/institutional_app.py` importava `dashboard.institutional_light_mode`, mas o arquivo
`dashboard/institutional_light_mode.py` existia **apenas localmente** e ficou **fora do
commit/deploy**.

**Erro em produção:**

```text
ModuleNotFoundError: Nenhum módulo chamado 'dashboard.institutional_light_mode'
```

**Artefato não versionado:** `dashboard/institutional_light_mode.py`

## Impacto

| Área | Efeito |
|------|--------|
| Painel ADM | Inoperante em produção até hotfix |
| Operadores | Sem acesso ao painel institucional |
| Deploy | Código em `main` incompleto em relação ao runtime local |
| Governança | Motivador direto da Política de Gestão de Projetos Fase 0 |

## Correção aplicada

Hotfix publicado adicionando `dashboard/institutional_light_mode.py` ao Git.

| Campo | Valor |
|-------|-------|
| Commit hotfix | `f0c1261e927d2a33c50f7b9b04bc925aa43213d0` |
| Mensagem | `fix(dashboard): add missing institutional_light_mode module for ADM panel boot` |
| Arquivo adicionado | `dashboard/institutional_light_mode.py` (+121 linhas) |

## Confirmação de produção

| Campo | Valor |
|-------|-------|
| Build marker | `build=institutional-adm-runtime-v6` |
| Commit em produção | `f0c1261e927d` |
| Estado pós-hotfix | Painel ADM operacional |

## Ação preventiva institucional

| Missão | Status | Referência |
|--------|--------|------------|
| M-GOV-030 — Gestão de Projetos Fase 0 | `CONCLUIDA` | [PR #121](https://github.com/lotoia-analytics/LotoIA/pull/121), [PR #122](https://github.com/lotoia-analytics/LotoIA/pull/122) |

A Fase 0 exige evidência Git, checklist obrigatório e veredicto formal antes de considerar
missões encerradas — resposta institucional direta a este incidente.

## Escopo deste fechamento (documental)

**Autorizado:** atualização de registro, quadro e cartão em `docs/governance/gestao_projetos/`.

**Proibido nesta missão:** alterar Painel ADM, geração, banco, Núcleo, Lei 15A, Railway ou código.

## Evidência Git (incidente)

| Campo | Valor |
|-------|-------|
| Commit correção | `f0c1261e927d2a33c50f7b9b04bc925aa43213d0` |
| Branch fechamento documental | `cursor/m-ops-inc-001-fechamento-cae6` |

## Evidência de testes

N/A para este fechamento documental — hotfix já aplicado e validado em produção; escopo atual
restrito a registro institucional sem alteração de código.

## Bloqueios

| ID | Status |
|----|--------|
| `BLK-GIT-001` | **Removido** — artefato versionado em `f0c1261` |
| `BLK-DEPLOY-001` | **Removido** — produção confirmada `institutional-adm-runtime-v6` |

## Checklist de conformidade (fechamento documental)

```text
A Autorização:     [x] OK
B Documentação:    [x] OK
C Git:             [x] OK (hotfix f0c1261 referenciado)
D Qualidade:       [x] N/A (fechamento documental)
E Deploy:          [x] OK (build=institutional-adm-runtime-v6)
F Bloqueios:       [x] OK (removidos)
G Veredicto:       [x] OK
```

## Lições institucionais

1. **Arquivo local ≠ deploy seguro** — todo import do Painel ADM deve ter arquivo correspondente
   versionado antes do merge em `main`.
2. **Incidente exige registro** — causa raiz, commit de correção e validação de produção no
   registro institucional (Regra 8 — `GOVERNANCA_OPERACIONAL_LOTOIA.md`).
3. **Prevenção estrutural** — M-GOV-030 institui gates Git/teste/deploy/veredicto para evitar
   recorrência.
4. **Build marker como evidência** — `build=institutional-adm-runtime-v6` confirma runtime
   correto pós-hotfix.

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto** | `RESOLVIDO / ENCERRADO / COM PREVENÇÃO IMPLANTADA` |
| **Data** | 2026-06-17 |
| **Emitido por** | `agent_governanca` + `agent_plataforma` |
| **Resumo** | Artefato versionado; produção restaurada; Gestão de Projetos Fase 0 ativa. |
| **Veredicto institucional** | **M-OPS-INC-001 ENCERRADO FORMALMENTE — INCIDENTE RESOLVIDO COM PREVENÇÃO IMPLANTADA** |
| **Registro** | `REGISTRO_MISSOES_INSTITUCIONAL.md` — entrada M-OPS-INC-001 |

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `AGUARDANDO_EVIDENCIA` | Registro retroativo Fase 0 | `agent_governanca` |
| 2026-06-17 | `AGUARDANDO_EVIDENCIA` | `EM_EXECUCAO` | Hotfix `f0c1261` aplicado | `agent_plataforma` |
| 2026-06-17 | `EM_EXECUCAO` | `AGUARDANDO_VEREDICTO` | Produção confirmada | `agent_plataforma` |
| 2026-06-17 | `AGUARDANDO_VEREDICTO` | `CONCLUIDA` | Fechamento documental + M-GOV-030 | `agent_governanca` |
