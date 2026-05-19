# Architectural Audit Reconciliation V2

Data: 2026-05-18

## Escopo

Auditoria especifica dos overlaps estruturais reconciliados:

- `src/database`
- `src/statistics`
- `src/ingestion`
- namespace paralelo `lotoia/`

Esta auditoria nao implementou mudancas de codigo. Foram executadas apenas validacoes, rastreamento de imports, inspecao estrutural e validacao operacional.

## Resultado Executivo

| Dominio | Classificacao | Conclusao |
| --- | --- | --- |
| Database | RESOLVIDO | Ownership oficial esta em `src/lotoia/database`; `src/database` atua como adapter legado. |
| Statistics | RESOLVIDO | Logica oficial esta em `src/lotoia/statistics`; `src/statistics/feature_store.py` e apenas adapter. |
| Ingestion | PARCIALMENTE RESOLVIDO | Pipeline oficial existe em `src/lotoia/ingestion`; legado virou adapter, mas permanecem diretorios transitorios e baixa cobertura explicita de ingestion. |
| Namespace paralelo `lotoia/` | RISCO FUTURO | O diretorio raiz ainda existe e pode sombrear o pacote oficial sem bootstrap/PYTHONPATH correto. |

## Evidencias de Imports Reais

Imports ativos de runtime, dashboard, scripts e testes apontam para o namespace institucional:

- `lotoia.database`
- `lotoia.statistics`
- `lotoia.backtesting`
- `lotoia.benchmark`
- `lotoia.ml`
- `lotoia.experiments`

Imports legados detectados ficam restritos aos proprios adapters:

- `src/database/__init__.py`
- `src/database/contest_repository.py`
- `src/statistics/feature_store.py`
- `src/ingestion/__init__.py`
- `src/ingestion/sync.py`
- `src/ingestion/providers/__init__.py`
- `src/ingestion/providers/api_provider.py`

Nao foram encontrados imports ativos de aplicacao/testes consumindo diretamente `database.*`, `statistics.feature_store` ou `ingestion.*` fora dos adapters.

## 1. Database

Classificacao: RESOLVIDO

### Verificacoes

- `src/lotoia/database` e o owner oficial.
- `src/database` existe apenas como camada legacy/transitoria.
- `src/database/contest_repository.py` reexporta `lotoia.database.contest_repository.ContestRepository`.
- `src/database/__init__.py` reexporta o mesmo owner oficial.
- Persistencia operacional de benchmark, backtesting e calibracao segue centralizada em `src/lotoia/database/database.py` e `src/lotoia/database/repository.py`.

### Duplicacao de repositories

Nao ha duplicacao estrutural concorrente fora do namespace oficial. Ha dois papeis dentro do owner oficial:

- `repository.py`: persistencia de runs institucionais.
- `contest_repository.py`: API legada de contests/frequency snapshots, agora sob ownership oficial.

Essa coexistencia nao quebra ownership, mas deve ser monitorada para nao virar novo paralelismo.

### Risco residual

RISCO FUTURO: `ContestRepository` usa `sqlite3` direto enquanto o restante da persistencia institucional usa SQLAlchemy. Como ambos estao em `src/lotoia/database`, isso nao e overlap de namespace, mas ainda e uma heterogeneidade de persistencia a governar.

## 2. Statistics

Classificacao: RESOLVIDO

### Verificacoes

- `src/lotoia/statistics` permanece como dominio estatistico oficial.
- `src/lotoia/statistics/feature_store.py` contem a implementacao oficial de `FeatureStore`.
- `src/statistics/feature_store.py` e apenas adapter para `lotoia.statistics.feature_store.FeatureStore`.
- Nao ha `src/statistics/__init__.py` ativo, evitando colisao com a biblioteca padrao `statistics`.
- Imports institucionais de estatistica continuam em `lotoia.statistics.*`.

### Duplicacoes e redundancias

Nao foram encontradas funcoes estatisticas redundantes ativas entre `src/statistics` e `src/lotoia/statistics`. O unico residuo e o adapter legado `feature_store.py`.

### Risco residual

RISCO FUTURO baixo: se `src/statistics/__init__.py` for recriado, pode sombrear `from statistics import pstdev`, usado por benchmark, reports, calibrator e database repository.

## 3. Ingestion

