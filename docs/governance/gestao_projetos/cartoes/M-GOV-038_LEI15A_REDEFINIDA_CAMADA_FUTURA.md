# M-GOV-038 — Lei 15A Redefinida como Camada Futura Subordinada ao CORE_002

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-GOV-038` |
| **Título** | Lei 15A redefinida como camada futura subordinada ao CORE_002, porém inoperante |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Governança / Constitucional / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_governanca` + `agent_geracao` + `agent_estatistico` + `agent_qualidade` |
| **Status atual** | `CONCLUIDA` |

## Frase obrigatória

A Lei 15A é uma camada futura subordinada ao LEI15_CORE_002. No estado atual, está redefinida e inoperante: não gera, não expande, não altera Núcleo, não ativa mecânica 15+1/15+2 e não possui efeito operacional.

## Entregáveis

| Item | Evidência |
|------|-----------|
| Documento de governança | `docs/governance/LEI_15A_CAMADA_FUTURA_SUBORDINADA_CORE_002.md` |
| Módulo read-only painel | `dashboard/institutional_lei15a_governance.py` |
| Status Constitucional atualizado | `_constitutional_status_lines()` em `institutional_app.py` |
| Governança read-only integrada | `render_governance_read_only_page()` |
| Build marker | `institutional-adm-runtime-v14` |
| Testes | `tests/dashboard/test_institutional_app_gov_038_lei15a_governance.py` |

## Bloqueios relacionados

- `BLK-GERACAO-001`
- `BLK-CORE002-001`
- `BLK-LEI15A-001`
- `BLK-ML-OPERACIONAL-001`
- `BLK-PUBLIC-APP-001`

## Confirmação

- LEI15_CORE_002 permanece soberano
- Lei 15A não ficou operacional
- Mecânica 15+1/15+2 não reativada
- Sem geração / purge / banco / Núcleo / public_app alterados operacionalmente

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto institucional** | **M-GOV-038 CONCLUÍDA — LEI 15A REDEFINIDA COMO CAMADA FUTURA SUBORDINADA AO CORE_002 E INOPERANTE** |
