# Stephanie.ai -- Executive Orchestration Interface

**Document status:** MGMT EST
**Component completion:** ~81% (per canonical NoblePortProgress.jsx / NoblePortPerformance.jsx)
**Verification level:** Internal management estimate. Not investor-grade until ERPNext reconciliation completes and timestamped voice CSVs (G1/G2) are produced.
**Replaces:** Prior "Stephanie.ai Executive Core Attribute Map" containing fabricated TVL, holder, validator, CUDA, and audit claims. That document failed fabrication review and must not propagate.
**External-use clearance:** This document is cleared for internal use and as a starting point for investor/municipal external materials, subject to securities counsel and the launch-law review.

---

## 1. Role

Stephanie.ai is NoblePort's internal executive orchestration interface for lead intake, document routing, workflow tracking, and human-gated decision support across construction operations, permitting, and contractor compliance.

Ultimate execution authority is reserved to licensed human professionals. Stephanie.ai is not a licensed CEO, broker, real estate professional, securities professional, lawyer, engineer, building official, or financial advisor, and is not represented as such in any external surface.

Stephanie coordinates downstream subsystems including GCagent.ai (operations) and PermitStream.ai (permitting workflow), routing requests, preparing documents, surfacing decisions for human review, and recording outcomes to a tamper-evident audit log.

---

## 2. Architecture (confirmed stack)

| Layer | Component |
|---|---|
| API / orchestration | FastAPI + LangGraph StateGraph |
| Worker orchestration | Temporal (not Celery) |
| Source of truth | PostgreSQL 16 with pgvector |
| Hot path | Redis (asyncio): session state, semantic cache, voice pipeline coordination |
| STT / TTS | ElevenLabs Conversational API |
| Real-time transport | LiveKit WebRTC -- single SFU on Vultr HF US-East |
| Semantic routing | FAISS |
| Accounting | ERPNext (sole accounting system across all 4 entities) |
| CRM | HubSpot (portal 244971555) |
| Construction ops | Buildertrend + Cost Certified |
| Primary payment rail | PayPal Instant Commerce |
| Secondary payment rail | Stripe (human-approval-gated only) |
| Secrets | HashiCorp Vault |
| Document anchoring | IPFS / Pinata |
| On-chain anchor | AnchorRegistry.sol on Arbitrum One |
| Governance config | Snapshot DAO (configured, not active) |
| Compute | Hetzner CPU workers -- no GPU cluster |
| DDoS / failover | Sharktech |
| Notification mirror | Notion (not a source of truth, cannot trigger system operations) |

---

## 3. Voice pipeline status

| Metric | Target | Interim | Current | Status |
|---|---|---|---|---|
| G1 -- Waveform P95 latency | < 90ms | 130ms (DR-001) | ~147ms | FAILING |
| G2 -- Caption drift P95 | < 2.0s | 2.5s | ~3.1s | FAILING |
| G3 -- LiveKit room stability | Pass | -- | In testing | IN PROGRESS |
| G4 -- 100-session load test | Pass | -- | Not run | PENDING |

Voice gates clear: **0 of 4**. These gates are the master commercial blocker. No marketing, investor, or municipal claim of "live" voice operation is made until they pass with timestamped evidence.

Sub-component completion (per canonical files):
- Voice pipeline (ElevenLabs + WebSocket): 88%
- LiveKit WebRTC integration: 75%
- React dashboard UI: 95%
- FastAPI backend: 72%
- WebSocket real-data connections: 55%

---

## 4. Avatar / visual layer

**Status:** DEFERRED.

No avatar surface, lip-sync surface, video generation surface, or voice-cloning surface exists today. No avatar layer ships until G1 and G2 cross threshold with timestamped evidence.

Documented evaluation sequence when gates clear:
1. ElevenLabs audio-first (already in stack)
2. D-ID streaming API, server-side (not a LiveKit plugin)
3. HeyGen, only if measurably superior to D-ID against documented criteria

HeyGen does not have a LiveKit plugin. It is a server-side streaming API.

Biometric / avatar / voiceprint capture requires counsel-reviewed consent and retention policy before any capture occurs (per launch-law review).

---

## 5. Governance and on-chain status

