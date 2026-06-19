# M-ML-074-DIAG-00 — Investigação Causal: Por Que o GP 15D Não Fecha com ML Habilitada

| Campo | Valor |
|-------|-------|
| **Missão** | M-ML-074-DIAG-00 |
| **Tipo** | Investigação causal read-only |
| **Agente líder** | `agent_ml` |
| **Data** | 2026-06-19 |
| **Veredito** | **CONCLUÍDA** — causa real do não fechamento do GP 15D identificada com evidência |
| **Alteração funcional** | Nenhuma |
| **Purge** | Nenhum |
| **Classificação** | **B** — Sistema parcialmente correto; falta mecanismo operacional |

---

## 1. Pergunta central

O usuário pede **GP:20 em 15D** com ML habilitada. Por que o sistema não entrega 20 jogos finais em alguns cenários?

**Resposta resumida:** A hierarquia operacional **M-ML-073** bloqueia intencionalmente o fechamento do GP (`gp_closure_allowed=False`) quando as etapas de conformidade, diversidade ou cobertura falham no **top slice** (`requested_count × 3`, ou seja 60 para GP:20), **após até 5 tentativas de remediação por etapa**. Nesse caminho, `compose_sovereign_gp` **nunca é executado** e o dashboard recebe **0 jogos** com estado `hierarchy_blocked`. A remediação existente (expansão pool 15D + rerank) **não garante** cruzar os hard gates — evidência quantitativa em M-STAT-001 (Δ diversidade +0.0129, insuficiente para 0.55).

---

## 2. Fluxo real executado (clique → entrega ou bloqueio)

| # | Componente | Ação |
|---|------------|------|
| 1 | `institutional_app._render_clean_law15_generation_page` | Clique "Gerar lote" → pop `_clean_law15_generate_clicked` |
| 2 | `institutional_app._run_clean_law15_generation` | Resolve `batch_label`, `seed`, chama `_invoke_sovereign_adm_generate_best_games` |
| 3 | `institutional_app._invoke_sovereign_adm_generate_best_games` | Chama `generate_best_games(ml_enabled=True)`; captura `MlOperationalHierarchyBlockedError` |
| 4 | `generate_best_games` | `build_sovereign_pool` → rerank → (se ML) hierarquia ou calibração pré-final |
| 5 | `execute_ml_operational_hierarchy` | Pool 15D expandido → conformidade → diversidade → cobertura → `gp_closure_allowed` |
| 6 | `basic_generator` (gate) | Se `gp_closure_allowed=False` → `MlOperationalHierarchyBlockedError` **antes** de `compose_sovereign_gp` |
| 7 | `compose_sovereign_gp` | Só executa se hierarquia liberou; monta N jogos finais + anti-clone |
| 8 | `apply_structural_policy_15d_to_sovereign_batch` | Pós-GP: valida/ajusta lote 15D |
| 9 | `institutional_app` persistência | Persiste lote se jogos válidos; bloqueio hierárquico não persiste GP |

**Evidência de encadeamento:** `dashboard/institutional_app.py` L13150–13172, L773–816; `src/lotoia/generator/basic_generator.py` L566–742, L769–800.

---

## 3. Respostas às 12 perguntas

### 1. Qual é o fluxo real executado hoje?

Ver seção 2. Com ML e hierarquia habilitada (`LOTOIA_ML_OPERATIONAL_HIERARCHY_ENABLED` default ativo para formatos suportados), o caminho soberano passa por `execute_ml_operational_hierarchy` **antes** do segundo `compose_sovereign_gp` final.

### 2. Em qual ponto exato o GP deixa de ser entregue?

**Ponto primário (cenário observado):**

```741:742:src/lotoia/generator/basic_generator.py
            if not _hierarchy_bundle.get("gp_closure_allowed"):
                raise MlOperationalHierarchyBlockedError.from_bundle(_hierarchy_bundle)
```

Efeito: **0 jogos** retornados ao dashboard (`games: []`, `hierarchy_blocked: True`).

**Ponto secundário (pós-hierarquia, menos frequente):**

