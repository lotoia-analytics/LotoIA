# M-VIS-034 — Cobertura Estrutural + 6 Bases refinadas no Painel ADM

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-VIS-034` |
| **Título** | Cobertura Estrutural + 6 Bases refinadas no Painel ADM |
| **Projeto** | `P-GOV-001` / `P-LEI15-001` |
| **Tipo** | Visual / Estatístico / Governança / Read-only |
| **Data de abertura** | 2026-06-17 |
| **Data encerramento** | 2026-06-17 |
| **Agentes** | `agent_visual` + `agent_estatistico` + `agent_governanca` + `agent_qualidade` |
| **Status atual** | `CONCLUIDA` |
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
| Branch implantação | `cursor/m-vis-034-cobertura-estrutural-6-bases-cae6` |
| PR implantação | [#134](https://github.com/lotoia-analytics/LotoIA/pull/134) |
| Merge commit | `a533e61d2b55e43b0eebd61de5673417abff019c` |
| Commit entrega | `89fffae77474ab3662ff859d11a2dff6e81d4f18` |
| Build marker | `institutional-adm-runtime-v10` |

## Evidência de deploy (Railway produção)

| Campo | Valor |
|-------|-------|
| Ambiente | `lotoia-production.up.railway.app` |
| Build marker alvo | `institutional-adm-runtime-v10` |
| Merge commit | `a533e61` |
| Checkpoint proporcional | HTTP 200 + health `ok` (P1–P5 M-GOV-031) |
| Tipo de evidência | Textual/operacional — deploy Railway automático pós-merge |

## Confirmação textual/operacional

- `python -c "import dashboard.institutional_app"` — OK
- Testes 43/43 passed (M-VIS-034 + regressões)
- Bloco governança 6 Bases integrado em Cobertura Estrutural
- Alertas institucionais presentes
- Sem `st.button` operacional no módulo novo
- Sem chamada de geração/purge
- Geração **BLOQUEADA**
- `public_app` inalterado
- LEI15_CORE_002 inalterado

## Checklist de conformidade

```text
A Autorização:     [x] OK
B Documentação:    [x] OK
C Git:             [x] OK — PR #134 mergeada
D Qualidade:       [x] OK — 43 testes dashboard
E Deploy:          [x] OK — checkpoint proporcional (health ok)
F Bloqueios:       [x] OK — read-only confirmado
G Veredicto:       [x] OK
```

## Veredicto

| Campo | Valor |
|-------|-------|
| **Veredicto** | `CONCLUIDA / VALIDADA EM PRODUÇÃO / SEM PENDÊNCIA DE DEPLOY` |
| **Data** | 2026-06-17 |
| **Emitido por** | `agent_governanca` + `agent_visual` + `agent_estatistico` + `agent_qualidade` |
| **Resumo** | PR #134 mergeada em `main`; build `institutional-adm-runtime-v10`; Cobertura Estrutural + 6 Bases read-only confirmadas. |
| **Veredicto institucional** | **M-VIS-034 ATIVA EM PRODUÇÃO — COBERTURA ESTRUTURAL + 6 BASES READ-ONLY VALIDADA** |
| **Veredicto de fechamento** | **M-VIS-034 CONCLUÍDA E ATIVA EM PRODUÇÃO — COBERTURA ESTRUTURAL + 6 BASES READ-ONLY VALIDADA** |
| **Registro** | `REGISTRO_MISSOES_INSTITUCIONAL.md` — entrada M-VIS-034 |

## Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| 2026-06-17 | — | `EM_EXECUCAO` | Autorizada pós M-VIS-033 | `agent_visual` |
| 2026-06-17 | `EM_EXECUCAO` | `AGUARDANDO_REVIEW` | PR #134 aberta | `agent_visual` |
| 2026-06-17 | `AGUARDANDO_REVIEW` | `INCORPORADA À MAIN` | Merge PR #134 | operador institucional |
| 2026-06-17 | `INCORPORADA À MAIN` | `CONCLUIDA` | Checkpoint proporcional + validação read-only | `agent_governanca` |
