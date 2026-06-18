# M-ML-VIS-053B — Corrigir rota da Central ML no Painel ADM

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-ML-VIS-053B` |
| **Título** | Corrigir rota da Central ML no Painel ADM |
| **Status** | `CONCLUIDA` |
| **Build ADM** | `institutional-adm-runtime-v33` |
| **Pré-requisito** | M-ML-VIS-053 |

## Problema

Central ML caía em **“Rota legada ou não institucionalizada — fallback”** porque
`_canonical_page_id()` não reconhecia `central_ml_diagnostics` como page_id válido.

## Correção

- `_canonical_page_id()` — aceita page_ids em `INSTITUTIONAL_ALLOWED_PAGES`
- `PAGE_TARGETS` — labels Central ML (atual + legado)
- `LEGACY_PAGE_ALIASES` — `Central de Diagnósticos ML`, `ml_diagnostics`, etc.

## Veredicto

**M-ML-VIS-053B CONCLUÍDA — CENTRAL ML ABRE CORRETAMENTE NO PAINEL ADM**
