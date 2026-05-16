import hashlib
import secrets
import uuid

from fastapi import Depends, Header, HTTPException, Request, status


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def mint_api_key() -> tuple[str, str]:
    raw = "np_" + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw)


async def current_user(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing_api_key")
    kh = hash_api_key(x_api_key)
    async with request.app.state.pg.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.email, u.role
              FROM api_keys k
              JOIN users u ON u.id = k.user_id
             WHERE k.key_hash = $1 AND k.revoked_at IS NULL
            """,
            kh,
        )
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    return {"id": str(row["id"]), "email": row["email"], "role": row["role"]}


def require_role(*allowed: str):
    async def _guard(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient_role")
        return user
    return _guard


def uuid_or_400(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_uuid")
