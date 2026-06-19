# M-STAT-001 — Auditoria da Eficácia da Remediação de Diversidade no Pool Estrutural 15D

| Campo | Valor |
|-------|-------|
| **Missão** | M-STAT-001 |
| **Tipo** | Auditoria read-only |
| **Agente líder** | `agent_estatistico` |
| **Agentes obrigatórios** | `agent_ml`, `agent_geracao`, `agent_qualidade`, `agent_governanca` |
| **Data** | 2026-06-19 |
| **Veredito** | **CONCLUÍDA** — eficácia da remediação de diversidade auditada |
| **Alteração funcional** | Nenhuma |
| **Purge** | Nenhum |

---

## 1. Resumo executivo

A hierarquia **M-ML-073 bloqueia corretamente** o GP quando `diversity_score < 0.55` na Etapa 2 (top `requested_count × 3`). Porém, o ciclo corretivo atual — `pool_estrutural_15d_expandido` + `rerank_diversidade` — **não produz ganho material suficiente** para cruzar o piso institucional em cenário GP:20 15D com pool=100.

**Conclusão:** a política 15D e a cobertura operam; a **remediação de diversidade é estruturalmente fraca** — combina expansão com famílias ainda correlacionadas e rerank que penaliza/reordena sem substituição determinística no top slice avaliado.

**`responsible_agent`:** `agent_estatistico` (via M-GOV-AGENTS-002 / `diversidade_baixa` + `rerank_diversidade`).

---

## 2. Problema observado (trace real)

| Indicador | Valor observado |
|-----------|-----------------|
| Hierarquia | M-ML-073-v1 |
| Etapa 1 Conformidade | Aprovada (`compliance_rate=1.0`) |
| Pool | 100 candidatos |
| Top slice avaliado | 60 (`requested_count=20 × 3`) |
| Etapa 2 Diversidade | **Reprovada** |
| `diversity_score` | 0.3441 |
| Limite institucional | 0.55 |
| `similarity_score` | 0.6559 |
| `max_overlap` | 13 |
| Sufixo dominante | 20-23-24 em 8/60 |
| Cobertura | Aprovada |
| GP | Bloqueado antes do fechamento |

---

## 3. Respostas às 7 perguntas de auditoria

| # | Pergunta | Resposta |
|---|----------|----------|
| 1 | `rerank_diversidade` apenas reordena? | **Predominantemente sim.** `apply_pre_final_pool_ml_calibration` aplica penalidades ML e reordena por `profile_score` / score calibrado. Sem `compose_gp`, `candidates_replaced` deriva da diferença de ordem no top `requested_count`, não de substituição estrutural garantida. |
| 2 | Substitui candidatos parecidos? | **Parcialmente.** `_remediate_pool_for_stage` chama `_filter_near_clone_games` (overlap ≥14 em 15D) e `build_ml_structural_15d_pool` antes do rerank. Substituição no top 60 ocorre se novos candidatos sobem no ranking — não há swap determinístico de clones. |
| 3 | Reduz overlap? | **Marginalmente.** No cenário sintético auditado: `max_overlap` 15→14 (Δ=-1). No trace real permanece 13. |
| 4 | Quebra sufixos/prefixos dominantes? | **Insuficiente.** Expansão 15D gera famílias novas, mas o top slice pós-rerank mantém concentração estrutural (família `*|22-23-24` dominante antes da expansão). |
| 5 | Aumenta `diversity_score`? | **Sim, mas abaixo do necessário.** Cenário GP:20: 0.3206→0.3335 (Δ=+0.0129, +4%). Permanece muito abaixo de 0.55. |
| 6 | Reduz `similarity_score`? | **Sim, marginal.** Δ=-0.0129 no cenário auditado. |
| 7 | Novo material ou só reorganiza? | **Ambos, com peso distinto.** `pool_estrutural_15d_expandido` gera candidatos novos conformes; `rerank_diversidade` reorganiza penalidades no pool existente. O gargalo é a **qualidade diversa** do material novo + **fraca substituição no top slice**. |

---

## 4. Métricas antes/depois (cenário auditado GP:20 15D)

Execução: `python3 scripts/audits/m_stat_001_diversity_remediation_audit.py`

| Métrica | ANTES | DEPOIS | Δ absoluto | Δ % |
|---------|-------|--------|------------|-----|
| `pool_size` | 100 | 100 | 0 | 0 |
| `candidate_pool_size` (top 60) | 60 | 60 | 0 | 0 |
| `diversity_score` | 0.3206 | 0.3335 | **+0.0129** | +4.02% |
| `similarity_score` | 0.6559 | 0.6665* | -0.0129 | -1.9% |
| `max_overlap` | 15 | 14 | **-1** | -6.67% |
| `near_duplicate_count` | 256 | 2 | -254 | — |
| Etapa 2 aprovada? | Não | Não | — | — |

