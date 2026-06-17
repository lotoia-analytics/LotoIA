# M-VIS-034 — Cobertura Estrutural + 6 Bases refinadas no Painel ADM

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-034` |
| **Título** | Cobertura Estrutural + 6 Bases refinadas no Painel ADM |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Estatístico / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_visual` + `agent_estatistico` + `agent_governanca` + `agent_qualidade` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade / Risco** | Médio (read-only); alto/crítico se tocar geração, banco, Núcleo, purge, Lei 15A, ML operacional ou public_app |

## Objetivo

Refinar no Painel ADM a leitura de Cobertura Estrutural e as 6 Bases do Núcleo Lei 15,
em modo read-only, sem operação ativa — transformando Cobertura Estrutural em leitura
institucional clara para governança do CORE_002.

## Regra constitucional

Hit isolado não é veredicto. Hit é evidência da Base 1, mas o Núcleo só é avaliado
pelo conjunto das 6 bases.

## Pré-requisitos

| Requisito | Evidência |
|-----------|-----------|
| M-VIS-033 fechada em `main` | PR #133 — merge `a2009cda` |
| Geração bloqueada | `LOTOIA_LEI15_CORE_002_GENERATION_ENABLED=0` |

## Escopo autorizado

- Refinar bloco/tela de Cobertura Estrutural
- Reorganizar leitura das 6 Bases em cards/tabelas read-only
- Exibir definição, métrica esperada, evidência e pendência por base
- Marcar evidência histórica vs métrica futura
- Reforçar CORE_002 como referência constitucional
- Alertas institucionais obrigatórios
- `dashboard/institutional_structural_coverage.py`
- Testes read-only + regressão M-VIS-031/032/033, M-LEI15-003

## Escopo proibido

- Liberar geração; alterar Núcleo; banco/schema; purge; Lei 15A; ML operacional; public_app; deploy manual; botões operacionais; edição de matriz; calibração automática

## Entregáveis

1. Cobertura Estrutural refinada em modo read-only
2. 6 Bases apresentadas de forma clara
3. Separação visual CORE_002 soberano vs evidências históricas
4. Textos institucionais de não promessa e não operação
5. Testes novos ou atualizados
6. Build marker v10

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-vis-034-cobertura-estrutural-6-bases-cae6` |
| Build marker | `institutional-adm-runtime-v10` |

## Veredicto alvo

**M-VIS-034 CONCLUÍDA — COBERTURA ESTRUTURAL + 6 BASES READ-ONLY AGUARDANDO REVIEW**
