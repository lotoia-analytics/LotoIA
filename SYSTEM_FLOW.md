# System Flow

## 1. Generation

The generation flow builds candidate games from the structural ranking logic.
It may optionally record lead metadata and historical context.

Operational outputs:

- generated numbers;
- ranking score;
- execution metadata;
- generation events;
- optional snapshots.

## 2. Conference

The conference flow validates a user-selected contest and set of numbers.
It records:

- contest identifier;
- hits;
- execution time;
- check events;
- optional audit trail entries.

## 3. Analytics

Analytics layers include:

- historical frequency;
- delay behavior;
- distribution;
- par/odd balance;
- sum behavior;
- recurrence analysis;
- pattern detection.

## 4. Reports

The report pipeline produces institutionally structured outputs:

- PDF reports;
- CSV exports;
- JSON payloads;
- chart artifacts;
- snapshot references.

## 5. Snapshots

Snapshots preserve institutional state across:

- generation;
- conference;
- analytics;
- ML calibration;
- model governance;
- observability events.

## 6. ML

The ML flow is governed by:

- leakage-free feature extraction;
- interpretable calibration;
- reranking;
- walk-forward validation;
- snapshots and model artifacts.

## 7. Observability

The observability flow records:

- runtime events;
- durations;
- statuses;
- contexts;
- audit trail;
- health metrics.

## Lifecycle Summary

The platform behaves as a controlled scientific system:

generation -> historical context -> ML reranking -> validation -> reporting -> observability -> audit.

