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
client -> FastAPI gateway -> [helius | birdeye | solscan] -> scoring -> audit_log (hash-chained) -> response
```

Every decision writes an audit row with `prev_hash` + `row_hash` before
returning. If the write fails, the request fails closed (BLOCK).

## Configuration

| Var                  | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `HELIUS_API_KEY`     | Helius RPC / DAS key                       |
| `BIRDEYE_API_KEY`    | Birdeye public API key                     |
| `SOLSCAN_API_KEY`    | Solscan Pro key                            |
| `DATABASE_URL`       | Postgres DSN                               |
| `REDIS_URL`          | Redis DSN (rate limit + breaker state)     |
| `PROVIDER_TIMEOUT_S` | per-provider HTTP timeout (default `3.0`)  |
| `RATE_LIMIT_PER_MIN` | per-IP requests / minute (default `60`)    |

## Tests

```bash
pip install -r requirements.txt
pytest -q
```