```773:777:src/lotoia/generator/basic_generator.py
        if len(best_games) < count:
            raise RuntimeError(
                f"[LEI15_CORE_002] compose_sovereign_gp retornou {len(best_games)}/{count} "
                "após anti-clone — lote inválido."
            )
```

### 3. Comportamento intencional ou efeito colateral?

**Intencional.** M-ML-073 implementa fail-closed: qualidade estrutural pré-GP tem prioridade sobre entrega incondicional de N jogos. O bundle expõe `gp_closure_blocked` e estágio `fechamento_gp` com `status: blocked`.

### 4. Qual módulo decide bloquear?

| Camada | Módulo | Papel |
|--------|--------|-------|
| Avaliação | `ml_operational_hierarchy.py` | `_evaluate_*_stage` → `gp_closure_allowed` |
| Enforcement | `basic_generator.py` | Levanta `MlOperationalHierarchyBlockedError` |
| UI | `institutional_app.py` | Converte exceção em `hierarchy_blocked` sem crash |

### 5. Qual condição exata aciona o bloqueio?

`gp_closure_allowed = pre_gp_stages_passed` onde `pre_gp_stages_passed` exige aprovação nas três etapas:

```631:634:src/lotoia/ml/ml_operational_hierarchy.py
    pre_gp_stages_passed = all(
        stage_results.get(stage_id, {}).get("passed") for stage_id in (STAGE_CONFORMITY, STAGE_DIVERSITY, STAGE_COVERAGE)
    )
    gp_closure_allowed = pre_gp_stages_passed
```

**Etapa 2 — Diversidade** (causa mais frequente em GP:20):

```328:331:src/lotoia/ml/ml_operational_hierarchy.py
    if diversity_score < DIVERSITY_LOW_THRESHOLD:
        failures.append(
            f"diversity_score={diversity_score:.4f} abaixo de {DIVERSITY_LOW_THRESHOLD}"
        )
```

`DIVERSITY_LOW_THRESHOLD = 0.55` em `overlap_format_thresholds.py` L19.

Avaliação no top slice:

```213:214:src/lotoia/ml/ml_operational_hierarchy.py
    limit = max(int(requested_count) * 3, int(requested_count), 20)
    return ranked[: min(limit, len(ranked))]
```

Para GP:20 → top **60** jogos por `profile_score`.

**Etapa 3 — Cobertura:** qualquer issue de cobertura no slice reprova (`passed = not failures`).

**Etapa 1 — Conformidade:** `compliance_rate < MIN_POOL_COMPLIANCE_RATE` ou pool conforme < `MIN_COMPLIANT_POOL_SIZE`.

### 6. Existe tentativa interna de recuperação?

**Sim.** Até **5 tentativas por etapa** (diversidade e cobertura):

```46:46:src/lotoia/ml/ml_operational_hierarchy.py
MAX_REMEDIATION_ATTEMPTS = 5
```

```608:626:src/lotoia/ml/ml_operational_hierarchy.py
        while not result["passed"] and attempts < MAX_REMEDIATION_ATTEMPTS:
            attempts += 1
            pool, pre_final_bundle = _apply_pool_remediation(
                ...
            )
            result = evaluator(pool)
            result["remediation_attempts"] = attempts
```

Remediação: `_filter_near_clone_games` + `build_ml_structural_15d_pool` + `apply_pre_final_pool_ml_calibration` com boosts por estágio.

**Limitação comprovada (M-STAT-001):** após 5 ciclos, `diversity_score` permanece abaixo de 0.55 em cenário GP:20 sintético/real.

### 7. A ML gera, modifica, reordena ou apenas avalia?

| Função | Gera | Modifica | Reordena | Avalia |
|--------|------|----------|----------|--------|
| `structural_pool_15d_generator` | **Sim** — candidatos conformes novos | Sim — metadados/score | Sim — seleção diversa | Sim — compliance |
| `pre_final_pool_ml_calibration` | Não | **Sim** — penalidades/boosts em `profile_score` | **Sim** — sort pós-calibração | Sim — métricas before/after |
| `supervised_output_calibration` | Não | Sim | Sim | Sim |
| `ml_operational_hierarchy` | Indireto (pool 15D) | Sim — remove clones | Indireto (via pré-final) | **Sim — hard gates** |
| `coverage_evidence_interpreter` | Não | Não | Não | Sim — read-only diagnóstico |
| `institutional_agent_routing_matrix` | Não | Não (metadata) | Não | Não |

