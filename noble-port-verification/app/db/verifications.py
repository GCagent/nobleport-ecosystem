import json
import uuid
from datetime import datetime, timezone

import asyncpg
from fastapi import HTTPException, status


TRUTH_STATES = {"VERIFIED", "DISPUTED", "LEGAL_HOLD", "REMOVED"}

# Only these transitions are allowed. REMOVED is terminal.
_ALLOWED = {
    "VERIFIED":   {"DISPUTED", "LEGAL_HOLD", "REMOVED"},
    "DISPUTED":   {"VERIFIED", "LEGAL_HOLD", "REMOVED"},
    "LEGAL_HOLD": {"DISPUTED", "REMOVED"},
    "REMOVED":    set(),
}

# Only these roles may drive a given transition.
_ROLE_FOR_TARGET = {
    "VERIFIED":   {"admin", "moderator"},
    "DISPUTED":   {"admin", "moderator", "contractor"},
    "LEGAL_HOLD": {"admin"},
    "REMOVED":    {"admin"},
}


def assert_transition(current: str, target: str, role: str) -> None:
    if target not in TRUTH_STATES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_state")
    if target not in _ALLOWED.get(current, set()):
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"transition_not_allowed:{current}->{target}")
    if role not in _ROLE_FOR_TARGET[target]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="role_cannot_perform_transition")


async def create(
    pool: asyncpg.Pool,
    *,
    address: str,
    final_decision: str,
    helius_status: str | None,
    birdeye_status: str | None,
    solscan_status: str | None,
    moderation: dict | None,
    created_by: str | None,
) -> dict:
    rid = str(uuid.uuid4())
    state = "VERIFIED" if final_decision == "PASS" else "DISPUTED"
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO verifications
                (id, address, state, final_decision,
                 helius_status, birdeye_status, solscan_status,
                 moderation, created_by, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9, now(), now())
            """,
            rid, address, state, final_decision,
            helius_status, birdeye_status, solscan_status,
            json.dumps(moderation) if moderation else None,
            uuid.UUID(created_by) if created_by else None,
        )
    return {"id": rid, "state": state}


async def get(pool: asyncpg.Pool, vid: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM verifications WHERE id = $1", uuid.UUID(vid))
    return dict(row) if row else None


async def transition(
    pool: asyncpg.Pool,
    *,
    vid: str,
    target: str,
    actor: dict,
) -> dict:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id, state FROM verifications WHERE id = $1 FOR UPDATE",
                uuid.UUID(vid),
            )
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="verification_not_found")
            assert_transition(row["state"], target, actor["role"])
            await conn.execute(
                "UPDATE verifications SET state=$1, updated_at=now() WHERE id=$2",
                target, row["id"],
            )
    return {"id": vid, "from": row["state"], "to": target}
