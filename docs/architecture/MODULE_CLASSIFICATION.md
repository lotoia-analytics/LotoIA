# Module Classification

## Objetivo

Este documento classifica os modulos e superficies do LotoIA durante o
FREEZE ARQUITETURAL INSTITUCIONAL V1.

A classificacao e governanca estrutural. Ela nao altera codigo, nao cria features e nao
modifica a logica cientifica existente.

---

## Classes Oficiais

### Core

Modulo oficial do sistema, parte do namespace institucional, com responsabilidade validada
ou necessaria ao runtime atual.

### Experimental

Area de pesquisa, benchmark, dataset, manifesto ou prova controlada. Pode informar o core,
mas nao substitui comportamento oficial sem ADR, testes e validacao temporal.

### Overlap

Area que duplica ou pode confundir responsabilidade ja existente no core. Deve ser congelada
ate reconciliacao.

### Transitorio

Area operacional, historica, auxiliar, interface, relatorio, backup, diagnostico ou suporte.
Pode ser necessaria para uso atual, mas nao deve receber logica cientifica primaria.

---

## Classificacao do Namespace Oficial

| Modulo | Classe | Responsabilidade institucional |
| --- | --- | --- |
| `src/lotoia/statistics` | Core | Estatistica estrutural, combinacoes, padroes, scoring estatistico e logica temporal estatistica. |
| `src/lotoia/backtesting` | Core | Validacao historica temporalmente valida. |
| `src/lotoia/benchmark` | Core | Benchmark cientifico e comparacao reprodutivel. |
| `src/lotoia/generator` | Core | Geracao operacional baseada nos criterios oficiais existentes. |
| `src/lotoia/calibration` | Core | Calibracao interpretavel de pesos e suporte ao ranking. |
| `src/lotoia/models` | Core | Modelos de dominio simples e estruturas compartilhadas. |
| `src/lotoia/data` | Core | Carregamento de dados para o runtime oficial. |
| `src/lotoia/database` | Core | Repositorios e acesso persistente oficial. |
| `src/lotoia/reports` | Core | Geracao de relatorios oficiais a partir de resultados existentes. |
| `src/lotoia/config.py` | Core | Configuracao do runtime oficial. |
| `src/lotoia/environment.py` | Core | Resolucao de ambiente compativel com execucao e testes. |
| `src/lotoia/cli.py` | Core | Pontos de entrada oficiais declarados no `pyproject.toml`. |
| `src/lotoia/ml` | Experimental | Assistencia supervisionada incremental, interpretavel e subordinada ao benchmark. |
| `src/lotoia/experiments` | Experimental | Codigo de governanca experimental e registries supervisionados/temporais. |
| `src/lotoia/governance` | Experimental | Governanca institucional em consolidacao, sujeita a controle de escopo. |
| `src/lotoia/observability` | Transitorio | Observabilidade operacional sem autoridade cientifica. |
| `src/lotoia/reliability` | Transitorio | Confiabilidade operacional sem autoridade cientifica. |
| `src/lotoia/storage` | Transitorio | Armazenamento de artefatos, sujeito a reconciliacao com persistencia. |
| `src/lotoia/persistence` | Transitorio | Sincronizacao e persistencia distribuida, sujeito a boundary estrito. |

---

## Classificacao de Estruturas Fora do Core

| Superficie | Classe | Diretriz |
| --- | --- | --- |
| `experiments` | Experimental | Fonte de manifestos, datasets versionados e registries; nao e runtime central. |
| `tests` | Core | Validacao automatizada e contrato de compatibilidade. |
| `ADRs` | Core | Registro institucional de decisoes arquiteturais. |
| `docs` | Core | Documentacao institucional. |
| `reports` | Transitorio | Saidas geradas e relatorios; nao fonte de verdade runtime. |
| `snapshots` | Transitorio | Marcos institucionais historicos. |
| `data` | Transitorio | Persistencia de dados brutos, derivados e estatisticos. |
| `dashboard` | Transitorio | Interface visual; nao deve duplicar logica cientifica. |
| `backend` | Transitorio | API ou camada de exposicao; nao deve conter decisao estatistica primaria. |
| `scripts` | Transitorio | Orquestracao e automacao de fluxos existentes. |
| `notebooks` | Experimental | Exploracao; sem autoridade runtime. |
| `lotoia_runtime.py` | Transitorio | Adaptador operacional externo ao core modular. |
| `lotoia` | Overlap | Namespace paralelo ao oficial; deve permanecer congelado ate reconciliacao. |
| `src/database` | Overlap | Estrutura paralela a `src/lotoia/database`. |
| `src/statistics` | Overlap | Estrutura paralela a `src/lotoia/statistics`. |
| `src/ingestion` | Overlap | Ingestao paralela sem boundary institucional consolidado. |
| `audit` | Transitorio | Artefatos de auditoria. |
| `audit_full` | Transitorio | Artefatos de auditoria ampliada. |
| `diagnostico` | Transitorio | Diagnosticos estruturais. |
| `backups` | Transitorio | Backups e preservacao historica. |
| `codex_context` | Transitorio | Contexto auxiliar de trabalho. |

---

## Modulos Congelados por Risco de Overlap

Os seguintes caminhos nao devem receber expansao funcional durante o freeze:

```text
lotoia
src/database
src/statistics
src/ingestion
```

Qualquer uso futuro deve ser precedido por:

- inventario de conteudo;
- comparacao com o modulo oficial correspondente;
- plano de migracao ou aposentadoria;
- execucao de pytest;
- ADR de reconciliacao quando houver impacto arquitetural.

---

## Regra de Graduacao

Um modulo experimental so pode virar core quando atender a todos os criterios:

- responsabilidade unica e nao duplicada;
- testes automatizados;
- compatibilidade com benchmark;
- ausencia demonstrada de leakage temporal;
- manifestos ou versionamento quando houver dataset/modelo;
- documentacao institucional;
- ADR aceito.

---

## Regra de Aposentadoria

Um modulo overlap ou transitorio so pode ser removido, migrado ou consolidado quando:

- nao houver imports ativos dependentes;
- houver destino institucional claro;
- a suite pytest permanecer compativel;
- relatorios e scripts afetados forem mapeados;
- a decisao for registrada em ADR ou snapshot.
