-- M-MEMORY-001 — memória evolutiva de cobertura estrutural (Lei 001 / PostgreSQL)

CREATE TABLE IF NOT EXISTS operational_structural_memory (
    id SERIAL PRIMARY KEY,
    generation_event_id INTEGER NOT NULL REFERENCES generation_events(id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prefix_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    suffix_distribution JSONB NOT NULL DEFAULT '{}'::jsonb,
    official_divergence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    bias_alerts JSONB NOT NULL DEFAULT '[]'::jsonb,
    mission_id VARCHAR(32) NOT NULL DEFAULT 'M-MEMORY-001',
    memory_status VARCHAR(48) NOT NULL DEFAULT 'PERSISTED',
    coverage_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_operational_structural_memory_generation_event UNIQUE (generation_event_id)
);

CREATE INDEX IF NOT EXISTS ix_operational_structural_memory_recorded_at
    ON operational_structural_memory (recorded_at DESC);

CREATE INDEX IF NOT EXISTS ix_operational_structural_memory_generation_event_id
    ON operational_structural_memory (generation_event_id);

CREATE INDEX IF NOT EXISTS ix_operational_structural_memory_memory_status
    ON operational_structural_memory (memory_status);
