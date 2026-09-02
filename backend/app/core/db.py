import json
from typing import AsyncGenerator

import asyncpg
from fastapi import Request, HTTPException

from app.core.config import settings

pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        command_timeout=settings.db_command_timeout,
        max_inactive_connection_lifetime=300,
    )


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """Plain connection from pool. No RLS context."""
    if pool is None:
        raise RuntimeError("DB pool not initialized")
    async with pool.acquire() as conn:
        yield conn


async def get_rls_conn(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Connection with Supabase JWT claims injected into the session.
    Postgres RLS policies read these via current_setting('request.jwt.claims').
    """
    if pool is None:
        raise RuntimeError("DB pool not initialized")

    # user_id and jwt_claims are set by the auth middleware
    user_id: str | None = getattr(request.state, "user_id", None)
    jwt_claims: dict | None = getattr(request.state, "jwt_claims", None)

    if not user_id or not jwt_claims:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async with pool.acquire() as conn:
        # Set the role to authenticated so RLS kicks in
        await conn.execute("set local role authenticated")
        await conn.execute(
            "select set_config('request.jwt.claims', $1, true)",
            json.dumps(jwt_claims),
        )
        await conn.execute(
            "select set_config('request.jwt.claim.sub', $1, true)",
            user_id,
        )
        yield conn
