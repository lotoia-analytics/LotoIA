# Política de Gestão de Projetos LotoIA — Fase 0

## Status

`POLITICA_GESTAO_PROJETOS_FASE_0_FORMALIZADA`

Documento oficial de governança documental para missões, tarefas, agentes, evidências Git,
testes, deploy e veredictos institucionais.

**Fase:** 0 — documental e versionada no Git.

**Não altera:** Painel ADM, geração, banco de dados, Núcleo `LEI15_CORE_002`, runtime ou
automação destrutiva.

---

## 1. Propósito

Após o incidente de deploy causado por artefato não versionado, a LotoIA institui uma camada
formal de Gestão de Projetos para impedir que missões avancem sem:

- evidência Git rastreável;
- validação de testes quando aplicável;
- validação de deploy quando aplicável;
- veredicto formal documentado;
- registro institucional atualizado.

Esta política complementa — e não substitui — Lei 001, governança operacional, política ML
assistivo e trilha ADR.

---

## 2. Escopo da Fase 0

### Autorizado

- documentos de lei, política, quadro, checklist, template, matriz e registro em
  `docs/governance/gestao_projetos/`;
- versionamento Git de missões e veredictos;
- roteamento explícito de agentes Cursor;
- bloqueio documental de avanço sem evidência.

### Proibido na Fase 0

- interface no Painel ADM;
- persistência em PostgreSQL ou outro banco;
- automação que altere código, schema, deploy ou geração sem missão autorizada;
- substituição de ADR, Lei 15, Lei 001 ou política ML assistivo;
- promoção automática de tarefas a componentes institucionais.

---

## 3. Princípios obrigatórios

1. **Nenhuma missão sem escopo escrito** — toda missão declara o que pode e o que não pode
   alterar.
2. **Nenhum avanço sem evidência Git** — branch, commits, push e referência de PR quando
   existir.
3. **Nenhum encerramento sem veredicto** — status final exige veredicto formal no registro.
4. **Agente único responsável por domínio** — roteamento explícito; mistura só com
   autorização documentada.
5. **Bloqueio explícito** — impedimentos são registrados, não omitidos.
6. **Reversibilidade** — toda missão deve indicar como desfazer ou congelar o que foi feito.
7. **Fase 0 é read-mostly para runtime** — documentação governa; execução continua pelos
   fluxos já existentes.

---

## 4. Hierarquia documental

| Camada | Artefato | Função |
|--------|----------|--------|
| Lei / política | `POLITICA_GESTAO_PROJETOS_LOTOIA.md` | Regras institucionais |
| Quadro | `gestao_projetos/QUADRO_PROJETOS_MISSOES.md` | Visão ativa de projetos e missões |
| Checklist | `gestao_projetos/CHECKLIST_MISSAO_OBRIGATORIO.md` | Gate obrigatório por missão |
| Checkpoint produção | `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md` | Evidência de produção proporcional ao risco |
| Template | `gestao_projetos/TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md` | Modelo de cartão de tarefa |
| Matriz | `gestao_projetos/MATRIZ_STATUS_TAREFAS.md` | Estados, transições e bloqueios |
| Registro | `gestao_projetos/REGISTRO_MISSOES_INSTITUCIONAL.md` | Log cronológico e veredictos |

---

## 5. Definições

| Termo | Definição |
|-------|-----------|
| **Projeto** | Conjunto institucional de missões com objetivo de longo prazo |
| **Missão** | Ordem institucional delimitada, com agente, escopo e critério de encerramento |
| **Tarefa** | Unidade executável dentro de uma missão; usa o cartão institucional |
| **Agente** | Domínio Cursor (`.cursor/rules/agent_*.mdc`) responsável pelo escopo |
| **Evidência Git** | Branch, commits, diff revisável e push para remoto |
| **Evidência de teste** | Saída de `pytest` e/ou `ruff check` quando o escopo tocar código |
| **Evidência de deploy** | Build + commit + confirmação deploy/painel (evidência leve); script HTTP e screenshot **condicionais** — ver `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md` |
| **Veredicto** | Decisão formal: `APROVADO`, `APROVADO_COM_RESSALVAS`, `BLOQUEADO`, `REJEITADO`, `CONGELADO` |
| **Bloqueio** | Impedimento registrado que impede transição de status |

