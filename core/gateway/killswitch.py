"""Kill switch — instant, fail-closed halt of execution.

Two scopes:
  * 'global'      — blocks ALL tool execution through the gateway.
  * '<agent>'     — blocks one agent (e.g. 'Cyborg.ai').

The hot flag lives in Redis so a check is one round-trip on the request path.
Every engage/release is also written to kill_switch_events for a durable,
audited record. Fail-closed: if Redis cannot be reached, the switch reads as
ENGAGED rather than letting traffic through.
"""

from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger("nobleport.gateway.killswitch")

GLOBAL = "global"
_KEY = "killswitch:{scope}"


class KillSwitch:
    def __init__(self, redis, pool=None):
        self.redis = redis
        self.pool = pool

    @staticmethod
    def _key(scope: str) -> str:
        return _KEY.format(scope=scope)

    async def engaged(self, agent: Optional[str] = None) -> tuple[bool, str]:
        """Return (is_engaged, scope_that_fired). Fail-closed on Redis error."""
        try:
            if await self.redis.get(self._key(GLOBAL)):
                return True, GLOBAL
            if agent and await self.redis.get(self._key(agent)):
                return True, agent
            return False, ""
        except Exception as exc:  # pragma: no cover - defensive
            log.error("kill switch read failed, failing closed: %s", exc)
            return True, "redis_unavailable"

    async def engage(self, scope: str, actor: str, reason: str = "") -> None:
        await self.redis.set(self._key(scope), "1")
        await self._record(scope, True, actor, reason)
        log.warning("KILL SWITCH ENGAGED scope=%s by=%s reason=%s", scope, actor, reason)

    async def release(self, scope: str, actor: str, reason: str = "") -> None:
        await self.redis.delete(self._key(scope))
        await self._record(scope, False, actor, reason)
        log.warning("KILL SWITCH RELEASED scope=%s by=%s", scope, actor)

    async def status(self) -> dict:
        keys = [GLOBAL, *(a for a in await self._known_scopes())]
        out = {}
        for scope in keys:
            try:
                out[scope] = bool(await self.redis.get(self._key(scope)))
            except Exception:  # pragma: no cover
                out[scope] = True
        return out

    async def _known_scopes(self) -> list[str]:
        from .registry import AGENT_NAMES
        return sorted(AGENT_NAMES)

    async def _record(self, scope: str, engaged: bool, actor: str, reason: str) -> None:
        if self.pool is None:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO kill_switch_events (scope, engaged, actor, reason)
                VALUES ($1, $2, $3, $4)
                """,
                scope, engaged, actor, reason or None,
            )
