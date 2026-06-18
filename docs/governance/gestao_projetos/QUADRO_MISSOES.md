# Quadro de Missões — LotoIA

Visão **ativa** de projetos e missões. Atualizar a cada mudança de status.

**Legenda status:** ver [MATRIZ_STATUS_TAREFAS.md](MATRIZ_STATUS_TAREFAS.md)

Última atualização: **2026-06-17**

---

## Em andamento / pendentes

| mission_id | Título | Owner | Status | Prioridade | Último commit | Veredicto / bloqueio |
|------------|--------|-------|--------|------------|---------------|----------------------|
| `PAINEL_ADM_CORE_002_ALIGN` | Alinhar Painel ADM ao CORE_002 (remover bypass `_generate_direct_15_games`) | `agent_visual` + `agent_plataforma` | `PLANEJADA` | high | — | Aguarda ADR-047 ordem 1 |
| `LEI15A_REACTIVATION` | Reativar Lei 15A sob gate soberano | `agent_governanca` + `agent_ml` | `PLANEJADA` | medium | — | Lei 15A **SUSPENSA** |
| `RAILWAY_CHECKPOINT_F0C1261` | Confirmar deploy produção em `f0c1261` | `agent_plataforma` | `EM_DEPLOY` | high | `f0c1261` | `DEPLOY EM ANDAMENTO` |
| `TIER_OPS_SCRIPTS` | Classificar scripts ops (run/purge/migrate) | `agent_governanca` | `PLANEJADA` | low | — | Recomendação auditoria constitucional |

---

## Concluídas recentes (referência rápida)

| mission_id | Owner | Status | Commit(s) | Veredicto |
|------------|-------|--------|-----------|-----------|
| `GESTAO_PROJETOS_FASE_0` | `agent_governanca` | `CONCLUÍDA` | `7b3d632` | `GESTAO_PROJETOS_FASE_0_IMPLANTADA` |
| `HOTFIX_INSTITUTIONAL_LIGHT_MODE` | `agent_visual` + `agent_plataforma` | `CONCLUÍDA` | `f0c1261` | `PAINEL RESTAURADO` |
| `LEI15_CORE_002_CONSTITUTIONAL_TRANSITION` | `agent_governanca` | `CONCLUÍDA` | `06d3932` | `GIT SINCRONIZADO` |
| `LEI15_CORE_002_SOVEREIGN` | `agent_geracao` | `CONCLUÍDA` | `fea8e2e` | Núcleo implantado; geração bloqueada |
| `HISTORY_PRESERVATION_EPOCH` | `agent_dados` | `CONCLUÍDA` | `d747bf2` | Purge bloqueado |
| `CORE_002_GENERATION_ROUTING` | `agent_geracao` | `CONCLUÍDA` | `f6a770a` | Legacy default bloqueado |
| `RESET_GENERATION_EPOCH_001` | `agent_dados` | `CONCLUÍDA` | *(ver registro)* | EPOCH_001 iniciado |
| `FIX_JSON_GENERATION_EVENTS` | `agent_visual` | `CONCLUÍDA` | `001b807` | Serialização JSON corrigida |
| `FIX_STRUCTURAL_COVERAGE_PREFIX_SUFFIX` | `agent_visual` | `CONCLUÍDA` | `545693f` | Tabelas prefixo/sufixo 4 |

---

## Backlog institucional (ADR-047)

Ordem recomendada — **não reordenar sem ADR**:

| # | Missão | Agente | Depende de |
|---|--------|--------|------------|
| 1 | Painel ADM sem bypass Lei 15 | `agent_visual`, `agent_plataforma` | ADR-047 registrada ✅ |
| 2 | Lei 15A sob gate | `agent_governanca`, `agent_ml` | Painel ADM alinhado |
| 3 | Habilitar geração CORE_002 | `agent_geracao` | Painel 100% + flag explícita |

---

## Regras do quadro

1. **Uma linha por missão ativa** — subtarefas vão no cartão ou registro.
2. **Não apagar linhas** — mover para `REGISTRO_MISSOES.md` ao arquivar.
3. **Commit hash** — preencher assim que existir push.
4. **Veredicto** — obrigatório ao sair de `ABERTA`.

---

## Como adicionar missão

1. Copiar [MODELO_CARTAO_TAREFA.md](MODELO_CARTAO_TAREFA.md).
2. Inserir linha na seção **Em andamento**.
3. Ao encerrar, mover resumo para **Concluídas** + append em [REGISTRO_MISSOES.md](REGISTRO_MISSOES.md).
