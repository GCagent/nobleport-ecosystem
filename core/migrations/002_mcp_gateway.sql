-- NoblePort MCP Gateway Schema
-- Migration: 002_mcp_gateway
-- Ref: Internal MCP architecture spec — Stephanie.ai front door,
--      GCagent.ai / PermitStream.ai / Cyborg.ai / Borg.ai / Kuzo.io servers.
--
-- Truth discipline: every module defaults to BLOCKED until a real source
-- table is wired into the KPI snapshot worker. No fake green lights.
-- Audit discipline: no state change executes before an AuditBeacon pre-write.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. AGENT REGISTRY — the five internal MCP servers behind the gateway.
CREATE TABLE IF NOT EXISTS mcp_agent_registry (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name   TEXT UNIQUE NOT NULL,
    endpoint     TEXT NOT NULL,
    owner_domain TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'staged',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_agent_status CHECK (status IN ('staged', 'live', 'disabled'))
);

-- 2. TOOL REGISTRY — every tool each agent exposes, with its approval level.
CREATE TABLE IF NOT EXISTS mcp_tool_registry (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name     TEXT NOT NULL,
    tool_name      TEXT NOT NULL,
    module_name    TEXT NOT NULL,
    approval_level TEXT NOT NULL,
    write_capable  BOOLEAN NOT NULL DEFAULT FALSE,
    audit_required BOOLEAN NOT NULL DEFAULT TRUE,
    enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_agent_tool UNIQUE (agent_name, tool_name),
    CONSTRAINT chk_approval_level CHECK (approval_level IN ('L0', 'L1', 'L2', 'L3', 'L4'))
);

-- 3. MODULE REGISTRY — the 50 NoblePort modules and the source each KPI needs.
CREATE TABLE IF NOT EXISTS nobleport_module_registry (
    module_id        INT PRIMARY KEY,
    module_name      TEXT NOT NULL,
    owner_agent      TEXT NOT NULL,
    kpi_name         TEXT NOT NULL,
    source_table     TEXT,
    truth_label      TEXT NOT NULL DEFAULT 'BLOCKED',
    last_verified_at TIMESTAMPTZ,
    CONSTRAINT chk_module_truth CHECK (truth_label IN ('LIVE', 'MODELED', 'BLOCKED'))
);

-- 4. CALL LOG — operational ledger, one row per gateway invocation.
CREATE TABLE IF NOT EXISTS mcp_call_log (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id           UUID NOT NULL,
    requesting_agent TEXT NOT NULL,
    target_agent     TEXT NOT NULL,
    module_name      TEXT NOT NULL,
    tool_name        TEXT NOT NULL,
    project_id       TEXT,
    truth_label      TEXT NOT NULL,
    approval_level   TEXT,
    status           TEXT NOT NULL,
    latency_ms       INT,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. KPI SNAPSHOT — append-only. The worker inserts; it never overwrites history.
CREATE TABLE IF NOT EXISTS kpi_snapshot (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id   INT NOT NULL REFERENCES nobleport_module_registry(module_id),
    kpi_name    TEXT NOT NULL,
    kpi_value   NUMERIC,
    kpi_unit    TEXT,
    truth_label TEXT NOT NULL,
    source_ref  TEXT,
    reason      TEXT,
    measured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_snapshot_truth CHECK (truth_label IN ('LIVE', 'MODELED', 'BLOCKED'))
);

-- 6. KILL SWITCH — fail-closed global / per-agent execution halt.
--    Redis holds the hot flag; this table is the durable, audited record.
CREATE TABLE IF NOT EXISTS kill_switch_events (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope      TEXT NOT NULL,              -- 'global' or an agent_name
    engaged    BOOLEAN NOT NULL,
    actor      TEXT NOT NULL,
    reason     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mcp_call_log_created   ON mcp_call_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mcp_call_log_run       ON mcp_call_log(run_id);
CREATE INDEX IF NOT EXISTS idx_mcp_call_log_latency   ON mcp_call_log(created_at DESC) WHERE latency_ms IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kpi_snapshot_module    ON kpi_snapshot(module_id, measured_at DESC);
CREATE INDEX IF NOT EXISTS idx_kill_switch_scope      ON kill_switch_events(scope, created_at DESC);
