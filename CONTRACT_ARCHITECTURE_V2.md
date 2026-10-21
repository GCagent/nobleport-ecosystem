# NoblePort Contract Architecture — v2 Implementation Spec

**Status:** Buildable Spec (Draft)
**Date:** 2026-05-09
**Scope:** Smart contract suite for construction operations, real estate closings, shared infrastructure, and optional advanced rails

---

## 1. Design Principles

1. **Modular, not monolithic.** Construction ops, closings, compliance, payments, and tokenization are separate contract domains with separate upgrade paths and audit scopes.
2. **Legal paper stays primary.** Smart contracts enforce gating, evidence, disbursement logic, and immutable logs. They do not replace signed legal agreements.
3. **Boring rails first.** Escrow, milestones, document hashing, access control, and audit anchoring ship before tokenization, DAOs, or fractional ownership.
4. **On-chain does what on-chain is good at.** Payment authorization, role enforcement, event logging, hash anchoring. Everything else stays off-chain with on-chain checkpoints.

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Solidity 0.8.x | Mature tooling, auditor familiarity |
| Libraries | OpenZeppelin 5.x | Battle-tested access control, proxy, pausable |
| Framework | Foundry | Fast compilation, fuzz/invariant testing, scripting |
| L2 | Arbitrum One | Low gas, EVM-equivalent, USDC native support |
| Stablecoin | USDC (native) | Circle attestations, no bridge risk on Arbitrum |
| Evidence storage | IPFS + Arweave | Content-addressed artifacts, permanent backup |
| Oracles | Signed oracle relays + Chainlink (where applicable) | See Section 8 |
| Indexer | Ponder or custom subgraph | Canonical event read model |

---

## 3. Contract Module Map

### 3A. Construction Operations

| Contract | Responsibility |
|---|---|
| `JobRegistry` | Creates and indexes jobs. Stores owner, contractor, metadata hash, lifecycle state. |
| `JobEscrow` | Holds USDC for a job. Releases funds only on milestone approval or dispute resolution. |
| `MilestoneManager` | Defines milestones per job. Accepts submissions, routes approvals, triggers escrow release. |
| `ChangeOrderManager` | Records change orders. Requires dual sign-off (owner + contractor). Adjusts escrow and milestones. |
| `RetainageVault` | Holds retainage percentage per job. Releases only after substantial completion + cure period. |
| `SubcontractorFlow` | Tracks sub-tier payments. Links sub-milestones to prime milestones. Enforces flow-down. |
| `WarrantyPunchlist` | Records punchlist items post-substantial-completion. Gates final retainage release. |

### 3B. Construction Compliance

| Contract | Responsibility |
|---|---|
| `PermitInspectionRegistry` | Records permit issuance and inspection results. Oracle-fed or manually attested. |
| `LienWaiverRegistry` | Anchors lien waiver hashes per payment. Blocks next disbursement without prior waiver. |
| `DisputeResolution` | Locks disputed funds. Records arbitration outcome. Releases or redistributes. |

### 3C. Real Estate Closings

| Contract | Responsibility |
|---|---|
| `PropertyRegistry` | Registers properties by parcel ID. Stores metadata hash, current status, linked contracts. |
| `PurchaseSaleAgreement` | Anchors PSA hash. Tracks contingency states. Does not store terms on-chain. |
| `EarnestMoneyEscrow` | Holds earnest money deposit. Releases to seller on close, returns to buyer on cancellation per PSA terms. |
| `ClosingEscrow` | Holds closing funds. Disburses to seller, agents, title company, tax authority per closing statement. |
| `TitleConditionRegistry` | Records title conditions/exceptions. Oracle-fed from title agent. Gates clear-to-close. |
| `DisclosureAcknowledgement` | Anchors disclosure document hashes. Records buyer acknowledgement signatures. |
| `CommissionSplitter` | Splits commission payments per recorded agreement. Executes on close. |
| `CancellationRefundManager` | Handles refund logic when a deal cancels. Enforces refund conditions from PSA. |

### 3D. Shared Infrastructure

| Contract | Responsibility |
|---|---|
| `AccessController` | Role-based access (owner, contractor, inspector, closer, admin, oracle). Per-job and global roles. |
| `EmergencyPause` | Guardian-triggered pause. Freezes all state-changing operations across linked contracts. |
| `AuditEventAnchor` | Append-only on-chain log. Anchors event hashes for off-chain audit trail reconstruction. |
| `DocumentHashRegistry` | Stores document hashes (legal agreements, reports, photos). Maps hash → uploader, timestamp, doc type. |
| `PaymentRouter` | Routes USDC payments. Handles splits, fee deductions, and multi-party disbursements. |
| `OracleVerificationHub` | Validates oracle signatures. Enforces quorum, freshness, and replay protection. See Section 8. |

### 3E. Optional Advanced Rails (Phase 4)

