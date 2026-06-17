# Quadro de Projetos e Missões — LotoIA

## Status do quadro

| Campo | Valor |
|-------|-------|
| Registro | `QUADRO_PROJETOS_MISSOES_FASE_0` |
| Atualização | 2026-06-17 (M-VIS-033 pacote Núcleo Lei 15) |
| Modo | Fase 0 — documental/Git |
| Política | `POLITICA_GESTAO_PROJETOS_LOTOIA.md` |

---

## Legenda de status (resumo)

| Status | Significado |
|--------|-------------|
| `PROPOSTA` | Aguardando autorização |
| `AUTORIZADA` | Escopo aprovado, pronta para execução |
| `EM_EXECUCAO` | Trabalho ativo |
| `AGUARDANDO_EVIDENCIA` | Falta Git, teste ou deploy |
| `BLOQUEADA` | Impedimento formal |
| `AGUARDANDO_VEREDICTO` | Evidências reunidas, falta decisão |
| `CONCLUIDA` | Veredicto positivo registrado |
| `CONGELADA` | Pausada institucionalmente |
| `ARQUIVADA` | Encerrada sem execução futura |

Detalhes completos: [`MATRIZ_STATUS_TAREFAS.md`](MATRIZ_STATUS_TAREFAS.md)

---

## Projetos institucionais ativos

### P-GOV-001 — Governança e constitucionalidade

| ID missão | Título | Agente primário | Status | Última evidência Git |
|-----------|--------|-----------------|--------|----------------------|
| M-RODADA-001 | Rodada multiagente Painel / CORE_002 | multiagente (8) | `CONCLUIDA` | merge `295f1c0` — [PR #130](https://github.com/lotoia-analytics/LotoIA/pull/130) |
| M-GOV-031 | Checkpoint produção simplificado | `agent_governanca` + `agent_plataforma` | `CONCLUIDA` | merge `1de7cfd` — [PR #129](https://github.com/lotoia-analytics/LotoIA/pull/129) |
| M-VIS-033 | Pacote Núcleo Lei 15 no Painel ADM | `agent_visual` + `agent_estatistico` | `EM EXECUCAO / AGUARDANDO REVIEW` | branch `cursor/m-vis-033-pacote-nucleo-lei15-cae6` |
| M-VIS-032 | Governança read-only no Painel ADM | `agent_visual` + `agent_governanca` | `CONCLUIDA` | merge `7df540c` — produção `institutional-adm-runtime-v7` |
| M-VIS-031 | Painel ADM Fase 1 — bloqueios constitucionais | `agent_visual` + `agent_plataforma` | `CONCLUIDA` | merge `a5a3f2f` — [PR #125](https://github.com/lotoia-analytics/LotoIA/pull/125) — produção `a5a3f2f250b1` / `institutional-adm-runtime-v6` |
| M-GOV-030 | Gestão de Projetos — Fase 0 | `agent_governanca` + `agent_plataforma` | `CONCLUIDA` | merge `7a10363` — [PR #121](https://github.com/lotoia-analytics/LotoIA/pull/121) |
| M-GOV-029 | Inventário funcional ADM (Mission 29) | `agent_visual` | `CONGELADA` | docs em `main` |
| M-GOV-028 | Manutenção institucional contínua (Mission 28) | `agent_governanca` | `CONCLUIDA` | `MISSION_28_CONTINUOUS_MAINTENANCE_POLICY.md` |
| M-GOV-027 | Auditoria constitucional pós LEI15_CORE_002 | `agent_governanca` | `AGUARDANDO_VEREDICTO` | `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md` |

### P-LEI15-001 — Núcleo soberano Lei 15

| ID missão | Título | Agente primário | Status | Bloqueio |
|-----------|--------|-----------------|--------|----------|
| M-LEI15-003 | Unificar path geração ADM → generate_best_games | `agent_geracao` + `agent_plataforma` | `CONCLUIDA` | merge `6dea9e7` — produção `institutional-adm-runtime-v8` |
| M-LEI15-002 | Implantação LEI15_CORE_002 | `agent_geracao` | `CONCLUIDA` | Geração bloqueada (`GENERATION_ENABLED=0`) |
| M-LEI15-001 | Alinhamento constitucional doc/painel/ADM | `agent_governanca` | `BLOQUEADA` | Painel ADM conflitante — ver auditoria |

### P-OPS-001 — Runtime e deploy cloud

| ID missão | Título | Agente primário | Status | Última evidência deploy |
|-----------|--------|-----------------|--------|-------------------------|
| M-OPS-015 | Cloud-only Railway (Lei 001) | `agent_plataforma` | `CONCLUIDA` | `RAILWAY_CLOUD_ONLY_DEPLOYMENT_2026_06_15.md` |
| M-OPS-INC-001 | Incidente deploy — artefato não versionado | `agent_plataforma` + `agent_governanca` | `CONCLUIDA` | hotfix `f0c1261` — `build=institutional-adm-runtime-v6` |

### P-ML-001 — ML assistivo e experimentos

| ID missão | Título | Agente primário | Status |
|-----------|--------|-----------------|--------|
| M-ML-009 | Política ML assistivo (ADR-042 / ADR-009) | `agent_ml` | `CONCLUIDA` |

---

## Missões sem projeto (documentais avulsas)

| ID | Título | Status | Referência |
|----|--------|--------|------------|
| DOC-001 | Expansão dimensional 16D–23D | `CONGELADA` | `ADR_EXPANSAO_DIMENSIONAL_16D_23D.md` |
| M-094 | ManyChat integração | `PROPOSTA` | `ADR-012-manychat.md` |

---

## Fila de abertura (backlog documental)

| Prioridade | Título sugerido | Agente | Motivo |
|------------|-----------------|--------|--------|
| Alta | Segregação public_app vs institutional_app | `agent_plataforma` | Rodada multiagente |
| Média | Consolidação corpus ADR (`ADRs/` vs `docs/adr/`) | `agent_governanca` | Duplicidade documental |
| Baixa | Fase 1 — gestão de projetos com painel | `agent_governanca` | Fora do escopo Fase 0 |

---

## Regras de manutenção do quadro

1. Toda nova missão recebe ID único `M-<DOMÍNIO>-<NNN>`.
2. Status deve seguir a matriz oficial — sem status inventado.
3. Bloqueios devem apontar documento ou veredicto que originou o bloqueio.
4. Missão `CONCLUIDA` exige veredicto no registro.
5. Atualizar este quadro no mesmo commit que altera o registro, quando possível.

---

## Referências

- [`REGISTRO_MISSOES_INSTITUCIONAL.md`](REGISTRO_MISSOES_INSTITUCIONAL.md)
- [`CHECKLIST_MISSAO_OBRIGATORIO.md`](CHECKLIST_MISSAO_OBRIGATORIO.md)
- [`TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md`](TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md)
