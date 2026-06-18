# Checklist Obrigatório de Missão — LotoIA

Todo cartão de missão deve passar por este checklist antes de transitar para
`AGUARDANDO_VEREDICTO` ou `CONCLUIDA`.

**Política:** `POLITICA_GESTAO_PROJETOS_LOTOIA.md`

---

## A. Autorização e escopo

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| A1 | Missão possui ID único (`M-<DOMÍNIO>-<NNN>`) | Sim | Cartão + registro |
| A2 | Escopo **autorizado** está escrito | Sim | Cartão |
| A3 | Escopo **proibido** está escrito | Sim | Cartão |
| A4 | Agente primário declarado | Sim | Cartão |
| A5 | Agentes consultivos declarados (se houver) | Quando aplicável | Cartão |
| A6 | Zonas protegidas respeitadas (Lei 15, Lei 001, ML, ADM) | Sim | Revisão governança |

---

## B. Planejamento documental

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| B1 | Cartão institucional preenchido | Sim | `TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md` |
| B2 | Entrada criada no quadro | Sim | `QUADRO_PROJETOS_MISSOES.md` |
| B3 | Entrada criada no registro | Sim | `REGISTRO_MISSOES_INSTITUCIONAL.md` |
| B4 | Status inicial coerente com a matriz | Sim | Matriz de status |
| B5 | Critério de encerramento definido | Sim | Cartão |

---

## C. Evidência Git

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| C1 | Branch criada no padrão institucional (`cursor/<nome>-cae6`) | Sim | `git branch` |
| C2 | Commits descritivos e atômicos | Sim | `git log` |
| C3 | Push para remoto (`origin`) | Sim | `git push` |
| C4 | Nenhum artefato crítico fora do Git | Sim | Diff + inventário |
| C5 | PR aberto ou referenciado (quando aplicável) | Quando aplicável | URL ou número PR |

> **Gate crítico:** missão que altera código **não pode** avançar sem C1–C4.

---

## D. Evidência de qualidade (quando o escopo toca código)

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| D1 | `ruff check` nos paths alterados | Sim | Saída do comando |
| D2 | `python -m pytest` (suite relevante ou completa) | Sim | Saída do comando |
| D3 | Sem regressão conhecida documentada | Sim | Notas no cartão |
| D4 | Agente `agent_qualidade` consultado (se mudança ampla) | Quando aplicável | Cartão |

Se o escopo for **somente documental**, marcar D1–D4 como `N/A` com justificativa no cartão.

---

## E. Evidência de deploy (quando aplicável)

> **Política:** `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md` — evidência proporcional ao risco.
> Screenshot e script HTTP **não são obrigatórios** por padrão.

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| E1 | Deploy exige validação formal | Quando aplicável | Política + cartão |
| E2 | SHA esperado documentado | Quando aplicável | Cartão / relatório |
| E3 | Perfil de risco classificado (baixo/médio/alto/crítico) | Quando aplicável | Cartão |
| E4 | **Evidência leve** (build + commit + deploy + painel OK + bloqueios) | Quando aplicável — missões baixo/médio risco | Texto / registro / PR |
| E5 | Checklist Railway ou script HTTP (`railway_panel_deploy_sync_check.py`) | **Condicional** — risco alto/crítico ou operador solicita | Log / relatório |
| E6 | Screenshot | **Condicional** — dúvida visual / layout crítico / divergência UI-runtime / solicitação | Imagem (opcional) |
| E7 | Build marker confirmado | Quando aplicável | Sidebar / log / texto |
| E8 | Rollback ou congelamento definido se falhar | Quando aplicável | Cartão |

Se o escopo **não envolve deploy**, marcar E1–E8 como `N/A`.

---

## F. Bloqueios e riscos

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| F1 | Bloqueios ativos registrados | Quando existir | Cartão + quadro |
| F2 | Risco de leakage temporal avaliado (ML/estatística) | Quando aplicável | Cartão |
| F3 | Risco a Lei 001 / PostgreSQL avaliado | Quando aplicável | Cartão |
| F4 | Risco a LEI15_CORE_002 avaliado | Quando aplicável | Cartão |
| F5 | Plano de reversão documentado | Sim | Cartão |

---

## G. Veredicto e encerramento

| # | Item | Obrigatório | Evidência |
|---|------|-------------|-----------|
| G1 | Veredicto formal emitido | Sim | Registro |
| G2 | Veredicto assinado por agente competente | Sim | Registro |
| G3 | Quadro atualizado com status final | Sim | Quadro |
| G4 | Lições aprendidas registradas (se incidente) | Quando aplicável | Registro |
| G5 | Artefatos versionados no commit final | Sim | Git |

### Veredictos aceitos

- `APROVADO`
- `APROVADO_COM_RESSALVAS`
- `BLOQUEADO`
- `REJEITADO`
- `CONGELADO`

---

## Resumo de conformidade (preencher no cartão)

```text
Missão ID:
Agente primário:
Escopo: [ ] documental  [ ] código  [ ] deploy  [ ] misto

A Autorização:     [ ] OK  [ ] N/A
B Documentação:    [ ] OK  [ ] N/A
C Git:             [ ] OK  [ ] N/A
D Qualidade:       [ ] OK  [ ] N/A
E Deploy:          [ ] OK  [ ] N/A
F Bloqueios:       [ ] OK  [ ] N/A
G Veredicto:       [ ] OK  [ ] pendente

Pode avançar para AGUARDANDO_VEREDICTO? [ ] Sim  [ ] Não
Pode encerrar como CONCLUIDA?             [ ] Sim  [ ] Não
```

---

## Regra de falha

Se qualquer item **obrigatório** estiver incompleto:

1. status da missão deve ser `AGUARDANDO_EVIDENCIA` ou `BLOQUEADA`;
2. o item faltante deve ser listado no cartão;
3. deploy de produção **não** deve ser considerado validado.