| Contract | Responsibility |
|---|---|
| `PropertyNFT` | ERC-721 representing property ownership record. Minted post-close. |
| `FractionalOwnership` | ERC-1400 compliant fractional interests. Requires investor whitelist. |
| `InvestorWhitelist` | KYC/accreditation gate. Oracle-fed or manual admin attestation. |
| `DAOApprovalGate` | Governance voting for major decisions (property acquisition, large disbursements). |

---

## 4. Trust Boundary Matrix

Every action in the system falls into exactly one trust category.

### On-chain Authoritative

These states are determined solely by on-chain logic. The chain is the source of truth.

| Action | Contract | Notes |
|---|---|---|
| Payment release state | `JobEscrow`, `ClosingEscrow`, `EarnestMoneyEscrow` | Funds move only when on-chain conditions are met |
| Audit anchor records | `AuditEventAnchor` | Append-only, immutable once written |
| Role permissions | `AccessController` | On-chain role assignment and enforcement |
| Retainage hold/release | `RetainageVault` | Time-locked, condition-gated |
| Commission split execution | `CommissionSplitter` | Executes per recorded on-chain agreement |
| Pause state | `EmergencyPause` | On-chain guardian control |

### Off-chain Authoritative

The signed document or off-chain system is the source of truth. On-chain stores only a hash or reference.

| Action | Source | On-chain Record |
|---|---|---|
| Signed contract PDFs | DocuSign / wet-ink | `DocumentHashRegistry` stores hash |
| Inspection reports | Licensed inspector | `DocumentHashRegistry` stores hash |
| Title documents | Title company | `DocumentHashRegistry` stores hash |
| Legal terms and conditions | Attorney-drafted agreements | Hash only; never on-chain |
| KYC/accreditation records | Compliance provider | `InvestorWhitelist` stores pass/fail attestation |

### Dual-confirmed

Both on-chain and off-chain systems must agree. Neither alone is sufficient.

| Action | Off-chain Source | On-chain Gate |
|---|---|---|
| Permit status | Municipal authority via signed adapter | `PermitInspectionRegistry` records oracle attestation |
| Inspection pass/fail | Licensed inspector via signed relay | `PermitInspectionRegistry` records oracle attestation |
| Clear-to-close state | Title agent / closing counsel | `TitleConditionRegistry` records signed update |
| Milestone completion | Contractor submits + owner inspects | `MilestoneManager` records both attestations |
| Change order approval | Both parties sign off-chain | `ChangeOrderManager` records dual on-chain signatures |

### Human-only Override

These actions cannot be automated. They require explicit human authorization with off-chain justification.

| Action | Who | Mechanism |
|---|---|---|
| Dispute initiation | Any party | `DisputeResolution` — requires signed filing |
| Emergency pause | Guardian (multisig) | `EmergencyPause` — multisig transaction |
| Contract cancellation with cause | Authorized party | Off-chain notice + on-chain state transition by admin |
| Upgrade execution | Timelock admin (multisig) | Timelock delay + multisig execution |
| Oracle key rotation | System admin (multisig) | `OracleVerificationHub` — multisig-gated |
| Retainage override | Owner + legal counsel | `RetainageVault` — multisig with documented reason |

---

## 5. State Machine Definitions

Every major contract family has explicit lifecycle states. Transitions are enforced on-chain. Invalid transitions revert.

### 5A. Construction Job Lifecycle

```
Draft
  │
  ▼ sign()
Signed
  │
  ▼ issueNTP()
NoticeToProceedPending
  │
  ▼ confirmNTP()
Active
  │
  ├──▶ submitMilestone() ──▶ MilestoneSubmitted
  │                              │
  │                    approveMilestone() ──▶ MilestoneApproved ──▶ [back to Active]
  │                              │
  │                    rejectMilestone() ──▶ [back to Active]
  │
  ├──▶ submitChangeOrder() ──▶ [ChangeOrder sub-flow]
  │
  ▼ declareSubstantialCompletion()
SubstantiallyComplete
  │
  ▼ completePunchlist() + releaseFinalRetainage()
Closed
```

**Terminal states:** `Closed`, `Terminated`, `Disputed`

**Side transitions from any active state:**
- `dispute()` → `Disputed` (freezes escrow)
- `terminate()` → `Terminated` (requires admin + documented cause)

**State enum:**
```solidity
enum JobState {
    Draft,              // 0
    Signed,             // 1
    NTPPending,         // 2
    Active,             // 3
    MilestoneSubmitted, // 4
    MilestoneApproved,  // 5
    SubstantiallyComplete, // 6
    Closed,             // 7
    Disputed,           // 8
    Terminated          // 9
}
```

### 5B. Real Estate Closing Lifecycle

```
Draft
  │
  ▼ executePSA()
Executed
  │
  ▼ fundEarnest()
EarnestFunded
  │
  ▼ [contingencies being resolved]
ContingenciesOpen
  │
  ▼ allContingenciesCleared()
ClearToClose
  │
  ▼ executeClose()
Closed
```

**Terminal states:** `Closed`, `Cancelled`, `Disputed`

