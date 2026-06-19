# M-GOV-AGENTS-001 — Auditoria dos Agentes Institucionais no Fluxo ML

| Campo | Valor |
|-------|-------|
| **Missão** | M-GOV-AGENTS-001 |
| **Tipo** | Auditoria read-only |
| **Agente líder** | `agent_governanca` |
| **Agentes obrigatórios** | `agent_ml`, `agent_qualidade` |
| **Data** | 2026-06-19 |
| **Veredito** | **CONCLUÍDA** — agentes institucionais auditados no fluxo ML |
| **Alteração funcional** | Nenhuma |
| **Purge** | Nenhum |

---

## 1. Resumo executivo

Os **8 agentes institucionais existem formalmente** no repositório (regras Cursor, diretriz de governança, cartões de missão e painel de governança). Porém, **o runtime ML operacional não persiste nem roteia por agente responsável**: diagnósticos, planos de calibração, `context_json`, snapshots da Central ML e memórias `ScientificInstitutionalMemory` registram missões (`M-ML-0xx`), métricas e ações técnicas — **não** `agent_*`.

**Lacuna principal:** ausência de matriz de responsabilidade **executável** no pipeline ML (somente documental/humana).

---

## 2. Agentes encontrados (8/8)

| # | Agente | Formalizado? | Onde aparece |
|---|--------|--------------|--------------|
| 1 | `agent_governanca` | Sim | `.cursor/rules/agent_governanca.mdc`, `DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md`, ADRs, `institutional_governance.py` |
| 2 | `agent_estatistico` | Sim | `.cursor/rules/agent_estatistico.mdc`, diretriz, cartões M-VIS-034/036, `ESPECIFICACAO_6_BASES_COBERTURA_ESTRUTURAL.md` |
| 3 | `agent_geracao` | Sim | `.cursor/rules/agent_geracao.mdc`, `lei15_generation_routing_policy.py`, ADR-047, cartões M-GER-* |
| 4 | `agent_dados` | Sim | `.cursor/rules/agent_dados.mdc`, `history_preservation_policy.py`, M-DADOS-* |
| 5 | `agent_ml` | Sim | `.cursor/rules/agent_ml.mdc`, missões M-ML-*, `src/lotoia/ml/` |
| 6 | `agent_qualidade` | Sim | `.cursor/rules/agent_qualidade.mdc`, CI, testes `tests/` |
| 7 | `agent_plataforma` | Sim | `.cursor/rules/agent_plataforma.mdc`, `backend/`, M-PLAT-* |
| 8 | `agent_visual` | Sim | `.cursor/rules/agent_visual.mdc`, `dashboard/`, M-VIS-* |

**Agentes ausentes:** nenhum dos 8 oficiais. **`agent_core` não existe** (busca retornou zero ocorrências — conforme esperado).

---

## 3. Matriz de responsabilidade atual

### 3.1 Documental (existe)

| Fonte | Tipo | Conteúdo |
|-------|------|----------|
| `docs/governance/DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md` | Tabela domínio × agente | Escopos institucionais |
| `.cursor/rules/agent_*.mdc` (8 arquivos) | Escopo Cursor | `allowed` / `read_only` / `forbidden` por path |
| `dashboard/institutional_governance.py` | `MISSION_ROWS` | Missão → string `"agent_ml + agent_visual + …"` |
| `docs/governance/gestao_projetos/` | Cartões de missão | Campo `Agentes` por missão |
| `CLAUDE.md` | Tabela resumo | Domínios dos 8 agentes |

### 3.2 Executável no fluxo ML (não existe)

Busca por `responsible_agent`, `agent_responsavel`, `action_owner`, `matriz_responsabilidade` em `src/lotoia/ml/`, `dashboard/institutional_ml_calibration_cockpit.py`, `coverage_evidence_interpreter.py` → **zero campos estruturados**.

---

