# M-GER-044 — Ativação da Geração Soberana Controlada CORE_002

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-GER-044` |
| **Título** | Ativação da Geração Soberana Controlada CORE_002 |
| **Projeto** | `P-GOV-001` / `P-OPS-001` |
| **Tipo** | Geração / Dados / Governança / Plataforma / Crítica |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_geracao` + `agent_dados` + `agent_qualidade` + `agent_governanca` + `agent_plataforma` |
| **Status atual** | `CONCLUIDA` |

## Path soberano ativado

```python
generate_best_games(
    count=...,
    pool_size=...,
    batch_label="STRUCT_LEI15_CORE_CANDIDATE_002_15D_001",
    ml_enabled=False,
)
```

## Controles

| Item | Valor |
|------|-------|
| Núcleo | `LEI15_CORE_002` |
| Label | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| Flag | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=1` (default) |
| Persistência | PostgreSQL — `generation_events` / `generated_games` |
| Build ADM | `institutional-adm-runtime-v18` |

## Smoke PostgreSQL real (checkpoint final)

| Campo | Valor |
|-------|-------|
| Data | 2026-06-17 |
| `generation_event_id` | **116** |
| `batch_label` | `STRUCT_LEI15_CORE_CANDIDATE_002_15D_001` |
| Quantidade solicitada | 1 |
| Quantidade persistida (`generated_games`) | 1 |
| `ml_enabled` (DB) | 0 |
| Jogos únicos | 1 |
| Veredicto smoke | **M-GER-044 VALIDADA COM SMOKE POSTGRESQL REAL** |

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto institucional** | **M-GER-044 CONCLUÍDA E ATIVA EM PRODUÇÃO — GERAÇÃO SOBERANA CONTROLADA CORE_002 VALIDADA COM PERSISTÊNCIA POSTGRESQL** |

## Evidência Git

| Campo | Valor |
|-------|-------|
| PR implantação | [#152](https://github.com/lotoia-analytics/LotoIA/pull/152) |
| Merge commit | `167d46e` |
| Commit entrega | `c05e135` |
| Build ADM | `institutional-adm-runtime-v18` |
