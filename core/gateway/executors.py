"""Tool execution layer.

The gateway proposes; the agent server executes. This module abstracts that
boundary so the controlled pipeline (governance + audit) is identical whether
the target is a live MCP server or a not-yet-wired stub.

  * StubExecutor — returns an honestly-labelled STAGED response. Used until a
    real agent endpoint is connected. It does NOT fabricate LIVE data.
  * HttpExecutor — POSTs the envelope to the agent's registered endpoint.
"""

from __future__ import annotations

from typing import Any

from .envelope import McpEnvelope


class ToolExecutor:
    async def execute(self, env: McpEnvelope) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError


class StubExecutor(ToolExecutor):
    """Truth-labelled placeholder. Echoes the request as STAGED, never LIVE."""

    async def execute(self, env: McpEnvelope) -> dict[str, Any]:
        return {
            "truth_label": "STAGED",
            "agent": env.target_agent,
            "tool": env.action,
            "module": env.module,
            "note": "Stub executor — connect the agent endpoint for live results.",
            "echo": env.payload,
        }


class HttpExecutor(ToolExecutor):
    def __init__(self, endpoints: dict[str, str], timeout_s: float = 10.0):
        # endpoints: agent_name -> base URL
        self.endpoints = endpoints
        self.timeout_s = timeout_s

    async def execute(self, env: McpEnvelope) -> dict[str, Any]:
        import httpx

        base = self.endpoints.get(env.target_agent)
        if not base:
            raise RuntimeError(f"no endpoint registered for {env.target_agent}")
        url = f"{base.rstrip('/')}/tool/{env.action}"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(url, json={
                "run_id": str(env.run_id),
                "module": env.module,
                "action": env.action,
                "payload": env.payload,
            })
            resp.raise_for_status()
            return resp.json()
