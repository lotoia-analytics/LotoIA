# Expansion Policy

## Objetivo

Esta politica define como a arquitetura do LotoIA pode evoluir apos o
FREEZE ARQUITETURAL INSTITUCIONAL V1.

Para expansao **dimensional de cartao** (15D → 23D) no runtime institucional Lei 15 / Lei 15A,
ver tambem `docs/governance/ADR_EXPANSAO_DIMENSIONAL_16D_23D.md` (DOC-001).

Durante o freeze, esta politica serve como regra de bloqueio: expansoes nao aprovadas nao
devem ser implementadas.

---

## Principio Central

O LotoIA nao cresce por adicao horizontal espontanea de modulos.

Toda expansao deve preservar:

- modularidade;
- separacao entre estatistica e persistencia;
- validade temporal;
- benchmark cientifico;
- interpretabilidade;
- reproducibilidade;
- compatibilidade com pytest;
- classificacao institucional de modulos.

---

## Expansoes Bloqueadas por Padrao

Sao bloqueadas ate aprovacao formal:

- novos pacotes dentro de `src/lotoia`;
- novos namespaces paralelos;
- duplicacao de `statistics`, `database`, `ml`, `benchmark` ou `experiments`;
- novos fluxos de scoring;
- novos modelos supervisionados;
- novas persistencias que alterem contratos de dados;
- dashboards ou APIs que implementem logica cientifica propria;
- scripts que contornem core, benchmark ou governanca temporal.

---

## Fluxo Obrigatorio de Expansao

Toda expansao arquitetural deve seguir este fluxo:

1. Declarar problema institucional.
2. Confirmar que nenhum modulo core atual ja possui a responsabilidade.
3. Classificar a proposta como core, experimental, transitoria ou reconciliacao.
4. Mapear impacto temporal, cientifico e de persistencia.
5. Definir testes necessarios.
6. Definir benchmark quando houver comportamento cientifico.
7. Definir versionamento de datasets/modelos quando aplicavel.
8. Criar ADR antes da implementacao.
9. Implementar de forma incremental e rastreavel.
10. Executar pytest.
11. Registrar relatorio, snapshot ou documento de governanca quando aplicavel.

---

## Criterios para Novo Modulo Core

Um novo modulo core so pode ser criado quando:

- nao houver modulo existente com a mesma responsabilidade;
- a responsabilidade for estavel e institucional;
- a boundary for clara;
- a interface com outros modulos for minima;
- nao houver dependencia de dashboard, scripts ou notebooks;
- houver testes;
- houver documentacao;
- houver ADR aprovado.

Preferencia institucional:

```text
expandir um modulo existente com boundary clara > criar novo modulo core
```

---

## Criterios para Modulo Experimental

Um modulo experimental deve:

- viver em area claramente experimental;
- declarar manifestos quando produzir dataset, modelo ou benchmark;
- nao substituir comportamento oficial;
- nao ser importado como dependencia obrigatoria do core sem ADR;
- declarar riscos de leakage;
- usar validacao walk-forward quando supervisionado.

Areas preferenciais:

```text
experiments
src/lotoia/experiments
```

---

## Criterios para Reconciliacao Sandbox x Core

Toda reconciliacao deve ser tratada como mudanca institucional.

O plano minimo deve conter:

- caminho sandbox de origem;
- caminho core de destino;
- responsabilidades duplicadas;
- imports afetados;
- testes afetados;
- dados ou artefatos afetados;
- risco temporal;
- criterio de aceite;
- estrategia de rollback sem perda de historico.

Durante reconciliacao, e proibido:

- mover logica cientifica sem teste;
- alterar algoritmo junto com migracao estrutural;
- mudar persistencia e estatistica no mesmo passo sem ADR especifico;
- apagar artefatos historicos sem snapshot ou registro.

---

## Politica de Anti-Overlap

Quando houver disputa de responsabilidade:

- estatistica pertence a `src/lotoia/statistics`;
- benchmark pertence a `src/lotoia/benchmark`;
- backtesting pertence a `src/lotoia/backtesting`;
- ML incremental pertence a `src/lotoia/ml`;
- governanca experimental pertence a `src/lotoia/experiments` e `experiments`;
- persistencia pertence a `src/lotoia/database`, `src/lotoia/data`, `src/lotoia/storage`
  ou `src/lotoia/persistence`, conforme boundary declarada;
- interface pertence a `dashboard` ou `backend`, sem logica cientifica primaria.

Nenhum modulo pode criar uma segunda fonte de verdade.

---

## Checklist de Aprovacao

Antes de qualquer expansao, responder:

- Existe ADR?
- Existe boundary clara?
- Existe modulo core que ja deveria receber a responsabilidade?
- Existe risco de overlap?
- Existe risco de leakage temporal?
- Existe benchmark quando a mudanca altera comportamento cientifico?
- Existe versionamento de dataset/modelo quando aplicavel?
- A suite pytest atual permanece compativel?
- A mudanca evita crescimento horizontal descontrolado?

Se qualquer resposta critica for negativa, a expansao deve ser bloqueada.

---

## Politica Durante o Freeze V1

Enquanto o freeze estiver vigente, apenas sao aceitas mudancas de:

- documentacao;
- ADR;
- inventario;
- classificacao;
- governanca estrutural sem runtime;
- testes de compatibilidade sem mudanca de comportamento.

Qualquer outra mudanca deve aguardar encerramento formal do freeze ou ADR especifico de
excecao.
