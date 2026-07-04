"""Declarative workflow definitions.

A workflow is an ordered list of steps; each step targets exactly one catalog
module. Risk handling is not declared here — the engine derives it from the
module's catalog entry, so a workflow cannot opt out of the human gate by
mislabeling a step.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Step:
    name: str
    module: str
    summary: str = ""


@dataclass(frozen=True)
class WorkflowDef:
    name: str
    description: str
    steps: tuple[Step, ...]


def _wf(name: str, description: str, *steps: Step) -> WorkflowDef:
    return WorkflowDef(name, description, tuple(steps))


WORKFLOWS: dict[str, WorkflowDef] = {w.name: w for w in (
    _wf("lead_to_estimate",
        "Intake a lead and produce a client-ready bid package",
        Step("capture", "intake.lead_capture", "Capture and normalize the lead"),
        Step("parse_property", "intake.property_parser", "Resolve property attributes"),
        Step("brief", "estimating.project_brief", "Generate the project brief"),
        Step("takeoff", "estimating.takeoff", "Quantity takeoff"),
        Step("cost", "estimating.cost_model", "Build the cost model"),
        Step("bid", "estimating.bid_package", "Assemble bid package for client")),

    _wf("permit_submission",
        "Prepare and file a municipal permit package",
        Step("intake", "permits.intake", "Detect jurisdiction and requirements"),
        Step("parse_docs", "permits.document_parser", "Parse supplied documents"),
        Step("checklist", "permits.checklist", "Build submission checklist"),
        Step("package", "permits.package_builder", "Assemble the package"),
        Step("compliance", "compliance.regulation_matcher", "Match against municipal code"),
        Step("file", "permits.submission", "File with the municipality"),
        Step("track", "permits.status_tracker", "Begin status polling")),

    _wf("awo_to_invoice",
        "Turn completed authorized work orders into a progress invoice",
        Step("awo_state", "jobs.awo_tracker", "Snapshot AWO completion state"),
        Step("build", "finance.invoice_builder", "Assemble the invoice"),
        Step("ledger", "finance.billing_state", "Emit billing ledger entries"),
        Step("reconcile", "finance.payment_reconcile", "Reconcile against payments")),

    _wf("subcontractor_payout",
        "Prepare a subcontractor payout for human multi-sig release",
        Step("reconcile", "finance.payment_reconcile", "Confirm funds and lien state"),
        Step("waiver", "compliance.lien_waiver", "Draft the lien waiver"),
        Step("release", "finance.payout_release",
             "Prepare payout — executes only via human multi-sig")),

    _wf("compliance_review",
        "Run a compliance sweep on an active project",
        Step("regs", "compliance.regulation_matcher", "Match applicable regulations"),
        Step("codes", "compliance.code_lookup", "Pull relevant code sections"),
        Step("licenses", "compliance.license_monitor", "Verify licenses and insurance"),
        Step("safety", "compliance.osha_checklist", "Generate safety checklist")),

    _wf("investor_onboarding",
        "Identity-gated investor onboarding for NBPT eligibility",
        Step("kyc", "intake.client_kyc", "Collect identity documents"),
        Step("zk_proof", "identity.zksbt_verifier", "Verify accreditation proof"),
        Step("registry", "identity.registry_bridge", "Stage on-chain identity record"),
        Step("simulate", "token.transfer_compliance", "Simulate transfer eligibility")),

    _wf("nbpt_mint_proposal",
        "Draft an NBPT mint/burn proposal for the human multi-sig",
        Step("state", "token.nbpt_state", "Read current supply state"),
        Step("draft", "token.mint_burn",
             "Draft proposal — execution is off-platform multi-sig only"),
        Step("audit", "platform.audit_log", "Anchor the proposal in the audit log")),

    _wf("daily_operations",
        "Daily field-operations rollup",
        Step("logs", "jobs.daily_log", "Collect daily field logs"),
        Step("schedule", "jobs.scheduler", "Refresh crew schedule"),
        Step("materials", "jobs.materials", "Update material delivery state"),
        Step("variance", "finance.budget_variance", "Compute budget variance"),
        Step("notify", "comms.notification_router", "Fan out internal notifications")),

    _wf("client_update",
        "Send a templated progress update to a client",
        Step("variance", "finance.budget_variance", "Summarize budget position"),
        Step("punch", "jobs.punch_list", "Summarize open punch items"),
        Step("send", "comms.client_updates", "Compose and send — approval gated")),

    _wf("property_due_diligence",
        "Real-estate acquisition due diligence",
        Step("parse", "intake.property_parser", "Resolve property attributes"),
        Step("valuation", "realestate.valuation", "Draft comparable valuation"),
        Step("diligence", "realestate.due_diligence", "Run diligence checklists"),
        Step("ledger", "realestate.property_ledger", "Record in portfolio ledger")),
)}