\*Após remediação completa; ganho de diversidade permanece insuficiente.

### Top slice (`requested_count × 3` = 60)

| Campo | Valor |
|-------|-------|
| `top_slice_changed` | **true** |
| `candidates_reordered` | **60** |
| `candidates_replaced` | **19** |

### Ação `pool_estrutural_15d_expandido` (no top slice 60)

| Campo | Valor |
|-------|-------|
| `pool_size_delta` | +40 (60→100 no recorte expandido) |
| `structural_generated_count` | 100 |
| `compliance_rate` | 1.0 |
| Famílias estruturais novas | 15 |
| Δ diversidade na expansão isolada | +0.143 (+16.7%) |

### Ação `rerank_diversidade` (M-ML-071 pré-final)

| Campo | Valor |
|-------|-------|
| `candidates_reordered` | 20 |
| `candidates_replaced` | 20 |
| `pre_final_calibration_applied` | true |
| Δ diversidade pré-final | marginal no ciclo completo |

---

## 5. Análise de prefixos/sufixos e famílias

**Antes (top 60):** família dominante `01-02-03|22-23-24` com 26/60 jogos (~43%).

**Depois da expansão isolada:** 15 famílias novas, mas frequência máxima por família cai para 4/100 — **diversidade melhora no pool total, não necessariamente no top 60 por score**.

**Gap identificado:** `_evaluate_diversity_stage` mede o **top slice por `profile_score`**, enquanto a expansão 15D ordena por `structural_pool_score`. O rerank ML altera scores, mas **não força descarte de famílias dominantes** do top 60.

---

## 6. Causa raiz

**Primária:** `rerank_fraco_sem_ganho_material`

**Contribuintes:**

1. **Rerank fraco** — penalidades (`redundancy_penalty_boost=1.35`, `max_overlap_penalty=1.25`) reordenam sem garantir substituição de famílias dominantes no top slice.
2. **Falta de substituição real determinística** — `_filter_near_clone_games` só remove clones se pool filtrado ≥ max(10, pool/4); caso contrário devolve pool original.
3. **Desalinhamento de ranking** — expansão 15D ranqueia por `structural_pool_score`; avaliação de diversidade usa `profile_score` no slice.
4. **Pool total insuficientemente diverso** — mesmo com 100 conformes, famílias correlacionadas (mesmo sufixo) persistem no topo.
5. **Limite 0.55 não é o problema primário** — com Δ=+0.0129 por ciclo, seriam necessários múltiplos ciclos (máx. 5) sem convergência garantida.

---

## 7. Recomendação da próxima missão

| Prioridade | Missão proposta | Agente |
|------------|-----------------|--------|
| **1** | **M-STAT-002** — Penalidade estrutural multidezena mais forte no rerank pré-final (prefixo/sufixo/família) | `agent_estatistico` + `agent_ml` |
| 2 | **M-GER-002** — Substituição ativa de clones no top `requested_count×3` (não só reordenação) | `agent_geracao` |
| 3 | **M-ML-072-FIX** — Geração 15D anti-família com seed orientado a diversidade estrutural | `agent_geracao` + `agent_ml` |

**Manter limite 0.55** até evidência contrária — não relaxar threshold sem ADR.

---

## 8. Artefatos da auditoria

| Artefato | Caminho |
|----------|---------|
| Módulo de auditoria | `src/lotoia/statistics/diversity_remediation_audit.py` |
| Script CLI | `scripts/audits/m_stat_001_diversity_remediation_audit.py` |
| Testes | `tests/statistics/test_m_stat_001_diversity_remediation_audit.py` |
| Relatório | `docs/governance/M_STAT_001_AUDITORIA_REMEDIACAO_DIVERSIDADE_POOL_15D.md` |

---

## 9. Confirmações

| Item | Status |
|------|--------|
| Alteração funcional em geração/rerank/thresholds/M-ML-073/072 | **Nenhuma** |
| CORE_002, Lei 15, Lei 15A, `public_app` | **Intactos** |
| M-ML-070/071/072/073 | **Intactas** |
| M-GOV-AGENTS-002 (`responsible_agent`) | **Intacta** |
| Purge | **Não executado** |

---

## 10. Veredito

**M-STAT-001 CONCLUÍDA — EFICÁCIA DA REMEDIAÇÃO DE DIVERSIDADE AUDITADA NO POOL ESTRUTURAL 15D**

A remediação atual **não é suficiente** para aprovar a Etapa 2 de diversidade em cenários como o trace observado. Próximo passo recomendado: **M-STAT-002** sob liderança de `agent_estatistico`.
