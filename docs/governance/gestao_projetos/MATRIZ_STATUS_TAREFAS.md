# Matriz de Status das Tarefas — LotoIA

Estados, transições permitidas e veredictos formais de encerramento.

---

## 1. Estados operacionais

| Status | Código | Descrição |
|--------|--------|-----------|
| Planejada | `PLANEJADA` | Missão registrada; execução não iniciada |
| Aberta | `ABERTA` | Em execução ativa |
| Bloqueada | `BLOQUEADA` | Impedimento externo (secrets, aprovação, dependência) |
| Em revisão | `EM_REVISAO` | Código/docs prontos; aguarda PR/merge/review |
| Em deploy | `EM_DEPLOY` | Merge feito; Railway/CI propagando |
| Concluída | `CONCLUÍDA` | Veredicto positivo; evidência completa |
| Cancelada | `CANCELADA` | Escopo descartado; motivo registrado |
| Arquivada | `ARQUIVADA` | Histórico preservado; sem ação pendente |

---

## 2. Transições permitidas

```text
PLANEJADA → ABERTA
ABERTA → BLOQUEADA | EM_REVISAO | CONCLUÍDA (só documental) | CANCELADA
BLOQUEADA → ABERTA | CANCELADA
EM_REVISAO → EM_DEPLOY | BLOQUEADA | CONCLUÍDA (sem deploy)
EM_DEPLOY → CONCLUÍDA | BLOQUEADA (deploy falhou)
CONCLUÍDA → ARQUIVADA
CANCELADA → ARQUIVADA
```

**Proibido:** `PLANEJADA → CONCLUÍDA` sem passar por `ABERTA`.
**Proibido:** `ABERTA → CONCLUÍDA` para missão com código em produção sem `EM_DEPLOY` ou checkpoint explícito N/A.

---

## 3. Veredictos de encerramento

Usar **exatamente um** veredicto por missão.

### 3.1 Sucesso

| Veredicto | Quando usar |
|-----------|-------------|
| `MISSÃO CONCLUÍDA` | Escopo cumprido; Git/testes OK; sem pendência operacional |
| `GESTAO_PROJETOS_FASE_0_IMPLANTADA` | Implantação de artefato de governança documental |
| `PAINEL RESTAURADO` | Hotfix produção; painel carrega sem erro de import/runtime |
| `GIT SINCRONIZADO` | Merge/push concluído; branch alinhada com remoto |
| `RAILWAY DEPLOYADO EM {SHA}` | Produção confirmada no commit indicado |
| `HISTÓRICO INSTITUCIONAL PROTEGIDO — PURGE BLOQUEADO` | Política de preservação implantada |
| `PATH ÚNICO CORE_002 GARANTIDO — LEGACY DEFAULT BLOQUEADO` | Routing Lei 15 implantado |
| `TRANSIÇÃO CONSTITUCIONAL REGISTRADA` | ADR/registro governança sem runtime |

### 3.2 Andamento / condicional

| Veredicto | Quando usar |
|-----------|-------------|
| `DEPLOY EM ANDAMENTO` | Push OK; Railway/CI ainda propagando |
| `HOTFIX PUBLICADO — AGUARDANDO DEPLOY` | Commit em main; produção ainda no SHA anterior |
| `EVIDÊNCIA PARCIAL` | Trabalho feito; falta item checklist (listar qual) |

### 3.3 Falha / bloqueio

| Veredicto | Quando usar |
|-----------|-------------|
| `MISSÃO BLOQUEADA` | Não executável no ambiente atual |
| `HOTFIX BLOQUEADO` | Correção não publicada (sem push/aprovação) |
| `DEPLOY AINDA QUEBRADO` | Produção com erro após deploy |
| `DEPLOY FALHOU` | Build/deploy Railway falhou |
| `RAILWAY AINDA EM {SHA}` | Produção não atualizou após merge |
| `RISCO DE PRODUÇÃO` | Código divergente Git vs runtime; import quebrado; dados em risco |
| `EVIDÊNCIA GIT AUSENTE` | Alteração local sem commit/push |
| `VIOLAÇÃO DE GOVERNANÇA` | Escopo proibido executado |
| `RISCO DE GOVERNANÇA GIT` | Missões locais sem commit (pré-consolidação) |

---

## 4. Matriz status × evidência

| Status | Git commit | Push | Testes | Deploy check | Pode encerrar? |
|--------|------------|------|--------|--------------|----------------|
| PLANEJADA | — | — | — | — | Não |
| ABERTA | opcional WIP | — | WIP | — | Não |
| EM_REVISAO | obrigatório | pendente ou OK | obrigatório* | — | Não |
| EM_DEPLOY | obrigatório | OK | obrigatório* | pendente | Condicional** |
| CONCLUÍDA | obrigatório | OK | OK ou N/A | OK ou N/A | Sim |

\* Quando missão altera código.
\*\* Encerrar com `DEPLOY EM ANDAMENTO` ou aguardar `RAILWAY DEPLOYADO EM {SHA}`.

---

## 5. Prioridade × SLA documental (Fase 0)

| Prioridade | Expectativa de registro | Checkpoint |
|------------|-------------------------|------------|
| `critical` | Atualizar quadro no mesmo dia | Deploy + veredicto |
| `high` | Atualizar quadro em 24h | Git + testes |
| `medium` | Atualizar quadro em 72h | Git |
| `low` | Atualizar quadro na semana | Veredicto |

*SLA documental — não automação.*

---

## 6. Mapeamento incidente → veredicto (referência)

| Situação | Veredicto |
|----------|-----------|
| `ModuleNotFoundError` pós-deploy por arquivo não versionado | `RISCO DE PRODUÇÃO` → hotfix → `PAINEL RESTAURADO` |
| Merge em main sem deploy refletido | `DEPLOY EM ANDAMENTO` ou `RAILWAY AINDA EM {SHA}` |
| Secrets ausentes no agente | `MISSÃO BLOQUEADA` |
| 7 commits locais sem push | `RISCO DE GOVERNANÇA GIT` |

---

## 7. Campos obrigatórios no registro ao mudar status

```yaml
mission_id:
status_anterior:
status_novo:
data:
responsavel:
evidencia: "link commit / PR / healthcheck"
veredicto: "se encerramento"
observacao:
```
