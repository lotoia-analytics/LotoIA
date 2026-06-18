# Política de Missões por Pacote — LotoIA

## Status

`POLITICA_MISSOES_POR_PACOTE_FASE_0`

Complementa `POLITICA_GESTAO_PROJETOS_LOTOIA.md` e `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`.

---

## 1. Propósito

Reduzir micro-missões e burocracia quando o risco for **baixo/médio**, agrupando entregas
relacionadas em **pacotes** com uma PR, classificação de risco única e veredicto proporcional.

---

## 2. Definição de pacote

**Pacote** = conjunto de entregas de um ou mais agentes, em branch única (ex.:
`cursor/rodada-multiagente-painel-core002-cae6`), com:

- escopo escrito no cartão/registro;
- classificação de risco do pacote (não só de cada micro-tarefa);
- checklist único;
- PR única para review institucional.

---

## 3. Classificação de risco

| Nível | Perfil | Exemplos | PR/merge |
|-------|--------|----------|----------|
| **Baixo** | Documental, read-only, sem deploy sensível | Governança, fechamento doc, captions | PR + review; merge após checklist |
| **Médio** | Visual read-only, testes, build marker bump | Governança ADM, menus informativos | PR + testes; evidência leve pós-deploy |
| **Alto** | Deploy pós-incidente, auth, entrypoint, API exposta | Segregação public_app, rotas generate | Autorização manual + evidência reforçada |
| **Crítico** | Geração, purge, banco/schema, Núcleo, ML operacional | Qualquer bypass Lei 15 | **Parar** — ADR + decisão institucional |

Referência completa: `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`.

---

## 4. Fechamento documental no mesmo PR

Para missões **baixo/médio risco**, o **fechamento documental** (cartão, registro, quadro) pode
entrar no **mesmo PR** da implantação, quando:

- escopo foi exclusivamente documental ou read-only;
- testes passaram (ou N/A justificado);
- evidência de produção segue política de checkpoint simplificado;
- não há bloqueio constitucional aberto.

Exemplos: M-VIS-031/M-VIS-032 fechamentos; M-GOV-031 política.

---

## 5. Autorização manual vs automática

| Situação | Autorização |
|----------|-------------|
| Pacote baixo/médio risco, checklist OK | PR aberta — merge após review institucional |
| Pacote alto risco | Autorização manual explícita antes do merge |
| Pacote crítico ou conflito constitucional | **Exige decisão institucional** — não mergear |
| Rodada multiagente com subfluxo bloqueado | Demais agentes podem concluir; subfluxo aguarda decisão |

---

## 6. Referências

- `POLITICA_GESTAO_PROJETOS_LOTOIA.md`
- `POLITICA_CHECKPOINT_PRODUCAO_LOTOIA.md`
- `DIRETRIZ_EXECUCAO_MULTIAGENTE_LOTOIA.md`
