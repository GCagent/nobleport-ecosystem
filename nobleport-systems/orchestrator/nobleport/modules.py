"""Canonical module catalog for the NoblePort nano-ecosystem.

Every capability in the platform is declared here as a ModuleSpec and loaded
into the ModuleRegistry at startup. Statuses mirror the operational-status
table in the repo README: LIVE modules serve traffic, STAGED modules are
registered but routed to simulation, and READ_ONLY modules may never emit
state-changing effects.

`risk` drives the HumanGate: any workflow step that touches a module with
risk HIGH or CRITICAL suspends until a human approves it. CRITICAL is
reserved for treasury/securities surfaces, which are additionally hard-blocked
from autonomous execution regardless of approval plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    LIVE = "LIVE"
    STAGED = "STAGED"
    READ_ONLY = "READ_ONLY"


class Risk(str, Enum):
    LOW = "LOW"          # informational, reversible
    MEDIUM = "MEDIUM"    # writes operational state
    HIGH = "HIGH"        # financial/legal exposure -> human gate
    CRITICAL = "CRITICAL"  # treasury/securities -> human multi-sig, never autonomous


@dataclass(frozen=True)
class ModuleSpec:
    name: str                      # unique dotted id, e.g. "permits.intake"
    cluster: str                   # domain cluster
    agent: str                     # owning agent
    status: Status
    risk: Risk = Risk.LOW
    description: str = ""
    tags: tuple[str, ...] = field(default=())


def _m(name: str, cluster: str, agent: str, status: Status, risk: Risk, desc: str,
       *tags: str) -> ModuleSpec:
    return ModuleSpec(name, cluster, agent, status, risk, desc, tuple(tags))


# ---------------------------------------------------------------------------
# Catalog — grouped by domain cluster. Keep names stable: they are workflow
# step targets and appear in audit logs.
# ---------------------------------------------------------------------------

CATALOG: tuple[ModuleSpec, ...] = (
    # -- Construction ingress & intake (LIVE per README) --------------------
    _m("intake.lead_capture", "intake", "stephanie", Status.LIVE, Risk.LOW,
       "Inbound lead capture from web, phone transcription, and referral feeds"),
    _m("intake.property_parser", "intake", "stephanie", Status.LIVE, Risk.LOW,
       "Property attribute parsing pipelines (parcel, zoning, assessor data)"),
    _m("intake.site_survey", "intake", "stephanie", Status.LIVE, Risk.LOW,
       "Site survey checklist generation and photo ingestion"),
    _m("intake.client_kyc", "intake", "cyborg", Status.STAGED, Risk.MEDIUM,
       "Client identity intake feeding the CyBorg identity layer"),

    # -- Scope & estimating (LIVE) ------------------------------------------
    _m("estimating.project_brief", "estimating", "stephanie", Status.LIVE, Risk.LOW,
       "Baseline project brief generation from intake data"),
    _m("estimating.takeoff", "estimating", "stephanie", Status.LIVE, Risk.LOW,
       "Quantity takeoff from plans and scope notes"),
    _m("estimating.cost_model", "estimating", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Assembly-based cost modeling with regional labor rates"),
    _m("estimating.bid_package", "estimating", "stephanie", Status.LIVE, Risk.HIGH,
       "Client-facing bid package assembly — human review before send"),
    _m("estimating.change_order", "estimating", "stephanie", Status.LIVE, Risk.HIGH,
       "Change-order pricing and client approval routing"),

    # -- Permits (PermitStream.ai, STAGED) -----------------------------------
    _m("permits.intake", "permits", "permitstream", Status.STAGED, Risk.LOW,
       "Permit application intake and jurisdiction detection"),
    _m("permits.document_parser", "permits", "permitstream", Status.STAGED, Risk.LOW,
       "Permit document parsing schemas (plans, forms, prior approvals)"),
    _m("permits.checklist", "permits", "permitstream", Status.STAGED, Risk.LOW,
       "Jurisdiction-specific submission checklist builder"),
    _m("permits.package_builder", "permits", "permitstream", Status.STAGED, Risk.MEDIUM,
       "Assembles submission-ready permit packages"),
    _m("permits.submission", "permits", "permitstream", Status.STAGED, Risk.HIGH,
       "Files packages with municipal portals — human sign-off required"),
    _m("permits.status_tracker", "permits", "permitstream", Status.STAGED, Risk.LOW,
       "Polls municipal systems for review status"),
    _m("permits.inspection_scheduler", "permits", "permitstream", Status.STAGED, Risk.MEDIUM,
       "Books inspections against project milestones"),

    # -- Compliance (GCagent.ai, STAGED) --------------------------------------
    _m("compliance.regulation_matcher", "compliance", "gcagent", Status.STAGED, Risk.LOW,
       "Municipal regulation text-matching routines"),
    _m("compliance.code_lookup", "compliance", "gcagent", Status.STAGED, Risk.LOW,
       "Building-code section retrieval by trade and jurisdiction"),
    _m("compliance.license_monitor", "compliance", "gcagent", Status.STAGED, Risk.MEDIUM,
       "Contractor license and insurance expiry monitoring"),
    _m("compliance.osha_checklist", "compliance", "gcagent", Status.STAGED, Risk.MEDIUM,
       "Site safety checklist generation and violation flagging"),
    _m("compliance.lien_waiver", "compliance", "gcagent", Status.STAGED, Risk.HIGH,
       "Lien waiver drafting — legal document, human gate"),
    _m("compliance.contract_review", "compliance", "gcagent", Status.STAGED, Risk.HIGH,
       "Contract clause extraction and risk flagging for counsel review"),

    # -- Jobs, AWOs & field ops (LIVE) ----------------------------------------
    _m("jobs.awo_tracker", "jobs", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Authorized-work-order tracking with Postgres write-ahead logging"),
    _m("jobs.scheduler", "jobs", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Crew and subcontractor schedule management"),
    _m("jobs.daily_log", "jobs", "stephanie", Status.LIVE, Risk.LOW,
       "Daily field log capture (weather, crew, progress, incidents)"),
    _m("jobs.punch_list", "jobs", "stephanie", Status.LIVE, Risk.LOW,
       "Punch-list tracking through closeout"),
    _m("jobs.materials", "jobs", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Material ordering state and delivery tracking"),
    _m("jobs.subcontractor_portal", "jobs", "stephanie", Status.STAGED, Risk.MEDIUM,
       "Subcontractor bid and document exchange portal"),

    # -- Invoicing & finance (LIVE workflow support, gated execution) ---------
    _m("finance.invoice_builder", "finance", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Progress-billing invoice assembly from AWO state"),
    _m("finance.billing_state", "finance", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Billing state management and ledger emission"),
    _m("finance.payment_reconcile", "finance", "stephanie", Status.LIVE, Risk.HIGH,
       "Payment reconciliation against ledger — human confirmation"),
    _m("finance.payout_release", "finance", "stephanie", Status.STAGED, Risk.CRITICAL,
       "Subcontractor payout release — treasury surface, never autonomous"),
    _m("finance.budget_variance", "finance", "stephanie", Status.LIVE, Risk.LOW,
       "Budget-vs-actual variance reporting"),

    # -- Real estate ----------------------------------------------------------
    _m("realestate.property_ledger", "realestate", "stephanie", Status.STAGED, Risk.MEDIUM,
       "Property portfolio ledger with document anchoring refs"),
    _m("realestate.valuation", "realestate", "stephanie", Status.STAGED, Risk.LOW,
       "Comparable-sales valuation drafts for underwriting"),
    _m("realestate.due_diligence", "realestate", "gcagent", Status.STAGED, Risk.MEDIUM,
       "Title, zoning, and encumbrance due-diligence checklists"),
    _m("realestate.avatar_concierge", "realestate", "stephanie", Status.STAGED, Risk.LOW,
       "Stephanie.ai live avatar concierge for property walkthroughs"),

    # -- Identity & security (CyBorg.ai, STAGED) ------------------------------
    _m("identity.registry_bridge", "identity", "cyborg", Status.STAGED, Risk.HIGH,
       "Bridge to on-chain ERC-3643 IdentityRegistry"),
    _m("identity.zksbt_verifier", "identity", "cyborg", Status.STAGED, Risk.HIGH,
       "Zero-knowledge accredited-investor proof verification"),
    _m("identity.session_monitor", "identity", "cyborg", Status.STAGED, Risk.LOW,
       "Anomalous session and access-pattern monitoring"),
    _m("identity.key_custody_audit", "identity", "cyborg", Status.STAGED, Risk.MEDIUM,
       "Key custody attestation and rotation audit trail"),

    # -- Token & treasury (STAGED / hard-blocked autonomous) ------------------
    _m("token.nbpt_state", "token", "cyborg", Status.READ_ONLY, Risk.LOW,
       "NBPT contract state reads (supply, holder counts)"),
    _m("token.mint_burn", "token", "cyborg", Status.STAGED, Risk.CRITICAL,
       "Human-gated mint/burn proposal drafting — multi-sig execution only"),
    _m("token.transfer_compliance", "token", "cyborg", Status.STAGED, Risk.HIGH,
       "Pre-trade ERC-3643 transfer compliance simulation"),
    _m("token.kuzo_quotes", "token", "cyborg", Status.READ_ONLY, Risk.LOW,
       "KUZO swap policy engine — simulated quotes only, execution disabled"),

    # -- Integrations ----------------------------------------------------------
    _m("integrations.solana_rail", "integrations", "cyborg", Status.READ_ONLY, Risk.LOW,
       "Solana USDC settlement rail observation (read-only)"),
    _m("integrations.ipfs_anchor", "integrations", "gcagent", Status.STAGED, Risk.LOW,
       "IPFS/Arweave document anchoring for audit artifacts"),
    _m("integrations.ens_resolver", "integrations", "cyborg", Status.LIVE, Risk.LOW,
       "nobleport.eth ENS record resolution and health checks"),
    _m("integrations.accounting_sync", "integrations", "stephanie", Status.STAGED, Risk.MEDIUM,
       "Ledger export to external accounting systems"),
    _m("integrations.muni_portal", "integrations", "permitstream", Status.STAGED, Risk.MEDIUM,
       "Municipal e-permit portal connectors"),

    # -- Avatar & communications ----------------------------------------------
    _m("avatar.session", "avatar", "stephanie", Status.STAGED, Risk.LOW,
       "Live avatar WebSocket session management"),
    _m("avatar.voice_synth", "avatar", "stephanie", Status.STAGED, Risk.LOW,
       "Stephanie.ai voice synthesis pipeline"),
    _m("comms.client_updates", "comms", "stephanie", Status.LIVE, Risk.MEDIUM,
       "Templated client progress updates — outbound requires approval"),
    _m("comms.notification_router", "comms", "stephanie", Status.LIVE, Risk.LOW,
       "Internal notification fan-out (email, dashboard, webhook)"),

    # -- Platform / observability ----------------------------------------------
    _m("platform.audit_log", "platform", "cyborg", Status.LIVE, Risk.LOW,
       "Append-only hash-chained audit logging"),
    _m("platform.health", "platform", "stephanie", Status.LIVE, Risk.LOW,
       "Module health checking and circuit-breaker state"),
    _m("platform.metrics", "platform", "stephanie", Status.LIVE, Risk.LOW,
       "Prometheus-format metrics emission"),
)


def catalog_by_agent(agent: str) -> tuple[ModuleSpec, ...]:
    return tuple(m for m in CATALOG if m.agent == agent)


def catalog_by_cluster(cluster: str) -> tuple[ModuleSpec, ...]:
    return tuple(m for m in CATALOG if m.cluster == cluster)
