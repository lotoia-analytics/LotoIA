# M-VIS-031 — Painel ADM Fase 1: Bloqueios Constitucionais e Status mínimo

Cartão ativo — correção constitucional defensiva do Painel ADM.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-031` |
| **Título** | Painel ADM Fase 1 — Bloqueios Constitucionais e Status mínimo |
| **Projeto** | `P-GOV-001` |
| **Tipo** | Correção constitucional defensiva |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_visual` (primário), `agent_plataforma` |
| **Status atual** | `AGUARDANDO_REVIEW` |
| **Prioridade** | `ALTA` |

## Objetivo

Tornar o Painel ADM constitucionalmente seguro em Fase 1: bloqueios defensivos, status
constitucional mínimo e eliminação de riscos imediatos do inventário PR #124.

## Base documental

- `docs/governance/INVENTARIO_REDesenHO_CONCEITUAL_PAINEL_ADM_LEI15_CORE002.md`
- PR #124 — merge `328d26f`

## Escopo autorizado

- `dashboard/institutional_app.py` — bloqueios UI e status constitucional
- testes em `tests/dashboard/test_institutional_app_phase1_constitutional_blocks.py`
- documentação Gestão de Projetos

## Escopo proibido

- Liberar geração; alterar Núcleo; purge; banco; Lei 15A; segregar public_app

## Bloqueios relacionados

| Código | Tratamento Fase 1 |
|--------|-------------------|
| `BLK-GERACAO-001` | Gerador bloqueado na UI + fail-safe em `_run_clean_law15_generation` |
| `BLK-PURGE-001` | Limpeza Controlada — botão purge removido |
| `BLK-ADM-001` | Status constitucional + órfã `generation` removida de `allowed_pages` |
| `BLK-DEPLOY-001` | PR para review — sem deploy manual |

## Entregáveis

1. Banner Status Constitucional (sidebar + home)
2. Gerador ADM CORE_002 — BLOQUEADO
3. NameError `analysis_batch_label` corrigido / inalcançável
4. Página órfã `generation` bloqueada
5. Limpeza Controlada — BLOQUEADA
6. Limpeza de Sessão preservada
7. Captions ML/diagnóstico assistivo

## Veredicto

Pendente — **M-VIS-031 CONCLUÍDA — PAINEL ADM FASE 1 AGUARDANDO REVIEW** (após merge PR).
