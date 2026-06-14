"""Redis cache + per-actor rate limiting for the gateway.

Cache entries are stored as base64 compression packets, so the cache is
compressed at rest and on the wire by default.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from . import compression


class Cache:
    def __init__(self, redis, ttl_s: int = 60):
        self.redis = redis
        self.ttl_s = ttl_s

    async def get(self, key: str) -> Optional[dict]:
        try:
            data = await self.redis.get(f"cache:{key}")
        except Exception:
            return None
        if not data:
            return None
        try:
            return compression.unpack_b64(data)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        try:
            await self.redis.setex(f"cache:{key}", ttl_s or self.ttl_s, compression.pack_b64(value))
        except Exception:
            pass


class RateLimiter:
    def __init__(self, redis, per_minute: int = 20):
        self.redis = redis
        self.per_minute = per_minute

    async def allow(self, actor: str) -> bool:
        window = int(time.time() // 60)
        key = f"rate:{actor}:{window}"
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 65)
        return count <= self.per_minute
