# Architectural Reconciliation Report V2

Data: 2026-05-18

## Objetivo

Executar reconciliacao arquitetural controlada nos overlaps:

- `src/database`
- `src/statistics`
- `src/ingestion`
- namespace paralelo `lotoia/`

O criterio adotado foi estabilidade institucional acima de limpeza agressiva: nenhum contrato publico foi removido, nenhuma logica cientifica foi alterada e os caminhos legados foram preservados por adapters minimos.

## Mapeamento de Dependencias

### Imports institucionais ativos

O runtime, dashboard, benchmark, ML e testes usam majoritariamente o namespace oficial:

- `lotoia.database`
- `lotoia.statistics`
- `lotoia.ingestion` passou a existir como owner oficial do pipeline legado
- `lotoia.ml`
- `lotoia.backtesting`
- `lotoia.benchmark`
- `lotoia.reports`
- `lotoia.experiments`

### Imports legados identificados

- `src/database/contest_repository.py`
- `src/statistics/feature_store.py`
- `src/ingestion/sync.py`
- `src/ingestion/providers/api_provider.py`

Esses modulos formavam uma trilha paralela de ingestao/persistencia/features fora do namespace institucional `src/lotoia`.

### Namespace paralelo fora do src-layout

Foi identificado `lotoia/ml/rerank.py` fora de `src/lotoia`.

Classificacao: adapter transitorio ja existente. Ele aponta para a implementacao oficial em `src/lotoia/ml/rerank.py`. Nao foi expandido nem promovido. O bootstrap institucional continua sendo `lotoia_runtime.ensure_src_layout()`, validado por testes.

## Classificacao

| Area | Estado anterior | Classificacao | Decisao |
| --- | --- | --- | --- |
| `src/lotoia/database` | Namespace oficial parcial | Institucional valido | Mantido como owner oficial |
| `src/database` | Implementacao paralela SQLite | Legacy/transitorio | Convertido para adapter |
| `src/lotoia/statistics` | Namespace oficial | Institucional valido | Mantido como owner oficial |
| `src/statistics` | FeatureStore paralelo | Legacy/transitorio com risco de conflito stdlib | Convertido para adapter de modulo, sem `__init__.py` |
| `src/ingestion` | Pipeline paralelo | Overlap | Convertido para adapter |
| `src/lotoia/ingestion` | Ausente | Owner oficial necessario | Criado com logica preservada |
| `lotoia/` raiz | Namespace paralelo parcial | Legacy/transitorio | Preservado como adapter existente, sem ampliar superficie |

## Consolidacao Executada

### Database

Owner oficial consolidado em:

- `src/lotoia/database/contest_repository.py`

Adapter legado preservado em:

- `src/database/contest_repository.py`
- `src/database/__init__.py`

`ContestRepository` tambem foi reexportado em `src/lotoia/database/__init__.py`.

### Statistics

Owner oficial consolidado em:

- `src/lotoia/statistics/feature_store.py`

Adapter legado preservado em:

- `src/statistics/feature_store.py`

Observacao importante: `src/statistics/__init__.py` nao foi mantido porque quebraria `from statistics import pstdev`, sombreando a biblioteca padrao usada por benchmark, reports, calibrator e repository. A compatibilidade segura permanece no nivel do arquivo legado, sem transformar `statistics` em pacote top-level.

### Ingestion

Owner oficial criado em:

- `src/lotoia/ingestion/__init__.py`
- `src/lotoia/ingestion/sync.py`
- `src/lotoia/ingestion/providers/__init__.py`
- `src/lotoia/ingestion/providers/api_provider.py`

Adapters legados preservados em:

- `src/ingestion/__init__.py`
- `src/ingestion/sync.py`
- `src/ingestion/providers/__init__.py`
- `src/ingestion/providers/api_provider.py`

O fluxo de `sync` foi mantido equivalente ao legado. Nao foi introduzido fetch automatico, nova regra de ingestao, nova validacao temporal ou alteracao cientifica.

## Decisoes de Controle

- Nao houve refactor massivo.
- Nao houve remocao de modulos legados com dependencias potenciais.
- Nao houve alteracao de contratos publicos existentes.
- Nao houve alteracao de logica estatistica, ML, benchmark ou backtesting.
- Caminhos legados foram preservados como reexports controlados.
- O risco de conflito com a stdlib `statistics` foi evitado deliberadamente.

## Validacao

Comandos obrigatorios executados:

```bash
python -B -m compileall src
python -m pytest tests -q
```

Resultado:

- `compileall`: sucesso
- `pytest`: 235 testes passaram
- Aviso residual: `PytestCacheWarning` por falta de permissao para escrita em `.pytest_cache`; sem falha funcional.

## Estado Final

- Namespace institucional unico preservado: `src/lotoia`.
- `src/lotoia/database` e `src/lotoia/statistics` sao owners oficiais.
- `src/lotoia/ingestion` passa a ser owner oficial do pipeline de ingestao existente.
- `src/database`, `src/statistics` e `src/ingestion` permanecem apenas como compatibilidade transitoria.
- Namespace paralelo `lotoia/` fora de `src` permanece classificado como legado/transitorio e nao deve receber novas implementacoes.
