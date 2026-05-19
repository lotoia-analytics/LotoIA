# Namespace Reconciliation Report

Data: 2026-05-18

## Objetivo

Eliminar o risco estrutural do namespace paralelo:

```text
lotoia/
```

sem alterar ML, benchmark, dashboard, backtesting, bootstrap institucional ou
contratos publicos existentes.

## Auditoria do Namespace Paralelo

O diretorio raiz `lotoia/` continha apenas compatibilidade transitoria:

- `lotoia/ml/rerank.py`
- `lotoia/ml/__init__.py`
- `lotoia/ml/README.txt`

`lotoia/ml/rerank.py` era um shim que carregava a implementacao oficial em:

```text
src/lotoia/ml/rerank.py
```

Nao havia logica ML institucional propria no diretorio raiz. O uso real de ML,
benchmark, dashboard e testes ja estava baseado no namespace oficial
`src/lotoia`.

## Consolidacao Executada

### Remocao segura

O diretorio paralelo `lotoia/` foi removido fisicamente.

Resultado validado:

```text
Test-Path lotoia -> False
```

### Fallback controlado

Foi adicionado `lotoia.py` na raiz como fallback minimo para execucoes feitas a
partir do diretorio do projeto sem bootstrap explicito e sem `PYTHONPATH=src`.

Esse arquivo:

- nao implementa dominio;
- nao duplica ML;
- nao cria subpacotes;
- nao contem logica cientifica;
- carrega `src/lotoia/__init__.py`;
- define `__path__` para `src/lotoia`;
- faz `import lotoia` se identificar como o pacote oficial.

Assim, o fallback preserva compatibilidade operacional sem recriar o namespace
paralelo em forma de diretorio.

## Validacoes de Resolucao

### Import nu a partir da raiz do projeto

```text
import lotoia
Path(lotoia.__file__).resolve()
-> C:\Projetos\LotoIA\src\lotoia\__init__.py
```

### Com bootstrap institucional

```text
from lotoia_runtime import ensure_src_layout
ensure_src_layout()
import lotoia
Path(lotoia.__file__).resolve()
-> C:\Projetos\LotoIA\src\lotoia\__init__.py
```

### Com PYTHONPATH=src

```text
PYTHONPATH=src
import lotoia
Path(lotoia.__file__).resolve()
-> C:\Projetos\LotoIA\src\lotoia\__init__.py
```

### ML oficial preservado

```text
import lotoia.ml.rerank
lotoia.ml.rerank.rerank_games.__name__
-> rerank_games
```

O modulo e resolvido a partir de `src/lotoia/ml/rerank.py`.

## Cobertura Adicionada

Arquivo:

- `tests/test_namespace_reconciliation.py`

Coberturas:

- ausencia fisica do diretorio paralelo `lotoia/`;
- `import lotoia` aponta para `src/lotoia/__init__.py`;
- `ensure_src_layout()` preserva o owner oficial;
- import nu a partir da raiz do projeto resolve o pacote oficial;
- `PYTHONPATH=src` resolve o pacote oficial.

## Contratos Preservados

Preservado:

- `import lotoia`
- `import lotoia.ml.rerank`
- `from lotoia.ml.rerank import rerank_games`
- `lotoia_runtime.ensure_src_layout`

Removido:

- namespace package paralelo `lotoia/`
- shim transitorio `lotoia/ml/rerank.py`

## Validacao Obrigatoria

Comandos executados:

```bash
python -B -m compileall src
python -m pytest tests -q
```

Resultado:

- `compileall`: sucesso
- `pytest`: 244 passed
- Aviso residual: `PytestCacheWarning` por falta de permissao de escrita em
  `.pytest_cache`; sem regressao operacional.

## Estado Final

O src-layout institucional esta estabilizado:

- `src/lotoia` e o owner oficial unico;
- o diretorio paralelo `lotoia/` foi eliminado;
- imports com bootstrap resolvem o pacote oficial;
- imports com `PYTHONPATH=src` resolvem o pacote oficial;
- import nu a partir da raiz do projeto tambem resolve o pacote oficial;
- ML, benchmark, dashboard e backtesting permanecem intactos.