| Item | Status |
|---|---|
| AnchorRegistry.sol on Arbitrum One | Deployed |
| Investor-visible on-chain transactions | Zero |
| NBPT token | Not deployed |
| Snapshot DAO | Configured, not active |
| NPP-001 governance proposal | Drafted, not published |
| Token holder count | Zero (no token deployed) |
| TVL | Zero (no token deployed) |
| AnchorRegistry deployment script (Solidity extension + off-chain listener + IPFS pinning) | Next build priority |
| External audit (CertiK, Trail of Bits, etc.) | None commissioned |

No component flips to VERIFIED without a timestamped Arbiscan transaction hash. No tokenomics, distribution, vesting, holder, or TVL claim is made until on-chain receipts exist and securities counsel has reviewed the structure.

---

## 6. Platform component context

Stephanie.ai sits inside a five-component platform:

| Component | Completion | Tier |
|---|---|---|
| Stephanie.ai | 81% | Launch-critical |
| GCagent.ai (112-agent construction operations mesh) | 44% | Phase 2 |
| PermitStream.ai (MA/NH/ME/CT permit workflow) | 38% | Phase 2 |
| Cyborg.ai (contractor identity, ERC-1400 / ERC-3643, zk-SBT) | 28% | Phase 3 |
| Discord Mission Control | 8% | Deferred |

Blended platform completion: ~46%. Platform ARR: $0.

---

## 7. Entity context

Stephanie.ai is a NoblePort Systems LLC product. NoblePort Systems LLC is one of four legal entities under the NoblePort umbrella, each with separate scope:

| Entity | Scope |
|---|---|
| NoblePort Construction LLC | General contracting (35+ years operating history) |
| NoblePort Systems LLC | AI platform -- Stephanie.ai, GCagent.ai, PermitStream.ai, Cyborg.ai |
| NoblePort Media LLC | Brand and media |
| NoblePort Real Estate Dev LLC | Real estate development |

Canonical address: 236 High Road, Newbury MA 01951.

Construction and software revenue, customer deposits, retainage, investor proceeds, and any future treasury assets must remain ledger-separated per launch-law review.

---

## 8. External-facing language (FTC / MA c. 93A safe)

Cleared phrasing for external surfaces (website, deck, municipal memo, customer-facing portal):

> Stephanie.ai is NoblePort's executive orchestration assistant for intake, routing, document preparation, workflow tracking, and human-gated decision support. Final decisions and execution remain with licensed human professionals. AI-assisted permitting and construction workflow review is subject to licensed human review and municipal authority approval.

Prohibited claims (per launch-law review and FTC AI enforcement posture):
- "Guarantees permit approval" / "guarantees no rejection"
- "Guarantees cost savings"
- "Automatically ensures compliance"
- "Licensed AI" / "Certified AI" / "AGI"
- "Autonomous CEO" / "AI CEO" externally
- "SEC-compliant" unless counsel-verified
- Yield / passive income / dividend / staking rewards / pegged / risk-free / token launch language
- Any TVL, holder count, validator count, throughput, or audit claim not backed by timestamped receipts

---

## 9. What is explicitly NOT claimed

The prior fabricated attribute map asserted the following. None of these are claimed here, and none should appear in any NoblePort surface until each line has a timestamped, externally verifiable receipt:

- Distributed validator mesh of any size
- NoblePort-trained large language model of any parameter count
- Deployed avatar model or lip-sync surface
- "IQCore" or any CUDA-based throughput metric
- Simultaneous task execution counts and completion rates
- TVL under management
- zk-SBT holder count
- NBPT supply, vesting, or distribution
- Audit attestations from Chainlink, zk KYT, Aragon, CertiK, or any third party
- Municipal simulation accuracy percentages
- Contract execution error rate
- "Embedded anchored voice signatures" or any other invented cryptographic feature
- CCIM, Series 7, Series 63, or any other professional licensure replication

---

## 10. Update protocol

This document is updated only when one of the following occurs:

1. A voice gate crosses threshold with timestamped CSV evidence
2. ERPNext reconciliation advances a measurable percentage
3. An on-chain transaction is anchored with an Arbiscan receipt
4. A signed customer or municipal pilot agreement closes
5. A canonical file (NoblePortProgress.jsx / NoblePortPerformance.jsx) is patched

Updates do not occur on the basis of ideation, AI-generated suggestion, or aspirational planning. Aspirational items go to a separate post-Series A ideas list.

---

**Last updated:** 2026-05-27
**Owner:** Michael O'Rourke, Founder, NoblePort Systems LLC
**Reviewers required before external release:** Securities counsel (sections 5, 8, 9), construction counsel (sections 1, 7, 8), CPA (sections 6, 7).
