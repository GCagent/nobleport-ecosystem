-- 002 — RBAC, truth states, evidence, moderation hooks
-- Backwards-compat: keeps existing audit_log rows valid (new cols nullable).

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    display     TEXT,
    role        TEXT NOT NULL CHECK (role IN ('admin','moderator','contractor','viewer')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api_keys (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash    CHAR(64) NOT NULL UNIQUE,  -- sha256 of raw key
    label       TEXT,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS api_keys_user_idx ON api_keys (user_id);

CREATE TABLE IF NOT EXISTS verifications (
    id              UUID PRIMARY KEY,
    address         TEXT NOT NULL,
    state           TEXT NOT NULL CHECK (state IN ('VERIFIED','DISPUTED','LEGAL_HOLD','REMOVED')),
    final_decision  TEXT NOT NULL,
    helius_status   TEXT,
    birdeye_status  TEXT,
    solscan_status  TEXT,
    moderation      JSONB,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS verifications_address_idx ON verifications (address);
CREATE INDEX IF NOT EXISTS verifications_state_idx ON verifications (state);

CREATE TABLE IF NOT EXISTS evidence (
    id              UUID PRIMARY KEY,
    verification_id UUID REFERENCES verifications(id) ON DELETE SET NULL,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    filename        TEXT NOT NULL,
    mime            TEXT NOT NULL,
    size_bytes      BIGINT NOT NULL,
    sha256          CHAR(64) NOT NULL,
    path            TEXT NOT NULL,
    note            TEXT,
    moderation      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS evidence_verification_idx ON evidence (verification_id);

-- Extend audit_log so it can record non-verify events while staying append-only.
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS kind TEXT;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_id UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS details JSONB;
ALTER TABLE audit_log ALTER COLUMN helius_status DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN birdeye_status DROP NOT NULL;
ALTER TABLE audit_log ALTER COLUMN solscan_status DROP NOT NULL;
UPDATE audit_log SET kind = 'verify' WHERE kind IS NULL;
