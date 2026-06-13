-- NoblePort MCP Gateway — sub-agents + compression telemetry
-- Migration: 003_subagents_compression
--
-- Adds the sub-agent topology (specialized workers under each main agent) and
-- the compression-packet measurements on the operational call log, so the
-- optimization is auditable rather than assumed.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sub-agent registry — specialists owned by a main agent.
CREATE TABLE IF NOT EXISTS mcp_subagent_registry (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parent_agent  TEXT NOT NULL,
    subagent_name TEXT NOT NULL,
    skill         TEXT NOT NULL,
    serves        TEXT[] NOT NULL DEFAULT '{}',
    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_parent_subagent UNIQUE (parent_agent, subagent_name)
);

-- Compression + delegation telemetry on each invocation.
ALTER TABLE mcp_call_log ADD COLUMN IF NOT EXISTS subagent_count INT;
ALTER TABLE mcp_call_log ADD COLUMN IF NOT EXISTS bytes_raw       INT;
ALTER TABLE mcp_call_log ADD COLUMN IF NOT EXISTS bytes_packed    INT;

CREATE INDEX IF NOT EXISTS idx_subagent_parent ON mcp_subagent_registry(parent_agent);
