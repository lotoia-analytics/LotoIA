# Modelo — Cartão de Tarefa Institucional

Copiar o bloco abaixo ao abrir missão. Preencher todos os campos. Anexar ao chat Cursor ou
referenciar em `QUADRO_MISSOES.md`.

---

```yaml
# =============================================================================
# CARTÃO DE TAREFA INSTITUCIONAL — LotoIA
# =============================================================================

mission_id: EXEMPLO_MISSAO_001
titulo: "Título curto verificável"
owner: agent_governanca          # um único agente responsável
support:
  - agent_plataforma
  - agent_qualidade
priority: low | medium | high | critical
status: PLANEJADA                # ver MATRIZ_STATUS_TAREFAS.md
operational_effect: false        # true somente se mutar runtime/dados operacionais

# -----------------------------------------------------------------------------
# Contexto
# -----------------------------------------------------------------------------
contexto: |
  Por que esta missão existe. Incidente, ADR, auditoria ou demanda operacional.

# -----------------------------------------------------------------------------
# Objetivo (uma frase verificável)
# -----------------------------------------------------------------------------
objetivo: |
  O que deve ser verdadeiro ao encerrar.

# -----------------------------------------------------------------------------
# Escopo
# -----------------------------------------------------------------------------
autorizado:
  - item permitido 1
  - item permitido 2

proibido:
  - alterar Lei 15 / Lei 15A / Núcleo LEI15_CORE_002
  - gerar jogos ou rodar piloto operacional
  - purge / reset de histórico
  - alterar schema ou banco (salvo missão agent_dados dedicada)
  - alterar Painel ADM (salvo missão agent_visual dedicada)
  - refatoração ampla não solicitada

# -----------------------------------------------------------------------------
# Dependências
# -----------------------------------------------------------------------------
depende_de:
  - mission_id_anterior | ADR-XXX | nenhuma

bloqueia:
  - mission_id_posterior | nenhuma

# -----------------------------------------------------------------------------
# Entregáveis
# -----------------------------------------------------------------------------
entregaveis:
  - artefato 1 (path esperado)
  - evidência Git (commit hash)
  - veredicto formal

# -----------------------------------------------------------------------------
# Testes mínimos
# -----------------------------------------------------------------------------
testes:
  - comando: "python -m pytest tests/..."
    criterio: "todos passam ou falha documentada"
  - comando: "ruff check ..."
    criterio: "sem erros novos"

# -----------------------------------------------------------------------------
# Deploy (se aplicável)
# -----------------------------------------------------------------------------
deploy:
  ambiente: Railway production | N/A
  checkpoint:
    - commit em main
    - healthcheck OK
    - CI gate (se existir)

# -----------------------------------------------------------------------------
# Veredictos aceitos (escolher um ao encerrar)
# -----------------------------------------------------------------------------
veredictos_possiveis:
  - MISSÃO CONCLUÍDA
  - MISSÃO BLOQUEADA
  - DEPLOY EM ANDAMENTO
  - DEPLOY AINDA QUEBRADO
  - RISCO DE PRODUÇÃO
  - EVIDÊNCIA GIT AUSENTE

# -----------------------------------------------------------------------------
# Evidência Git (preencher ao encerrar)
# -----------------------------------------------------------------------------
git:
  branch:
  commits: []
  pr:
  push_confirmado: false

# -----------------------------------------------------------------------------
# Notas
# -----------------------------------------------------------------------------
notas: |
  Observações, riscos, handoff para próxima missão.
```

---

## Exemplo mínimo (missão documental)

```yaml
mission_id: GESTAO_PROJETOS_FASE_0
titulo: "Implantar Gestão de Projetos Fase 0"
owner: agent_governanca
support: [agent_plataforma]
priority: high
status: CONCLUÍDA
operational_effect: false
objetivo: "Base documental versionada em docs/governance/gestao_projetos/"
autorizado: [criar política, quadro, checklist, modelo, matriz, registro]
proibido: [painel, banco, geração, núcleo]
veredicto_final: GESTAO_PROJETOS_FASE_0_IMPLANTADA
```
