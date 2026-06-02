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

### E-signature — "Seal" (open-source envelope signing)

An audit-first, from-scratch e-signature layer — the open-source counterpart
to a hosted signing service — for getting AWOs, change orders, invoices and
permit authorizations signed. No third-party signing account required.

Lifecycle (state machine in `app/engine/esign.py`, enforced server-side):

```
envelope:   DRAFT ──send──→ SENT ──all signed──→ COMPLETED  (terminal)
              │               ├── recipient declines ─→ DECLINED (terminal)
              └── void ───────┴── void ─────────────→ VOIDED  (terminal)

recipient:  PENDING ──→ SIGNED
                   └──→ DECLINED
```

Flow:

1. `POST /esign/envelopes` (multipart) — sender (`admin|moderator|contractor`)
   uploads the document with `subject`, optional `message`, and
   `routing` (`sequential` | `parallel`). The document is hashed (SHA-256)
   and stored under `ESIGN_DIR`.
2. `POST /esign/envelopes/{id}/recipients` — add `{name, email, role,
   routing_order}`. Roles: `signer`, `approver` (both block completion) and
   `viewer` (non-blocking). Recipients are locked once the envelope is sent.
3. `POST /esign/envelopes/{id}/send` — `DRAFT → SENT`; mints a one-time
   signing token per recipient (hashed at rest, raw returned once — deliver
   out-of-band, like the API-key model).
4. `POST /esign/envelopes/{id}/sign` — token-authenticated (no account).
   Requires explicit `consent_given` (ESIGN Act / UETA). In `sequential`
   routing a signer is blocked until all lower `routing_order` signers are
   done. Completing the last signer flips the envelope to `COMPLETED`.
5. `POST /esign/envelopes/{id}/decline` / `/void` — recipient declines (token)
   or sender voids (API key).

Each signature is **tamper-evident**: `signature_hash =
sha256(document_sha256 || recipient_id || email || signed_at || consent)`.
`GET /esign/envelopes/{id}/certificate` returns a deterministic Certificate of
Completion carrying every signer's hash plus its own `certificate_hash`.
`GET /esign/envelopes/{id}/document?token=…` serves the source document to a
token holder or an authenticated sender role. Every send/sign/decline/void
appends an `esign_*` row to the shared audit chain (below).

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
| `ESIGN_DIR`             | where e-signature documents land on disk           |
| `ESIGN_MAX_BYTES`       | per-document upload cap (default 25 MiB)           |
| `ESIGN_ALLOWED_MIME`    | CSV of accepted document Content-Types             |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```

58 tests covering scoring, validator, breaker, hash chain, moderation,
truth-state transitions, auth-key minting, and the e-signature engine
(envelope/recipient state machines, signing tokens, signature & certificate
hashing, sequential/parallel routing).
