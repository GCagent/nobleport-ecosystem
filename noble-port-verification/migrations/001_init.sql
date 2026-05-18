CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY,
    address         TEXT NOT NULL,
    helius_status   TEXT NOT NULL,
    birdeye_status  TEXT NOT NULL,
    solscan_status  TEXT NOT NULL,
    final_decision  TEXT NOT NULL,
    reason          TEXT,
    prev_hash       CHAR(64) NOT NULL,
    row_hash        CHAR(64) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_address_idx ON audit_log (address);
CREATE INDEX IF NOT EXISTS audit_log_created_at_idx ON audit_log (created_at DESC);