**Side transitions:**
- `cancel()` → `Cancelled` (triggers `CancellationRefundManager`)
- `dispute()` → `Disputed` (freezes all escrows)
- `refund()` → `Refunded` (only from `Cancelled`, after refund conditions met)

**State enum:**
```solidity
enum ClosingState {
    Draft,              // 0
    Executed,           // 1
    EarnestFunded,      // 2
    ContingenciesOpen,  // 3
    ClearToClose,       // 4
    Closed,             // 5
    Cancelled,          // 6
    Refunded,           // 7
    Disputed            // 8
}
```

### 5C. Change Order Lifecycle

```
Proposed
  │
  ├──▶ ownerApprove() ──▶ OwnerApproved
  │                          │
  │              contractorConfirm() ──▶ Executed
  │
  ├──▶ contractorApprove() ──▶ ContractorApproved
  │                               │
  │                   ownerConfirm() ──▶ Executed
  │
  ▼ reject()
Rejected
```

**State enum:**
```solidity
enum ChangeOrderState {
    Proposed,           // 0
    OwnerApproved,      // 1
    ContractorApproved, // 2
    Executed,           // 3
    Rejected            // 4
}
```

### 5D. Dispute Lifecycle

```
Filed
  │
  ▼ assignArbitrator()
UnderReview
  │
  ├──▶ resolveForClaimant() ──▶ ResolvedForClaimant
  ├──▶ resolveForRespondent() ──▶ ResolvedForRespondent
  ▼ settleMutually()
Settled
```

### 5E. Earnest Money Lifecycle

```
Unfunded
  │
  ▼ deposit()
Funded
  │
  ├──▶ releaseToSeller() ──▶ ReleasedToSeller    (on close)
  ▼ returnToBuyer()
ReturnedToBuyer                                   (on cancellation)
```

---

## 6. Canonical Event Schema

All contracts emit events following a standard structure. Events are the primary interface for the off-chain indexer and audit system.

### 6A. Event Naming Convention

```
{Domain}{Action}
```

- Domain: `Job`, `Milestone`, `ChangeOrder`, `Payment`, `Permit`, `Inspection`, `Closing`, `Document`, `Access`, `System`
- Action: `Created`, `Updated`, `Submitted`, `Approved`, `Rejected`, `Released`, `Anchored`, `Paused`, `Resumed`

### 6B. Standard Event Fields

Every event includes:

```solidity
// Standard indexed fields present in all events:
// - bytes32 indexed entityId    (job ID, property ID, etc.)
// - address indexed actor       (who triggered the action)
// - uint256 timestamp           (block.timestamp)
```

### 6C. Core Event Catalog

#### Construction Domain

```solidity
event JobCreated(bytes32 indexed jobId, address indexed owner, address indexed contractor, bytes32 metadataHash);
event JobStateChanged(bytes32 indexed jobId, address indexed actor, JobState fromState, JobState toState);
event MilestoneCreated(bytes32 indexed jobId, uint256 indexed milestoneIndex, bytes32 descriptionHash, uint256 amount);
event MilestoneSubmitted(bytes32 indexed jobId, uint256 indexed milestoneIndex, address indexed contractor, bytes32 evidenceHash);
event MilestoneApproved(bytes32 indexed jobId, uint256 indexed milestoneIndex, address indexed approver);
event MilestoneRejected(bytes32 indexed jobId, uint256 indexed milestoneIndex, address indexed rejector, bytes32 reasonHash);
event PaymentReleased(bytes32 indexed jobId, address indexed recipient, uint256 amount, bytes32 invoiceHash);
event ChangeOrderProposed(bytes32 indexed jobId, uint256 indexed changeOrderIndex, address indexed proposer, int256 amountDelta, bytes32 descriptionHash);
event ChangeOrderApproved(bytes32 indexed jobId, uint256 indexed changeOrderIndex, address indexed approver);
event ChangeOrderExecuted(bytes32 indexed jobId, uint256 indexed changeOrderIndex);
event RetainageHeld(bytes32 indexed jobId, uint256 amount);
event RetainageReleased(bytes32 indexed jobId, address indexed recipient, uint256 amount);
event LienWaiverAnchored(bytes32 indexed jobId, uint256 indexed paymentIndex, bytes32 waiverHash, address indexed signer);
event SubcontractorPaymentRouted(bytes32 indexed jobId, address indexed subcontractor, uint256 amount);
```

#### Compliance Domain

```solidity
event PermitRecorded(bytes32 indexed jobId, bytes32 indexed permitId, bytes32 permitHash, address indexed oracle);
event InspectionRecorded(bytes32 indexed jobId, bytes32 indexed inspectionId, bool passed, address indexed oracle);
event DisputeFiled(bytes32 indexed entityId, address indexed claimant, bytes32 reasonHash);
event DisputeResolved(bytes32 indexed entityId, address indexed arbitrator, uint8 outcome);
```

#### Real Estate Domain

