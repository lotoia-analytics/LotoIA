# Política de Gestão de Projetos — LotoIA (Fase 0)

## Status

`POLITICA_GESTAO_PROJETOS_FASE_0_FORMALIZADA`

| Campo | Valor |
|-------|-------|
| Registro | `POLITICA_GESTAO_PROJETOS_LOTOIA` |
| Fase | **0** — documental, versionada no Git |
| Data | 2026-06-17 |
| Agentes | `agent_governanca`, `agent_plataforma` |
| Escopo | Governança de missões — **sem** Painel ADM, banco, geração ou Núcleo |

---

## Contexto

Após o incidente de deploy em produção causado por `dashboard/institutional_light_mode.py`
existir localmente mas **não estar versionado no Git** (`ModuleNotFoundError` em
`institutional_app.py`), ficou registrado que a LotoIA precisa de uma camada formal de
**Gestão de Projetos** para controlar:

- missões e tarefas institucionais;
- roteamento por agente;
- status e bloqueios;
- evidência Git;
- testes mínimos;
- deploy e checkpoint de produção;
- veredicto formal de encerramento.

Esta política **não substitui** ADRs, Lei No 001, Lei 15/15A ou políticas científicas.
Complementa a governança operacional com disciplina de **execução de missões**.

---

## Objetivo

Impedir que tarefas avancem, sejam consideradas concluídas ou entrem em produção **sem**
evidência rastreável de:

1. escopo declarado e respeitado;
2. commit e push no GitHub;
3. testes mínimos executados (quando aplicável);
4. checkpoint de deploy (quando aplicável);
5. veredicto institucional explícito.

---

## Fase 0 — o que é

| Característica | Fase 0 |
|----------------|--------|
| Formato | Markdown versionado em `docs/governance/gestao_projetos/` |
| Interface | **Nenhuma** — fora do Painel ADM |
| Banco | **Nenhum** — sem tabelas ou persistência operacional |
| Automação destrutiva | **Proibida** |
| Automação de deploy | **Proibida** — deploy continua manual/Railway/CI existente |
| Rastreabilidade | Git + quadro documental + registro de missões |

---

## Fase 0 — o que não é

- Não é ferramenta de PM (Jira, Linear, etc.).
- Não é alteração de runtime, API, dashboard ou schema.
- Não autoriza geração de jogos, purge, reset de histórico ou mudança de Núcleo.
- Não substitui PR, CODEOWNERS ou branch protection em `main`.

---

## Princípios institucionais

### 1. Uma missão, um foco

Cada missão deve ter **um agente responsável** e escopo delimitado. Proibido misturar na
mesma ordem operacional: banco + geração + painel + governança constitucional.

Referência: ADR-047 — ordem de transição por agente.

### 2. Nada concluído sem evidência Git

Toda entrega operacional ou de código **deve** terminar com:

- `git status` final;
- branch utilizada;
- arquivos alterados;
- commit realizado;
- hash do commit;
- push confirmado para o GitHub;
- link do commit ou branch.

Missões **somente documentais** encerram com commit dos artefatos em
`docs/governance/gestao_projetos/`.

### 3. Arquivo referenciado = arquivo versionado

Se código importa, referencia ou depende de um módulo/arquivo, esse arquivo **deve**
existir no Git **antes** do merge em `main`. Incidente tipo `institutional_light_mode`
é **falha de governança de projeto**, não apenas bug de runtime.

### 4. Veredicto obrigatório

Toda missão encerra com **um** veredicto da matriz oficial
(`gestao_projetos/MATRIZ_STATUS_TAREFAS.md`). Veredictos ambíguos ou omitidos =
missão **não encerrada**.

### 5. Deploy ≠ commit

Push em `main` **não** prova produção atualizada. Missões que afetam produção exigem
checkpoint Railway separado (commit implantado, healthcheck, CI gate quando existir).

### 6. operational_effect = false por padrão

Missões de diagnóstico, auditoria, relatório ou documentação **não** alteram geração,
histórico operacional ou comportamento do painel, salvo autorização explícita.

