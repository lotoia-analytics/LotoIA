# Ingestion Final Consolidation Report

Data: 2026-05-18

## Objetivo

Encerrar a reconciliacao controlada do dominio ingestion sem alterar logica cientifica,
benchmark, ML, dashboard ou contratos publicos existentes.

## Decisao Institucional

Owner oficial unico:

```text
src/lotoia/ingestion
```

Namespace legado:

```text
src/ingestion
```

O namespace legado foi mantido apenas como adapter compativel. Novas implementacoes
de ingestion estao proibidas fora de `src/lotoia/ingestion`.

## Consolidacao Executada

### Owner oficial

Mantido e reforcado:

- `src/lotoia/ingestion/__init__.py`
- `src/lotoia/ingestion/sync.py`
- `src/lotoia/ingestion/providers/__init__.py`
- `src/lotoia/ingestion/providers/api_provider.py`

Adicionado placeholder institucional explicito:

- `src/lotoia/ingestion/validators/__init__.py`

Nao ha validators publicos neste momento. O namespace oficial existe apenas para
classificar o ponto de extensao futuro dentro do owner correto.

### Namespace legado

Mantido como camada minima de compatibilidade:

- `src/ingestion/__init__.py`
- `src/ingestion/sync.py`
- `src/ingestion/providers/__init__.py`
- `src/ingestion/providers/api_provider.py`
- `src/ingestion/validators/__init__.py`

O legado expoe somente redirects ou placeholders sem API publica nova.

### Validators vazios

Decisao: placeholder institucional explicito com redirect legado.

Motivo:

- evita diretorio vazio e ambiguo;
- nao remove contrato importavel potencial;
- impede interpretacao como area livre para novas implementacoes;
- preserva compatibilidade com import de `ingestion.validators`.

## Politica Anti-Overlap

Documentacao adicionada:

- `docs/architecture/INGESTION_OWNERSHIP.md`
- `src/ingestion/README.md`

Regras registradas:

- novas implementacoes devem entrar em `src/lotoia/ingestion`;
- `src/ingestion` aceita apenas adapters, redirects e placeholders classificados;
- providers, validators e pipelines novos sao proibidos no namespace legado;
- logica estatistica, persistencia e ML nao pertencem ao dominio ingestion legado.

## Cobertura Adicionada

Arquivo:

- `tests/test_ingestion_consolidation.py`

Coberturas institucionais:

- `lotoia.ingestion.sync.main`;
- `LotteryDataProvider.fetch_latest`;
- `LotteryDataProvider.fetch_contest`;
- redirects de `src/ingestion`;
- redirects de providers legados;
- neutralizacao explicita de `ingestion.validators`.

## Contratos Preservados

Contratos publicos mantidos:

- `ingestion.main`
- `ingestion.sync.main`
- `ingestion.LotteryDataProvider`
- `ingestion.providers.LotteryDataProvider`
- `ingestion.providers.api_provider.LotteryDataProvider`
- `ingestion.validators`

Contratos oficiais preservados:

- `lotoia.ingestion.main`
- `lotoia.ingestion.sync.main`
- `lotoia.ingestion.LotteryDataProvider`
- `lotoia.ingestion.providers.LotteryDataProvider`
- `lotoia.ingestion.providers.api_provider.LotteryDataProvider`

## Validacao

Comandos obrigatorios executados:

```bash
python -B -m compileall src
python -m pytest tests -q
```

Resultado:

- `compileall`: sucesso
- `pytest`: 239 passed
- Aviso residual: `PytestCacheWarning` por falta de permissao para escrita em `.pytest_cache`; sem regressao operacional.

## Estado Final

O dominio ingestion esta institucionalmente estabilizado:

- owner oficial unico preservado em `src/lotoia/ingestion`;
- namespace legado reduzido a compatibilidade minima;
- validators vazios classificados e neutralizados;
- documentacao anti-overlap registrada;
- cobertura minima institucional garantida;
- sem regressao operacional detectada.