```solidity
event PropertyRegistered(bytes32 indexed propertyId, bytes32 indexed parcelId, bytes32 metadataHash);
event PSAExecuted(bytes32 indexed propertyId, bytes32 psaHash, address indexed buyer, address indexed seller);
event EarnestDeposited(bytes32 indexed propertyId, address indexed buyer, uint256 amount);
event EarnestReleased(bytes32 indexed propertyId, address indexed recipient, uint256 amount, bytes32 reason);
event ContingencyCleared(bytes32 indexed propertyId, bytes32 indexed contingencyId, address indexed clearedBy);
event ClearToCloseUpdated(bytes32 indexed propertyId, bool ready, address indexed updater);
event ClosingExecuted(bytes32 indexed propertyId, uint256 totalDisbursed, bytes32 closingStatementHash);
event ClosingCancelled(bytes32 indexed propertyId, address indexed cancelledBy, bytes32 reasonHash);
event TitleConditionUpdated(bytes32 indexed propertyId, bytes32 indexed conditionId, bool cleared, address indexed oracle);
event DisclosureAcknowledged(bytes32 indexed propertyId, bytes32 disclosureHash, address indexed acknowledger);
event CommissionDisbursed(bytes32 indexed propertyId, address indexed agent, uint256 amount);
```

#### Infrastructure Domain

```solidity
event DocumentAnchored(bytes32 indexed entityId, bytes32 indexed documentHash, address indexed uploader, uint8 docType);
event AuditEventRecorded(bytes32 indexed entityId, bytes32 indexed eventHash, address indexed recorder, uint256 sequence);
event RoleGranted(bytes32 indexed entityId, address indexed account, bytes32 indexed role, address grantor);
event RoleRevoked(bytes32 indexed entityId, address indexed account, bytes32 indexed role, address revoker);
event PauseTriggered(address indexed guardian, bytes32 reasonHash);
event PauseLifted(address indexed guardian);
event OracleAttestationRecorded(bytes32 indexed entityId, address indexed oracle, bytes32 dataHash, uint256 timestamp);
```

### 6D. Event Indexer Requirements

The off-chain indexer must:

1. Subscribe to all events from all deployed contracts
2. Store events in a normalized relational schema
3. Maintain a `sequence_number` per entity for ordering
4. Expose a read API for dashboards, audit exports, and compliance queries
5. Support replay from any block number for disaster recovery
6. Validate event signatures against known contract addresses

---

## 7. Role Matrix

### 7A. Global Roles

| Role | Description | Assigned By |
|---|---|---|
| `SYSTEM_ADMIN` | Deploy, upgrade (via timelock), rotate oracle keys | Multisig |
| `GUARDIAN` | Emergency pause/unpause | Multisig |
| `ORACLE_SIGNER` | Submit oracle attestations | `SYSTEM_ADMIN` via `OracleVerificationHub` |

### 7B. Per-Job Roles (Construction)

| Role | Description | Assigned By |
|---|---|---|
| `JOB_OWNER` | Creates job, approves milestones, approves change orders | Self (on creation) |
| `CONTRACTOR` | Submits milestones, proposes change orders | `JOB_OWNER` |
| `INSPECTOR` | Submits inspection results (if not oracle-fed) | `JOB_OWNER` or `SYSTEM_ADMIN` |
| `SUBCONTRACTOR` | Linked to sub-milestones, receives routed payments | `CONTRACTOR` |

### 7C. Per-Property Roles (Closings)

| Role | Description | Assigned By |
|---|---|---|
| `BUYER` | Deposits earnest, acknowledges disclosures | Self (on PSA execution) |
| `SELLER` | Receives proceeds on close | Self (on PSA execution) |
| `CLOSING_AGENT` | Updates contingency states, executes close | `BUYER` + `SELLER` agreement |
| `TITLE_AGENT` | Updates title conditions | `CLOSING_AGENT` or oracle |
| `LISTING_AGENT` | Receives commission split | Recorded in `CommissionSplitter` |
| `BUYERS_AGENT` | Receives commission split | Recorded in `CommissionSplitter` |

---

## 8. Oracle Model

### 8A. Oracle-fed Data Sources

| Data | Source Adapter | Signer Quorum | Freshness Window |
|---|---|---|---|
| Permit issuance status | Municipal API signed adapter | 1-of-1 (designated municipal relay) | 24 hours |
| Inspection pass/fail | Licensed inspector signed relay | 1-of-1 (credentialed inspector) | 48 hours |
| Title condition status | Title agent / closing counsel signed update | 1-of-1 (credentialed title agent) | 72 hours |
| Property valuation | Chainlink data feed OR approved appraiser | 1-of-1 (Chainlink) or 2-of-3 (appraiser panel) | 30 days |
| KYC/accreditation | Compliance provider attestation | 1-of-1 (approved provider) | 365 days |
| USDC price | Chainlink USDC/USD feed | Chainlink native | 1 hour |

### 8B. Oracle Verification Contract (`OracleVerificationHub`)

