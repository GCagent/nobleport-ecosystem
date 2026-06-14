"""Sub-agents — specialized workers that help the main MCP agents.

Each main agent (GCagent.ai, PermitStream.ai, ...) fans a request out to the
sub-agents that serve the requested tool. A sub-agent owns one narrow skill and
returns a partial, honestly-labelled (STAGED) finding. The Supervisor (see
supervisor.py) runs them concurrently and aggregates.

Delegation does NOT bypass enforcement: the parent call has already cleared the
governance gate and been pre-written to the audit chain before any sub-agent
runs. Sub-agents are workers of an already-authorized main-agent call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from .envelope import McpEnvelope

# A handler takes the envelope and returns a partial result dict.
Handler = Callable[[McpEnvelope], Awaitable[dict]]


@dataclass(frozen=True)
class SubAgent:
    parent: str
    name: str
    skill: str
    serves: frozenset[str]          # tool actions it helps with; empty = generalist
    handler: Handler
    enabled: bool = True


def _finding(name: str, skill: str, env: McpEnvelope, summary: str, **fields) -> dict:
    """Uniform STAGED partial. Sub-agents propose; they never assert LIVE truth."""
    return {
        "subagent": name,
        "skill": skill,
        "truth_label": "STAGED",
        "module": env.module,
        "summary": summary,
        **fields,
    }


# --- Handlers (lightweight, deterministic, STAGED) -------------------------
def _make(name: str, skill: str, summary: str) -> Handler:
    async def handler(env: McpEnvelope) -> dict:
        return _finding(name, skill, env, summary,
                        considered=sorted(env.payload.keys()))
    return handler


# --- Topology: 2-3 sub-agents per main agent -------------------------------
SUBAGENTS: tuple[SubAgent, ...] = (
    # Stephanie.ai
    SubAgent("Stephanie.ai", "router", "intent routing", frozenset(),
             _make("router", "intent routing", "Routed request to owning agent")),
    SubAgent("Stephanie.ai", "summarizer", "result summarization", frozenset(),
             _make("summarizer", "result summarization", "Condensed sub-agent findings")),
    # GCagent.ai
    SubAgent("GCagent.ai", "estimator", "cost estimating",
             frozenset({"gcagent.price_estimate"}),
             _make("estimator", "cost estimating", "Drafted cost basis for scope")),
    SubAgent("GCagent.ai", "scoper", "scope breakdown",
             frozenset({"gcagent.create_scope"}),
             _make("scoper", "scope breakdown", "Generated scope line items")),
    SubAgent("GCagent.ai", "scheduler", "schedule analysis", frozenset(),
             _make("scheduler", "schedule analysis", "Assessed schedule impact")),
    # PermitStream.ai
    SubAgent("PermitStream.ai", "ahj_analyst", "AHJ rule lookup",
             frozenset({"permitstream.check_ahj_requirements"}),
             _make("ahj_analyst", "AHJ rule lookup", "Matched jurisdiction requirements")),
    SubAgent("PermitStream.ai", "deficiency_scanner", "deficiency scan",
             frozenset({"permitstream.run_deficiency_scan"}),
             _make("deficiency_scanner", "deficiency scan", "Scanned packet for deficiencies")),
    # Cyborg.ai
    SubAgent("Cyborg.ai", "policy_auditor", "policy audit", frozenset(),
             _make("policy_auditor", "policy audit", "Checked request against policy set")),
    SubAgent("Cyborg.ai", "risk_scorer", "risk scoring",
             frozenset({"cyborg.score_project_risk"}),
             _make("risk_scorer", "risk scoring", "Produced provisional risk score")),
    # Borg.ai
    SubAgent("Borg.ai", "job_runner", "job execution",
             frozenset({"borg.run_job"}),
             _make("job_runner", "job execution", "Prepared job for the queue")),
    SubAgent("Borg.ai", "health_monitor", "telemetry read", frozenset(),
             _make("health_monitor", "telemetry read", "Collected infrastructure telemetry")),
    # Kuzo.io
    SubAgent("Kuzo.io", "intake_clerk", "intake normalization",
             frozenset({"kuzo.capture_lead", "kuzo.update_customer_profile"}),
             _make("intake_clerk", "intake normalization", "Normalized intake fields")),
    SubAgent("Kuzo.io", "notifier", "customer notification",
             frozenset({"kuzo.send_customer_update"}),
             _make("notifier", "customer notification", "Drafted customer notification")),
)


def select(target_agent: str, action: str) -> tuple[SubAgent, ...]:
    """Which sub-agents help this call.

    Specialists that serve the action come first; if none match, the parent's
    generalists (serves == empty) help instead.
    """
    pool = [s for s in SUBAGENTS if s.parent == target_agent and s.enabled]
    specialists = [s for s in pool if action in s.serves]
    if specialists:
        generalists = [s for s in pool if not s.serves]
        return tuple(specialists + generalists)
    return tuple(s for s in pool if not s.serves)