---

## 6. Fluxo institucional mínimo

```text
Proposta
  -> Autorização (escopo + agente)
  -> Execução (branch + commits)
  -> Evidência Git
  -> Evidência de testes (se aplicável)
  -> Evidência de deploy (se aplicável)
  -> Veredicto formal
  -> Registro atualizado
  -> Encerramento ou arquivamento
```

Nenhuma etapa pode ser pulada por conveniência operacional.

---

## 7. Roteamento de agentes

| Agente | Domínio principal |
|--------|-------------------|
| `agent_governanca` | ADRs, políticas, snapshots, aprovações institucionais |
| `agent_plataforma` | FastAPI, runtime, deploy, scripts operacionais |
| `agent_dados` | Ingestão, PostgreSQL, pipelines |
| `agent_estatistico` | Scoring, estatística estrutural |
| `agent_geracao` | Lei 15 / Lei 15A, motor de geração |
| `agent_ml` | ML assistivo, walk-forward, experimentos |
| `agent_qualidade` | Testes, ruff, CI |
| `agent_visual` | Streamlit, layout, UX |

Missões multi-agente devem declarar agente **primário** e agentes **consultivos** no cartão.

---

## 8. Relação com incidentes e deploy

Todo incidente operacional ou de deploy com impacto institucional deve:

1. abrir ou referenciar uma missão no registro;
2. registrar causa raiz, módulo afetado e artefatos não versionados identificados;
3. exigir evidência Git antes de considerar correção encerrada;
4. produzir veredicto formal antes de retomar deploy de produção quando aplicável.

Esta política responde diretamente ao gap identificado: **tarefa concluída sem prova no Git
não é tarefa concluída**.

---

## 9. Zonas protegidas (sempre)

Sem missão autorizada e ADR quando exigido, é proibido alterar via Gestão de Projetos:

- Núcleo soberano `LEI15_CORE_002` e flags `LOTOIA_LEI15_CORE_002*`;
- regras de geração Lei 15 / Lei 15A;
- schema ou dados operacionais PostgreSQL;
- Painel ADM (Fase 0 não adiciona superfície de gestão);
- `FINAL_SCORE_WEIGHTS`, `validation_threshold` e promoções ML institucionais.

---

## 10. Evolução prevista (fora da Fase 0)

Fases futuras podem incluir — somente com nova política ou ADR:

- painel de gestão no ADM;
- persistência de missões no PostgreSQL;
- automação de gates CI/CD;
- integração com observabilidade institucional.

A Fase 0 **não antecipa** essas implementações.

---

## 11. Conformidade

Uma missão está em conformidade com esta política quando:

- [ ] possui cartão institucional preenchido;
- [ ] consta no quadro e no registro;
- [ ] passou pelo checklist obrigatório;
- [ ] respeita a matriz de status;
- [ ] encerrou com veredicto formal quando aplicável.

---

## 12. Referências

- `docs/governance/GOVERNANCA_OPERACIONAL_LOTOIA.md`
- `docs/governance/LEI_001_FONTE_UNICA_DA_VERDADE.md`
- `docs/governance/POLITICA_ML_ASSISTIVO.md`
- `docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md`
- `docs/governance/gestao_projetos/README.md`
- `docs/governance/POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`
- `AGENTS.md`
- `.cursor/rules/agent_governanca.mdc`
- `.cursor/rules/agent_plataforma.mdc`

---

## Histórico

| Data | Evento |
|------|--------|
| 2026-06-17 | Formalização da Política de Gestão de Projetos — Fase 0 |
| 2026-06-17 | Referência à Política de Checkpoint de Produção simplificada |
