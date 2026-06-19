# M-ML-076-AUDIT-00 — Separar Veredito Estrutural de Veredito por Hits

**Status:** CONCLUÍDA  
**Classificação:** **D** — Hits interferem no veredito/liberação  
**Data:** 2026-06-19  
**BUILD_MARKER vigente (sem alteração):** `institutional-adm-runtime-v76`

---

## Resposta objetiva

**Hits estão interferindo na liberação?**  
**Sim, condicionalmente.** A ausência de captura 13/14/15 **não reprova sozinha**, mas combinada com redundância alta (`similaridade_media ≥ 0,55` ou quase repetidos ≥ 20) eleva o veredito para `PRECISA CALIBRAR`, bloqueando `official_release_allowed`. Em lotes estruturalmente saudáveis (`APROVADO`), hits zero ainda geram bloco decisório e item de plano de calibração — misturando linguagem analítica na Central ML.

**O veredito ML principal julga por qualidade estrutural ou acerto histórico?**  
**Híbrido.** A base é estrutural (similaridade, overlap, quase repetidos, política 15D), porém existe regra explícita `captura_ausente_redundancia` que injeta comparação histórica de hits na decisão operacional.

---

## Pergunta central — evidência

Cenário contrafactual reproduzido (GP:20 15D limítrofe):

| Condição | `ml_verdict` | `official_release_allowed` | `rule_triggers` |
|----------|--------------|---------------------------|-----------------|
| `similaridade=0,56`, `quase_repetidos=2`, **hits 0/0/0** | `PRECISA CALIBRAR` | `false` | `captura_ausente_redundancia` |
| Mesmas métricas, **hits ≥ 1** | `APROVADO` | `true` | `[]` |

**Conclusão:** hits alteram a decisão operacional em faixa limítrofe estrutural.

---

## Tabela 1 — Métricas encontradas

| Métrica | Tipo | Onde calculada | Entra no veredito? | Entra na promoção? | Deve entrar? |
|---------|------|----------------|--------------------|--------------------|--------------|
| `similaridade_media` | Estrutural | `card_structure_diagnostics.py` | **Sim** (`ml_operational_verdict.py`) | Indireto via `ml_verdict` | **Sim** |
| `diversity_score` | Estrutural | `card_structure_diagnostics.py` | Indireto (plano/blocos) | Não direto | **Sim** (plano) |
| `sobreposicao_maxima` | Estrutural | `compute_gp_redundancy` | **Sim** | Indireto | **Sim** |
| `quase_repetidos_criticos` | Estrutural | `compute_gp_redundancy` | **Sim** | Indireto | **Sim** |
| `pares_em_atencao` | Estrutural | `compute_gp_redundancy` | **Sim** (combinações) | Indireto | **Sim** |
| `dezenas_subcobertas` | Estrutural | `card_structure_diagnostics.py` | Via plano/blocos | Indireto | **Sim** |
| `policy_compliance_*` | Estrutural (15D) | `structural_policy_15d` | **Sim** | Indireto | **Sim** |
| `prefixos_sufixos_viciados` | Estrutural | `card_structure_diagnostics.py` | Via blocos/plano | Não direto | **Sim** (plano) |
| `desempenho_13_hits` | **Hit** | `card_structure.py` → `analyze_stuck_games` | **Sim** (com redundância) | Indireto | **Não** (só analítico) |
| `desempenho_14_hits` | **Hit** | idem | **Sim** (com redundância) | Indireto | **Não** |
| `desempenho_15_hits` | **Hit** | idem | **Sim** (com redundância) | Indireto | **Não** |
| `captura_13_14_ausente` (bloco) | **Hit** | `coverage_evidence_interpreter.py` | Não direto no veredito | Não | **Não** (UI/plano) |
| Plano "captura 13/14" | **Hit** | `build_calibration_plan` | Não | Não | **Não** |
| `gp_quality_tier` | Estrutural (hierarquia) | `ml_operational_hierarchy.py` | Paralelo ao veredito | **Sim** | **Sim** |
| `jogos_com_13/14/15_hits` (lista) | **Hit** | `analyze_stuck_games` vs concursos oficiais | Agregado em métricas | Não direto | **Não** |

