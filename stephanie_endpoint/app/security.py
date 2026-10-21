"""Security utilities: Bearer API key auth and HMAC webhook validation."""

import hashlib
import hmac
import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

API_KEY = os.getenv("STEPHANIE_API_KEY", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


async def verify_api_key(
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Validate Bearer token against the configured API key."""
    if not API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer scheme",
        )
    if not hmac.compare_digest(token, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return token


async def verify_webhook_signature(request: Request) -> bytes:
    """Validate HMAC-SHA256 signature on incoming webhook payloads."""
    if not WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured on server",
        )
    signature = request.headers.get("X-Webhook-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Webhook-Signature header",
        )
    body = await request.body()
    expected = hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(f"sha256={expected}", signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )
    return body


ApiKeyDep = Annotated[str, Depends(verify_api_key)]