## 4. Respostas às 12 perguntas de auditoria

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | Os 8 agentes existem na memória institucional? | **Parcial.** Existem em diretriz, regras Cursor e painel governança. **Não** em `ScientificInstitutionalMemory` nem em memórias ML (`structural_policy_15d`, `ml_operational_hierarchy`, `structural_calibration_memory`). |
| 2 | A Central ML conhece esses agentes? | **Não.** `institutional_ml_calibration_cockpit.py` e `institutional_supervised_ml.py` não referenciam `agent_*`. |
| 3 | Diagnósticos ML indicam qual agente deve agir? | **Não.** `coverage_evidence_interpreter._build_decision_block` emite `problema_detectado`, `acao_recomendada`, `severidade` — sem `responsible_agent`. |
| 4 | Plano de calibração diferencia domínio (geração/ML/estatística/…)? | **Não estruturalmente.** `build_calibration_plan` gera `plan_items` textuais (overlap, diversidade, subcobertura) sem owner por agente. |
| 5 | Problema pool/matéria-prima → `agent_geracao`? | **Não roteado.** Ações como `expandir_pool_estrutural_15d` (M-ML-073) não mapeiam para agente. |
| 6 | Diversidade/cobertura → `agent_estatistico`? | **Não roteado.** Métricas vêm de `analyze_pool_structural_issues` / Cobertura, mas sem handoff de agente. |
| 7 | Memória/veredito/calibração → `agent_ml`? | **Implícito** (código em `src/lotoia/ml/`), mas **sem campo** `agent_ml` em trace/snapshot. |
| 8 | Tela/render → `agent_visual` / `agent_plataforma`? | **Não no diagnóstico ML.** Render guards (M-ML-VIS-071) não etiquetam agente responsável. |
| 9 | Regra institucional/ADR/Lei 15 → `agent_governanca`? | **Documental** (ADRs, cartões). **Não** no veredito ML automático. |
| 10 | Existe matriz de responsabilidade? | **Sim (documental)** / **Não (runtime ML)**. |
| 11 | Evidência de agente em `context_json`/snapshot/Central ML? | **Não.** Campos persistidos: `mission_id`, `ml_hierarchy_version`, `stage_results`, `calibration_plan`, etc. |
| 12 | Risco de missões/plano sem agente? | **Alto.** Planos e hierarquia podem bloquear GP sem indicar qual agente humano/Cursor deve atuar. |

---

## 5. Evidência por agente no fluxo ML

### `agent_governanca`
- ADR-047, ADR-046: tabelas de encaminhamento por agente
- `lei15_core_candidate_decision.py`: único módulo ML com `next_agent`, `validation_agent` (promoção CAND-002 — **fora** do cockpit)
- `institutional_governance.py`: missões ML listadas com string de agentes

### `agent_ml`
- Domínio principal: `src/lotoia/ml/*`, `observability/coverage_evidence_interpreter.py`
- Memórias: `structural_policy_15d`, `ml_operational_hierarchy`, `structural_calibration_memory` — **sem campo agente**
- M-ML-073: `corrective_action_applied` (técnico), não `responsible_agent`

### `agent_estatistico`
- `analyze_pool_structural_issues`, `structural_concentration_audit`, `overlap_format_thresholds`
- Especificação 6 bases em `docs/governance/gestao_projetos/rodada_multiagente/`
- **Sem** roteamento em `decision_blocks`

### `agent_geracao`
- `basic_generator.py`, `lei15_core_002`, `structural_pool_15d_generator.py` (pool matéria-prima)
- M-ML-073 bloqueia GP antes de `compose_sovereign_gp` — ação `gerar_pool_estrutural_15d` sem owner

### `agent_dados`
- `ScientificInstitutionalMemory` (persistência)
- Políticas purge em `history_preservation_policy.py`
- **Não** referenciado em planos de calibração ML

### `agent_qualidade`
- `tests/ml/test_m_ml_*`, CI governance-gate
- Cartões de missão associam validação — **não** no veredito Central ML

### `agent_plataforma`
- `backend/`, runtime Railway, pool PostgreSQL
- Cartões M-PLAT-* — **não** em diagnósticos ML

### `agent_visual`
- `dashboard/institutional_ml_calibration_cockpit.py`, `institutional_app.py`
- Exibe hierarquia, pool, política 15D — **não** exibe agente responsável

---

## 6. Artefatos ML auditados (read-only)

| Artefato | Registra agente? | Observação |
|----------|------------------|------------|
| `ScientificInstitutionalMemory` | Não | `memory_kind` técnico (`structural_policy_15d`, `ml_operational_hierarchy`) |
| `ml_operational_hierarchy` | Não | `stage_results`, `corrective_action_applied` |
| `structural_policy_15d` | Não | Política M-ML-070-v1 |
| `pre_final_pool_ml_calibration` | Não | Métricas antes/depois, `actions_applied` |
| `structural_pool_15d` (M-ML-072) | Não | `pool_origin=ML_STRUCTURAL_15D_POOL` |
| `coverage_evidence_interpreter` | Não | `decision_blocks`, `calibration_plan`, `acoes_recomendadas` |
| `build_calibration_plan` | Não | Itens textuais apenas |
| `institutional_ml_calibration_cockpit` | Não | Cards por missão, não por agente |
| `context_json` (geração) | Não | Trace ML completo sem `responsible_agent` |
| `institutional_supervised_ml` snapshot | Não | Propaga `coverage_evidence` sem agente |