**Cálculo de hits:** compara cada cartão contra `official_numbers` da janela oficial (até 50 concursos) em `card_structure_diagnostics._load_official_cards` → `analyze_stuck_games` em `card_structure.py`.

---

## Tabela 2 — Decisão atual vs decisão estrutural pura

Cenários sintéticos (evidência JSON: `docs/audits/M-ML-076-AUDIT-00_evidence.json`).

### Cenário A — Estrutural saudável, zero hits

| Campo | Decisão atual | Decisão sem hits | Diferença |
|-------|---------------|------------------|-----------|
| `ml_verdict` | `APROVADO` | `APROVADO` | Nenhuma |
| `gp_quality_tier` | (não derivado neste fluxo) | — | — |
| `official_release_allowed` | `true` | `true` | Nenhuma |
| `lot_operational_status` | elegível se promovido | — | — |
| `promotion_block_reason` | — | — | — |
| `plano recomendado` | **Inclui** item captura 13/14 | **Inclui** item captura 13/14 | UI/plano mistura hit |
| `motivo_principal` | Sem bloqueios | Sem bloqueios | OK |
| `problema_detectado` (UI) | **"Baixa força de captura 13/14"** | idem | **Linguagem inadequada** |

### Cenário B — Redundância alta, zero hits

| Campo | Decisão atual | Decisão sem hits | Diferença |
|-------|---------------|------------------|-----------|
| `ml_verdict` | `PRECISA CALIBRAR` | `PRECISA CALIBRAR` | Severidade igual |
| `official_release_allowed` | `false` | `false` | Nenhuma |
| `motivo_principal` | Inclui **"ausência de captura 13/14/15 com redundância alta"** | Só estrutural | **Texto hit misturado** |
| `plano recomendado` | Inclui captura 13/14 | Inclui captura 13/14 | Plano hit |

### Cenário C — Limítrofe (sim=0,56, QR=2, hits zero) — **crítico**

| Campo | Decisão atual | Decisão sem hits (hits≥1) | Diferença |
|-------|---------------|---------------------------|-----------|
| `ml_verdict` | `PRECISA CALIBRAR` | `APROVADO` | **Veredito alterado** |
| `official_release_allowed` | `false` | `true` | **Liberação alterada** |
| `promotion_block_reason` | `ml_verdict_precisa_calibrar_not_releasable` | — | **Promoção bloqueada por hit+redundância** |
| `plano recomendado` | Com captura | Sem captura | Plano hit |

### Cenário D — Crítico estrutural (sim=0,72), zero hits

| Campo | Decisão atual | Decisão sem hits | Diferença |
|-------|---------------|------------------|-----------|
| `ml_verdict` | `REPROVADO` | `REPROVADO` | Nenhuma (estrutural domina) |
| `official_release_allowed` | `false` | `false` | Nenhuma |

---

## Tabela 3 — Causa real da reprovação

| Fator | Estrutural ou hit | Peso na decisão | Evidência |
|-------|-------------------|-----------------|-----------|
| Overlap crítico/ruim por formato | Estrutural | **Alto** — `REPROVADO`/`BLOQUEADO` | `ml_operational_verdict.py` L146-154 |
| Similaridade por banda format-aware | Estrutural | **Alto** | L156-185 |
| Quase repetidos ≥ 20 + sim alta | Estrutural | **Alto** — `PRECISA CALIBRAR` | L187-192 |
| Política 15D não conforme | Estrutural | **Alto** | L216-248 |
| Ausência hits 13/14/15 + redundância alta | **Hit + estrutural** | **Médio** — pode elevar `APROVADO`→`PRECISA CALIBRAR` | L201-204, `captura_ausente_redundancia` |
| Ausência hits 13/14 sem redundância | **Hit** | **Baixo no veredito** / **Alto no plano e UI** | `coverage_evidence_interpreter.py` L307-319, L469-492 |
| `gp_quality_tier` | Estrutural (hierarquia) | **Alto na promoção** | `lot_operational_status.py` L225-260 |
| `ml_verdict` na promoção | Estrutural (+ hit indireto) | **Alto** | `lot_operational_status.py` |

