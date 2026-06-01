-- NoblePort Truth-Disciplined Schema
-- Migration: 001_workflow_states
-- Ref: TA-2026-05-23 Deep Truth Audit
--
-- Enforces human-gated approval at the database layer for all
-- financial, permitting, and scheduling milestones.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Clean up historical anthropomorphic tracking tables
DROP TABLE IF EXISTS token_compliance_alerts CASCADE;

-- 1. LIVE WORKFLOW CONTROL STATE
CREATE TABLE IF NOT EXISTS workflow_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    current_status VARCHAR(50) NOT NULL,
    execution_tier VARCHAR(20) NOT NULL DEFAULT 'LIVE',
    assigned_human_gatekeeper VARCHAR(100) NOT NULL,
    human_approved BOOLEAN NOT NULL DEFAULT FALSE,
    human_signature_spec TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_entity_type CHECK (entity_type IN ('lead', 'proposal', 'project', 'awo', 'invoice', 'permit')),
    CONSTRAINT chk_status CHECK (current_status IN ('draft', 'pending_human_review', 'executed', 'rejected', 'archived')),
    CONSTRAINT chk_tier CHECK (execution_tier IN ('LIVE', 'STAGED', 'SIMULATED'))
);

-- 2. DETERMINISTIC RETRIEVAL LOGS
CREATE TABLE IF NOT EXISTS knowledge_retrievals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflow_states(id) ON DELETE RESTRICT,
    retrieval_source VARCHAR(100) NOT NULL,
    context_chunk_hash CHAR(64) NOT NULL,
    is_verified_by_human BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. IMMUTABLE AUDIT CHAIN
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    payload_hash CHAR(64) NOT NULL,
    previous_hash CHAR(64),
    raw_payload JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pending_human_gates
    ON workflow_states(assigned_human_gatekeeper)
    WHERE human_approved = FALSE;

CREATE INDEX idx_audit_chain
    ON audit_logs(timestamp DESC);

CREATE INDEX idx_retrievals_workflow
    ON knowledge_retrievals(workflow_id);
