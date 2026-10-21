from fastapi import APIRouter, Depends
import asyncpg

from app.core.db import get_conn

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(conn: asyncpg.Connection = Depends(get_conn)):
    row = await conn.fetchval("select 1")
    return {"status": "ok", "db": row == 1}
