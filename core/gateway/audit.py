"""AuditBeacon — hash-chained, append-only audit of every gateway decision.

Writes into the same immutable `audit_logs` chain used by the orchestration
spine (core/api/gated_router.py), so the whole platform shares one tamper-
evident ledger. The pre-write commits BEFORE any tool runs: that is the
audit-before-state-change guarantee. If the pre-write fails, the caller fails
closed and nothing executes.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

GENESIS_HASH = "0" * 64


def _hash(prev_hash: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prev_hash.encode() + body).hexdigest()


class AuditBeacon:
    def __init__(self, pool):
        self.pool = pool

    async def _append(self, action: str, run_id: UUID, bundle: dict) -> dict:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                prev = await conn.fetchval(
                    "SELECT payload_hash FROM audit_logs ORDER BY timestamp DESC LIMIT 1"
                )
                prev_hash = prev or GENESIS_HASH
                payload_hash = _hash(prev_hash, bundle)
                await conn.execute(
                    """
                    INSERT INTO audit_logs
                        (action, entity_type, entity_id, payload_hash, previous_hash, raw_payload)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                    """,
                    action, "mcp_call", run_id, payload_hash, prev_hash, json.dumps(bundle, default=str),
                )
        return {"payload_hash": payload_hash, "previous_hash": prev_hash}

    async def prewrite(self, env, level: str) -> dict:
        bundle = {
            "phase": "PRE",
            "run_id": str(env.run_id),
            "requesting_agent": env.requesting_agent,
            "target_agent": env.target_agent,
            "module": env.module,
            "action": env.action,
            "approval_level": level,
            "truth_label": env.truth_label,
            "project_id": env.project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self._append("MCP_AUDIT_PREWRITE", env.run_id, bundle)

    async def postwrite(self, env, status: str, latency_ms: Optional[int],
                        result: Optional[dict], error: Optional[str] = None) -> dict:
        bundle = {
            "phase": "POST",
            "run_id": str(env.run_id),
            "target_agent": env.target_agent,
            "action": env.action,
            "status": status,
            "latency_ms": latency_ms,
            "result_keys": sorted(result.keys()) if isinstance(result, dict) else None,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return await self._append("MCP_AUDIT_POSTWRITE", env.run_id, bundle)


class CallLog:
    """Operational ledger — one row per invocation in mcp_call_log."""

    def __init__(self, pool):
        self.pool = pool

    async def record(self, env, *, status: str, level: str, truth_label: str,
                    latency_ms: Optional[int] = None, error: Optional[str] = None) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO mcp_call_log
                    (run_id, requesting_agent, target_agent, module_name, tool_name,
                     project_id, truth_label, approval_level, status, latency_ms, error_message)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                """,
                env.run_id, env.requesting_agent, env.target_agent, env.module, env.action,
                env.project_id, truth_label, level, status, latency_ms, error,
            )
