# Registro de Missões — LotoIA

Histórico auditável. **Append-only** — não editar entradas passadas; corrigir via nova entrada.

Formato compacto. Detalhes completos nos commits, ADRs e relatórios referenciados.

---

## Índice por data

| Data | mission_id | Veredicto |
|------|------------|-----------|
| 2026-06-17 | `GESTAO_PROJETOS_FASE_0` | `GESTAO_PROJETOS_FASE_0_IMPLANTADA` |
| 2026-06-17 | `HOTFIX_INSTITUTIONAL_LIGHT_MODE` | `PAINEL RESTAURADO` |
| 2026-06-17 | `LEI15_CORE_002_CONSTITUTIONAL_TRANSITION` | `GIT SINCRONIZADO` |
| 2026-06-17 | `LEI15_CORE_002_SOVEREIGN` | Núcleo implantado |
| 2026-06-17 | `CONSTITUTIONAL_AUDIT` | `LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL` |
| 2026-06-17 | `ADR_047_TRANSITION` | `TRANSIÇÃO CONSTITUCIONAL REGISTRADA` |
| 2026-06-17 | `HISTORY_PRESERVATION` | Purge bloqueado |
| 2026-06-17 | `CORE_002_GENERATION_ROUTING` | Path único garantido |
| 2026-06-16 | `RESET_GENERATION_EPOCH_001` | EPOCH_001 |
| 2026-06-16 | `RESULTADOS_STRUCT_TEST_15D_20D_001` | Relatório entregue |
| 2026-06-16 | `STRUCT_TEST_15D` | Teste estrutural (painel/manual) |
| 2026-06-16 | `FIX_JSON_GENERATION_EVENTS` | JSON safe |
| 2026-06-16 | `FIX_STRUCTURAL_COVERAGE_PREFIX_SUFFIX` | Cobertura 4D |

---

## Entradas detalhadas

### 2026-06-17 — GESTAO_PROJETOS_FASE_0

```yaml
mission_id: GESTAO_PROJETOS_FASE_0
owner: agent_governanca
support: [agent_plataforma]
operational_effect: false
objetivo: Implantar camada documental de Gestão de Projetos Fase 0
artefatos:
  - docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md
  - docs/governance/gestao_projetos/*
commit: 7b3d632
branch: main
causa_gatilho: Incidente deploy — institutional_light_mode.py não versionado
veredicto: GESTAO_PROJETOS_FASE_0_IMPLANTADA
notas: Sem painel, banco, geração ou Núcleo alterados
```

---

### 2026-06-17 — HOTFIX_INSTITUTIONAL_LIGHT_MODE

```yaml
mission_id: HOTFIX_INSTITUTIONAL_LIGHT_MODE
owner: agent_visual
support: [agent_plataforma]
operational_effect: true
problema: ModuleNotFoundError dashboard.institutional_light_mode
causa_raiz: Arquivo existia localmente; fora do commit 06d3932
correcao: Adicionar dashboard/institutional_light_mode.py ao Git
commit: f0c1261e927d2a33c50f7b9b04bc925aa43213d0
branch: main
testes: import dashboard.institutional_light_mode OK
deploy: push main; CI gate em andamento no encerramento
veredicto: PAINEL RESTAURADO
licao: Reforça POLITICA_GESTAO_PROJETOS — arquivo referenciado deve estar versionado
```

---

### 2026-06-17 — LEI15_CORE_002_CONSTITUTIONAL_TRANSITION (consolidação Git)

```yaml
mission_id: LEI15_CORE_002_CONSTITUTIONAL_TRANSITION
owner: agent_governanca
operational_effect: true
branch: feat/lei15-core-002-constitutional-transition → main
commits:
  - 95b83fd  # ADR-046 artifacts
  - fea8e2e  # CORE_002 sovereign
  - 3aa196c  # ADR-047
  - d747bf2  # history preservation
  - f6a770a  # generation routing
  - df0ca4f  # JSON reports
  - 06d3932  # tests
head_pos_merge: 06d3932
testes: 71 passed, 1 error ambiental Windows
deploy: 06d3932 quebrou painel (light_mode); corrigido por f0c1261
veredicto: GIT SINCRONIZADO
```

---

### 2026-06-17 — LEI15_CORE_002_SOVEREIGN

