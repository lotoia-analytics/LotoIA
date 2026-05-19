# Ingestion Ownership Policy

## Official Owner

The official ingestion domain is:

```text
src/lotoia/ingestion
```

All future ingestion work must be implemented inside the official owner.

## Legacy Namespace

The legacy namespace remains only for compatibility:

```text
src/ingestion
```

It must not receive new domain implementations. Files under `src/ingestion`
may only redirect to `lotoia.ingestion` or classify a transitional namespace.

## Validators

The official validators namespace is:

```text
src/lotoia/ingestion/validators
```

There are no public ingestion validators at this stage. The legacy validators
namespace exposes no validator API and exists only to prevent ambiguous empty
directories.

## Anti-Overlap Rule

New providers, validators, sync pipelines, persistence logic, statistical logic,
or ML logic are forbidden in `src/ingestion`.

The only accepted compatibility pattern is:

```python
from lotoia.ingestion.some_module import PublicName
```
