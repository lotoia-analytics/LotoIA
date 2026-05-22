# ENTRYPOINT IMPORT POLICY

## Purpose

Define the import contract for Streamlit and dashboard entrypoints so the
LotoIA bootstrap remains lightweight, predictable, and resilient in production.

## Mandatory Rules

- Entrypoints must keep top-level imports light.
- Entrypoints must avoid eager loading of heavy subsystems.
- Entrypoints must not import generator, benchmark, backtesting, ML, telemetry
  engines, or reconciliation at module import time.
- Heavy subsystems must be loaded through lazy imports, provider injection, or
  runtime composition.
- Entrypoints must not execute side effects during import.
- Bootstrap validation must run in a clean process and remain fast.

## Preferred Patterns

- Local imports inside handler functions.
- Lazy package exports via `__getattr__`.
- Small bootstrap modules with explicit `main()` functions.
- Runtime composition for optional subsystems.

## Disallowed Patterns

- `from ... import ...` of heavy modules at the top of entrypoints.
- eager initialization of ML, benchmark, or reconciliation layers.
- import cascades that reach scientific cores before user action.
- startup tests that depend on external APIs or long-running workflows.

## Bootstrap Contract

Entrypoints should satisfy:

- clean cold start
- no import cascade into scientific heavy layers
- no observable side effects during import
- stable runtime handoff to the application main function

