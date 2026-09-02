import asyncio
import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.config import settings
from app.db import verifications as vdb
from app.db.audit import AuditLog
from app.engine.scoring import (
    BLOCK,
    birdeye_check,
    combine,
    helius_check,
    solscan_check,
)
from app.routers.admin import router as admin_router
from app.routers.esign import router as esign_router
from app.routers.evidence import router as evidence_router
from app.security.auth import hash_api_key
from app.security.ratelimit import RateLimiter
from app.security.validate import is_valid_solana_address
from app.services import birdeye, helius, solscan


logging.basicConfig(level=settings.log_level)
log = logging.getLogger("noble-port")


class VerifyRequest(BaseModel):
    address: str = Field(min_length=32, max_length=44)


class VerifyResponse(BaseModel):
    status: str
    reason: str | None = None
    sources: dict
    audit: dict


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pg = await asyncpg.create_pool(settings.database_url, min_size=1, max_size=10)
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    app.state.audit = AuditLog(app.state.pg)
    app.state.ratelimit = RateLimiter(app.state.redis, settings.rate_limit_per_min)
    try:
        yield
    finally:
        await app.state.pg.close()
        await app.state.redis.aclose()


app = FastAPI(title="NoblePort Verification Engine", lifespan=lifespan)
app.include_router(admin_router)
app.include_router(evidence_router)
app.include_router(esign_router)


async def _resolve_optional_user(request: Request, x_api_key: str | None) -> dict | None:
    """Same logic as security.auth.current_user, but never raises — /verify
    accepts unauthenticated callers (gateway behavior) while still recording
    the actor when a key is supplied."""
    if not x_api_key:
        return None
    async with request.app.state.pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.role
              FROM api_keys k
              JOIN users u ON u.id = k.user_id
             WHERE k.key_hash = $1 AND k.revoked_at IS NULL
            """,
            hash_api_key(x_api_key),
        )
    return {"id": str(row["id"]), "email": row["email"], "role": row["role"]} if row else None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready(request: Request):
    try:
        async with request.app.state.pg.acquire() as conn:
            await conn.fetchval("SELECT 1")
        await request.app.state.redis.ping()
    except Exception as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    return {"status": "ready"}


@app.post("/verify", response_model=VerifyResponse)
async def verify(
    req: VerifyRequest,
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> VerifyResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not await request.app.state.ratelimit.allow(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="rate_limited")

    address = req.address.strip()
    if not is_valid_solana_address(address):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_address")

    actor = await _resolve_optional_user(request, x_api_key)
    actor_id = actor["id"] if actor else None

    helius_data, birdeye_data, solscan_data = await asyncio.gather(
        helius.get_account(address),
        birdeye.get_liquidity(address),
        solscan.get_transactions(address),
    )

    missing = [
        name for name, val in (
            ("helius", helius_data),
            ("birdeye", birdeye_data),
            ("solscan", solscan_data),
        ) if val is None
    ]
    if missing:
        reason = f"missing_source:{','.join(missing)}"
        audit = await request.app.state.audit.append(
            address=address,
            helius_status="MISSING" if "helius" in missing else "UNKNOWN",
            birdeye_status="MISSING" if "birdeye" in missing else "UNKNOWN",
            solscan_status="MISSING" if "solscan" in missing else "UNKNOWN",
            final_decision=BLOCK,
            reason=reason,
            actor_id=actor_id,
        )
        return VerifyResponse(
            status=BLOCK,
            reason=reason,
            sources={"helius": None, "birdeye": None, "solscan": None},
            audit=audit,
        )

    h = helius_check(helius_data)
    b = birdeye_check(birdeye_data)
    s = solscan_check(solscan_data)
    final = combine(h, b, s)

    audit = await request.app.state.audit.append(
        address=address,
        helius_status=h,
        birdeye_status=b,
        solscan_status=s,
        final_decision=final,
        actor_id=actor_id,
    )

    verification = await vdb.create(
        request.app.state.pg,
        address=address,
        final_decision=final,
        helius_status=h, birdeye_status=b, solscan_status=s,
        moderation=None,
        created_by=actor_id,
    )

    return VerifyResponse(
        status=final,
        sources={"helius": h, "birdeye": b, "solscan": s},
        audit={**audit, "verification_id": verification["id"], "truth_state": verification["state"]},
    )
