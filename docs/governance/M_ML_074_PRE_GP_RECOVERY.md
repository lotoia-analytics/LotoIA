# M-ML-074 — Recuperação Determinística Pré-GP

| Campo | Valor |
|-------|-------|
| **Missão** | M-ML-074 |
| **Build** | `institutional-adm-runtime-v65` |
| **Env** | `LOTOIA_ML_PRE_GP_RECOVERY_ATTEMPTS` (default 5) |
| **Veredito** | Loop pré-GP antes de bloqueio visível M-ML-073 |

## Comportamento

1. `generate_best_games` chama `execute_pre_gp_recovery_cycle` quando hierarquia ML está ativa.
2. Até N tentativas (default 5): executa M-ML-073 → se reprovar, aplica ações determinísticas → repete.
3. Se alguma tentativa aprovar: entrega GP completo e registra ciclo em `pre_gp_recovery`.
4. Se todas falharem: `MlOperationalHierarchyBlockedError` com mensagem de esgotamento + `best_attempt_metrics`.

## Ações determinísticas

- Expansão pool 15D (M-ML-072)
- Substituição material no top slice (não só rerank)
- Penalização de famílias dominantes
- Anti-clone forte
- Reforço de dezenas subcobertas

## Subordinadas intactas

M-ML-070, M-ML-071, M-ML-072, M-ML-073, M-GOV-AGENTS-002 — sem alteração de thresholds ou Lei 15.
