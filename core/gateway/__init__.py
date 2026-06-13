"""NoblePort MCP Gateway.

A controlled internal connection layer that sits between the Stephanie.ai
orchestrator and the GCagent.ai / PermitStream.ai / Cyborg.ai / Borg.ai /
Kuzo.io MCP servers.

Pipeline (fail-closed, audit-before-state-change):

    AI Request
      -> Kill Switch check
      -> Schema validation (MCP envelope)
      -> Governance gate (L0-L4)
      -> Rate limit
      -> Cache (read-only / idempotent)
      -> AuditBeacon PRE-write   (required; blocks on failure)
      -> Tool execution
      -> AuditBeacon POST-write  (result + latency)
      -> KPI snapshot update
"""

__all__ = ["__version__"]

__version__ = "1.0.0"
