# M-VIS-032 — Governança read-only no Painel ADM

Cartão encerrado — missão concluída, validada em produção e incorporada à `main`.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-032` |
| **Título** | Governança read-only no Painel ADM |
| **Projeto** | `P-GOV-001` |
| **Tipo** | Visual / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Data de encerramento** | 2026-06-17 |
| **Agentes** | `agent_visual` (primário), `agent_governanca`, `agent_plataforma` |
| **Status atual** | `CONCLUIDA` |
| **Prioridade** | `ALTA` |

## Objetivo

Implementar no Painel ADM uma área de Governança Institucional em modo read-only, exibindo
Gestão de Projetos Fase 0, missões, bloqueios, leis/ADRs e status Git/Railway — sem ações
operacionais.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-VIS-031 fechada em `main` | PR #126 — merge `510cccb` |
| M-VIS-031 validada em produção | build `institutional-adm-runtime-v6` @ `a5a3f2f250b1` |
| Painel ADM Fase 1 ativo | Status Constitucional + bloqueios M-VIS-031 |

## Escopo autorizado

- `dashboard/institutional_governance.py` — bloco read-only
- `dashboard/institutional_app.py` — menu/rota Governança
- `dashboard/institutional_build.py` — bump build marker
- testes em `tests/dashboard/test_institutional_app_governance_read_only.py`
- documentação Gestão de Projetos

## Escopo proibido

- Liberar geração; purge; banco; Núcleo; Lei 15A; ML operacional; deploy manual; edição de missões

## Bloqueios relacionados

| Código | Tratamento | Estado pós-validação |
|--------|------------|----------------------|
| `BLK-GERACAO-001` | Exibido como ATIVO — sem liberar geração | `MITIGADO` (exibição read-only) |
| `BLK-PURGE-001` | Exibido como ATIVO — sem botão de purge | `MITIGADO` (exibição read-only) |
| `BLK-ADM-001` | Governança read-only — sem rotas operacionais | `MITIGADO` |
| `BLK-DEPLOY-001` | REMOVIDO — tela informativa apenas | `MONITORAMENTO` |

## Entregáveis

1. Menu/bloco **Governança Institucional — read-only**
2. Seção Gestão de Projetos Fase 0 (leitura de docs versionados)
3. Missões M-GOV-030, M-OPS-INC-001, M-VIS-031, M-VIS-032
4. Bloqueios institucionais ativos
5. Leis/ADRs principais (Lei 001, Lei 15, ADR-047, políticas)
6. Git/Railway informativo (build/commit)
7. Alerta fixo read-only
8. Testes de import e bloco read-only

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch implantação | `cursor/m-vis-032-governanca-read-only-cae6` |
| PR implantação | [#127](https://github.com/lotoia-analytics/LotoIA/pull/127) |
| Merge commit | `7df540ce3bcc3a0eae3916afdf8baaa6c97a447f` |
| Merge em `main` | 2026-06-17 |
| Branch fechamento | `cursor/m-vis-032-fechamento-cae6` |

## Evidência de testes

| Campo | Valor |
|-------|-------|
| Arquivo | `tests/dashboard/test_institutional_app_governance_read_only.py` |
| Resultado | 13/13 passed (com suite Fase 1, pós-merge em `main`) |
| Escopo | bloco Governança read-only — import, snapshot, rota, sem geração/purge |

## Evidência de deploy (Railway produção)

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker | `institutional-adm-runtime-v7` |
| Commit em produção | `7df540ce3bcc` |
| Deploy | via GitHub merge PR #127 — sem deploy manual |
| Pendência de deploy | **NENHUMA** |
| Tipo de evidência | Textual/operacional (build + commit + confirmação operador) — screenshot/script HTTP **não exigidos** |

## Confirmação textual/operacional em produção

Validação registrada pelo operador:

- Painel ADM carregando em produção
- Build `institutional-adm-runtime-v7` ativo na sidebar
- Commit `7df540ce3bcc` ativo na sidebar
- Menu/tela **Governança Institucional — read-only** disponível
- **Gestão de Projetos — Fase 0** visível
- Missões M-GOV-030, M-OPS-INC-001, M-VIS-031 e M-VIS-032 disponíveis
- Bloqueios institucionais exibidos (BLK-GERACAO/PURGE/ADM/DEPLOY)
- Leis e ADRs exibidos (Lei 001, Lei 15, ADR-047, ML assistivo, Preservação, Inventário PR #124)
- Geração **BLOQUEADA**; purge **PROTEGIDO**; ML **ASSISTIVO**; Lei 15A **SUSPENSA**
- Sem botões de geração, purge, merge, deploy ou edição na área read-only
- Status Constitucional LotoIA visível na tela de Governança

## Checklist de conformidade

```text
A Autorização:     [x] OK
B Documentação:    [x] OK
C Git:             [x] OK
D Qualidade:       [x] OK — 13 testes dashboard
E Deploy:          [x] OK — evidência leve produção
F Bloqueios:       [x] OK — exibidos sem liberar operação
G Veredicto:       [x] OK
```

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto** | `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| **Data** | 2026-06-17 |
| **Emitido por** | `agent_governanca` + `agent_visual` + `agent_plataforma` |
| **Resumo** | PR #127 mergeada em `main`; Railway em `7df540ce3bcc` com build `institutional-adm-runtime-v7`; Governança read-only confirmada textualmente em produção. |
| **Veredicto institucional** | **M-VIS-032 ATIVA EM PRODUÇÃO — GOVERNANÇA READ-ONLY VALIDADA** |
| **Veredicto de fechamento** | **M-VIS-032 FECHADA FORMALMENTE — GOVERNANÇA READ-ONLY VALIDADA EM PRODUÇÃO** |
| **Registro** | `REGISTRO_MISSOES_INSTITUCIONAL.md` — entrada M-VIS-032 |

## Próxima missão autorizável

A definir após fechamento da atualização da política de checkpoint simplificado (M-GOV-031).

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `PROPOSTA` | Autorizada pós M-VIS-031 | `agent_governanca` |
| 2026-06-17 | `PROPOSTA` | `EM_EXECUCAO` | Implementação bloco read-only | `agent_visual` |
| 2026-06-17 | `EM_EXECUCAO` | `AGUARDANDO_REVIEW` | PR #127 aberta | `agent_visual` |
| 2026-06-17 | `AGUARDANDO_REVIEW` | `CONCLUIDA` | Merge em `main` + deploy Railway + validação textual produção | `agent_governanca` |
