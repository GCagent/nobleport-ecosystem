"""The controlled MCP execution pipeline.

    Kill switch -> Governance (L0-L4) -> Rate limit -> Cache
      -> AuditBeacon PRE (required) -> Tool execution
      -> AuditBeacon POST -> Call log

Every terminal state — BLOCKED, PARKED, SUCCESS, FAILED, CACHED — is written
to the operational call log, and every decision that touches execution is
anchored in the immutable audit chain. Nothing here trusts the tool to behave:
the gate runs first, and the pre-write commits before the tool is called.
"""

from __future__ import annotations

import logging
import time

from .audit import AuditBeacon, CallLog
from .cache import Cache, RateLimiter
from .envelope import InvokeResult, McpEnvelope
from .executors import ToolExecutor
from .governance import GovernanceGate
from .killswitch import KillSwitch
from .registry import TOOLS

log = logging.getLogger("nobleport.gateway")

_TOOLS_BY_ACTION = {t.tool_name: t for t in TOOLS}


def _cacheable(env: McpEnvelope, level: str) -> bool:
    tool = _TOOLS_BY_ACTION.get(env.action)
    # Only cache read-only, non-write tool calls.
    return level == "L0" and not (tool.write_capable if tool else False)


class Gateway:
    def __init__(self, *, pool, gate: GovernanceGate, killswitch: KillSwitch,
                 cache: Cache, ratelimiter: RateLimiter, beacon: AuditBeacon,
                 calllog: CallLog, executor: ToolExecutor):
        self.pool = pool
        self.gate = gate
        self.killswitch = killswitch
        self.cache = cache
        self.ratelimiter = ratelimiter
        self.beacon = beacon
        self.calllog = calllog
        self.executor = executor

    async def invoke(self, env: McpEnvelope) -> InvokeResult:
        level = env.normalized_level()

        # 1. Kill switch — instant, fail-closed.
        engaged, scope = await self.killswitch.engaged(env.target_agent)
        if engaged:
            return await self._terminal(env, level, "BLOCKED", "KILL",
                                        f"kill_switch_engaged:{scope}")

        # 2. Governance gate.
        outcome = self.gate.evaluate(env)
        if outcome.decision == "BLOCK":
            return await self._terminal(env, outcome.level, "BLOCKED", outcome.level,
                                        outcome.reason, decision="BLOCK")

        # 3. Rate limit.
        if not await self.ratelimiter.allow(env.requesting_agent):
            return await self._terminal(env, level, "BLOCKED", "L2",
                                        "rate_limit_exceeded", decision="BLOCK")

        # 4. PARK — sensitive write without a human signature.
        if outcome.decision == "PARK":
            await self.beacon.prewrite(env, outcome.level)
            await self.calllog.record(env, status="PARKED", level=outcome.level,
                                      truth_label=env.truth_label)
            return InvokeResult(run_id=str(env.run_id), status="PARKED",
                                decision="PARK", level=outcome.level,
                                reason=outcome.reason, truth_label=env.truth_label)

        # 5. Cache (read-only only).
        cache_key = None
        if _cacheable(env, level):
            cache_key = f"{env.action}:{hash((env.message, repr(sorted(env.payload.items()))))}"
            cached = await self.cache.get(cache_key)
            if cached is not None:
                await self.calllog.record(env, status="CACHED", level=level,
                                          truth_label=cached.get("truth_label", env.truth_label))
                return InvokeResult(run_id=str(env.run_id), status="CACHED",
                                    decision="PERMIT", level=level, latency_ms=0,
                                    truth_label=cached.get("truth_label", env.truth_label),
                                    result=cached)

        # 6. AuditBeacon PRE-write — required. Fail closed if it cannot commit.
        try:
            audit = await self.beacon.prewrite(env, level)
        except Exception as exc:
            log.error("audit pre-write failed, blocking execution: %s", exc)
            await self.calllog.record(env, status="FAILED", level=level,
                                      truth_label=env.truth_label, error="audit_prewrite_failed")
            return InvokeResult(run_id=str(env.run_id), status="FAILED", decision="BLOCK",
                                level=level, reason="audit_prewrite_failed",
                                truth_label=env.truth_label)

        # 7. Tool execution.
        start = time.monotonic()
        try:
            result = await self.executor.execute(env)
            latency = int((time.monotonic() - start) * 1000)
            truth_label = result.get("truth_label", env.truth_label) if isinstance(result, dict) else env.truth_label
            await self.beacon.postwrite(env, "SUCCESS", latency, result)
            await self.calllog.record(env, status="SUCCESS", level=level,
                                      truth_label=truth_label, latency_ms=latency)
            if cache_key:
                await self.cache.set(cache_key, result)
            return InvokeResult(run_id=str(env.run_id), status="SUCCESS", decision="PERMIT",
                                level=level, latency_ms=latency, truth_label=truth_label,
                                result=result, audit=audit)
        except Exception as exc:
            latency = int((time.monotonic() - start) * 1000)
            await self.beacon.postwrite(env, "FAILED", latency, None, error=str(exc))
            await self.calllog.record(env, status="FAILED", level=level,
                                      truth_label=env.truth_label, latency_ms=latency, error=str(exc))
            return InvokeResult(run_id=str(env.run_id), status="FAILED", decision="PERMIT",
                                level=level, latency_ms=latency, reason=str(exc),
                                truth_label=env.truth_label)

    async def _terminal(self, env, level, status, fired_level, reason, decision="BLOCK"):
        """Record a denied/halted call in both the call log and the audit chain."""
        try:
            await self.beacon.postwrite(env, status, None, None, error=reason)
        except Exception as exc:  # never let audit failure mask the block
            log.error("audit of %s failed: %s", status, exc)
        await self.calllog.record(env, status=status, level=fired_level,
                                  truth_label=env.truth_label, error=reason)
        return InvokeResult(run_id=str(env.run_id), status=status, decision=decision,
                            level=fired_level, reason=reason, truth_label=env.truth_label)
