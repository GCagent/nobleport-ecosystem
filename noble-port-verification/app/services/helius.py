import httpx

from app.config import settings
from app.security.breaker import CircuitBreaker


_breaker = CircuitBreaker(
    fail_threshold=settings.breaker_fail_threshold,
    reset_after_s=settings.breaker_reset_s,
)


async def get_account(address: str) -> dict | None:
    """Resolve identity / structural fields via Helius DAS.

    Returns None on any failure — caller treats None as BLOCK.
    """
    if not _breaker.allow():
        return None
    if not settings.helius_api_key:
        return None

    url = f"https://mainnet.helius-rpc.com/?api-key={settings.helius_api_key}"
    payload = {
        "jsonrpc": "2.0",
        "id": "noble-port",
        "method": "getAsset",
        "params": {"id": address},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_s) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            body = r.json()
    except Exception:
        _breaker.record_failure()
        return None

    _breaker.record_success()
    result = body.get("result") or {}
    if not result:
        return None

    authorities = result.get("authorities") or []
    ownership = result.get("ownership") or {}
    return {
        "id": result.get("id"),
        "type": result.get("interface") or "token_account",
        "mint_authority": next(
            (a.get("address") for a in authorities if "mint" in (a.get("scopes") or [])),
            None,
        ),
        "freeze_authority": ownership.get("frozen") or None,
        "raw": result,
    }
