# NoblePort Systems — Monitoring Stack

SRE-grade observability for the NoblePort operating layer: Prometheus +
Alertmanager + Grafana, with multi-window SLO burn-rate alerts, runbook links
on every alert, and component-based routing.

> **Truth baseline.** Everything here is instrumented against the canonical
> `deployment_metrics.json` (audit ref **TA-2026-05-23**), not against
> aspirational figures. There are **no GPU/CUDA panels** (the platform runs on
> Hetzner CPU workers — no GPU cluster), **no TVL / ROI / token-price panels**
> (`tvl: 0`, `nbpt_deployed: false`, `platform_arr: 0`), and **no avatar-node
> counts** (avatar layer is `DEFERRED`). `validate-monitoring-stack.py`
> enforces this: it fails CI if any file reintroduces a claim from the audit's
> `deprecated_claims` list. See "Divergence from the Dec-2025 package" below.

## Layout

```
monitoring/
├── prometheus/
│   ├── prometheus.yml                 # scrape config (CPU workers, no GPU jobs)
│   └── rules/
│       ├── slo_burn_rates.yml         # multi-window burn-rate alerts
│       ├── stephanie_voice_gates.yml  # g1–g4 STAGED voice promotion gates
│       ├── platform_health.yml        # targets, latency, datastores, audit chain
│       └── governance_guardrails.yml  # hard-block / launch-gate / geo / human-gate
├── alertmanager/alertmanager.yml      # component + compliance routing
├── grafana/
│   ├── dashboards/nobleport-ops.json  # 20 panels, 5 rows
│   └── provisioning/                  # datasource + dashboard providers
├── scripts/
│   ├── deploy-monitoring.sh           # idempotent k8s deploy
│   ├── health-check.py                # live guardrail + target check (stdlib)
│   └── validate-monitoring-stack.py   # static validation + truth guard
└── docker-compose.yml                 # local bring-up
```

## Quick start (local)

```bash
python3 monitoring/scripts/validate-monitoring-stack.py     # static + truth guard
docker compose -f monitoring/docker-compose.yml up -d
open http://localhost:3000        # Grafana (admin/admin) → dashboard "nobleport-ops"
open http://localhost:9090/alerts # Prometheus alerts
```

## Deploy (Kubernetes)

```bash
monitoring/scripts/deploy-monitoring.sh nobleport-monitoring
# later, against a running Prometheus:
python3 monitoring/scripts/health-check.py --prometheus http://prometheus:9090
```

## SLO catalog (truth-bounded)

| SLO | Target | Source |
|-----|--------|--------|
| Verification gateway availability | 99.9% | this stack |
| Construction ingress availability | 99.5% | LIVE @ 95% readiness |
| AWO / invoice workflow success | 99.9% | LIVE @ 100% |
| Audit-chain write success | 100% (fail-closed) | "no log = no go" |
| API p95 latency | < 300ms | architecture target |
| Voice G1 waveform p95 | ≤ 90ms | `voice_pipeline.g1` (currently ~147ms, FAILING) |
| Voice G2 caption drift p95 | ≤ 2.0s | `voice_pipeline.g2` (currently ~3.1s, FAILING) |
| Voice G3 LiveKit room stability | ≥ 98% | `voice_pipeline.g3` (IN_PROGRESS) |

The voice gates are the objective signal for promoting Stephanie.ai out of
`STAGED` — **0 of 4 currently clear**, so those alerts are expected to fire
until the pipeline meets target.

## Governance guardrails (must always read zero)

`governance_guardrails.yml` turns the hard constraints in
`core/config/launch-gates.json` and `deployment_metrics.json` into alerts.
Any of these firing is a **compliance incident**, routed to `compliance-oncall`
with no grouping delay:

- Autonomous **treasury** action fired (HARD_BLOCKED)
- Autonomous **securities** operation fired (HARD_BLOCKED)
- A **RED launch-gate** module executed (nbpt_sale, kuzo_swap_execution, hosted_wallets, ai_trade_execution, …)
- **KUZO** swap execution attempted (engine must be read-only)
- **New York** blocked virtual-currency activity attempted (NYDFS BitLicense)
- **Human-approval gate** bypassed (high-risk action auto-approved without `human_signature`)
- **OFAC** screenable events outpacing screening
- Audit hash-chain broken / write failures

## Metric contract

The stack expects services to expose Prometheus metrics at `/metrics`. Names
referenced by the rules and dashboard (instrument these in the apps):

| Metric | Type | Emitted by |
|--------|------|-----------|
| `verification_requests_total{outcome}` | counter | verification engine |
| `construction_ingress_requests_total{outcome}` | counter | construction ingress |
| `http_request_duration_seconds_bucket{component}` | histogram | all FastAPI services |
| `awo_write_total` | counter | AWO tracking |
| `nobleport_human_gate_pending` | gauge | truth-bounded spine |
| `audit_log_write_failures_total` | counter | verification engine |
| `audit_log_chain_intact` | gauge (1/0) | verification engine |
| `stephanie_voice_waveform_latency_seconds_bucket` | histogram | Stephanie voice |
| `stephanie_voice_caption_drift_seconds_bucket` | histogram | Stephanie voice |
| `livekit_room_joins_total` / `livekit_room_disconnects_total` | counter | LiveKit bridge |
| `stephanie_ws_messages_total`, `stephanie_ws_connections` | counter/gauge | Stephanie backend |
| `nobleport_autonomous_treasury_action_total` | counter | spine (should never increment) |
| `nobleport_autonomous_securities_action_total` | counter | spine (should never increment) |
| `nobleport_red_gate_execution_total{module}` | counter | launch-gate enforcer |
| `kuzo_swap_execution_attempt_total` | counter | KUZO engine |
| `nobleport_ny_blocked_activity_total{activity}` | counter | geo-block middleware |
| `nobleport_high_risk_action_auto_approved_total` | counter | human-gate router |
| `nobleport_ofac_screenable_events_total` / `nobleport_ofac_screened_total` | counter | compliance |
| `permitstream_discrepancy_total` | counter | PermitStream |

A small `prometheus-client` `/metrics` endpoint on the FastAPI verification
engine is the natural first instrumentation step — ask and it can be added.

## Divergence from the Dec-2025 "Stephanie.ai Production Monitoring" package

The uploaded summary (dated Dec 8–9 2025) predates the **Deep Truth Audit
TA-2026-05-23** and assumes figures the audit later deprecated. This stack
deliberately omits them:

| Summary item | Why omitted | Canonical reality |
|--------------|-------------|-------------------|
| GPU / CUDA / nvidia-smi panels, "120T ops/sec" | No GPU cluster | `compute: Hetzner CPU workers` |
| "$162M TVL", token price, "$1.25M ROI / 166x" | Marketing / securities risk | `tvl: 0`, `platform_arr: 0`, danger_words |
| "3000+ avatar nodes", "validators" | Not deployed | `avatar_layer: DEFERRED` |
| "96.5% task completion, all targets exceeded" | Not validated | voice gates 0/4 clear, g1/g2 FAILING |
| DAO governance participation panels | Not active | `snapshot_dao: configured_not_active` |

What was kept and re-grounded: multi-window SLO burn rates, runbook links on
alerts, component-based Alertmanager routing, datastore/host health, and a
one-command deploy — applied to the systems NoblePort actually runs, plus the
governance guardrails the audit makes essential.
