# Checklist Obrigatório de Missão — LotoIA

Usar **antes**, **durante** e **ao encerrar** toda missão institucional.

Marcar `[x]` somente com evidência. Item sem evidência = item **não cumprido**.

---

## A. Abertura

- [ ] **A1.** `mission_id` único definido (formato `SNAKE_CASE` ou `MISSAO_*`)
- [ ] **A2.** Agente responsável (`owner`) único identificado
- [ ] **A3.** Agentes de apoio listados (sem sobreposição de escopo)
- [ ] **A4.** Objetivo em uma frase verificável
- [ ] **A5.** Escopo **permitido** explícito
- [ ] **A6.** Escopo **proibido** explícito (Lei 15, geração, purge, banco, etc.)
- [ ] **A7.** Dependências de missões anteriores identificadas
- [ ] **A8.** Cartão registrado em `QUADRO_MISSOES.md` (status `ABERTA` ou `PLANEJADA`)

---

## B. Governança e fronteiras

- [ ] **B1.** Missão **não** altera Lei 15 / Lei 15A sem ADR + `agent_governanca`
- [ ] **B2.** Missão **não** altera `FINAL_SCORE_WEIGHTS` ou `validation_threshold` sem ADR
- [ ] **B3.** Missão **não** promove ML a componente institucional sem relatório comparativo
- [ ] **B4.** `operational_effect` declarado (`true` / `false`)
- [ ] **B5.** Se `operational_effect=false`, confirmado que nenhum dado operacional será mutado
- [ ] **B6.** Purge / reset / delete_history **não** executados salvo missão `agent_dados` dedicada

---

## C. Execução técnica

- [ ] **C1.** Branch de trabalho identificada (ou `main` se hotfix autorizado)
- [ ] **C2.** Nenhum arquivo referenciado por import permanece fora do Git
- [ ] **C3.** Secrets/credenciais **não** commitados (`.env`, tokens, URLs com senha)
- [ ] **C4.** Escopo limitado ao pedido — sem refatoração ampla não solicitada
- [ ] **C5.** SQLite / CSV **não** usados como fonte operacional (Lei No 001)

---

## D. Testes mínimos

*(Aplicável quando missão altera código Python, dashboard ou API.)*

- [ ] **D1.** Testes de regressão relevantes executados (listar comando)
- [ ] **D2.** Resultado dos testes registrado (passed / failed / skipped + motivo)
- [ ] **D3.** Import/boot do módulo afetado verificado (ex.: dashboard, API)
- [ ] **D4.** Falhas ambientais documentadas separadamente de falhas de código

**Missão somente documental:** marcar N/A e citar revisão humana.

---

## E. Evidência Git (obrigatória se houver alteração de repositório)

- [ ] **E1.** `git status` final limpo para arquivos da missão
- [ ] **E2.** Commit realizado com mensagem descritiva
- [ ] **E3.** Hash do commit registrado
- [ ] **E4.** Push confirmado para GitHub
- [ ] **E5.** Link do commit ou PR registrado
- [ ] **E6.** PR + review quando `main` protegida (exceto hotfix autorizado)

---

## F. Deploy e produção

*(Aplicável quando missão afeta runtime Railway / painel / API.)*

- [ ] **F1.** Commit em `main` confirmado no GitHub
- [ ] **F2.** Deploy Railway iniciado ou confirmado
- [ ] **F3.** Commit implantado identificado (SHA curto)
- [ ] **F4.** Healthcheck produção OK (`/_stcore/health` ou `/health`)
- [ ] **F5.** CI gate relevante consultado (ex.: `railway-panel-deploy-gate`)
- [ ] **F6.** Veredicto deploy: `DEPLOYADO` / `EM ANDAMENTO` / `FALHOU`

**Sem impacto em produção:** marcar N/A.

---

## G. Encerramento

- [ ] **G1.** Veredicto final da matriz oficial selecionado (um único)
- [ ] **G2.** `QUADRO_MISSOES.md` atualizado
- [ ] **G3.** Entrada append em `REGISTRO_MISSOES.md`
- [ ] **G4.** Pendências remanescentes listadas (se houver)
- [ ] **G5.** Handoff para próxima missão documentado (se aplicável)

---

## H. Bloqueios — fail closed

Encerrar com veredicto **negativo** se qualquer item abaixo ocorrer sem correção:

| Bloqueio | Veredicto típico |
|----------|------------------|
| Código em produção referencia arquivo não versionado | `RISCO DE PRODUÇÃO` |
| Push feito mas deploy quebrado | `DEPLOY AINDA QUEBRADO` |
| Escopo proibido violado | `MISSÃO BLOQUEADA` |
| Sem commit quando houve alteração de código | `EVIDÊNCIA GIT AUSENTE` |
| Geração/purge executados fora de missão autorizada | `VIOLAÇÃO DE GOVERNANÇA` |

---

## Modelo de preenchimento (rodapé)

```yaml
mission_id:
owner:
data_abertura:
data_encerramento:
commits: []
testes: "comando + resultado"
deploy_sha:
veredicto:
checklist_preenchido_por: agent_governanca | agent_plataforma | ...
```