```solidity
struct OracleConfig {
    address[] signers;           // approved signer addresses
    uint8 quorum;                // minimum signatures required
    uint256 freshnessWindow;     // max age in seconds
    bool active;                 // can be deactivated without removal
}

// Key functions:
function registerOracle(bytes32 oracleType, OracleConfig calldata config) external onlyRole(SYSTEM_ADMIN);
function submitAttestation(bytes32 oracleType, bytes32 entityId, bytes32 dataHash, bytes calldata signatures) external;
function isAttestationValid(bytes32 oracleType, bytes32 entityId) external view returns (bool);
```

### 8C. Replay Protection

- Each attestation includes a monotonically increasing `nonce` per `(oracleType, entityId)` pair
- The contract rejects any attestation with a nonce <= the last recorded nonce
- Attestations include `block.chainid` to prevent cross-chain replay

### 8D. Failure Mode: Missing Oracle Input

When oracle input is required but missing or stale:

1. The gated action **cannot proceed** (fail closed)
2. An `OracleInputStale` event is emitted with the entity ID and oracle type
3. The `GUARDIAN` may invoke emergency override **only** via multisig with a documented reason hash
4. The override is recorded in `AuditEventAnchor` as a human-only override

---

## 9. Upgradeability Policy

### 9A. What Is Upgradeable

| Contract Category | Upgrade Strategy | Rationale |
|---|---|---|
| `AccessController` | UUPS proxy + 48-hour timelock | Core access logic may need role additions |
| `PaymentRouter` | UUPS proxy + 48-hour timelock | Payment routing rules evolve with business needs |
| `JobRegistry`, `PropertyRegistry` | UUPS proxy + 48-hour timelock | Schema may evolve; data preserved via proxy storage |
| `MilestoneManager`, `ChangeOrderManager` | UUPS proxy + 48-hour timelock | Business logic refinement expected |
| `OracleVerificationHub` | UUPS proxy + 48-hour timelock | Oracle configs and verification logic may change |
| Escrow contracts (`JobEscrow`, `ClosingEscrow`, `EarnestMoneyEscrow`) | UUPS proxy + 72-hour timelock | Longer delay because funds are at risk |
| `CommissionSplitter`, `CancellationRefundManager` | UUPS proxy + 48-hour timelock | Disbursement logic refinement |

### 9B. What Is Immutable

| Contract | Rationale |
|---|---|
| `AuditEventAnchor` | Audit integrity requires immutability. Once deployed, behavior never changes. |
| `DocumentHashRegistry` | Document hash records are permanent evidence. Logic is trivial and must not change. |
| `EmergencyPause` | Pause mechanism must be trustworthy and unchangeable. |

### 9C. Who Can Upgrade

- **Proposer:** `SYSTEM_ADMIN` multisig (3-of-5 recommended)
- **Timelock:** 48 hours standard, 72 hours for escrow contracts
- **Cancellation:** Any multisig signer can cancel a pending upgrade during the timelock window
- **Emergency:** `GUARDIAN` can freeze the timelock (preventing execution) but cannot bypass it

### 9D. Upgrade Process

1. `SYSTEM_ADMIN` multisig proposes upgrade with new implementation address
2. Timelock period begins; `UpgradeScheduled` event emitted
3. Community / operators can review the new implementation
4. After timelock expires, any multisig signer executes the upgrade
5. `UpgradeExecuted` event emitted with old and new implementation addresses
6. Post-upgrade: verify storage layout compatibility, run integration tests

### 9E. Migration Path

If a contract must be replaced entirely (not upgraded):

1. Deploy new contract
2. Pause the old contract
3. Migrate state via admin script (read from old, write to new)
4. Update references in dependent contracts via their upgrade mechanisms
5. Unpause the new contract
6. Old contract remains paused indefinitely as a read-only archive

### 9F. Tokenization Rails: Separate Upgrade Domain

Phase 4 contracts (`PropertyNFT`, `FractionalOwnership`, `InvestorWhitelist`, `DAOApprovalGate`) operate under a separate upgrade authority. This prevents tokenization governance decisions from affecting core operational contracts.

---

## 10. Off-chain Orchestration Boundaries

The smart contracts are half the system. Off-chain services orchestrate them.

### 10A. Service Map

```
┌─────────────────────────────────────────────────────────┐
│                    Off-chain Services                    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   FastAPI     │  │   Temporal   │  │   Signer     │  │
│  │   Gateway     │  │   Workflows  │  │   Service    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐  │
│  │   Indexer /   │  │   IPFS /     │  │   Oracle     │  │
│  │   Read Model  │  │   Arweave    │  │   Adapters   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
                     ┌──────┴───────┐
                     │  Arbitrum    │
                     │  Contracts   │
                     └──────────────┘
```

### 10B. FastAPI Gateway

**Responsibility:** HTTP API for all client-facing reads and writes.