---

## 7. Lacunas identificadas

1. **Gap semântico:** governança humana conhece 8 agentes; runtime ML conhece missões (`M-ML-0xx`) e ações técnicas.
2. **Sem roteamento pool → `agent_geracao`** quando bloqueio hierárquico é conformidade/pool.
3. **Sem roteamento diversidade/cobertura → `agent_estatistico`** apesar das métricas serem estatísticas estruturais.
4. **Central ML não exibe agente responsável** por bloqueio ou recomendação.
5. **`decision_blocks` incompletos:** falta `responsible_agent`, `agent_scope`, `handoff_target`.
6. **`calibration_plan` monolítico:** não separa owners (ML vs geração vs visual).
7. **Único handoff estruturado** (`lei15_core_candidate_decision.py`) é fluxo de promoção CAND-002, não cockpit operacional.
8. **Risco operacional:** operador vê "bloqueio hierárquico" sem saber se aciona `agent_geracao`, `agent_ml` ou `agent_estatistico`.

---

## 8. Recomendação para M-GOV-AGENTS-002 (implementação)

**Objetivo:** matriz executável agente × problema × missão no fluxo ML.

### 8.1 Memória institucional
- Novo registro ou extensão de `ml_operational_hierarchy` / diretriz persistida:
  - `memory_kind`: `institutional_agent_routing_matrix`
  - versão: `M-GOV-AGENTS-002-v1`
  - mapa: `issue_type` → `primary_agent` + `support_agents[]`

### 8.2 Runtime ML (subordinado a M-ML-073)
- Enriquecer `_build_decision_block` e `build_calibration_plan` com:
  - `responsible_agent`
  - `support_agents`
  - `routing_reason`
- Mapeamento sugerido (rascunho para ADR):

| Problema | Agente primário | Apoio |
|----------|-----------------|-------|
| Pool/matéria-prima/conformidade L1 | `agent_geracao` | `agent_ml` |
| Diversidade/overlap/cobertura | `agent_estatistico` | `agent_ml` |
| Calibração/veredito/memória ML | `agent_ml` | `agent_qualidade` |
| Render/cockpit | `agent_visual` | `agent_plataforma` |
| Persistência/trace PostgreSQL | `agent_dados` | `agent_plataforma` |
| ADR/Lei 15/promoção | `agent_governanca` | — |
| Testes/regressão | `agent_qualidade` | `agent_ml` |

### 8.3 Central ML + Cobertura
- Card "Agente responsável" por `decision_block` e por etapa hierárquica bloqueada.
- Persistir em `context_json`: `responsible_agent`, `agent_routing_matrix_version`.

### 8.4 Governança
- ADR M-GOV-AGENTS-002 antes de alterar payloads persistidos.
- Testes em `tests/governance/test_m_gov_agents_002_routing.py`.

---

## 9. Comandos de auditoria executados

```bash
# Busca pelos 8 agentes
rg 'agent_governanca|agent_estatistico|agent_geracao|agent_dados|agent_ml|agent_qualidade|agent_plataforma|agent_visual' /workspace

# Busca por roteamento/ownership
rg 'responsible_agent|agent_responsavel|ownership|matriz_responsabilidade|action_owner' /workspace

# Busca agent_core (deve ser zero)
rg 'agent_core' /workspace

# Busca agentes no domínio ML runtime
rg 'agent_' /workspace/src/lotoia/ml/
rg 'agent_' /workspace/dashboard/institutional_ml_calibration_cockpit.py
rg 'agent_' /workspace/src/lotoia/observability/

# Regras Cursor
ls /workspace/.cursor/rules/agent_*.mdc
```

---

## 10. Confirmações obrigatórias

| Item | Status |
|------|--------|
| Alteração funcional | **Nenhuma** — auditoria read-only |
| Purge | **Nenhum** |
| Lei 15 / Lei 15A | **Intactas** — não auditadas com alteração |
| CORE_002 / `public_app` | **Intactos** |
| Código de geração/Central ML | **Não alterado** nesta missão |

---

## 11. Veredito

**M-GOV-AGENTS-001 CONCLUÍDA — AGENTES INSTITUCIONAIS DA LOTOIA AUDITADOS NO FLUXO ML**

Os 8 agentes estão **formalizados na governança documental e nas regras Cursor**, mas **não estão integrados ao pipeline decisório ML** (diagnóstico, calibração, hierarquia, snapshot, `context_json`). Próxima missão recomendada: **M-GOV-AGENTS-002** — matriz executável e persistência de `responsible_agent`.