Classificacao: PARCIALMENTE RESOLVIDO

### Verificacoes

- `src/lotoia/ingestion` foi criado como namespace oficial.
- `LotteryDataProvider` oficial esta em `src/lotoia/ingestion/providers/api_provider.py`.
- `sync.main` oficial esta em `src/lotoia/ingestion/sync.py`.
- `src/ingestion` e `src/ingestion/providers` reexportam os owners oficiais.
- `src/ingestion/validators` permanece vazio, sem validators redundantes ativos.

### Pipelines paralelos

Nao ha pipeline paralelo funcional em `src/ingestion`; o caminho legado chama `lotoia.ingestion.sync.main`.

### Providers duplicados

Nao ha provider concorrente ativo. O provider legado e adapter para o provider oficial.

### Risco residual

RISCO FUTURO: `src/ingestion` e `src/ingestion/validators` continuam existindo como estrutura transitoria. Embora nao executem logica propria hoje, podem induzir novas implementacoes fora do owner oficial se a regra institucional nao for mantida.

RISCO FUTURO: `src/lotoia/ingestion/sync.py` instancia `LotteryDataProvider`, mas o fluxo atual nao usa o provider durante o snapshot. Isso preserva o comportamento legado, mas indica que ingestion ainda nao esta plenamente governada por testes especificos.

## 4. Namespace Paralelo `lotoia/`

Classificacao: RISCO FUTURO

### Verificacoes

Existe namespace paralelo fora do src-layout:

- `lotoia/ml/__init__.py`
- `lotoia/ml/rerank.py`
- `lotoia/ml/README.txt`

Nao existe `lotoia/__init__.py`, portanto a raiz atua como namespace package quando o diretorio do projeto esta em `sys.path`.

### Risco de shadowing

Sem bootstrap, a resolucao de namespace encontra o diretorio raiz:

```text
ModuleSpec(name='lotoia', loader=None, submodule_search_locations=_NamespacePath(['C:\\Projetos\\LotoIA\\lotoia']))
```

Com `ensure_src_layout()`, a resolucao institucional e correta:

```text
C:\Projetos\LotoIA\src\lotoia\__init__.py
['C:\\Projetos\\LotoIA\\src\\lotoia']
```

Com `PYTHONPATH=src`, a resolucao tambem e correta:

```text
C:\Projetos\LotoIA\src\lotoia\__init__.py
```

### Conclusao

Operacionalmente, runtime e testes estao protegidos pelo src-layout e bootstrap. Estruturalmente, a existencia de `lotoia/` na raiz ainda e uma ambiguidade real de PYTHONPATH e deve permanecer marcada como risco futuro ate ser removida ou formalmente neutralizada.

## 5. Runtime Institucional

Classificacao: RESOLVIDO com risco localizado no namespace paralelo

Validacoes executadas:

- `ensure_src_layout()` resolve `src/lotoia/__init__.py`.
- `PYTHONPATH=src` resolve `src/lotoia/__init__.py`.
- `from statistics import pstdev` resolve a biblioteca padrao corretamente.
- Adapter `database.contest_repository.ContestRepository` e o mesmo objeto de `lotoia.database.contest_repository.ContestRepository`.
- Adapter `ingestion.sync.main` e o mesmo objeto de `lotoia.ingestion.sync.main`.

## Validacao Operacional Obrigatoria

Comandos executados:

```bash
python -B -m compileall src
python -m pytest tests -q
```

Resultado:

- `compileall`: sucesso
- `pytest`: 235 passed
- Aviso: `PytestCacheWarning` por falta de permissao para escrita em `.pytest_cache`; sem regressao operacional.

## Conclusao Final

A reconciliacao estabilizou os overlaps de `database`, `statistics` e `ingestion` no uso operacional e nos imports ativos.

Estado institucional:

- `src/lotoia/database`: RESOLVIDO
- `src/lotoia/statistics`: RESOLVIDO
- `src/lotoia/ingestion`: PARCIALMENTE RESOLVIDO
- `lotoia/` raiz: RISCO FUTURO

Nao ha regressao operacional detectada. O principal residuo arquitetural real e o namespace paralelo `lotoia/` fora do src-layout, que continua capaz de causar shadowing quando o projeto e executado sem bootstrap ou sem `PYTHONPATH=src`.
