from fastapi import Request, HTTPException
from jose import jwt, JWTError

from app.core.config import settings


async def auth_middleware(request: Request, call_next):
    """
    Validates Supabase JWT from Authorization header.
    Sets request.state.user_id and request.state.jwt_claims.
    Skips auth for health endpoints.
    """
    # Skip auth for health and public audit endpoints
    skip_paths = {"/health", "/docs", "/openapi.json", "/redoc"}
    if request.url.path in skip_paths:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        request.state.user_id = None
        request.state.jwt_claims = None
        return await call_next(request)

    token = auth_header.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        request.state.user_id = payload.get("sub")
        request.state.jwt_claims = payload
    except JWTError:
        request.state.user_id = None
        request.state.jwt_claims = None

    return await call_next(request)


def require_auth(request: Request) -> str:
    """Dependency that requires a valid authenticated user. Returns user_id."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
    return user_id


def require_role(allowed_roles: list[str]):
    """Dependency factory that requires the user to have one of the given roles."""

    def checker(request: Request) -> dict:
        user_id = require_auth(request)
        claims = getattr(request.state, "jwt_claims", {}) or {}
        role = claims.get("app_role") or claims.get("user_metadata", {}).get("role")
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return {"user_id": user_id, "role": role, "claims": claims}

    return checker
