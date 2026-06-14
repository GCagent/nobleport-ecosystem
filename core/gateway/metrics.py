"""Latency metrics — P50/P95/P99 plus CSV export (G1 voice/AI gate requirement).

`percentile` is a pure function so it is unit-testable without a database.
`p95_report` and `export_csv` read the operational call log.
"""

from __future__ import annotations

import csv
import io
from typing import Optional


def percentile(values: list[float], pct: float) -> Optional[float]:
    """Nearest-rank percentile. pct in [0, 100]. None for empty input."""
    if not values:
        return None
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")
    ordered = sorted(values)
    if pct == 0:
        return float(ordered[0])
    rank = -(-len(ordered) * pct // 100)  # ceil(n * pct / 100)
    idx = min(int(rank) - 1, len(ordered) - 1)
    return float(ordered[idx])


def summarize(latencies: list[float]) -> dict:
    return {
        "count": len(latencies),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "max_ms": max(latencies) if latencies else None,
    }


async def fetch_latencies(pool, agent: Optional[str] = None, window_hours: int = 24) -> list[float]:
    where = "latency_ms IS NOT NULL AND created_at >= NOW() - ($1 || ' hours')::interval"
    params: list = [str(window_hours)]
    if agent:
        where += " AND target_agent = $2"
        params.append(agent)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT latency_ms FROM mcp_call_log WHERE {where}", *params
        )
    return [float(r["latency_ms"]) for r in rows]


async def p95_report(pool, agent: Optional[str] = None, window_hours: int = 24) -> dict:
    latencies = await fetch_latencies(pool, agent=agent, window_hours=window_hours)
    return {
        "scope": agent or "all_agents",
        "window_hours": window_hours,
        **summarize(latencies),
    }


async def export_csv(pool, window_hours: int = 24) -> str:
    """Per-agent P50/P95/P99 as CSV text."""
    from .registry import AGENT_NAMES

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["agent", "count", "p50_ms", "p95_ms", "p99_ms", "max_ms", "window_hours"])
    for agent in [None, *sorted(AGENT_NAMES)]:
        rep = await p95_report(pool, agent=agent, window_hours=window_hours)
        writer.writerow([
            rep["scope"], rep["count"], rep["p50_ms"], rep["p95_ms"],
            rep["p99_ms"], rep["max_ms"], window_hours,
        ])
    return buf.getvalue()
