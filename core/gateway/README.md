# NoblePort MCP Gateway

A controlled internal connection layer that sits between the **Stephanie.ai**
orchestrator and the five NoblePort MCP servers — **GCagent.ai**,
**PermitStream.ai**, **Cyborg.ai**, **Borg.ai**, **Kuzo.io** — across the
50 NoblePort Systems modules.

Truth label: this is the **execution + governance + audit + KPI** layer.
It is wired and tested. KPI values are **BLOCKED until real telemetry is
connected** — the gateway will not fabricate LIVE numbers.

## Pipeline (fail-closed, audit-before-state-change)

```
POST /agent/invoke  (MCP envelope)
   ↓
Kill Switch        — global / per-agent instant halt (fail-closed)
   ↓
Governance Gate    — L0–L4, driven by core/config/launch-gates.json
   ↓
Rate Limit         — per requesting agent (Redis)
   ↓
Cache              — read-only (L0, non-write) calls only
   ↓
AuditBeacon PRE    — hash-chained INSERT into audit_logs (REQUIRED; blocks on failure)
   ↓
Tool Execution     — StubExecutor (STAGED) or HttpExecutor (live agent)
   ↓
AuditBeacon POST   — result + latency
   ↓
mcp_call_log       — operational ledger row
```

Nothing executes before the AuditBeacon pre-write commits. Any unexpected
error in the kill switch or governance gate resolves to **BLOCK**, never to a
silent pass.

## Governance ladder (L0–L4)

| Level | Meaning                         | Behavior in the gate                              |
|-------|---------------------------------|---------------------------------------------------|
| L0    | read-only                       | topology check; unknown target agent → BLOCK      |
| L1    | draft                           | permitted after claim/scope screening             |
| L2    | internal update                 | oversize payload → BLOCK; rate-limit applies       |
| L3    | customer / vendor-facing        | NY geo-block; write needs human signature → PARK  |
| L4    | money / legal / permit-critical | prohibited claim / RED-gate scope → BLOCK; write needs signature → PARK |

Prohibited claims, RED-gate scopes, and the NY geo-block are **not** hard-coded
here — they are read from `core/config/launch-gates.json`, the same config the
pre-launch law review governs.

## Decisions

- **PERMIT** → executed; result returned.
- **PARK** → sensitive write without a human signature; audited, queued, not executed.
- **BLOCK** → denied; audited as a terminal event in both ledgers.

## Endpoints

| Method | Path                          | Purpose                                  |
|--------|-------------------------------|------------------------------------------|
| GET    | `/health`, `/ready`           | liveness / readiness                     |
| POST   | `/agent/invoke`               | run an MCP call through the gateway      |
| GET    | `/api/kpi/modules`            | all 50 modules + latest snapshot         |
| GET    | `/api/kpi/module/{id}`        | one module + snapshot history            |
| GET    | `/api/kpi/agent/{name}`       | modules owned by an agent                |
| GET    | `/api/mcp/calls`              | operational call log                     |
| GET    | `/api/audit/events`           | immutable hash-chained audit events      |
| GET    | `/api/metrics/p95`            | P50/P95/P99 latency (JSON)               |
| GET    | `/api/metrics/p95.csv`        | **G1 P95 export** (CSV, per agent)       |
| GET    | `/api/killswitch/status`      | current kill-switch state                |
| POST   | `/api/killswitch/engage`      | halt execution (requires `X-Admin-Token`)|
| POST   | `/api/killswitch/release`     | resume execution (requires `X-Admin-Token`)|

## Run

```bash
cd core/gateway
cp .env.example .env          # set ADMIN_TOKEN
docker compose up --build
```

Postgres initializes from `core/migrations/` (001 then 002). On startup the
gateway seeds the agent / tool / module registries and starts the KPI snapshot
worker.

### Smoke

```bash
curl localhost:8080/health
curl -X POST localhost:8080/agent/invoke -H 'Content-Type: application/json' -d '{
  "requesting_agent":"Stephanie.ai","target_agent":"GCagent.ai",
  "module":"Estimate Engine","action":"gcagent.price_estimate",
  "message":"Explain contractor deposits"}'

# governance must block this:
curl -X POST localhost:8080/agent/invoke -H 'Content-Type: application/json' -d '{
  "requesting_agent":"Stephanie.ai","target_agent":"GCagent.ai",
  "module":"Estimate Engine","action":"gcagent.price_estimate",
  "message":"guaranteed returns on real estate"}'
```

## Test

```bash
pip install -r core/gateway/requirements.txt
python -m pytest core/gateway/tests -q        # run from the repo root
```

The suite (27 tests) covers the governance ladder, kill-switch fail-closed
behavior, P95 math, registry integrity (50 modules), and envelope validation —
no database required.

## KPI truth discipline

Every module seeds as **BLOCKED**. The snapshot worker only flips a module to
**LIVE** when a resolver reads a real value from a real table. Today only the
modules backed by tables that already exist (`audit_logs`, `mcp_call_log`,
`workflow_states`, `kpi_snapshot`, the registry itself) report LIVE; the rest
stay BLOCKED with a reason until their source is wired in
(`kpi_worker.RESOLVERS`). The worker is append-only — it never overwrites
history.

## Files

```
core/migrations/002_mcp_gateway.sql   schema: agents, tools, modules, call log, snapshots, kill switch
core/gateway/registry.py              5 agents, 30 tools, 50 modules (single source of truth)
core/gateway/envelope.py              MCP envelope + schema-validation gate
core/gateway/governance.py            L0–L4 gate, fail-closed
core/gateway/killswitch.py            global / per-agent kill switch
core/gateway/audit.py                 AuditBeacon (hash chain) + operational call log
core/gateway/cache.py                 Redis cache + rate limiter
core/gateway/executors.py             StubExecutor (STAGED) / HttpExecutor (live)
core/gateway/metrics.py               P50/P95/P99 + CSV export
core/gateway/kpi_worker.py            registry seeding + KPI snapshot worker
core/gateway/gateway.py               the pipeline orchestrator
core/gateway/app.py                   FastAPI entrypoint
```
