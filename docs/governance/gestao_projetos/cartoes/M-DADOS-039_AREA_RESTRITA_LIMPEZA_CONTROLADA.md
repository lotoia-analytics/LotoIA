# M-DADOS-039 — Área Restrita / Limpeza Controlada protegida pela Lei 001

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-DADOS-039` |
| **Título** | Área Restrita / Limpeza Controlada protegida pela Lei 001 |
| **Projeto** | `P-GOV-001` / `P-OPS-001` |
| **Tipo** | Dados / Governança / Visual / Segurança / Read-only defensivo |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_dados` + `agent_governanca` + `agent_visual` + `agent_qualidade` + `agent_plataforma` |
| **Status atual** | `CONCLUIDA` |

## Frase obrigatória

Limpeza de sessão não é purge. Purge real é operação crítica, protegida pela Lei 001, e não pode apagar evidência institucional sem missão específica, dry-run, guarda por label e autorização.

## Entregáveis

| Item | Evidência |
|------|-----------|
| Módulo Área Restrita | `dashboard/institutional_controlled_cleanup.py` |
| Integração painel ADM | `_render_restricted_controlled_cleanup_page()` |
| Separação sessão / purge / dry-run | 4 abas read-only defensivas |
| Build marker | `institutional-adm-runtime-v15` |
| Testes | `tests/dashboard/test_institutional_app_dados_039_controlled_cleanup.py` |

## Bloqueios relacionados

- `BLK-PURGE-001`
- `BLK-LEI001-001`
- `BLK-HISTORICO-001`
- `BLK-GERACAO-001`
- `BLK-CORE002-001`
- `BLK-PUBLIC-APP-001`

## Evidência Git

| Campo | Valor |
|-------|-------|
| PR implantação | [#144](https://github.com/lotoia-analytics/LotoIA/pull/144) |
| Merge commit | `ae15edf` |
| Commit entrega | `7e502d1` |
| Build marker | `institutional-adm-runtime-v15` |

## Confirmação

- Purge real bloqueado — sem botão destrutivo
- Limpeza de sessão separada de purge
- Lei 001 exibida como guarda soberana
- Tabelas e labels protegidos listados
- Sem geração / purge real / banco / Núcleo / public_app alterados

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto institucional** | **M-DADOS-039 CONCLUÍDA E ATIVA EM PRODUÇÃO — ÁREA RESTRITA / LIMPEZA CONTROLADA VALIDADA COM PURGE BLOQUEADO** |