---

## Artefatos obrigatórios (Fase 0)

| Artefato | Caminho | Função |
|----------|---------|--------|
| Política (este documento) | `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md` | Lei operacional de PM |
| Quadro de missões | `docs/governance/gestao_projetos/QUADRO_MISSOES.md` | Visão ativa de projetos |
| Checklist de missão | `docs/governance/gestao_projetos/CHECKLIST_MISSAO_OBRIGATORIO.md` | Gate antes/durante/depois |
| Cartão de tarefa | `docs/governance/gestao_projetos/MODELO_CARTAO_TAREFA.md` | Template de abertura |
| Matriz de status | `docs/governance/gestao_projetos/MATRIZ_STATUS_TAREFAS.md` | Estados e veredictos |
| Registro de missões | `docs/governance/gestao_projetos/REGISTRO_MISSOES.md` | Histórico auditável |

---

## Fluxo de vida de uma missão (Fase 0)

```text
Abertura (cartão preenchido)
  → Roteamento (agente responsável + apoio)
  → Execução (escopo permitido apenas)
  → Checklist preenchido
  → Evidência Git (commit/push/PR)
  → Testes mínimos (se aplicável)
  → Checkpoint deploy (se aplicável)
  → Veredicto formal
  → Atualização QUADRO + REGISTRO
```

---

## Roteamento por agente

| Agente | Domínio típico de missão |
|--------|--------------------------|
| `agent_governanca` | ADRs, políticas, pesos, promoção ML, transição constitucional |
| `agent_plataforma` | FastAPI, Railway, runtime, deploy, secrets, CI |
| `agent_dados` | PostgreSQL, ingestão, reset operacional controlado, backup |
| `agent_geracao` | Lei 15, motores, routing, labels de lote |
| `agent_estatistico` | Scoring, relatórios estruturais, benchmarks |
| `agent_ml` | Modelos assistivos, walk-forward, experimentos |
| `agent_visual` | Streamlit, layout, UX do painel |
| `agent_qualidade` | pytest, ruff, gates de CI |

**Regra:** missão com `owner` único; agentes de apoio **não** expandem escopo.

---

## Relação com documentos existentes

| Documento | Relação |
|-----------|---------|
| `GOVERNANCA_OPERACIONAL_LOTOIA.md` | Fonte única PostgreSQL — PM não altera |
| `BRANCH_PROTECTION_MAIN.md` | PR e checks — PM exige conformidade |
| `POLITICA_ML_ASSISTIVO.md` | ML auxiliar — PM não promove modelos |
| `POLITICA_PRESERVACAO_HISTORICO_LOTOIA.md` | Purge bloqueado — PM não autoriza limpeza |
| ADR-047 | Ordem de transição Lei 15 — PM registra dependências |

---

## Incidentes que esta política previne

| Incidente | Controle Fase 0 |
|-----------|-----------------|
| Arquivo local não versionado quebra produção | Checklist § dependências versionadas |
| Missão “concluída” sem push | Cláusula Git obrigatória |
| Merge constitucional sem testes | Checklist § testes mínimos |
| Deploy assumido sem checkpoint | Matriz: `DEPLOY EM ANDAMENTO` vs `DEPLOYADO` |
| Escopo misturado (painel + banco + núcleo) | Princípio 1 + cartão de tarefa |

---

## Próximas fases (fora do escopo atual)

| Fase | Conteúdo | Pré-requisito |
|------|----------|---------------|
| **1** | Scripts read-only de sync quadro ↔ JSON export | Fase 0 estável 30 dias |
| **2** | Gate CI opcional (missão sem checklist = warning) | ADR dedicada |
| **3** | Painel ADM — módulo read-only de status | Missão `agent_visual` dedicada |

**Nenhuma fase posterior é autorizada por este documento.**

---

## Veredicto desta implantação

`GESTAO_PROJETOS_FASE_0_IMPLANTADA`

---

*Referências: ADR-047, `AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17`, incidente hotfix `f0c1261`.*
