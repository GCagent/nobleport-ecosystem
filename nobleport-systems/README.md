# NoblePort Systems — Platform Core

Full-stack implementation of the NoblePort nano-ecosystem: a Rust edge
gateway, a Python orchestrator hosting the four AI agents and the 50+ module
catalog, a declarative workflow engine with human-gated execution, and a
Docker deployment targeting a single Hostinger VPS.

```
                    nobleportsystem.io / *.kuzo.io
                                 |
                      [ Caddy — TLS termination ]
                                 |
                 [ gateway/  — Rust (axum), :8080 ]
                 rate limiting · /api/* proxy · /ws/avatar passthrough
                                 |
              [ orchestrator/ — Python (FastAPI), :8000 ]
        module registry (50+) · workflow engine · human gate · avatar WS
              /                  |                  \
        [ Postgres 15 ]     [ Redis 7 ]      [ agents (in-process) ]
        durability layer    cache/queues     stephanie · gcagent
                                             permitstream · cyborg
```

## Layout

| Path | What it is |
|------|------------|
| `gateway/` | Rust (axum) edge gateway: per-IP token-bucket rate limiting, `/api/*` reverse proxy, `/ws/avatar` WebSocket bridge |
| `orchestrator/nobleport/modules.py` | Canonical catalog of 50+ modules across 13 domain clusters, each with status (`LIVE`/`STAGED`/`READ_ONLY`) and risk (`LOW`→`CRITICAL`) |
| `orchestrator/nobleport/registry.py` | Module registry: lookup, execution policy, health + circuit breakers |
| `orchestrator/nobleport/workflows/` | Declarative workflow definitions (10 shipped) + the engine that runs them |
| `orchestrator/nobleport/human_gate.py` | Approval routing for HIGH/CRITICAL-risk steps |
| `orchestrator/nobleport/agents/` | Stephanie.ai (orchestrator), GCagent.ai (compliance), PermitStream.ai (permits), CyBorg.ai (identity/token) |
| `orchestrator/nobleport/api.py` | FastAPI surface the gateway proxies to |
| `migrations/` | Postgres schema (runs, approvals, avatar sessions, append-only audit log) |
| `deploy/Caddyfile` | TLS front proxy config for the VPS |
| `docker-compose.yml` | The whole stack |

## Execution policy (enforced, not advisory)

These mirror the repo-level constraints from the Deep Truth Audit
(TA-2026-05-23) and are implemented in `registry.py` + `workflows/engine.py`:

- **HIGH-risk steps** (bids, filings, legal documents, payments) suspend the
  workflow and open a human-gate approval request. Rejection terminates the
  run; the step never executes.
- **CRITICAL steps** (treasury payouts, NBPT mint/burn) never execute
  in-platform even after approval — the engine records
  `PREPARED_FOR_MULTISIG` and execution happens off-platform via human
  multi-sig. There is no code path that dispatches them.
- **STAGED modules** always run in simulation; **READ_ONLY** modules
  (KUZO quotes, Solana rail) can never emit state-changing effects.
- Risk is derived from the module catalog, not the workflow definition, so a
  workflow cannot opt itself out of gating.

## Run locally

Orchestrator (Python ≥3.11):

```bash
cd orchestrator
pip install -e .[dev]
pytest                       # 21 tests
uvicorn nobleport.api:app --port 8000
```

Gateway (Rust ≥1.75):

```bash
cd gateway
ORCHESTRATOR_URL=http://127.0.0.1:8000 cargo run
```

Then, through the gateway:

```bash
curl localhost:8080/api/modules | jq .count            # 57
curl -X POST localhost:8080/api/workflows/lead_to_estimate/start \
     -H 'content-type: application/json' \
     -d '{"payload":{"lead":{"name":"Ada"},"line_items":[{"amount":1000}]}}'
# -> AWAITING_APPROVAL with a pending_approval_id; resolve it:
curl -X POST localhost:8080/api/approvals/<id>/resolve \
     -H 'content-type: application/json' \
     -d '{"approved":true,"actor":"ops@nobleport"}'
```

Avatar channel: connect a WebSocket client to `ws://localhost:8080/ws/avatar`
and send plain text; Stephanie replies as JSON.

## Deploy (Hostinger VPS)

1. Provision a VPS (4 GB RAM / 2 vCPU minimum), install Docker + compose.
2. Point A records for `nobleportsystem.io` and `*.kuzo.io` at the VPS IP.
3. `cp .env.example .env` and set a real `POSTGRES_PASSWORD`.
4. `docker compose up -d --build` — Caddy provisions TLS automatically and
   the Postgres container applies `migrations/` on first boot.
5. Verify: `curl https://nobleportsystem.io/gateway/status`.

## Extending

- **New module:** add a `ModuleSpec` to `modules.py` (status/risk are policy,
  pick them honestly), optionally register a handler in the owning agent.
  Unhandled modules get a structured simulated acknowledgment, so catalog
  breadth never blocks workflow authoring.
- **New workflow:** add a `WorkflowDef` in `workflows/definitions.py`; a test
  (`test_all_workflow_steps_target_catalog_modules`) fails if any step targets
  a module that doesn't exist.
- **Model-backed avatar:** replace `StephanieAgent.avatar_reply` — the
  WebSocket plumbing (gateway bridge + session endpoint) stays unchanged.