---

## Classificação final

### **D — Hits interferem no veredito/liberação**

Justificativa:
1. Regra `captura_ausente_redundancia` em `evaluate_ml_operational_verdict` altera veredito e liberação em lotes limítrofes.
2. Mesmo quando não alteram severidade, hits aparecem em `motivo_principal` e podem ser `primary_decision` na UI.
3. Plano de calibração inclui ações de captura 13/14 sem exigir redundância estrutural.

Não é **E** (causa principal): lotes claramente ruins são reprovados por overlap/similaridade estrutural independente de hits.

Não é **A**: hits não são apenas informativos.

---

## Validação da regra institucional proposta

> "Veredito estrutural decide liberação operacional. Hits e capturas históricas ficam apenas para Histórico Analítico, Conferir Resultados e Backtesting."

**Status:** **NÃO CONFORME** no estado atual.

**Gaps identificados:**
1. `ml_operational_verdict.py` — regra `captura_ausente_redundancia`
2. `coverage_evidence_interpreter.py` — bloco `captura_13_14_ausente` e plano com texto de captura
3. Central ML — pode exibir "Baixa força de captura" como problema principal mesmo com `APROVADO`

---

## Recomendação da próxima missão

**M-ML-076-FIX-01** (proposta, não implementada nesta auditoria):

1. Remover regra `captura_ausente_redundancia` de `evaluate_ml_operational_verdict` (veredito/liberação).
2. Remover bloco `captura_13_14_ausente` de `interpret_coverage_evidence` e item de plano associado.
3. Manter `desempenho_13/14/15_hits` apenas em Auditoria Técnica / Histórico Analítico.
4. ADR obrigatório documentando separação régua estrutural vs régua de hits.
5. Testes contrafactuais permanentes (cenário limítrofe sim=0,56).

---

## Arquivos auditados

| Arquivo | Papel |
|---------|-------|
| `src/lotoia/ml/ml_operational_verdict.py` | Veredito ML — **regra hit+redundância** |
| `src/lotoia/observability/coverage_evidence_interpreter.py` | Blocos decisórios e plano — **captura 13/14** |
| `src/lotoia/observability/card_structure_diagnostics.py` | Agregação métricas + hits |
| `src/lotoia/statistics/card_structure.py` | `analyze_stuck_games` |
| `src/lotoia/operations/lot_operational_status.py` | Promoção (via veredito, não hits diretos) |
| `src/lotoia/ml/ml_operational_hierarchy.py` | `gp_quality_tier` (estrutural) |
| `src/lotoia/governance/institutional_agent_routing_matrix.py` | Roteamento `captura_13_14_ausente` |
| `dashboard/institutional_ml_calibration_cockpit.py` | Exibição motivo/plano |

---

## Comandos usados

```bash
python scripts/audits/m_ml_076_audit_00_structural_vs_hits.py
python -m pytest tests/audits/test_m_ml_076_audit_00_structural_vs_hits.py -q
```

Evidência machine-readable: `docs/audits/M-ML-076-AUDIT-00_evidence.json`

---

## Confirmações obrigatórias

| Item | Status |
|------|--------|
| CORE_002 intacto | ✅ Nenhuma alteração |
| Lei 15 intacta | ✅ Nenhuma alteração |
| Lei 15A intacta | ✅ Nenhuma alteração |
| public_app intacto | ✅ Nenhuma alteração |
| Purge executado | ✅ Não |
| Veredito alterado | ✅ Não (auditoria read-only) |
| Thresholds alterados | ✅ Não |
| Geração alterada | ✅ Não |
| Promoção alterada | ✅ Não |

---

## Veredito

**M-ML-076-AUDIT-00 CONCLUÍDA — RÉGUA ESTRUTURAL E RÉGUA DE HITS SEPARADAS COM EVIDÊNCIA**
