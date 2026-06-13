"""Supervisor executor — main agents delegating to sub-agents.

Replaces the bare StubExecutor on the gateway's execution step. For an
authorized call it:

  1. selects the sub-agents that help the requested tool,
  2. runs them concurrently,
  3. packs each finding into a compression packet (measuring the saving),
  4. aggregates into one result with provenance + optimization meta.

If no sub-agent serves the call it falls back to the inner executor, so the
pipeline contract is unchanged. The aggregate carries a private "_meta" block
that the pipeline lifts into InvokeResult.optimization and the call log.
"""

from __future__ import annotations

import asyncio

from . import compression
from .envelope import McpEnvelope
from .executors import StubExecutor, ToolExecutor
from .subagents import select


class Supervisor(ToolExecutor):
    def __init__(self, inner: ToolExecutor | None = None):
        self.inner = inner or StubExecutor()

    async def execute(self, env: McpEnvelope) -> dict:
        subs = select(env.target_agent, env.action)
        if not subs:
            return await self.inner.execute(env)

        findings = await asyncio.gather(*(s.handler(env) for s in subs))

        raw_total = 0
        packet_total = 0
        packed_findings = []
        for finding in findings:
            st = compression.stats(finding)
            raw_total += st.raw_bytes
            packet_total += st.packet_bytes
            packed_findings.append(finding)

        compressed = compression.stats(packed_findings)

        return {
            "truth_label": "STAGED",
            "agent": env.target_agent,
            "tool": env.action,
            "module": env.module,
            "delegated_to": [s.name for s in subs],
            "findings": packed_findings,
            "_meta": {
                "subagent_count": len(subs),
                "bytes_raw": compressed.raw_bytes,
                "bytes_packed": compressed.packet_bytes,
                "compression_ratio": compressed.ratio,
                "saved_bytes": compressed.saved_bytes,
                "per_finding_raw_bytes": raw_total,
            },
        }