| Operation | Direction | Details |
|---|---|---|
| Create job | Write → chain | Validates input, constructs transaction, sends via signer service |
| Submit milestone evidence | Write → IPFS + chain | Uploads evidence to IPFS, then calls `MilestoneManager.submit()` |
| Get job status | Read ← indexer | Reads from indexed event database, not from chain |
| Get audit trail | Read ← indexer | Reconstructs timeline from indexed events |
| Upload document | Write → IPFS + chain | Stores file on IPFS, anchors hash via `DocumentHashRegistry` |
| Dashboard data | Read ← indexer | Aggregated views for operator dashboards |

### 10C. Temporal Workflows

**Responsibility:** Long-running, durable orchestration of multi-step processes.

| Workflow | Steps | Failure Handling |
|---|---|---|
| `JobCreationWorkflow` | Validate → create on-chain → index → notify | Retry on-chain submission with exponential backoff |
| `MilestoneApprovalWorkflow` | Verify evidence → notify owner → await approval → release payment | Timeout after configurable period → escalate |
| `ChangeOrderWorkflow` | Propose → notify both parties → await dual sign-off → execute | Expire after 14 days if not fully approved |
| `ClosingWorkflow` | PSA executed → earnest funded → contingencies tracked → clear-to-close → disburse | Each step is a Temporal activity with idempotent on-chain calls |
| `DisputeWorkflow` | File → freeze funds → assign arbitrator → await resolution → release | Human-in-the-loop activity for arbitrator decision |
| `OraclePollingWorkflow` | Poll municipal API → sign attestation → submit on-chain | Retry with backoff; alert on repeated failure |

### 10D. Signer Service

**Responsibility:** Holds private keys. Signs and submits transactions.

- Runs in an isolated environment (HSM or cloud KMS)
- Receives unsigned transaction payloads from FastAPI or Temporal
- Signs with the appropriate key based on role
- Submits to Arbitrum RPC with gas management and nonce tracking
- Never exposes private keys to other services

### 10E. Evidence Storage (IPFS / Arweave)

**Responsibility:** Store and pin evidence artifacts.

| Artifact Type | Storage | On-chain Record |
|---|---|---|
| Milestone evidence (photos, reports) | IPFS (pinned) + Arweave (permanent) | `MilestoneManager` stores IPFS CID hash |
| Legal documents (PDFs) | IPFS (pinned) + Arweave (permanent) | `DocumentHashRegistry` stores content hash |
| Inspection reports | IPFS (pinned) | `PermitInspectionRegistry` stores hash |
| Lien waivers | IPFS (pinned) | `LienWaiverRegistry` stores hash |

### 10F. Indexer / Read Model

**Responsibility:** Build a queryable database from on-chain events.

- Listens to all contract events on Arbitrum
- Writes to PostgreSQL with normalized schema
- Maintains entity-level state by replaying events
- Exposes read API consumed by FastAPI Gateway
- Supports reindexing from any block number
- Stores raw event data alongside computed state

---

## 11. System of Record

For every data type in the system, exactly one source of truth is defined.

| Data | Source of Truth | On-chain Role | Off-chain Role |
|---|---|---|---|
| Legal agreements | Signed PDF (DocuSign or wet-ink) | `DocumentHashRegistry` stores hash | IPFS/Arweave stores file |
| Job operational state | On-chain `JobRegistry` state enum | Authoritative | Indexer mirrors for queries |
| Milestone status | On-chain `MilestoneManager` | Authoritative | Indexer mirrors for queries |
| Disbursement authorization | On-chain escrow contracts | Authoritative | FastAPI triggers, signer executes |
| Evidence artifacts | IPFS file (content-addressed) | Hash anchored in relevant contract | IPFS/Arweave stores actual file |
| Identity and permissions | On-chain `AccessController` | Role assignments authoritative | Off-chain KYC feeds into `InvestorWhitelist` |
| Permit and inspection data | Municipal authority (off-chain) | `PermitInspectionRegistry` stores oracle attestation | Oracle adapter polls/receives from municipal system |
| Title conditions | Title company (off-chain) | `TitleConditionRegistry` stores oracle attestation | Title agent signs update |
| Financial records | Off-chain accounting system | On-chain payment events are evidence | Accounting system is authoritative for tax/reporting |
| User contact info | Off-chain CRM / database | Not stored on-chain | CRM is authoritative |
| Token ownership | On-chain token contract | Authoritative (Phase 4 only) | Indexer mirrors for queries |

---

## 12. Phased Delivery Plan

### Phase 1 — Core Operations (Weeks 1-6)

Ship the minimum viable money-control and audit infrastructure.

| Contract | Priority | Dependencies |
|---|---|---|
| `AccessController` | P0 | None |
| `EmergencyPause` | P0 | `AccessController` |
| `DocumentHashRegistry` | P0 | `AccessController` |
| `AuditEventAnchor` | P0 | `AccessController` |
| `PaymentRouter` | P0 | `AccessController` |
| `JobRegistry` | P0 | `AccessController` |
| `JobEscrow` | P0 | `AccessController`, `PaymentRouter` |
| `MilestoneManager` | P0 | `JobRegistry`, `JobEscrow`, `AccessController` |
| `ChangeOrderManager` | P1 | `JobRegistry`, `JobEscrow`, `MilestoneManager` |

