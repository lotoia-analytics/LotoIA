# ADR 031 - Consolidacao Operacional Cientifica

Status: Accepted

## Context

The post-governance phase requires the current dashboard nuclei to stop behaving as
loosely named buttons and become officially separated scientific engines.

The platform must now expose:

- operational generation as a dedicated engine;
- structural expansion as a dedicated engine;
- temporal validation as a dedicated engine;
- temporal benchmark comparison as a dedicated engine;
- supervised reranking as a dedicated engine;
- institutional history as a dedicated engine;
- scientific persistence as a dedicated engine.

At the same time, the runtime and visual layer need to stop blending these nuclei into
ambiguous labels.

## Decision

LotoIA adopts a consolidated scientific nuclei registry for the CG-01 to CG-04 scope.

The registry formalizes:

1. **Core scientific nuclei**
   - `Gerar Jogos`
   - `Expansivo`
   - `Testar Estratégia`
   - `Comparativos`
   - `Ranking ML`
   - `Jogos Passados`
   - `Analíticas Persistidas`

2. **Visual differentiation**
   - sidebar groups are rendered by scientific purpose;
   - each nucleus gets a distinct visual identity;
   - support surfaces remain visibly separated from core engines.

3. **Runtime stability**
   - consolidated labels are backed by a governed registry;
   - dashboard titles are aligned to the scientific nuclei;
   - the runtime must keep these labels stable across reloads.

4. **Preparation for supervised score_ml**
   - the registry keeps the supervised reranking nucleus explicitly marked as
     score-ML-ready;
   - temporal validation, benchmark temporal, segregated datasets and anti-leakage
     remain mandatory prerequisites.

## Consequences

### Positive

- each nucleus becomes easier to reason about scientifically;
- the dashboard becomes less ambiguous for institutional users;
- runtime and visual naming now reflect the same governed model;
- the score_ml pathway is prepared without prematurely activating unsafeguarded ML.

### Trade-offs

- some UI labels and tests need to be updated when the governance model changes;
- the sidebar becomes more explicit and slightly more structured;
- the consolidation adds another registry object that must remain synchronized with the
  dashboard layer.

## Implementation Notes

The consolidated nuclei registry is implemented in:

- `src/lotoia/governance/scientific_nuclei_registry.py`

The dashboard consumes the registry through:

- `dashboard/labels.py`
- `dashboard/admin_app.py`

The registry is validated by dedicated tests to ensure:

- all core nuclei exist;
- labels are consistent with the scientific consolidation;
- score_ml readiness remains explicit;
- runtime stability and visual differentiation are preserved.

