-- NoblePort Systems orchestrator schema
-- Persistence for workflow runs, human-gate approvals, avatar sessions, and
-- the hash-chained audit log. The in-process engine is the source of truth
-- today; this schema is the durability layer it flushes into.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS workflow_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name   VARCHAR(64)  NOT NULL,
    state           VARCHAR(24)  NOT NULL DEFAULT 'RUNNING'
                    CHECK (state IN ('RUNNING','AWAITING_APPROVAL','COMPLETED',
                                     'REJECTED','FAILED')),
    cursor          INTEGER      NOT NULL DEFAULT 0,
    payload         JSONB        NOT NULL DEFAULT '{}',
    error           TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_runs_state ON workflow_runs (state);
CREATE INDEX IF NOT EXISTS idx_runs_name  ON workflow_runs (workflow_name);

CREATE TABLE IF NOT EXISTS workflow_step_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID         NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_index      INTEGER      NOT NULL,
    step_name       VARCHAR(64)  NOT NULL,
    module          VARCHAR(64)  NOT NULL,
    agent           VARCHAR(32)  NOT NULL,
    simulated       BOOLEAN      NOT NULL,
    output          JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (run_id, step_index)
);

CREATE TABLE IF NOT EXISTS approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID         NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    step_name       VARCHAR(64)  NOT NULL,
    module          VARCHAR(64)  NOT NULL,
    risk            VARCHAR(12)  NOT NULL CHECK (risk IN ('HIGH','CRITICAL')),
    summary         TEXT         NOT NULL DEFAULT '',
    state           VARCHAR(12)  NOT NULL DEFAULT 'PENDING'
                    CHECK (state IN ('PENDING','APPROVED','REJECTED')),
    resolved_by     VARCHAR(128),
    resolution_note TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_approvals_pending ON approvals (state)
    WHERE state = 'PENDING';

CREATE TABLE IF NOT EXISTS avatar_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona         VARCHAR(32)  NOT NULL DEFAULT 'stephanie',
    client_ip       INET,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS avatar_interactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID         NOT NULL REFERENCES avatar_sessions(id) ON DELETE CASCADE,
    message         TEXT         NOT NULL,
    response        TEXT         NOT NULL,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Append-only, hash-chained audit log; matches the pattern used by
-- noble-port-verification. entry_hash = sha256(prev_hash || payload).
CREATE TABLE IF NOT EXISTS audit_log (
    seq             BIGSERIAL PRIMARY KEY,
    run_id          UUID,
    module          VARCHAR(64),
    event           VARCHAR(64)  NOT NULL,
    payload         JSONB        NOT NULL DEFAULT '{}',
    prev_hash       CHAR(64),
    entry_hash      CHAR(64)     NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Guard: audit_log is append-only.
CREATE OR REPLACE FUNCTION forbid_audit_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_no_update ON audit_log;
CREATE TRIGGER audit_no_update
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();
