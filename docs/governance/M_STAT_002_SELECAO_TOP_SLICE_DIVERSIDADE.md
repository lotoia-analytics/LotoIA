# M-STAT-002 — Seleção Estatística Diversa do Top Slice Pré-GP

| Campo | Valor |
|-------|-------|
| **Missão** | M-STAT-002 |
| **Build** | `institutional-adm-runtime-v66` |
| **Agente líder** | `agent_estatistico` |
| **Veredito** | **CONCLUÍDA** — top slice pré-GP selecionado por diversidade e não apenas por score |

## Problema

O recorte `requested_count × 3` (GP:20 → 60 jogos) era montado por `profile_score` puro, permitindo domínio de prefixo/sufixo/família estrutural e `diversity_score` ~0.35.

## Solução

Módulo `src/lotoia/statistics/diverse_top_slice_selection.py`:

1. Recorte inicial por `profile_score` (`requested_count × 3`)
2. Substituição determinística de excesso de sufixo/prefixo/família por candidatos sub-representados
3. Tetos: `MAX_PREFIX_SUFFIX_SHARE=0.14`, `MAX_FAMILY_SHARE=0.10` (prefixo ignorado quando o pool é monoprefixo)
4. Reordenação do pool — slice diverso promovido ao topo antes do portão M-ML-073
5. Critério: `diversity_score >= 0.55` **ou** ganho material `>= +0.20`

## Integração

- `execute_ml_operational_hierarchy` — após pool 15D, antes das etapas 1–3
- Env: `LOTOIA_DIVERSE_TOP_SLICE_ENABLED` (default `1`)
- Payload: `diverse_top_slice_m_stat_002`
- `context_json`: trace via `build_diverse_top_slice_trace`

## Subordinadas intactas

M-ML-070/071/072/073, M-ML-074, M-GOV-AGENTS-002 — sem alteração de thresholds.
