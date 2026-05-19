# Legacy Ingestion Namespace

`src/ingestion` is a compatibility namespace only.

Do not add new ingestion implementations here. Official ownership belongs to:

```text
src/lotoia/ingestion
```

Allowed content in this namespace:

- import redirects;
- compatibility adapters;
- explicit placeholders that point to the official owner.

Disallowed content:

- new providers;
- new validators;
- new sync pipelines;
- persistence logic;
- statistical or ML logic.
