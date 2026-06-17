# M-GOV-031 — Política de Checkpoint de Produção Simplificado

Cartão ativo — decisão institucional documental.

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-GOV-031` |
| **Título** | Política de Checkpoint de Produção Simplificado |
| **Projeto** | `P-GOV-001` |
| **Tipo** | Governança / Política |
| **Data de abertura** | 2026-06-17 |
| **Agentes** | `agent_governanca` (primário), `agent_plataforma` |
| **Status atual** | `EM EXECUCAO / AGUARDANDO REVIEW` |
| **Prioridade** | `ALTA` |

## Objetivo

Formalizar evidência de produção proporcional ao risco; remover obrigatoriedade de
screenshot e script HTTP como padrão; aceitar evidência leve (build + commit + confirmação
textual/operacional).

## Contexto

Validações M-VIS-031 e M-VIS-032: screenshot e script HTTP consumiam tempo/créditos;
Streamlit não expõe build/commit no HTML estático para sync automatizado.

## Decisão institucional

| Evidência | Padrão |
|-----------|--------|
| Screenshot | **Opcional/condicional** — não obrigatório |
| Script HTTP | **Opcional/condicional** — não obrigatório |
| Evidência leve P1–P5 | **Suficiente** para baixo/médio risco |

## Escopo autorizado

- `docs/governance/POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`
- `CHECKLIST_MISSAO_OBRIGATORIO.md`, template, política Gestão de Projetos, README
- `.cursor/rules/agent_governanca.mdc` (referência)
- registro e quadro

## Escopo proibido

- Painel ADM funcional; geração; purge; banco; Núcleo; Lei 15A; ML operacional; Railway; deploy manual; automação obrigatória nova

## Entregáveis

1. Política de checkpoint simplificada
2. Checklist seção E atualizada
3. Template de cartão atualizado
4. Cartão, registro e quadro M-GOV-031

## Matriz de risco (resumo)

| Risco | Perfil | Evidência mínima |
|-------|--------|------------------|
| Baixo | Documental/read-only sem deploy sensível | Git + veredicto |
| Médio | Visual simples / painel informativo | P1–P5 evidência leve |
| Alto/Crítico | Geração, purge, banco, auth, entrypoint, public_app, API | Checklist ampliado + script HTTP quando exigido |

## Evidência Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/m-gov-031-checkpoint-producao-simplificado-cae6-v2` |
| PR | pendente |

## Evidência de testes

N/A — escopo exclusivamente documental.

## Veredicto alvo

**POLÍTICA DE CHECKPOINT SIMPLIFICADA — SCREENSHOT E SCRIPT HTTP NÃO OBRIGATÓRIOS**

**M-GOV-031 CONCLUÍDA — POLÍTICA DE CHECKPOINT SIMPLIFICADO AGUARDANDO REVIEW** (após PR).
