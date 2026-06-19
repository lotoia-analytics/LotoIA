# M-STAT-002 — Seleção Estatística Diversa do Top Slice Pré-GP

| Campo | Valor |
|-------|-------|
| **Missão** | M-STAT-002 |
| **Build** | `institutional-adm-runtime-v68` |
| **Agente líder** | `agent_estatistico` |
| **Veredito** | **CONCLUÍDA** — top slice pré-GP selecionado por diversidade e não apenas por score |

## Problema

O recorte `requested_count × 3` (GP:20 → 60 jogos) era montado por `profile_score` puro, permitindo domínio de prefixo/sufixo/família estrutural e `diversity_score` ~0.35.

## Solução

Módulo `src/lotoia/statistics/diverse_top_slice_selection.py`:

1. Baseline por `profile_score` (top `requested_count × 3`)
2. **Camada 1** — swap iterativo de sufixo/família com teto `LOTOIA_MSTAT_002_SUFFIX_CAP` (default `6`, alinhado ao `DOMINANCE_CALIBRATION_THRESHOLD`)
3. **Camada 2** — swap anti-clone quando overlap > `LOTOIA_MSTAT_002_MAX_OVERLAP` (default `12` em 15D)
4. Reordenação do pool antes do portão M-ML-073
5. Critério registrado: `diversity_score >= 0.55` **ou** ganho material `>= +0.20`

## Integração

- `execute_ml_operational_hierarchy` — após pool 15D, antes das etapas 1–3
- Env: `LOTOIA_DIVERSE_TOP_SLICE_ENABLED` (default `1`)
- Payload: `diverse_top_slice_m_stat_002`
- `context_json`: trace via `build_diverse_top_slice_trace`

## Subordinadas intactas

M-ML-070/071/072/073, M-ML-074, M-GOV-AGENTS-002 — sem alteração de thresholds.
