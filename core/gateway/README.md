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
Supervisor         — main agent delegates to its sub-agents (concurrent)
   ↓                  each finding packed into a compression packet
AuditBeacon POST   — result + latency + optimization meta
   ↓
mcp_call_log       — operational ledger row (incl. bytes + sub-agent count)
```

Nothing executes before the AuditBeacon pre-write commits. Any unexpected
error in the kill switch or governance gate resolves to **BLOCK**, never to a
silent pass. Delegation happens *after* the gate and the pre-write, so
sub-agents are workers of an already-authorized call — they never bypass
enforcement.

## Sub-agents (helping the main agents)

Each main agent owns a small set of specialized sub-agents. When a call comes
in, the **Supervisor** selects the sub-agents that serve the requested tool,
runs them concurrently, and aggregates their findings:

```
Stephanie.ai      router · summarizer
GCagent.ai        estimator · scoper · scheduler
PermitStream.ai   ahj_analyst · deficiency_scanner
Cyborg.ai         policy_auditor · risk_scorer
Borg.ai           job_runner · health_monitor
Kuzo.io           intake_clerk · notifier
```

Routing: a *specialist* whose `serves` set contains the action is preferred;
if none match, the parent's *generalists* help. Sub-agents return STAGED
partials — they propose, they never assert LIVE truth. The set is seeded into
`mcp_subagent_registry` on startup.

## Built-in compression packets

Every payload that crosses an internal boundary — cache entries and sub-agent
findings — is serialized into a self-describing packet (`compression.py`):

```
[ MAGIC | version | flags | orig_len | body (zlib | raw) ]
```

Compression is smart: payloads under 256 B are stored raw (the zlib header
would cost more than it saves); larger ones are deflated. The realized ratio is
measured per call and rolled up at `/api/metrics/optimization`, so the saving
is auditable, not assumed. The Redis cache is compressed at rest and on the
wire by default.

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
| GET    | `/api/metrics/optimization`   | compression savings + sub-agent dispatch |
| GET    | `/api/killswitch/status`      | current kill-switch state                |
| POST   | `/api/killswitch/engage`      | halt execution (requires `X-Admin-Token`)|
| POST   | `/api/killswitch/release`     | resume execution (requires `X-Admin-Token`)|

## Run

```bash
cd core/gateway
cp .env.example .env          # set ADMIN_TOKEN
docker compose up --build
```

Postgres initializes from `core/migrations/` in order (001 → 003). On startup
the gateway seeds the agent / tool / module / sub-agent registries and starts
the KPI snapshot worker.

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

The suite (39 tests) covers the governance ladder, kill-switch fail-closed
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

## Code stack

The package is organized by responsibility — one concern per module, layered
from the entrypoint down to the codecs:

```
app.py            FastAPI entrypoint — wiring + HTTP surface
└─ gateway.py     pipeline orchestrator (the order of the gates)
   ├─ governance/      governance.py     L0–L4 gate, fail-closed
   ├─ control/         killswitch.py     global / per-agent kill switch
   │                   cache.py          rate limit + compressed cache
   ├─ agents/          registry.py       5 agents · 30 tools · 50 modules
   │                   subagents.py      specialized sub-agents per agent
   │                   supervisor.py     delegation + aggregation executor
   │                   executors.py      Stub (STAGED) / Http (live) inner
   ├─ audit/           audit.py          AuditBeacon hash chain + call log
   ├─ transport/       compression.py    self-describing compression packets
   │                   envelope.py       MCP envelope + result models
   └─ observability/   metrics.py        P50/P95/P99 + CSV export
                       kpi_worker.py     seeding + KPI snapshot worker

config.py             settings (env-driven)

core/migrations/
  002_mcp_gateway.sql           agents, tools, modules, call log, snapshots, kill switch
  003_subagents_compression.sql sub-agent registry + compression telemetry columns
```

(Files are flat within `core/gateway/`; the grouping above is the logical
layering — imports flow strictly downward, entrypoint → pipeline → codecs.)