### 8. Métricas são hard gates ou metas de qualidade?

**Hard gates** nas etapas 1–3 da hierarquia. Definição:

- `DIVERSITY_LOW_THRESHOLD = 0.55` — `overlap_format_thresholds.py`
- Overlap `LEVEL_RUIM` / `LEVEL_CRITICO` — `_evaluate_diversity_stage` L333–335
- `near_dup_ratio >= DEFAULT_NEAR_DUP_PAIR_RATIO` — L341–345
- Cobertura: qualquer issue no slice — `_evaluate_coverage_stage` L389–398

Não são metas soft: `passed = not failures` bloqueia `gp_closure_allowed`.

### 9. Sistema desenhado para sempre entregar N ou bloquear quando hierarquia reprova?

**Bloquear quando reprova** (com ML + hierarquia habilitada). Prova:

- `gp_closure_allowed` derivado de `all(passed)` — L631–634
- Exceção antes de compose — `basic_generator.py` L741–742
- Dashboard retorna 0 jogos — `institutional_app.py` L810–815

Sem hierarquia (`is_ml_operational_hierarchy_enabled()` False), o caminho legado aplica pool 15D + pré-final **sem** gate pré-GP e tenta compose — comportamento distinto.

### 10. Agentes institucionais interferem na decisão?

**Não.** `enrich_hierarchy_bundle` apenas anexa `responsible_agent`, `blocking_responsible_agent` e matriz de roteamento — **não altera** `gp_closure_allowed`:

```306:333:src/lotoia/governance/institutional_agent_routing_matrix.py
def enrich_hierarchy_bundle(bundle: Mapping[str, Any] | None) -> dict[str, Any]:
    source = dict(bundle or {})
    ...
    source["blocking_responsible_agent"] = blocking_agent
    ...
    return source
```

`gp_closure_allowed` é definido **antes** do enrich em `execute_ml_operational_hierarchy` L670.

### 11. Onde está o problema?

| Hipótese | Avaliação |
|----------|-----------|
| Conceito institucional | Parcial — fail-closed é intencional; expectativa de "sempre entregar N" não está formalizada no runtime |
| Threshold | Não é bug — 0.55 é gate explícito |
| Ausência de retry | **Parcial** — há 5 retries/etapa, mas **sem substituição determinística** no top slice |
| Falta de diversidade no pool | **Sim** — material novo correlacionado (M-STAT-001) |
| Fechamento GP | Não alcançado quando bloqueado pré-compose |
| Interpretação da métrica | Correta — slice = top 60 por `profile_score` |
| Conflito entre módulos | **Parcial** — remediação (M-ML-071/072) não fecha gap para gate M-ML-073 |

**Causa raiz:** remediação operacional insuficiente entre política/gate e expectativa de entrega incondicional.

### 12. Correção mínima para alinhar expectativa vs comportamento

**M-ML-074** — Recuperação determinística pré-GP: substituição ativa no top slice (famílias dominantes / quase-clones) **antes** do bloqueio final, mantendo hard gates mas aumentando chance de aprovação sem mascarar falhas.

Alternativa de governança (sem código): formalizar na UX que GP:N 15D com ML é **entrega condicionada** à hierarquia — não corrige o gap operacional.

---

## 4. Tabela obrigatória de componentes

