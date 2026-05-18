import httpx

from app.config import settings
from app.security.breaker import CircuitBreaker


_breaker = CircuitBreaker(
    fail_threshold=settings.breaker_fail_threshold,
    reset_after_s=settings.breaker_reset_s,
)


async def get_liquidity(address: str) -> dict | None:
    if not _breaker.allow():
        return None
    if not settings.birdeye_api_key:
        return None

    url = "https://public-api.birdeye.so/defi/token_overview"
    headers = {
        "X-API-KEY": settings.birdeye_api_key,
        "x-chain": "solana",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_s) as client:
            r = await client.get(url, headers=headers, params={"address": address})
            r.raise_for_status()
            body = r.json()
    except Exception:
        _breaker.record_failure()
        return None

    _breaker.record_success()
    data = body.get("data") or {}
    if not data:
        return None
    return {
        "liquidity_usd": float(data.get("liquidity") or 0.0),
        "volume_24h": float(data.get("v24hUSD") or 0.0),
        "raw": data,
    }
