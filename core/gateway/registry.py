"""Static source-of-truth for the NoblePort MCP topology.

This module is the single place that defines:
  * the five internal MCP agents and their hard boundaries,
  * the tools each agent exposes and the approval level each tool carries,
  * the 50 NoblePort modules and the source table each KPI requires.

The gateway seeds the database from these constants on startup (idempotent
upsert), so Python and Postgres can never drift. Every module defaults to
truth_label BLOCKED — it only flips to LIVE once a real source is wired into
the KPI snapshot worker.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# --- Approval levels -------------------------------------------------------
# L0  read-only
# L1  draft
# L2  internal update
# L3  customer / vendor-facing
# L4  money / legal / permit-critical (human approval required)
APPROVAL_LEVELS = ("L0", "L1", "L2", "L3", "L4")

# Levels at which an autonomous (unsigned) write must PARK for human approval
HUMAN_APPROVAL_LEVELS = frozenset({"L3", "L4"})


@dataclass(frozen=True)
class Agent:
    name: str
    owner_domain: str
    role: str
    boundary: str


@dataclass(frozen=True)
class Tool:
    agent_name: str
    tool_name: str
    module_name: str
    approval_level: str
    write_capable: bool = False
    audit_required: bool = True
    enabled: bool = False


@dataclass(frozen=True)
class Module:
    module_id: int
    module_name: str
    owner_agent: str
    kpi_name: str
    source_table: Optional[str]
    truth_label: str = "BLOCKED"


# --- Agents ----------------------------------------------------------------
AGENTS: tuple[Agent, ...] = (
    Agent("Stephanie.ai", "nobleport.ai", "Executive orchestrator / front door",
          "Routes, summarizes, recommends"),
    Agent("GCagent.ai", "gcagent.ai", "Construction execution, estimating, scope, field ops",
          "No permit approval, no legal signoff"),
    Agent("PermitStream.ai", "permitstream.ai", "Permit intake, AHJ rules, deficiency checks",
          "No stamped engineering judgment"),
    Agent("Cyborg.ai", "cyborg.ai", "Security, policy, compliance, risk gates",
          "No treasury movement"),
    Agent("Borg.ai", "borg.ai", "System automation, infrastructure, job runners",
          "No autonomous write without audit"),
    Agent("Kuzo.io", "kuzo.io", "Customer/vendor/project interface layer",
          "No source-of-truth mutation without validation"),
)

AGENT_NAMES = frozenset(a.name for a in AGENTS)


# --- Tools (approval level per tool) ---------------------------------------
TOOLS: tuple[Tool, ...] = (
    # GCagent.ai
    Tool("GCagent.ai", "gcagent.create_scope", "Scope Builder", "L1", write_capable=True),
    Tool("GCagent.ai", "gcagent.price_estimate", "Estimate Engine", "L1"),
    Tool("GCagent.ai", "gcagent.generate_awo", "AWO Engine", "L2", write_capable=True),
    Tool("GCagent.ai", "gcagent.update_job_cost", "Job Costing", "L2", write_capable=True),
    Tool("GCagent.ai", "gcagent.create_punch_list", "Punch List", "L2", write_capable=True),
    Tool("GCagent.ai", "gcagent.generate_closeout_package", "Closeout Package", "L3", write_capable=True),
    # PermitStream.ai
    Tool("PermitStream.ai", "permitstream.check_ahj_requirements", "AHJ Rules Engine", "L0"),
    Tool("PermitStream.ai", "permitstream.run_deficiency_scan", "Deficiency Checker", "L1"),
    Tool("PermitStream.ai", "permitstream.build_permit_checklist", "Document Checklist", "L1", write_capable=True),
    Tool("PermitStream.ai", "permitstream.flag_engineer_stamp", "Structural Stamp Tracker", "L2"),
    Tool("PermitStream.ai", "permitstream.schedule_inspection", "Inspection Scheduler", "L3", write_capable=True),
    Tool("PermitStream.ai", "permitstream.track_permit_status", "CO / Final Approval", "L0"),
    # Cyborg.ai
    Tool("Cyborg.ai", "cyborg.policy_check", "Policy Gate", "L0"),
    Tool("Cyborg.ai", "cyborg.security_scan_prompt", "Prompt Injection Defense", "L0"),
    Tool("Cyborg.ai", "cyborg.validate_tool_permission", "Tool Permission Guard", "L0"),
    Tool("Cyborg.ai", "cyborg.verify_vendor_docs", "Vendor Risk Check", "L2"),
    Tool("Cyborg.ai", "cyborg.score_project_risk", "Risk Score Engine", "L1"),
    Tool("Cyborg.ai", "cyborg.prewrite_audit_event", "AuditBeacon", "L2", write_capable=True),
    # Borg.ai
    Tool("Borg.ai", "borg.run_job", "Job Runner", "L2", write_capable=True),
    Tool("Borg.ai", "borg.check_worker_health", "Worker Health", "L0"),
    Tool("Borg.ai", "borg.monitor_queue", "Queue Monitor", "L0"),
    Tool("Borg.ai", "borg.verify_backup", "Backup Monitor", "L0"),
    Tool("Borg.ai", "borg.check_api_health", "API Health", "L0"),
    Tool("Borg.ai", "borg.process_file", "File Processing", "L2", write_capable=True),
    # Kuzo.io
    Tool("Kuzo.io", "kuzo.capture_lead", "Lead Intake", "L2", write_capable=True),
    Tool("Kuzo.io", "kuzo.update_customer_profile", "Customer Profile Engine", "L2", write_capable=True),
    Tool("Kuzo.io", "kuzo.send_customer_update", "Notification Center", "L3", write_capable=True),
    Tool("Kuzo.io", "kuzo.collect_document", "Document Checklist", "L2", write_capable=True),
    Tool("Kuzo.io", "kuzo.show_project_portal_status", "Project Registry", "L0"),
    Tool("Kuzo.io", "kuzo.capture_customer_approval", "Approval Queue", "L4", write_capable=True),
)


# --- 50 modules ------------------------------------------------------------
MODULES: tuple[Module, ...] = (
    # Executive / Platform layer
    Module(1, "Executive Command Center", "Stephanie.ai", "Daily decisions routed", "mcp_call_log"),
    Module(2, "Lead Intake", "Kuzo.io", "New leads captured", "leads"),
    Module(3, "Customer Profile Engine", "Kuzo.io", "Complete client profiles", "customers"),
    Module(4, "Project Registry", "Stephanie.ai", "Active projects", "workflow_states"),
    Module(5, "Workflow Router", "Stephanie.ai", "Correct routing rate", "mcp_call_log"),
    Module(6, "Approval Queue", "Cyborg.ai", "Pending human approvals", "workflow_states"),
    Module(7, "AuditBeacon", "Cyborg.ai", "% actions audit-logged", "audit_logs"),
    Module(8, "Truth Ledger", "Cyborg.ai", "LIVE/MODELED/BLOCKED ratio", "nobleport_module_registry"),
    Module(9, "Notification Center", "Kuzo.io", "Alerts acknowledged", "notifications"),
    Module(10, "KPI Dashboard", "Stephanie.ai", "Modules reporting live data", "kpi_snapshot"),
    # Construction / GCagent.ai layer
    Module(11, "Estimate Engine", "GCagent.ai", "Estimates created / week", "estimates"),
    Module(12, "Scope Builder", "GCagent.ai", "Scope line items generated", "scope_items"),
    Module(13, "AWO Engine", "GCagent.ai", "AWOs identified / approved / invoiced", "awo"),
    Module(14, "Job Costing", "GCagent.ai", "Actual vs budget variance", "job_cost"),
    Module(15, "Schedule Builder", "GCagent.ai", "Schedule slippage days", "project_tasks"),
    Module(16, "Subcontractor Manager", "GCagent.ai", "Sub response time", "vendor_comms"),
    Module(17, "Material Procurement", "GCagent.ai", "Materials ordered on time", "purchase_orders"),
    Module(18, "Field Daily Logs", "GCagent.ai", "Logs submitted per active job", "daily_logs"),
    Module(19, "Punch List", "GCagent.ai", "Open punch items", "punch_list"),
    Module(20, "Closeout Package", "GCagent.ai", "Closeout completion %", "closeout_docs"),
    # PermitStream.ai layer
    Module(21, "Permit Intake", "PermitStream.ai", "Permit packets started", "permit_intake"),
    Module(22, "AHJ Rules Engine", "PermitStream.ai", "Jurisdictions supported", "rulesets"),
    Module(23, "Deficiency Checker", "PermitStream.ai", "Issues found before submission", "deficiency_log"),
    Module(24, "Document Checklist", "PermitStream.ai", "Missing docs per permit", "doc_checklist"),
    Module(25, "Zoning Review", "PermitStream.ai", "Zoning risks flagged", "zoning_review"),
    Module(26, "Conservation Trigger", "PermitStream.ai", "Wetland/flood flags", "environmental_data"),
    Module(27, "Structural Stamp Tracker", "PermitStream.ai", "Engineering stamps required", "permit_requirements"),
    Module(28, "Inspection Scheduler", "PermitStream.ai", "Inspections scheduled/pass/fail", "inspections"),
    Module(29, "Rejection Tracker", "PermitStream.ai", "Rejections prevented / received", "ahj_responses"),
    Module(30, "CO / Final Approval", "PermitStream.ai", "Final approvals received", "permit_status"),
    # Security / Cyborg.ai layer
    Module(31, "Policy Gate", "Cyborg.ai", "Policy checks passed/failed", "policy_events"),
    Module(32, "Identity / Role Access", "Cyborg.ai", "Unauthorized attempts blocked", "auth_logs"),
    Module(33, "Prompt Injection Defense", "Cyborg.ai", "Suspicious prompts blocked", "ai_security_logs"),
    Module(34, "Tool Permission Guard", "Cyborg.ai", "Denied tool calls", "mcp_policy_logs"),
    Module(35, "Treasury Firewall", "Cyborg.ai", "Unauthorized treasury attempts", "treasury_events"),
    Module(36, "Vendor Risk Check", "Cyborg.ai", "Vendors missing docs", "vendor_compliance"),
    Module(37, "Insurance / License Tracker", "Cyborg.ai", "Expired docs", "compliance_docs"),
    Module(38, "Immutable Audit Chain", "Cyborg.ai", "Anchored audit events", "audit_logs"),
    Module(39, "Incident Response", "Cyborg.ai", "Open incidents", "incidents"),
    Module(40, "Risk Score Engine", "Cyborg.ai", "Project risk score", "risk_events"),
    # Borg.ai / Infrastructure layer
    Module(41, "Job Runner", "Borg.ai", "Successful automation runs", "job_queue"),
    Module(42, "Worker Health", "Borg.ai", "Worker uptime", "server_telemetry"),
    Module(43, "Queue Monitor", "Borg.ai", "Failed / delayed jobs", "queue_metrics"),
    Module(44, "Backup Monitor", "Borg.ai", "Last successful backup", "backup_logs"),
    Module(45, "Deployment Tracker", "Borg.ai", "Deploy success rate", "cicd_logs"),
    Module(46, "Error Monitor", "Borg.ai", "Open system errors", "error_logs"),
    Module(47, "API Health", "Borg.ai", "Endpoint uptime / latency", "api_telemetry"),
    Module(48, "Database Health", "Borg.ai", "DB latency / storage / locks", "pg_metrics"),
    Module(49, "File Processing", "Borg.ai", "PDFs/images processed", "file_events"),
    Module(50, "Revenue Workflow Ops", "Stephanie.ai", "Lead->Estimate->Deposit->Permit->Build->Invoice->Closeout conversion", "revenue_ledger"),
)


def validate() -> None:
    """Internal consistency checks. Raised at import-time by the test suite."""
    ids = [m.module_id for m in MODULES]
    assert len(ids) == 50, f"expected 50 modules, found {len(ids)}"
    assert len(set(ids)) == 50, "module_id values are not unique"
    assert ids == sorted(ids), "modules are not ordered by id"
    for m in MODULES:
        assert m.owner_agent in AGENT_NAMES, f"module {m.module_id} has unknown owner {m.owner_agent}"
        assert m.truth_label == "BLOCKED", f"module {m.module_id} must seed as BLOCKED"
    for t in TOOLS:
        assert t.agent_name in AGENT_NAMES, f"tool {t.tool_name} has unknown agent {t.agent_name}"
        assert t.approval_level in APPROVAL_LEVELS, f"tool {t.tool_name} has bad level {t.approval_level}"
