# M-DADOS-048 — Card Último concurso monitorado

| Campo | Valor |
|-------|-------|
| Missão | M-DADOS-048 |
| Tipo | Fonte operacional PostgreSQL / card home |
| Build ADM | `institutional-adm-runtime-v24` |

## Problema

O card **Último concurso monitorado** na home ADM podia usar fallbacks (`lotofacil_official_history`, CSV, session_state) em vez de `imported_contests`.

## Correção

- Fonte soberana: **PostgreSQL / imported_contests**
- Origem exibida no card
- Divergência de sync via `LOTOIA_OPERATOR_EXPECTED_CONTEST` (sem hardcode de 3712 no código)
- Referência operacional 3712 usada apenas em testes/validação

## Veredicto alvo

**CARD ÚLTIMO CONCURSO CORRIGIDO — POSTGRESQL EXIBE 3712 OU DIVERGÊNCIA DE SYNC REPORTADA**
