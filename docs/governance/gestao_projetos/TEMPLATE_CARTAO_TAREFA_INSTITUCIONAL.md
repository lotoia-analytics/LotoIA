# Cartão de Tarefa Institucional — LotoIA

> Copiar este template para cada missão ou tarefa. Manter o original intacto.
> Salvar cópias em `docs/governance/gestao_projetos/cartoes/` quando a missão
> gerar volume documental relevante.

---

## Metadados

| Campo | Valor |
|-------|-------|
| **ID da missão** | `M-____-___` |
| **ID da tarefa** | `T-____-___` (opcional) |
| **Título** | |
| **Projeto** | `P-____-___` |
| **Data de abertura** | YYYY-MM-DD |
| **Agente primário** | `agent________` |
| **Agentes consultivos** | |
| **Solicitante** | |
| **Status atual** | ver `MATRIZ_STATUS_TAREFAS.md` |
| **Prioridade** | `ALTA` / `MÉDIA` / `BAIXA` |

---

## 1. Objetivo

Descrever em uma ou duas frases o resultado institucional esperado.

---

## 2. Contexto

- Por que esta missão existe?
- Qual incidente, auditoria ou decisão a originou?
- Quais documentos de referência se aplicam?

---

## 3. Escopo autorizado

Liste explicitamente o que **pode** ser alterado:

- [ ] Documentação em `docs/governance/`
- [ ] ADRs em `ADRs/`
- [ ] Código em `src/lotoia/`
- [ ] Backend `backend/`
- [ ] Dashboard `dashboard/`
- [ ] Testes `tests/`
- [ ] Scripts `scripts/`
- [ ] Deploy / Railway
- [ ] Outro: _______________

---

## 4. Escopo proibido

Liste explicitamente o que **não pode** ser alterado:

- [ ] Painel ADM (se Fase 0)
- [ ] Geração / Lei 15 / `LEI15_CORE_002`
- [ ] Banco PostgreSQL / schema
- [ ] `FINAL_SCORE_WEIGHTS`
- [ ] Promoção ML institucional
- [ ] Outro: _______________

---

## 5. Entregáveis

| # | Entregável | Tipo | Caminho / referência |
|---|------------|------|----------------------|
| 1 | | doc / código / relatório | |
| 2 | | | |

---

## 6. Evidências exigidas

### Git

| Campo | Valor |
|-------|-------|
| Branch | `cursor/________________-cae6` |
| Commits principais | |
| PR | |
| SHA merge (se aplicável) | |

### Testes

| Comando | Resultado | Data |
|---------|-----------|------|
| `ruff check ...` | PASS / FAIL / N/A | |
| `python -m pytest ...` | PASS / FAIL / N/A | |

### Deploy

> Seguir `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md` — evidência proporcional ao risco.

| Campo | Valor |
|-------|-------|
| Exige deploy? | Sim / Não |
| Perfil de risco | Baixo / Médio / Alto / Crítico |
| SHA deployado | |
| Build marker | |
| Evidência leve (P1–P5) | build + commit + deploy + painel OK + bloqueios (texto) |
| Script HTTP | Condicional — só risco alto/crítico ou solicitação |
| Screenshot | Condicional — só dúvida visual / layout crítico / solicitação |
| Validação pós-deploy | Veredicto textual ou formal no registro |

---

## 7. Bloqueios

| ID | Descrição | Desde | Responsável remoção |
|----|-----------|-------|---------------------|
| B-1 | | | |

Se não houver bloqueios, escrever: `Nenhum bloqueio ativo`.

---

## 8. Riscos e reversão

| Risco | Mitigação | Plano de reversão |
|-------|-----------|---------------------|
| | | |

---

## 9. Checklist de conformidade

Preencher conforme [`CHECKLIST_MISSAO_OBRIGATORIO.md`](CHECKLIST_MISSAO_OBRIGATORIO.md).

```text
A Autorização:     [ ] OK
B Documentação:    [ ] OK
C Git:             [ ] OK
D Qualidade:       [ ] OK / N/A
E Deploy:          [ ] OK / N/A
F Bloqueios:       [ ] OK
G Veredicto:       [ ] pendente
```

---

## 10. Veredicto (preencher ao encerrar)

| Campo | Valor |
|-------|-------|
| **Veredicto** | `APROVADO` / `APROVADO_COM_RESSALVAS` / `BLOQUEADO` / `REJEITADO` / `CONGELADO` |
| **Data** | YYYY-MM-DD |
| **Emitido por** | agente / papel |
| **Resumo** | |
| **Ressalvas** | |
| **Registro** | link para entrada em `REGISTRO_MISSOES_INSTITUCIONAL.md` |

---

## 11. Histórico de transições

| Data | De | Para | Motivo | Responsável |
|------|----|------|--------|-------------|
| | `PROPOSTA` | | | |

---

## Exemplo mínimo (Fase 0)

```markdown
ID: M-GOV-030
Título: Gestão de Projetos — Fase 0
Agente: agent_governanca + agent_plataforma
Escopo autorizado: docs/governance/gestao_projetos/*
Escopo proibido: Painel ADM, banco, LEI15_CORE_002, geração
Veredicto: (pendente)
```
