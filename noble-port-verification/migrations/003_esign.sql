-- 003 — e-signature ("Seal") module: open-source envelope signing.
-- Audit-first: every send/sign/decline/void also appends an audit_log row
-- (kind = esign_*) so signatures share the same tamper-evident hash chain.

CREATE TABLE IF NOT EXISTS envelopes (
    id              UUID PRIMARY KEY,
    subject         TEXT NOT NULL,
    message         TEXT,
    document_name   TEXT NOT NULL,
    document_mime   TEXT NOT NULL,
    document_sha256 CHAR(64) NOT NULL,
    document_path   TEXT NOT NULL,
    document_bytes  BIGINT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('DRAFT','SENT','COMPLETED','DECLINED','VOIDED')),
    routing         TEXT NOT NULL DEFAULT 'sequential' CHECK (routing IN ('sequential','parallel')),
    created_by      UUID NOT NULL REFERENCES users(id),
    voided_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at         TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS envelopes_status_idx ON envelopes (status);
CREATE INDEX IF NOT EXISTS envelopes_created_by_idx ON envelopes (created_by);

CREATE TABLE IF NOT EXISTS envelope_recipients (
    id                 UUID PRIMARY KEY,
    envelope_id        UUID NOT NULL REFERENCES envelopes(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'signer' CHECK (role IN ('signer','approver','viewer')),
    routing_order      INT  NOT NULL DEFAULT 1,
    status             TEXT NOT NULL CHECK (status IN ('PENDING','SIGNED','DECLINED')),
    access_token_hash  CHAR(64),               -- sha256 of one-time signing token
    consent_given      BOOLEAN NOT NULL DEFAULT FALSE,
    signature_hash     CHAR(64),               -- sha256(doc || signer || ts || consent)
    decline_reason     TEXT,
    signed_ip          TEXT,
    signed_at          TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS envelope_recipients_envelope_idx ON envelope_recipients (envelope_id);
CREATE UNIQUE INDEX IF NOT EXISTS envelope_recipients_token_idx
    ON envelope_recipients (access_token_hash) WHERE access_token_hash IS NOT NULL;
