from collections import Counter

import httpx

from app.config import settings
from app.security.breaker import CircuitBreaker


_breaker = CircuitBreaker(
    fail_threshold=settings.breaker_fail_threshold,
    reset_after_s=settings.breaker_reset_s,
)


async def get_transactions(address: str, limit: int = 50) -> list[dict] | None:
    if not _breaker.allow():
        return None
    if not settings.solscan_api_key:
        return None

    url = "https://pro-api.solscan.io/v2.0/account/transactions"
    headers = {"token": settings.solscan_api_key, "accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=settings.provider_timeout_s) as client:
            r = await client.get(url, headers=headers, params={"address": address, "limit": limit})
            r.raise_for_status()
            body = r.json()
    except Exception:
        _breaker.record_failure()
        return None

    _breaker.record_success()
    data = body.get("data") or []
    if not isinstance(data, list):
        return None
    return data


def detect_wallet_loops(txs: list[dict]) -> bool:
    """Same counterparty pair seen >=3 times in both directions."""
    pairs: Counter = Counter()
    for tx in txs:
        src = tx.get("from") or tx.get("src")
        dst = tx.get("to") or tx.get("dst")
        if src and dst:
            pairs[(src, dst)] += 1
    for (src, dst), n in pairs.items():
        if n >= 3 and pairs.get((dst, src), 0) >= 3:
            return True
    return False


def detect_single_source_funding(txs: list[dict]) -> bool:
    """>80% of inbound funds came from one address."""
    inbound: Counter = Counter()
    total = 0
    for tx in txs:
        src = tx.get("from") or tx.get("src")
        amt = float(tx.get("amount") or 0)
        if src and amt > 0:
            inbound[src] += amt
            total += amt
    if total <= 0 or not inbound:
        return False
    top = max(inbound.values())
    return (top / total) > 0.80