```yaml
mission_id: LEI15_CORE_002_SOVEREIGN
owner: agent_geracao
operational_effect: false
artefatos:
  - src/lotoia/governance/lei15_core_002_sovereign.py
  - src/lotoia/generation/lei15_core_002.py
label: STRUCT_LEI15_CORE_CANDIDATE_002_15D_001
flags:
  LOTOIA_LEI15_CORE_002: sovereign
  LOTOIA_LEI15_CORE_002_GENERATION_ENABLED: 0
veredicto: Núcleo implantado; geração BLOQUEADA
```

---

### 2026-06-17 — CONSTITUTIONAL_AUDIT

```yaml
mission_id: CONSTITUTIONAL_AUDIT
owner: agent_governanca
operational_effect: false
relatorio: docs/governance/AUDITORIA_CONSTITUCIONAL_LOTOIA_2026_06_17.md
veredicto: LOTOIA CONFLITANTE — EXIGE CORREÇÃO ANTES DO PAINEL
```

---

### 2026-06-17 — ADR_047_TRANSITION

```yaml
mission_id: ADR_047_TRANSITION
owner: agent_governanca
operational_effect: false
adr: docs/adr/ADR-047-TRANSICAO-CONSTITUCIONAL-LEI15-CORE002.md
veredicto: TRANSIÇÃO CONSTITUCIONAL REGISTRADA
```

---

### 2026-06-17 — HISTORY_PRESERVATION

```yaml
mission_id: HISTORY_PRESERVATION
owner: agent_dados
operational_effect: true
artefato: src/lotoia/governance/history_preservation_policy.py
commit: d747bf2
veredicto: HISTÓRICO INSTITUCIONAL PROTEGIDO — PURGE BLOQUEADO
```

---

### 2026-06-17 — CORE_002_GENERATION_ROUTING

```yaml
mission_id: CORE_002_GENERATION_ROUTING
owner: agent_geracao
operational_effect: true
artefato: src/lotoia/governance/lei15_generation_routing_policy.py
commit: f6a770a
veredicto: PATH ÚNICO CORE_002 GARANTIDO — LEGACY DEFAULT BLOQUEADO
```

---

### 2026-06-16 — RESET_GENERATION_EPOCH_001

```yaml
mission_id: RESET_GENERATION_EPOCH_001
owner: agent_dados
operational_effect: true
escopo: generation_events, generated_games, reconciliation_runs
preservado: lotofacil_official_history (3711 concursos)
backup: data/backups/pre_epoch_001_20260616_0634.json
veredicto: EPOCH_001 iniciado
```

---

### 2026-06-16 — RESULTADOS_STRUCT_TEST_15D_20D_001

```yaml
mission_id: RESULTADOS_STRUCT_TEST_15D_20D_001
owner: agent_estatistico
operational_effect: false
labels:
  - STRUCT_TEST_15D_001 … STRUCT_TEST_20D_001
fonte: Railway PostgreSQL
veredicto: Relatório entregue (leitura only)
```

---

### 2026-06-16 — FIX_JSON_GENERATION_EVENTS

```yaml
mission_id: FIX_JSON_GENERATION_EVENTS
owner: agent_visual
problema: datetime not JSON serializable
local: dashboard/institutional_app.py (_persist_generation_snapshot)
correcao: helper _json_safe()
commit: 001b807
veredicto: MISSÃO CONCLUÍDA
```

---

### 2026-06-16 — FIX_STRUCTURAL_COVERAGE_PREFIX_SUFFIX

```yaml
mission_id: FIX_STRUCTURAL_COVERAGE_PREFIX_SUFFIX_RENDER
owner: agent_visual
objetivo: Tabelas prefixo_4 e sufixo_4 na Cobertura Estrutural
commit: 545693f
build_marker: institutional-adm-runtime-v5
veredicto: MISSÃO CONCLUÍDA
```

---

## Incidentes registrados (lições)

| ID | Data | Descrição | Controle Fase 0 |
|----|------|-----------|-----------------|
| INC-001 | 2026-06-17 | Deploy 06d3932 quebrou ADM por módulo não versionado | Checklist C2; Política § arquivo referenciado |
| INC-002 | 2026-06-16 | Secrets Railway não visíveis no shell local | Veredicto MISSÃO BLOQUEADA até DATABASE_URL |
| INC-003 | 2026-06-17 | 7 commits constitucionais só locais pré-consolidação | Veredicto RISCO DE GOVERNANÇA GIT |

---

## Próxima entrada esperada

Ao concluir `PAINEL_ADM_CORE_002_ALIGN`, append entrada com commit, testes, deploy e veredicto.