**Deliverable:** A contractor can create a job, fund escrow, submit milestones, get approvals, and receive payment. All actions are logged and auditable. Emergency pause works.

**Off-chain in Phase 1:** FastAPI gateway, signer service, IPFS integration, basic indexer.

### Phase 2 — Construction Compliance (Weeks 7-10)

Add compliance gates that block disbursement without proper documentation.

| Contract | Priority | Dependencies |
|---|---|---|
| `PermitInspectionRegistry` | P0 | `OracleVerificationHub`, `AccessController` |
| `OracleVerificationHub` | P0 | `AccessController` |
| `LienWaiverRegistry` | P0 | `JobEscrow`, `AccessController` |
| `RetainageVault` | P1 | `JobEscrow`, `MilestoneManager` |
| `SubcontractorFlow` | P1 | `JobEscrow`, `MilestoneManager`, `PaymentRouter` |
| `WarrantyPunchlist` | P2 | `RetainageVault` |
| `DisputeResolution` | P2 | `JobEscrow`, `AccessController` |

**Deliverable:** Jobs require lien waivers before payment release. Permit and inspection status is oracle-verified. Retainage is held and released per contract terms. Subcontractor payments flow down.

**Off-chain in Phase 2:** Oracle adapters for municipal APIs, Temporal workflows for milestone approval and dispute handling.

### Phase 3 — Real Estate Closing Rails (Weeks 11-16)

Extend to real estate transaction lifecycle.

| Contract | Priority | Dependencies |
|---|---|---|
| `PropertyRegistry` | P0 | `AccessController` |
| `PurchaseSaleAgreement` | P0 | `PropertyRegistry`, `DocumentHashRegistry` |
| `EarnestMoneyEscrow` | P0 | `PropertyRegistry`, `PaymentRouter` |
| `ClosingEscrow` | P0 | `PropertyRegistry`, `PaymentRouter` |
| `TitleConditionRegistry` | P1 | `OracleVerificationHub`, `PropertyRegistry` |
| `DisclosureAcknowledgement` | P1 | `PropertyRegistry`, `DocumentHashRegistry` |
| `CommissionSplitter` | P1 | `ClosingEscrow`, `PaymentRouter` |
| `CancellationRefundManager` | P2 | `EarnestMoneyEscrow` |

**Deliverable:** A real estate transaction flows from PSA execution through earnest deposit, contingency clearance, clear-to-close, and final disbursement. Cancellation and refund paths work.

**Off-chain in Phase 3:** Closing workflow in Temporal, title agent oracle adapter, enhanced indexer with property views.

### Phase 4 — Optional Advanced Rails (Weeks 17+)

Only after Phases 1-3 are production-stable and generating revenue.

| Contract | Priority | Dependencies |
|---|---|---|
| `PropertyNFT` | P1 | `PropertyRegistry`, `ClosingEscrow` |
| `FractionalOwnership` | P2 | `PropertyNFT`, `InvestorWhitelist` |
| `InvestorWhitelist` | P1 | `OracleVerificationHub` |
| `DAOApprovalGate` | P3 | `AccessController` |

**Deliverable:** Properties can be tokenized as NFTs post-close. Fractional ownership with accredited investor gating. DAO governance for major decisions.

**This phase has a separate upgrade domain and separate audit scope.**

---

## 13. Audit Readiness Checklist

Before mainnet (production Arbitrum) deployment of any phase:

### Code Quality

- [ ] All contracts compile without warnings on Solidity 0.8.x
- [ ] 100% line coverage on unit tests
- [ ] Fuzz tests for all arithmetic and state transition functions
- [ ] Invariant tests for all escrow balance properties
- [ ] Static analysis clean (Slither, no high/medium findings)

### Access Control

- [ ] Role abuse tests: every function tested with unauthorized caller (must revert)
- [ ] Role escalation tests: no path from lower role to higher role
- [ ] Admin key rotation tested
- [ ] Multisig threshold tested (cannot execute below quorum)

### Escrow and Payment

- [ ] Escrow release tests: funds only move on valid approval path
- [ ] Escrow cannot be drained by any single role
- [ ] Partial release tests: milestone-by-milestone disbursement works
- [ ] Retainage hold and release timing tested
- [ ] USDC decimal handling tested (6 decimals)
- [ ] Payment router split accuracy tested (no dust loss beyond 1 wei)

### Emergency Controls

- [ ] Pause/unpause tests: all state-changing functions blocked when paused
- [ ] Pause does not block view functions
- [ ] Pause does not lock funds permanently (unpause path exists)
- [ ] Upgrade timelock tested: cannot execute before delay expires
- [ ] Upgrade cancellation tested

### Oracle

- [ ] Oracle replay protection tested (reused nonce rejected)
- [ ] Oracle freshness tested (stale attestation rejected)
- [ ] Oracle quorum tested (below-quorum rejected)
- [ ] Missing oracle input tested (gated action fails closed)
- [ ] Oracle key rotation tested (old key rejected after rotation)

