-- M-DADOS-066 — reset absoluto operacional (SQL de emergência Railway Postgres)
-- Executar no plugin Postgres → Query (após snapshot/backup Railway).
-- Preserva: imported_contests, lotofacil_official_history, governança constitucional.

BEGIN;

DELETE FROM reconciliation_games;
DELETE FROM expansion_events;
DELETE FROM institutional_validated_expansions;
DELETE FROM lotoia_client_generations;
DELETE FROM lotoia_client_conference_results;
DELETE FROM ml_usage_events;
DELETE FROM reconciliation_events;
DELETE FROM report_events;
DELETE FROM workflow_events;
DELETE FROM check_events;
DELETE FROM ml_diagnostic_decisions;
DELETE FROM reconciliation_runs;
DELETE FROM generated_games;
DELETE FROM institutional_output_signatures;
DELETE FROM generation_events;
DELETE FROM runtime_lineage;
DELETE FROM runtime_metrics;
DELETE FROM runtime_spans;
DELETE FROM runtime_snapshots;
DELETE FROM runtime_executions;
DELETE FROM workflow_steps;
DELETE FROM workflow_runs;

ALTER SEQUENCE IF EXISTS generation_events_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS generated_games_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS reconciliation_runs_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS reconciliation_games_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS institutional_output_signatures_id_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS ml_diagnostic_decisions_id_seq RESTART WITH 1;

COMMIT;

-- Validação pós-reset:
-- SELECT COUNT(*) FROM generation_events;        -- esperado: 0
-- SELECT COUNT(*) FROM generated_games;          -- esperado: 0
-- SELECT COUNT(*) FROM imported_contests;        -- preservado
-- SELECT last_value FROM generation_events_id_seq;