| Componente | O que deveria fazer | O que faz hoje | Evidência | Está correto? | Por quê |
|------------|---------------------|----------------|-----------|---------------|---------|
| `generate_best_games` | Entregar dict com N jogos finais CORE_002 | Entrega N jogos **ou** levanta exceção pré/pós compose | `basic_generator.py` L741–777 | Parcial | Contrato condicionado à hierarquia ML |
| `structural_pool_15d_generator` | Expandir pool com ≥100 conformes diversos | Gera conformes; diversidade no top slice pode permanecer baixa | M-STAT-001 Δ +0.0129 | Parcial | Expansão ≠ diversidade no slice avaliado |
| `pre_final_pool_ml_calibration` | Melhorar pool pré-GP para fechamento | Reordena/penaliza; raramente substitui famílias dominantes | `pre_final_pool_ml_calibration.py` | Parcial | Calibração assistiva, não swap determinístico |
| `ml_operational_hierarchy` | Garantir qualidade antes do GP | Bloqueia se etapas 1–3 falham após 5 tentativas/etapa | `ml_operational_hierarchy.py` L608–634, L741–742 | **Sim** | Fail-closed intencional M-ML-073 |
| `structural_policy_15d` | Validar/ajustar lote 15D pós-compose | Aplica após GP montado; não é gate pré-GP | `basic_generator.py` L794–800 | **Sim** | Política pós-fechamento M-ML-070 |
| `coverage_evidence_interpreter` | Diagnosticar para Central ML | Read-only; não interfere na geração | `coverage_evidence_interpreter.py` | **Sim** | Camada observacional |
| `agent_routing_matrix` | Roteamento institucional auditável | Enriquece `responsible_agent`; zero efeito decisório | `institutional_agent_routing_matrix.py` L306–333 | **Sim** | M-GOV-AGENTS-002 metadata-only |
| `compose_sovereign_gp` | Fechar exatamente N jogos do pool | `compose_diverse_gp` + anti-clone; pode retornar <N | `lei15_core_002.py` L182–200 | Parcial | Anti-clone pós-hierarquia é gate separado |
| Central ML | Exibir diagnóstico e plano | Read-only cockpit; aviso pré-GP se `hierarchy_blocked` | `institutional_ml_hierarchy_block.py` | **Sim** | Não decide bloqueio |
| Cobertura Estrutural | Métricas históricas para decisão ML | Fonte de evidência; não bloqueia geração em tempo real | `institutional_operational_structural_coverage.py` | **Sim** | Painel analítico separado do gate |

---

## 5. Classificação final

### **B) Sistema parcialmente correto; falta mecanismo operacional**

- A hierarquia M-ML-073 **funciona conforme especificado** (fail-closed).
- A remediação M-ML-071/072 **existe** mas **não fecha o gap** entre pool correlacionado e hard gate 0.55.
- A expectativa do usuário ("tratar falhas internamente antes da entrega") **não está implementada** como recuperação determinística pré-bloqueio.

Não é **A** (expectativa precisa mudar sozinha) porque há gap operacional real.  
Não é **C** (ML não deveria bloquear) — bloqueio é regra soberana.  
Não é **D** puro — módulos não entram em conflito de regra; há **deficit de eficácia** da remediação.

---

## 6. Próxima missão recomendada

**M-ML-074** — Recuperação determinística pré-GP: substituição ativa no top slice antes do bloqueio final da hierarquia (`agent_ml` + `agent_estatistico` + `agent_geracao`).

---

## 7. Comandos utilizados

```bash
# Relatório causal (read-only)
python3 scripts/audits/m_ml_074_diag_00_gp_delivery_causal.py
python3 scripts/audits/m_ml_074_diag_00_gp_delivery_causal.py --json

# Testes da missão
python3 -m pytest tests/governance/test_m_ml_074_diag_00_gp_delivery.py -q

# Regressões relacionadas
python3 -m pytest tests/ml/test_m_ml_073_operational_hierarchy.py -q
python3 -m pytest tests/statistics/test_m_stat_001_diversity_remediation_audit.py -q
python3 -m pytest tests/governance/test_m_gov_agents_002_routing.py -q

# Gate de governança
python3 scripts/checks/governance_contract_check.py
```

---

## 8. Confirmações

| Item | Status |
|------|--------|
| Alteração funcional | **Nenhuma** — apenas módulo de diagnóstico, script de auditoria, testes e este relatório |
| Purge executado | **Nenhum** |
| Threshold alterado | **Não** |
| Lei 15 alterada | **Não** |
| `public_app` alterado | **Não** |

---

**M-ML-074-DIAG-00 CONCLUÍDA — CAUSA REAL DO NÃO FECHAMENTO DO GP 15D IDENTIFICADA COM EVIDÊNCIA**