### Events

- [ ] Every state change emits the correct event
- [ ] Event parameters match actual state changes
- [ ] No state change is silent (missing event)
- [ ] Indexer can reconstruct full entity state from events alone

### Upgrade Safety

- [ ] Storage layout compatibility verified between versions
- [ ] No storage collisions with proxy
- [ ] Initializer cannot be called twice
- [ ] Implementation contract cannot be initialized directly

### Legal and Compliance

- [ ] Legal mapping review: each contract's on-chain behavior mapped to legal agreement terms
- [ ] Document hash flow tested end-to-end (upload → IPFS → anchor → verify)
- [ ] Lien waiver gating tested (payment blocked without waiver)
- [ ] Contingency flow tested (closing blocked with uncleared contingencies)

### Operational Security

- [ ] Signer key management review (HSM / KMS)
- [ ] Multisig signer operational procedures documented
- [ ] Emergency runbook documented and tested
- [ ] Monitoring and alerting configured for critical events
- [ ] Gas estimation and funding strategy for signer wallets

---

## 14. Contract Dependency Graph

```
AccessController ◄──────────────────────────────────────────────────┐
  │                                                                  │
  ├──► EmergencyPause                                                │
  ├──► DocumentHashRegistry                                          │
  ├──► AuditEventAnchor                                              │
  ├──► PaymentRouter ◄────────────────────────────────┐              │
  │      │                                             │              │
  ├──► JobRegistry                                     │              │
  │      │                                             │              │
  │      ├──► JobEscrow ──────────────────────► PaymentRouter         │
  │      │      │                                                     │
  │      │      ├──► RetainageVault                                   │
  │      │      └──► LienWaiverRegistry                               │
  │      │                                                            │
  │      ├──► MilestoneManager ──► JobEscrow                          │
  │      │      │                                                     │
  │      │      └──► SubcontractorFlow ──► PaymentRouter              │
  │      │                                                            │
  │      └──► ChangeOrderManager ──► JobEscrow, MilestoneManager      │
  │                                                                   │
  ├──► OracleVerificationHub                                          │
  │      │                                                            │
  │      ├──► PermitInspectionRegistry                                │
  │      └──► TitleConditionRegistry                                  │
  │                                                                   │
  ├──► PropertyRegistry                                               │
  │      ├──► PurchaseSaleAgreement ──► DocumentHashRegistry          │
  │      ├──► EarnestMoneyEscrow ──► PaymentRouter                    │
  │      ├──► ClosingEscrow ──► PaymentRouter                         │
  │      │      └──► CommissionSplitter ──► PaymentRouter             │
  │      ├──► DisclosureAcknowledgement ──► DocumentHashRegistry      │
  │      └──► CancellationRefundManager ──► EarnestMoneyEscrow        │
  │                                                                   │
  ├──► DisputeResolution ──► JobEscrow, ClosingEscrow                 │
  └──► WarrantyPunchlist ──► RetainageVault                           │
                                                                      │
  Phase 4 (separate upgrade domain):                                  │
  PropertyNFT ──► PropertyRegistry                                    │
  InvestorWhitelist ──► OracleVerificationHub ─────────────────────────┘
  FractionalOwnership ──► PropertyNFT, InvestorWhitelist
  DAOApprovalGate ──► AccessController
```

---

## 15. What This Document Does NOT Cover

These items are out of scope for this spec and belong in separate documents:

- **Token economics:** NBPT token supply, vesting, burns, staking. See `tokenomics/`.
- **AI agent architecture:** Stephanie.ai, GCagent.ai, PermitStream.ai orchestration. Separate spec.
- **Frontend / dashboard design:** UI/UX for operator and client portals.
- **Legal opinion:** This spec describes technical enforcement. It does not constitute legal advice.
- **Gas optimization:** Deferred to implementation phase. Spec focuses on correctness first.
- **Cross-chain deployment:** This spec targets Arbitrum One. Multi-chain strategy is a separate decision.

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| NTP | Notice to Proceed — formal authorization to begin construction work |
| PSA | Purchase and Sale Agreement — legal contract between buyer and seller |
| Retainage | Percentage of payment withheld until substantial completion |
| Lien waiver | Document from contractor/sub waiving right to file a mechanic's lien for payment received |
| Substantial completion | Point at which the work is sufficiently complete for the owner to occupy/use |
| Punchlist | List of minor items to be completed or corrected after substantial completion |
| Clear-to-close | All contingencies satisfied; closing can proceed |
| Earnest money | Good-faith deposit from buyer demonstrating intent to purchase |
| UUPS | Universal Upgradeable Proxy Standard (EIP-1822) |
| HSM | Hardware Security Module — dedicated hardware for key management |
| CID | Content Identifier — IPFS content-addressed hash |
| Attestation | Signed statement from an oracle confirming off-chain data |

---

*This document is the canonical architecture spec for the NoblePort smart contract suite. It supersedes any prior concept documents. Implementation should follow the phased delivery plan in Section 12.*
