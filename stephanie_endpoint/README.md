# Stephanie Endpoint

FastAPI service powering NoblePort's Stephanie AI operations layer.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check |
| `POST` | `/api/v1/stephanie/execute` | Bearer API key | Execute an action (create_job, check_permit, sync_crm, etc.) |
| `POST` | `/api/v1/webhooks/openclaw` | HMAC-SHA256 | Receive webhook events from OpenC Law |

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with real keys
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Example: Execute

```bash
curl -X POST http://localhost:8000/api/v1/stephanie/execute \
  -H "Authorization: Bearer replace-with-long-random-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create_job",
    "source": "openc law",
    "dry_run": true,
    "data": {
      "client": "Dave McCoy",
      "address": "33 Ashland St, Newburyport, MA",
      "scope": "Porch repair and threshold replacement",
      "budget": 25000
    }
  }'
```

## Tests

```bash
cd stephanie_endpoint
pytest tests/ -v
```

## Architecture

- `app/main.py` — FastAPI app, middleware, route definitions
- `app/schemas.py` — Pydantic request/response models
- `app/security.py` — Bearer API key auth + HMAC webhook signature validation
- `app/rate_limit.py` — In-process sliding-window rate limiter
- `app/services.py` — Action dispatcher and business logic stubs

### Production Readiness

This is production-oriented but not fully production-complete. Before deploying:

1. Replace stub handlers in `services.py` with real GCagent / PermitStream / CRM adapters
2. Add Postgres persistence for job state
3. Swap in Redis-backed distributed rate limiting (e.g. `slowapi` + Redis)
4. Add structured logging to your observability stack
