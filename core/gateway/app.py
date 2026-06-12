"""NoblePort MCP Gateway — FastAPI entrypoint.

    uvicorn core.gateway.app:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from redis.asyncio import Redis

from . import metrics
from .audit import AuditBeacon, CallLog
from .cache import Cache, RateLimiter
from .config import settings
from .envelope import InvokeResult, McpEnvelope
from .executors import HttpExecutor, StubExecutor
from .gateway import Gateway
from .governance import GovernanceGate
from .killswitch import GLOBAL, KillSwitch
from .kpi_worker import KpiWorker

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("nobleport.gateway.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pg = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    gate = GovernanceGate(settings.launch_gates_path, settings.max_message_chars)
    killswitch = KillSwitch(app.state.redis, app.state.pg)
    cache = Cache(app.state.redis, settings.cache_ttl_s)
    ratelimiter = RateLimiter(app.state.redis, settings.rate_limit_per_min)
    beacon = AuditBeacon(app.state.pg)
    calllog = CallLog(app.state.pg)

    if settings.use_http_executor:
        async with app.state.pg.acquire() as conn:
            rows = await conn.fetch("SELECT agent_name, endpoint FROM mcp_agent_registry")
        executor = HttpExecutor({r["agent_name"]: r["endpoint"] for r in rows}, settings.tool_timeout_s)
    else:
        executor = StubExecutor()

    app.state.killswitch = killswitch
    app.state.gateway = Gateway(
        pool=app.state.pg, gate=gate, killswitch=killswitch, cache=cache,
        ratelimiter=ratelimiter, beacon=beacon, calllog=calllog, executor=executor,
    )

    app.state.kpi = KpiWorker(app.state.pg, settings.kpi_interval_s)
    await app.state.kpi.seed()
    if settings.enable_kpi_worker:
        app.state.kpi.start()

    try:
        yield
    finally:
        if settings.enable_kpi_worker:
            await app.state.kpi.stop()
        await app.state.pg.close()
        await app.state.redis.aclose()


app = FastAPI(title="NoblePort MCP Gateway", version="1.0.0", lifespan=lifespan)


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="admin_token_required")


# --- Health ----------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready(request: Request):
    try:
        async with request.app.state.pg.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await request.app.state.redis.ping()
    except Exception as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return {"status": "ready"}


# --- Core invocation -------------------------------------------------------
@app.post("/agent/invoke", response_model=InvokeResult)
async def invoke(env: McpEnvelope, request: Request) -> InvokeResult:
    return await request.app.state.gateway.invoke(env)


# --- Dashboard API ---------------------------------------------------------
@app.get("/api/kpi/modules")
async def kpi_modules(request: Request):
    async with request.app.state.pg.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT m.module_id, m.module_name, m.owner_agent, m.kpi_name,
                   m.source_table, m.truth_label, m.last_verified_at,
                   s.kpi_value, s.kpi_unit, s.source_ref, s.reason, s.measured_at
              FROM nobleport_module_registry m
              LEFT JOIN LATERAL (
                  SELECT kpi_value, kpi_unit, source_ref, reason, measured_at
                    FROM kpi_snapshot WHERE module_id = m.module_id
                ORDER BY measured_at DESC LIMIT 1
              ) s ON TRUE
             ORDER BY m.module_id
            """
        )
    return [dict(r) for r in rows]


@app.get("/api/kpi/module/{module_id}")
async def kpi_module(module_id: int, request: Request):
    async with request.app.state.pg.acquire() as conn:
        mod = await conn.fetchrow(
            "SELECT * FROM nobleport_module_registry WHERE module_id=$1", module_id
        )
        if not mod:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="module_not_found")
        history = await conn.fetch(
            "SELECT kpi_value, kpi_unit, truth_label, source_ref, reason, measured_at "
            "FROM kpi_snapshot WHERE module_id=$1 ORDER BY measured_at DESC LIMIT 50",
            module_id,
        )
    return {"module": dict(mod), "history": [dict(h) for h in history]}


@app.get("/api/kpi/agent/{agent_name}")
async def kpi_agent(agent_name: str, request: Request):
    async with request.app.state.pg.acquire() as conn:
        rows = await conn.fetch(
            "SELECT module_id, module_name, kpi_name, truth_label, last_verified_at "
            "FROM nobleport_module_registry WHERE owner_agent=$1 ORDER BY module_id",
            agent_name,
        )
    return [dict(r) for r in rows]


@app.get("/api/mcp/calls")
async def mcp_calls(request: Request, limit: int = 100):
    async with request.app.state.pg.acquire() as conn:
        rows = await conn.fetch(
            "SELECT run_id, requesting_agent, target_agent, module_name, tool_name, "
            "truth_label, approval_level, status, latency_ms, error_message, created_at "
            "FROM mcp_call_log ORDER BY created_at DESC LIMIT $1",
            min(limit, 500),
        )
    return [dict(r) for r in rows]


@app.get("/api/audit/events")
async def audit_events(request: Request, limit: int = 100):
    async with request.app.state.pg.acquire() as conn:
        rows = await conn.fetch(
            "SELECT action, entity_type, entity_id, payload_hash, previous_hash, timestamp "
            "FROM audit_logs ORDER BY timestamp DESC LIMIT $1",
            min(limit, 500),
        )
    return [dict(r) for r in rows]


# --- Metrics (G1 P95 export) ----------------------------------------------
@app.get("/api/metrics/p95")
async def metrics_p95(request: Request, agent: str | None = None, window_hours: int = 24):
    return await metrics.p95_report(request.app.state.pg, agent=agent, window_hours=window_hours)


@app.get("/api/metrics/p95.csv")
async def metrics_p95_csv(request: Request, window_hours: int = 24):
    body = await metrics.export_csv(request.app.state.pg, window_hours=window_hours)
    return Response(
        content=body, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nobleport_p95.csv"},
    )


# --- Kill switch (admin) ---------------------------------------------------
@app.get("/api/killswitch/status")
async def killswitch_status(request: Request):
    return await request.app.state.killswitch.status()


@app.post("/api/killswitch/engage", dependencies=[Depends(require_admin)])
async def killswitch_engage(request: Request, scope: str = GLOBAL, reason: str = ""):
    await request.app.state.killswitch.engage(scope, actor="admin", reason=reason)
    return {"scope": scope, "engaged": True}


@app.post("/api/killswitch/release", dependencies=[Depends(require_admin)])
async def killswitch_release(request: Request, scope: str = GLOBAL, reason: str = ""):
    await request.app.state.killswitch.release(scope, actor="admin", reason=reason)
    return {"scope": scope, "engaged": False}
