# Cyborg.ai — Truth Model & Content Classification

**Applies to:** Cyborg.ai public website, application interfaces, security dashboards, revenue dashboards, and connected infrastructure  
**Public deployment:** https://cyborgai-awbvqt.manus.space/  
**Last updated:** 2026-07-18  
**Classification:** Audit-Aligned Truth Model

## Current Verified State

| Component | Classification | Evidence / Required Action |
|---|---|---|
| Public Website | DEPLOYED — VERIFIED ACCESSIBLE | Public Manus deployment resolves. Public accessibility does not establish production backend functionality. |
| Application Dashboard | DEPLOYED / VERIFICATION REQUIRED | Interface is publicly accessible; workflows, persistence, authentication, payments, monitoring, and security-engine behavior require end-to-end verification. |
| Security Engine | NOT LIVE | No verified production telemetry, security-event stream, audit output, or active target monitoring evidence is attached to the evidence ledger. |
| Stripe Commerce | STAGED / TEST MODE | No independently verified production transaction evidence is attached. |
| Revenue Metrics | DEMO / STAGED | Reported internal values, including approximately $190K+ monthly modeled/test activity, are not production revenue until reconciled to live payment evidence. |
| On-Chain Monitoring | STAGED / VERIFICATION REQUIRED | No authenticated live-chain data source has been evidenced. |

## Canonical Labels

Every metric, chart, counter, capability statement, revenue figure, security event, and operational claim must carry exactly one classification:

- **LIVE** — Real production data from an active, authenticated source with checkable evidence.
- **DEPLOYED** — Publicly accessible functionality or infrastructure not yet fully production-verified.
- **STAGED** — Development, sandbox, test, pre-production, or controlled validation state.
- **DEMO** — Mock, simulated, seeded, projected, illustrative, or synthetic information.

No unlabeled operational metric should appear on a production-facing Cyborg.ai dashboard.

## Stripe Production Promotion Gate

Stripe processing may move to **LIVE — VERIFIED** only after all of the following are evidenced:

1. Production products and prices are verified.
2. Production secrets are installed only in the approved secret-management environment.
3. Production webhook endpoint is registered and signature validation passes.
4. Idempotency and duplicate-event protection are verified.
5. A controlled real production transaction succeeds.
6. The transaction is reconciled to the internal ledger.
7. Refund/reversal handling is verified.
8. Evidence package is captured with deployment ID, timestamps, transaction ID, webhook evidence, ledger evidence, and governance approval.

## Security Engine Promotion Gate

The security engine may move to **LIVE — VERIFIED** only after:

1. At least one real production target is actively monitored.
2. Telemetry ingestion is authenticated and timestamped.
3. A controlled detection event is generated.
4. Detection-to-alert workflow is verified end-to-end.
5. Dashboard counters are proven to derive from the telemetry source.
6. Failure and false-positive handling are logged.
7. Audit evidence is captured.

## Promotion Rules

- **REPORTED → DEPLOYED:** requires a publicly accessible artifact or verified deployment evidence.
- **DEPLOYED → LIVE:** requires functional production execution and checkable evidence.
- **STAGED → LIVE:** requires production integration, successful end-to-end validation, and audit evidence.
- **DEMO → LIVE:** requires replacement of simulated data with an authenticated production source.

A classification may not be promoted solely from an AI-generated report, static dashboard, internal projection, or marketing statement.

## Current Canonical Classification

- Cyborg.ai Public Website: **DEPLOYED — VERIFIED ACCESSIBLE**
- Cyborg.ai Application: **DEPLOYED — FUNCTIONAL VERIFICATION REQUIRED**
- Stripe Commerce Stack: **STAGED / TEST MODE**
- Revenue Metrics: **DEMO / STAGED**
- Security Engine: **NOT LIVE / VERIFICATION REQUIRED**
- On-Chain Monitoring: **STAGED / VERIFICATION REQUIRED**
- Production Revenue: **$0 VERIFIED under the current evidence ledger unless transaction evidence is subsequently attached**

> Publicly deployed does not mean operationally verified. Configured does not mean live. A metric becomes authoritative only when its source, execution path, and evidence can be independently verified.
