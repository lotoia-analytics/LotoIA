# M-VIS-032 — Governança read-only no Painel ADM

Cartão ativo — camada read-only de Governança Institucional no Painel ADM.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-032` |
| **Título** | Governança read-only no Painel ADM |
| **Projeto** | `P-GOV-001` |
| **Tipo** | Visual / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_visual` (primário), `agent_governanca`, `agent_plataforma` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
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

| Código | Tratamento |
|--------|------------|
| `BLK-GERACAO-001` | Exibido como ATIVO — sem liberar geração |
| `BLK-PURGE-001` | Exibido como ATIVO — sem botão de purge |
| `BLK-ADM-001` | Governança read-only — sem rotas operacionais |
| `BLK-DEPLOY-001` | REMOVIDO — tela informativa apenas |

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
| Branch | `cursor/m-vis-032-governanca-read-only-cae6` |
| PR | pendente |
| Build marker esperado | `institutional-adm-runtime-v7` |

## Veredicto

Pendente — **M-VIS-032 CONCLUÍDA — GOVERNANÇA READ-ONLY AGUARDANDO REVIEW** (após PR).
