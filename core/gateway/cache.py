"""Redis cache + per-actor rate limiting for the gateway."""

from __future__ import annotations

import json
import time
from typing import Any, Optional


class Cache:
    def __init__(self, redis, ttl_s: int = 60):
        self.redis = redis
        self.ttl_s = ttl_s

    async def get(self, key: str) -> Optional[dict]:
        try:
            data = await self.redis.get(f"cache:{key}")
        except Exception:
            return None
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl_s: Optional[int] = None) -> None:
        try:
            await self.redis.setex(f"cache:{key}", ttl_s or self.ttl_s, json.dumps(value, default=str))
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
