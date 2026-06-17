# M-PLAT-041 — Separação public_app x ADM Institucional

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-PLAT-041` |
| **Título** | Separação public_app x ADM Institucional |
| **Projeto** | `P-GOV-001` / `P-OPS-001` |
| **Tipo** | Plataforma / Segurança / Governança / Alto risco |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_plataforma` + `agent_governanca` + `agent_visual` + `agent_qualidade` |
| **Status atual** | `CONCLUIDA` |

## Decisão aplicada

**Opção A:** Railway permanece em `institutional_app.py`. `public_app.py` default = canal público seguro; ADM via `LOTOIA_DASHBOARD_MODE=institutional` explícito.

## Entregáveis

| Item | Evidência |
|------|-----------|
| Canal público seguro | `dashboard/public_surface.py` |
| Entrypoint inventory | `dashboard/entrypoint_inventory.py` |
| public_app separado | `dashboard/public_app.py` |
| Governança read-only | `dashboard/institutional_public_separation.py` |
| Inventário documental | `docs/governance/INVENTARIO_ENTRYPOINTS_PUBLIC_ADM_M_PLAT_041.md` |
| Build ADM | `institutional-adm-runtime-v17` |
| Build público | `public-surface-v1-m-plat-041` |

## Confirmação

- Railway entrypoint: `institutional_app.py` (inalterado)
- public_app não espelha ADM por default
- Sem geração / purge / banco / Núcleo alterados

## Evidência Git

| Campo | Valor |
|-------|-------|
| PR implantação | [#148](https://github.com/lotoia-analytics/LotoIA/pull/148) |
| Merge commit | `1f8688a` |
| Commit entrega | `9d030c4` |
| Build ADM | `institutional-adm-runtime-v17` |
| Build público | `public-surface-v1-m-plat-041` |

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto institucional** | **M-PLAT-041 CONCLUÍDA E ATIVA EM PRODUÇÃO — PUBLIC_APP SEPARADO DO ADM INSTITUCIONAL COM SEGURANÇA** |
