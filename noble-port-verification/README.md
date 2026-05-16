# NoblePort Verification Engine

Fail-closed, audit-first verification gateway for Solana addresses.
Combines three independent data layers and gates execution behind a
unified decision:

- **Helius** — identity / structural legitimacy
- **Birdeye** — liquidity / execution viability
- **Solscan** — behavioral / forensic audit

A decision is **PASS**, **HOLD**, or **BLOCK**. Missing data is BLOCK.
No log = no go.

## Quickstart

```bash
cp .env.example .env       # fill API keys
docker compose up --build
curl -X POST http://localhost:8080/verify \
     -H 'content-type: application/json' \
     -d '{"address":"So11111111111111111111111111111111111111112"}'
```

Health probes: `GET /health`, `GET /ready`.

## Architecture

```
client -> FastAPI gateway -> [helius | birdeye | solscan] -> scoring
       -> verifications (truth state) -> audit_log (hash-chained) -> response
```

Every decision writes an audit row with `prev_hash` + `row_hash` before
returning. If the write fails, the request fails closed (BLOCK).

## Modules

### RBAC

API-key auth via `X-API-Key` header. Roles: `admin`, `moderator`,
`contractor`, `viewer`. `require_role(*roles)` is a FastAPI dependency
that guards endpoints. Keys are stored as SHA-256 hashes only — raw
keys are shown once at mint time and never persisted. See
`app/security/auth.py`.

### Truth state machine

Every `/verify` creates a `verifications` row in one of:

```
VERIFIED ⇄ DISPUTED
   ↓         ↓
LEGAL_HOLD ──→ REMOVED   (terminal)
```

Transitions are enforced server-side in `app/db/verifications.py`:

| target       | allowed roles                            |
| ------------ | ---------------------------------------- |
| VERIFIED     | admin, moderator                         |
| DISPUTED     | admin, moderator, contractor             |
| LEGAL_HOLD   | admin                                    |
| REMOVED      | admin                                    |

`POST /admin/verifications/{id}/transition` performs a transition and
appends a `state_transition` row to the audit chain.

### Evidence uploads

`POST /evidence` (multipart) — accepts `file`, optional `verification_id`,
optional `note`. Enforces MIME allowlist (`EVIDENCE_ALLOWED_MIME`) and
size cap (`EVIDENCE_MAX_BYTES`, default 25 MiB). Stores file on disk
under `EVIDENCE_DIR`, persists `{filename, mime, size_bytes, sha256,
path}` and runs the moderation stub over `note`. Every upload appends an
`evidence_upload` audit row carrying the SHA-256.

### Moderation (stub)

`app/services/moderation.py` exposes a `Moderator` protocol with a
`HeuristicModerator` default. Verdicts: `{label, score, hits}` where
label is `ok | flagged | block`. Detects:

- profanity (small wordlist)
- defamation hot-words (forces `block`)
- PII regex: email, phone, SSN, Solana-shaped addresses

Swap the backend with any class that implements `moderate(text) ->
Verdict` to call a real model.

### Append-only audit log

`audit_log` is hash-chained: `row_hash = sha256(prev_hash || canonical_json(payload))`,
genesis = `0×64`. Schema now carries `kind`, `actor_id`, `details JSONB`
so `verify`, `state_transition`, and `evidence_upload` events all
share one tamper-evident chain.

## Configuration

| Var                     | Purpose                                            |
| ----------------------- | -------------------------------------------------- |
| `HELIUS_API_KEY`        | Helius RPC / DAS key                               |
| `BIRDEYE_API_KEY`       | Birdeye public API key                             |
| `SOLSCAN_API_KEY`       | Solscan Pro key                                    |
| `DATABASE_URL`          | Postgres DSN                                       |
| `REDIS_URL`             | Redis DSN (rate limit + breaker state)             |
| `PROVIDER_TIMEOUT_S`    | per-provider HTTP timeout (default `3.0`)          |
| `RATE_LIMIT_PER_MIN`    | per-IP requests / minute (default `60`)            |
| `EVIDENCE_DIR`          | where uploads land on disk                         |
| `EVIDENCE_MAX_BYTES`    | per-file upload cap (default 25 MiB)               |
| `EVIDENCE_ALLOWED_MIME` | CSV of accepted Content-Types                      |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

37 tests covering scoring, validator, breaker, hash chain, moderation,
truth-state transitions, and auth-key minting.
