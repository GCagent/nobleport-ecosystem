# NoblePort Production Ecosystem
## AI-Assisted Construction Operating Layer

### System Profile

NoblePort Systems is an AI-assisted construction and real estate operating layer
providing intake, estimating, permit preparation, compliance routing, audit
logging, and human-gated execution.

**Canonical Reference:** April 2026 Whitepaper
**Audit Ref:** TA-2026-05-23 — Deep Truth Audit

---

## Operational Status

| Component | Classification | Status |
|-----------|---------------|--------|
| Construction Ingress API | LIVE (95%) | Property attribute parsing pipelines |
| Scope & Estimate Support | LIVE | Baseline project brief generation |
| Job & AWO Tracking | LIVE | Postgres write-ahead log operations |
| Invoice Workflow Support | LIVE | Billing state management and ledger emission |
| Human Approval Routing | LIVE | Manual sign-off on all high-risk events |
| Stephanie.ai Orchestrator | STAGED (81%) | Multi-agent state manager in dev containers |
| GCagent.ai Compliance | STAGED (44%) | Municipal regulation text-matching routines |
| PermitStream.ai Review | STAGED (38%) | Document parsing schemas; awaiting API validation |
| Cyborg.ai Identity Layer | STAGED (28%) | ERC-3643 / identity token scaffolding |
| KUZO Swap Policy Engine | STAGED / READ-ONLY | Simulated quotes only; on-chain execution disabled |
| NBPT Token Contracts | STAGED | Contract framework validated; mainnet pending |

## Tokenomics (NBPT)

- **Total Supply:** 100,000,000 NBPT (Fixed)
- **Standard:** ERC-3643 (T-REX) security token
- **Compliance:** Human-gated mint/burn, identity-verified transfers
- **Status:** Mainnet deployment pending

## AI Operating Layer

### Stephanie.ai — Core Orchestrator
- Multi-agent construction workflow coordinator
- Human-gated approval routing for all financial and legal actions
- Constitutional governance framework

### Specialized Agents
- **GCagent.ai:** Compliance monitoring and municipal regulation matching
- **PermitStream.ai:** Permit document parsing and review pipeline
- **CyBorg.ai:** Identity verification and security monitoring

## Architecture

```
[ PUBLIC / INVESTOR ENTRYPOINT ]
              |
   +----------+----------+
   v                      v
 LIVE OPERATIONAL     STAGED / SIMULATED
 - Construction       - Stephanie Orchestrator
 - Scope & Estimate   - GCagent & PermitStream
 - AWO & Invoices     - KUZO Read-Only Engine
 - Human-Gate Router  - NBPT Framework
```

## Multi-Chain Integration

- **Primary:** Ethereum (ERC-3643 security tokens)
- **Payment Rail:** Solana (USDC settlement only)
- **Storage:** IPFS + Arweave (document anchoring)

## Quick Start

```bash
git clone https://github.com/nobleport/ecosystem
cd ecosystem
python3 -m http.server 8000
# Open http://localhost:8000
```

## Security & Compliance

- **ERC-3643:** Identity-gated transfer restrictions
- **zkSBT:** Zero-knowledge accredited investor verification
- **Multi-sig:** Gnosis Safe treasury management
- **Human Gate:** All treasury/securities actions require manual approval
- **Autonomous Treasury Actions:** BLOCKED (hard-coded restriction)
- **Autonomous Securities Operations:** BLOCKED (human multi-sig required)

## Key Addresses

- **Ethereum Wallet:** `0xc59e66BB2b6E19699F82A72a1569821cb1711504`
- **Solana Rail:** `6fbr88Qmc1LSh5XATjcaGzvVnq1H7QmB57wAyxrKMXas`
- **NBPT Contract:** `0x3778E67655Ec26D6bC8294C6F7a1e754AFD2C91C`
- **ENS:** `nobleport.eth`

---

**Contact:** nobleport.eth
