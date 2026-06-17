# Relatório agent_ml — Rodada Multiagente

**Veredicto:** **CONCLUÍDO — ML ASSISTIVO AUDITADO; SEM EFEITO OPERACIONAL**

---

## Papel reforçado

ML = **diagnóstico / recomendação / alerta** — `operational_effect=False` sempre.

Fonte: `src/lotoia/observability/ml_diagnostic_panels.py`

---

## Campos auditados

| Campo | Valor |
|-------|-------|
| `generation_cmd` | Hard-coded **False** |
| `recalibration_cmd` | Hard-coded **False** |
| `operational_effect` | **False** |
| Routing LOCAL vs RECURRENT | Threshold 20 GEs |

---

## Telas

- Central ML Assistiva — read-only verdicts
- Vazamento Lateral — observacional
- Simulação Institucional + ML — **planejado** (walk-forward futuro)

---

## Arquivos alterados

Nenhum.

---

## Confirmações

- ML operacional: **não ativado**
- Geração via ML: **não**

---

## Próximo passo

**M-ML-033** (proposta): Plano integração ML × Simulação Institucional (documental + contrato).
