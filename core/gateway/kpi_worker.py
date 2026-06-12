"""KPI snapshot worker.

On startup it seeds the agent / tool / module registries from registry.py
(idempotent). On each cycle it walks all 50 modules and writes one append-only
kpi_snapshot row per module:

  * LIVE     — a resolver read a real value from a real table.
  * BLOCKED  — no resolver wired yet, or the source table does not exist.

It never fabricates numbers and never overwrites history. Today only the
modules whose source tables already exist in this database (audit_logs,
mcp_call_log, workflow_states, kpi_snapshot, the registry itself) report LIVE.
Everything else is honestly BLOCKED until its telemetry is connected.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from .registry import AGENTS, MODULES, TOOLS

log = logging.getLogger("nobleport.gateway.kpi")

# A resolver returns (value, unit, source_ref) or None to signal BLOCKED.
Resolver = Callable[["object"], Awaitable[Optional[tuple[float, str, str]]]]


async def _r_decisions_routed(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval(
        "SELECT COUNT(DISTINCT run_id) FROM mcp_call_log WHERE created_at::date = NOW()::date"
    )
    return (float(val or 0), "count", "postgres.mcp_call_log")


async def _r_active_projects(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval(
        "SELECT COUNT(*) FROM workflow_states WHERE entity_type='project' AND current_status NOT IN ('archived','rejected')"
    )
    return (float(val or 0), "count", "postgres.workflow_states")


async def _r_routing_calls(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval("SELECT COUNT(*) FROM mcp_call_log")
    return (float(val or 0), "count", "postgres.mcp_call_log")


async def _r_pending_approvals(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval(
        "SELECT COUNT(*) FROM workflow_states WHERE current_status='pending_human_review'"
    )
    return (float(val or 0), "count", "postgres.workflow_states")


async def _r_audit_events(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval("SELECT COUNT(*) FROM audit_logs")
    return (float(val or 0), "count", "postgres.audit_logs")


async def _r_truth_ratio(conn) -> Optional[tuple[float, str, str]]:
    row = await conn.fetchrow(
        "SELECT COUNT(*) FILTER (WHERE truth_label='LIVE') AS live, COUNT(*) AS total "
        "FROM nobleport_module_registry"
    )
    total = row["total"] or 0
    pct = (row["live"] / total * 100) if total else 0.0
    return (round(float(pct), 1), "percent", "postgres.nobleport_module_registry")


async def _r_modules_live(conn) -> Optional[tuple[float, str, str]]:
    val = await conn.fetchval(
        """
        SELECT COUNT(*) FROM (
            SELECT DISTINCT ON (module_id) module_id, truth_label
            FROM kpi_snapshot ORDER BY module_id, measured_at DESC
        ) s WHERE truth_label='LIVE'
        """
    )
    return (float(val or 0), "count", "postgres.kpi_snapshot")


# module_id -> resolver. Absent => BLOCKED (honest default).
RESOLVERS: dict[int, Resolver] = {
    1: _r_decisions_routed,
    4: _r_active_projects,
    5: _r_routing_calls,
    6: _r_pending_approvals,
    7: _r_audit_events,
    8: _r_truth_ratio,
    10: _r_modules_live,
    38: _r_audit_events,
}


class KpiWorker:
    def __init__(self, pool, interval_s: int = 600):
        self.pool = pool
        self.interval_s = interval_s
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def seed(self) -> None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for a in AGENTS:
                    await conn.execute(
                        """
                        INSERT INTO mcp_agent_registry (agent_name, endpoint, owner_domain, status)
                        VALUES ($1, $2, $3, 'staged')
                        ON CONFLICT (agent_name) DO UPDATE SET owner_domain = EXCLUDED.owner_domain
                        """,
                        a.name, f"https://{a.owner_domain}/mcp", a.owner_domain,
                    )
                for t in TOOLS:
                    await conn.execute(
                        """
                        INSERT INTO mcp_tool_registry
                            (agent_name, tool_name, module_name, approval_level, write_capable, audit_required, enabled)
                        VALUES ($1,$2,$3,$4,$5,$6,$7)
                        ON CONFLICT (agent_name, tool_name) DO UPDATE
                            SET module_name=EXCLUDED.module_name,
                                approval_level=EXCLUDED.approval_level,
                                write_capable=EXCLUDED.write_capable
                        """,
                        t.agent_name, t.tool_name, t.module_name, t.approval_level,
                        t.write_capable, t.audit_required, t.enabled,
                    )
                for m in MODULES:
                    await conn.execute(
                        """
                        INSERT INTO nobleport_module_registry
                            (module_id, module_name, owner_agent, kpi_name, source_table, truth_label)
                        VALUES ($1,$2,$3,$4,$5,'BLOCKED')
                        ON CONFLICT (module_id) DO UPDATE
                            SET module_name=EXCLUDED.module_name,
                                owner_agent=EXCLUDED.owner_agent,
                                kpi_name=EXCLUDED.kpi_name,
                                source_table=EXCLUDED.source_table
                        """,
                        m.module_id, m.module_name, m.owner_agent, m.kpi_name, m.source_table,
                    )
        log.info("seeded %d agents, %d tools, %d modules", len(AGENTS), len(TOOLS), len(MODULES))

    async def snapshot_once(self) -> int:
        written = 0
        async with self.pool.acquire() as conn:
            for m in MODULES:
                value = unit = source_ref = reason = None
                truth = "BLOCKED"
                resolver = RESOLVERS.get(m.module_id)
                if resolver is None:
                    reason = f"No resolver wired for source '{m.source_table}'"
                else:
                    try:
                        res = await resolver(conn)
                        if res is not None:
                            value, unit, source_ref = res
                            truth = "LIVE"
                    except Exception as exc:
                        reason = f"source unavailable: {type(exc).__name__}"
                await conn.execute(
                    """
                    INSERT INTO kpi_snapshot
                        (module_id, kpi_name, kpi_value, kpi_unit, truth_label, source_ref, reason)
                    VALUES ($1,$2,$3,$4,$5,$6,$7)
                    """,
                    m.module_id, m.kpi_name, value, unit, truth, source_ref, reason,
                )
                await conn.execute(
                    "UPDATE nobleport_module_registry SET truth_label=$1, last_verified_at=NOW() WHERE module_id=$2",
                    truth, m.module_id,
                )
                written += 1
        log.info("kpi snapshot written for %d modules", written)
        return written

    async def run(self) -> None:
        await self.seed()
        while not self._stop.is_set():
            try:
                await self.snapshot_once()
            except Exception as exc:  # never let the loop die
                log.error("kpi snapshot cycle failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_s)
            except asyncio.TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task
