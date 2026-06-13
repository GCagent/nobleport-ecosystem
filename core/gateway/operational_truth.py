"""Operational-truth feature matrix.

A single, honest declaration of every feature surface this repository actually
contains, each classified by *code maturity* — not by marketing. The matrix
drives `/health/features` and is the canonical answer to "what does the
platform really expose today?"

Label definitions (deliberately strict — this is the anti-inflation layer):

  LIVE         Implemented, tested, and self-instrumenting. Runs and produces
               real telemetry with only Postgres + Redis — no external API,
               no creds. (It still must be *deployed* to serve public traffic;
               LIVE describes the code, not a running URL.)
  STAGED       Implemented and tested, but needs deployment, configuration, or
               external credentials / services before it functions.
  MODELED      A data model, schema, or spec exists; the logic does not run yet.
  INTERNAL_RD  Research / aspirational (e.g. smart contracts, tokenization).

Every feature carries an `evidence` pointer to a real path in this repo, so the
classification can be checked, not trusted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

LIVE = "LIVE"
STAGED = "STAGED"
MODELED = "MODELED"
INTERNAL_RD = "INTERNAL_RD"

STATUSES = (LIVE, STAGED, MODELED, INTERNAL_RD)


@dataclass(frozen=True)
class Feature:
    key: str
    name: str
    surface: str          # which agent / subsystem owns it
    status: str
    evidence: str         # real path in this repo
    kpi_source: str | None = None
    notes: str = ""


# --- The matrix — honest, evidence-backed, no inflation --------------------
FEATURES: tuple[Feature, ...] = (
    # LIVE — self-instrumenting; needs only Postgres + Redis.
    Feature("mcp_gateway_invoke", "MCP gateway invocation", "Stephanie.ai / gateway",
            LIVE, "core/gateway/gateway.py", "mcp_call_log",
            "Controlled /agent/invoke pipeline."),
    Feature("governance_gate", "Governance gate (L0–L4)", "Cyborg.ai",
            LIVE, "core/gateway/governance.py", "mcp_call_log",
            "Fail-closed; config-driven from launch-gates.json."),
    Feature("audit_chain", "Immutable audit chain", "Cyborg.ai",
            LIVE, "core/gateway/audit.py", "audit_logs",
            "Hash-chained pre/post-write (AuditBeacon)."),
    Feature("kill_switch", "Kill switch", "Cyborg.ai",
            LIVE, "core/gateway/killswitch.py", "kill_switch_events",
            "Global / per-agent instant halt, fail-closed."),
    Feature("rate_limiter", "Rate limiting", "gateway",
            LIVE, "core/gateway/cache.py", "mcp_call_log",
            "Per requesting-agent, Redis window."),
    Feature("compression_packets", "Built-in compression packets", "transport",
            LIVE, "core/gateway/compression.py", "mcp_call_log",
            "Smart-threshold zlib; compressed cache."),
    Feature("subagent_supervisor", "Sub-agent delegation", "all agents",
            LIVE, "core/gateway/supervisor.py", "mcp_call_log",
            "Main agents delegate to specialized sub-agents."),
    Feature("kpi_snapshot_worker", "KPI snapshot worker", "Stephanie.ai",
            LIVE, "core/gateway/kpi_worker.py", "kpi_snapshot",
            "Append-only; flips a module LIVE only when its source returns."),
    Feature("p95_latency_export", "P95 latency export (G1)", "Borg.ai",
            LIVE, "core/gateway/metrics.py", "mcp_call_log",
            "JSON + per-agent CSV."),
    Feature("operational_truth_matrix", "Operational-truth feature matrix", "Cyborg.ai",
            LIVE, "core/gateway/operational_truth.py", "operational_truth",
            "This surface — /health/features."),

    # STAGED — built + tested; needs deploy / external creds.
    Feature("solana_token_verification", "Solana token verification", "verification engine",
            STAGED, "noble-port-verification/app/main.py", None,
            "Needs Helius / Birdeye / Solscan API keys."),
    Feature("content_moderation_screen", "Content moderation screen", "verification engine",
            STAGED, "noble-port-verification/app/services/moderation.py", None,
            "Built; requires provider config."),
    Feature("evidence_vault", "Evidence vault", "verification engine",
            STAGED, "noble-port-verification/app/db/evidence.py", None,
            "Tamper-evident evidence storage."),
    Feature("rbac_api_keys", "RBAC / API keys", "verification engine",
            STAGED, "noble-port-verification/app/security/auth.py", None,
            "Role-based access; needs key provisioning."),
    Feature("http_agent_executor", "Live agent executor (HTTP)", "gateway",
            STAGED, "core/gateway/executors.py", None,
            "Calls real MCP agent servers; off by default (USE_HTTP_EXECUTOR)."),
    Feature("ops_dashboard_ui", "Operations dashboard UI", "frontend",
            STAGED, "dashboards/", None,
            "Static HTML; not yet wired to the live gateway API."),

    # MODELED — model / spec exists; logic not running.
    Feature("nobleport_kpi_modules", "NoblePort 50-module KPI registry", "Stephanie.ai",
            MODELED, "core/gateway/registry.py", "nobleport_module_registry",
            "Registry seeded; most modules BLOCKED until telemetry connected."),
    Feature("tokenomics_model", "Tokenomics model", "NoblePort Systems",
            MODELED, "tokenomics/tokenomics_calculator.py", None,
            "Spreadsheet/model only."),
    Feature("ens_solana_registry", "ENS↔Solana registry", "infra",
            MODELED, "scripts/ens-solana-setup.js", None,
            "Setup scripts; not operational."),
    Feature("jupiter_routing_lab", "Jupiter routing lab", "research",
            MODELED, "jupiter-routing-lab/", None,
            "Execution-comparison lab; not a product surface."),

    # INTERNAL_RD — research / aspirational.
    Feature("erc3643_security_token", "ERC-3643 security token", "contracts",
            INTERNAL_RD, "contracts/src/token/NBPTSecurityToken.sol", None,
            "RED-gated; securities counsel required before any use."),
    Feature("zksbt_accreditation", "zkSBT accreditation", "contracts",
            INTERNAL_RD, "contracts/src/zksbt/ZkSBTVerifier.sol", None,
            "Zero-knowledge accreditation research."),
    Feature("modular_compliance", "Modular compliance", "contracts",
            INTERNAL_RD, "contracts/src/compliance/ModularCompliance.sol", None,
            "On-chain compliance modules, research."),
)


# --- Frozen commands — actions the system refuses to run autonomously ------
# Curated autonomous-action freezes that map to the gateway's human-gate.
_AUTONOMOUS_FREEZES = (
    ("autonomous_payment_disbursement", "Money movement requires human approval (L4)."),
    ("autonomous_token_issuance", "Securities issuance is RED-gated; counsel required."),
    ("autonomous_contract_generation", "Legal documents require human signature."),
    ("autonomous_treasury_movement", "Treasury movement requires human approval (L4)."),
    ("autonomous_permit_filing", "Permit filing requires licensed human review."),
)


def load_frozen_commands(config_path: str) -> list[dict]:
    """RED-gate scopes (from launch-gates.json) + autonomous-action freezes.

    One source of truth: the RED modules counsel already reviews, merged with
    the autonomous actions the governance human-gate refuses to run unsigned.
    """
    commands: list[dict] = []
    try:
        data = json.loads(Path(config_path).read_text())
        red = data.get("launch_gates", {}).get("red", {}).get("modules", {})
        for key, meta in red.items():
            commands.append({
                "command": key,
                "reason": meta.get("reason", "RED-gated"),
                "blocker": meta.get("blocker"),
                "source": "launch_gates.red",
            })
    except Exception:
        pass
    for key, reason in _AUTONOMOUS_FREEZES:
        commands.append({
            "command": key,
            "reason": reason,
            "blocker": "human_gate",
            "source": "governance.human_gate",
        })
    return commands


def summary() -> dict[str, int]:
    counts = {s: 0 for s in STATUSES}
    for f in FEATURES:
        counts[f.status] += 1
    return counts


def feature_map() -> list[dict]:
    return [
        {
            "key": f.key, "name": f.name, "surface": f.surface,
            "status": f.status, "evidence": f.evidence,
            "kpi_source": f.kpi_source, "notes": f.notes,
        }
        for f in FEATURES
    ]


def report(config_path: str) -> dict:
    frozen = load_frozen_commands(config_path)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_features": len(FEATURES),
        "status_counts": summary(),
        "label_definitions": {
            "LIVE": "Implemented, tested, self-instrumenting (needs only Postgres+Redis).",
            "STAGED": "Built + tested; needs deployment / external credentials.",
            "MODELED": "Model or spec exists; logic not running.",
            "INTERNAL_RD": "Research / aspirational (contracts, tokenization).",
        },
        "features": feature_map(),
        "frozen_commands": {"count": len(frozen), "commands": frozen},
        "disclaimer": (
            "Status reflects code+test maturity in this repository, not "
            "production deployment or marketing claims. Public KPIs still "
            "require deployment and connected telemetry. No inflated counts."
        ),
    }


def validate() -> None:
    keys = [f.key for f in FEATURES]
    assert len(keys) == len(set(keys)), "duplicate feature keys"
    assert sum(summary().values()) == len(FEATURES), "status counts must total features"
    for f in FEATURES:
        assert f.status in STATUSES, f"{f.key} has bad status {f.status}"
        assert f.evidence, f"{f.key} missing evidence pointer"
