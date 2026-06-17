# Política de Checkpoint de Produção — LotoIA

## Status

`POLITICA_CHECKPOINT_PRODUCAO_SIMPLIFICADA`

Decisão institucional registrada em 2026-06-17 após validações M-VIS-031 e M-VIS-032.

**Veredicto:** **POLÍTICA DE CHECKPOINT SIMPLIFICADA — SCREENSHOT E SCRIPT HTTP NÃO OBRIGATÓRIOS**

---

## 1. Propósito

Definir evidência mínima e proporcional ao risco para validar que uma missão mergeada em
`main` está refletida em produção (Railway), sem burocracia excessiva em missões de baixo
ou médio risco.

Esta política complementa:

- `POLITICA_GESTAO_PROJETOS_LOTOIA.md`
- `CHECKLIST_MISSAO_OBRIGATORIO.md`
- `GOVERNANCA_OPERACIONAL_LOTOIA.md`

**Não altera:** Painel ADM, geração, purge, banco, Núcleo `LEI15_CORE_002`, Lei 15A, ML
operacional ou fluxo Railway.

---

## 2. Decisão institucional

**Screenshot** e **script HTTP/checkpoint automatizado** deixam de ser **obrigatórios** como
evidência padrão de produção.

Passam a ser **evidências opcionais e condicionais**, exigidas somente quando o risco ou o
contexto justificar (ver seções 4 e 5).

A validação de produção deve ser **proporcional ao risco da missão**.

---

## 3. Evidência leve (padrão — baixo/médio risco)

Para missões **documentais**, **read-only**, **visuais simples** ou **sem operação
sensível**, a evidência abaixo é **suficiente** para veredicto de produção:

| # | Evidência | Descrição |
|---|-----------|-----------|
| P1 | **Build marker** | Valor informado (ex.: sidebar `build=institutional-adm-runtime-vN`) |
| P2 | **Commit ativo** | SHA ou prefixo informado (ex.: sidebar `commit=7df540ce3bcc`) |
| P3 | **Deploy Railway ou GitHub** | Confirmação textual/operacional de que o deploy ocorreu |
| P4 | **Painel carregou** | Confirmação textual de que o Painel ADM abriu sem erro de boot |
| P5 | **Bloqueios ativos** | Confirmação textual de que bloqueios esperados permanecem (quando aplicável) |

**Formato aceito:** texto informado pelo operador, registro no cartão/registro institucional,
ou anotação na PR de fechamento. **Screenshot não é obrigatório** quando P1–P5 estiverem
preenchidos de forma clara.

### Exemplos de missões elegíveis à evidência leve

- Fechamento documental de missão (ex.: M-VIS-031, M-VIS-032)
- Governança read-only no Painel ADM
- Ajustes de copy/caption sem operação
- Documentação de governança em `docs/governance/`

---

## 4. Screenshot — quando exigir (condicional)

Screenshot (captura de tela) **só** será exigido quando:

| Condição |
|----------|
| Houver **dúvida visual** sobre o estado em produção |
| Houver **erro de renderização** ou layout quebrado |
| Houver **mudança crítica de layout** ou navegação |
| O **operador solicitar** evidência visual |
| A **evidência textual (P1–P5) for insuficiente** para veredicto |
| Houver **risco alto de divergência** entre UI e runtime |

Fora desses casos, screenshot é **opcional** e pode ser anexado como reforço, não como gate
obrigatório.

---

## 5. Script HTTP / checkpoint automatizado — quando exigir (condicional)

Scripts como `scripts/checks/railway_panel_deploy_sync_check.py` e gates CI de sync HTTP
**só** serão exigidos quando:

| Condição |
|----------|
| Missão **crítica de produção** (runtime, entrypoint, autenticação, deploy sensível) |
| Alteração de **geração** ou flags `LOTOIA_LEI15_CORE_002*` |
| Alteração de **purge** ou política de preservação de histórico |
| Alteração de **banco/schema** ou persistência operacional |
| Alteração de **autenticação**, entrypoint ou **deploy** |
| Alteração de **`public_app`**, **API** ou superfície pública crítica |
| **Falha anterior de deploy** ou incidente (ex.: M-OPS-INC-001) |
| O **operador solicitar** checkpoint automatizado |
| **Governança classificar** a missão como **risco alto** |

Fora desses casos, o script HTTP é **opcional**. Falha do script por limitação de renderização
Streamlit (HTML estático sem build/commit) **não bloqueia** veredicto se P1–P5 estiverem
confirmados por outro meio aceito nesta política.

---

## 6. Matriz de risco × evidência

| Perfil da missão | Risco | Evidência mínima | Screenshot | Script HTTP |
|------------------|-------|------------------|------------|-------------|
| Documental / Git only; read-only sem deploy sensível | **Baixo** | Git + veredicto (deploy N/A) | Opcional | N/A |
| Visual simples; painel informativo read-only | **Médio** | P1–P5 (evidência leve) + testes quando código | Condicional | Opcional |
| Dashboard sem operação sensível | **Médio** | P1–P5 + testes | Condicional | Opcional |
| Deploy pós-incidente | **Alto** | P1–P5 + script ou checklist ampliado | Condicional | **Recomendado** |
| Geração / purge / banco / schema / auth / entrypoint / deploy sensível / `public_app` / API / produção crítica | **Alto / Crítico** | Checklist ampliado + testes + veredicto formal | Condicional | **Obrigatório** |

---

## 7. Veredictos de produção

| Situação | Veredicto sugerido |
|----------|-------------------|
| Merge em `main`, deploy pendente | `INCORPORADA À MAIN — AGUARDANDO CHECKPOINT PRODUÇÃO` |
| P1–P5 confirmados (evidência leve) | `ATIVA EM PRODUÇÃO — VALIDADA` |
| P1–P5 + screenshot (reforço) | `ATIVA EM PRODUÇÃO — VALIDADA COM EVIDÊNCIA VISUAL` |
| Script HTTP PASS (quando exigido) | `ATIVA EM PRODUÇÃO — SYNC AUTOMÁTICO CONFIRMADO` |
| Evidência insuficiente | `AGUARDANDO EVIDÊNCIA DE PRODUÇÃO` |

---

## 8. Relação com Gestão de Projetos Fase 0

- Seção **E (Deploy)** do `CHECKLIST_MISSAO_OBRIGATORIO.md` referencia esta política.
- Cartões de missão usam o template atualizado — deploy pós-produção segue matriz de risco.
- Incidentes operacionais continuam exigindo registro formal (Regra 8 — governança operacional).

---

## 9. Conformidade

Uma validação de produção está em conformidade quando:

- [ ] o perfil de risco da missão foi classificado;
- [ ] a evidência mínima da matriz (seção 6) foi reunida;
- [ ] screenshot/script HTTP só foram exigidos se aplicável (seções 4–5);
- [ ] veredicto formal foi registrado no cartão/registro.

---

## 10. Referências

- `docs/governance/POLITICA_GESTAO_PROJETOS_LOTOIA.md`
- `docs/governance/gestao_projetos/CHECKLIST_MISSAO_OBRIGATORIO.md`
- `docs/governance/gestao_projetos/TEMPLATE_CARTAO_TAREFA_INSTITUCIONAL.md`
- `scripts/checks/railway_panel_deploy_sync_check.py` (ferramenta opcional/condicional)
- `.github/workflows/railway-panel-deploy-gate.yml` (gate CI — não substitui evidência leve)

---

## Histórico

| Data | Evento |
|------|--------|
| 2026-06-17 | Formalização — lições M-VIS-031 / M-VIS-032; screenshot e HTTP deixam de ser obrigatórios por padrão |
