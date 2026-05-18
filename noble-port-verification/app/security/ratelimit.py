import time
from redis.asyncio import Redis


class RateLimiter:
    def __init__(self, redis: Redis, per_minute: int):
        self.redis = redis
        self.per_minute = per_minute

    async def allow(self, key: str) -> bool:
        window = int(time.time() // 60)
        rk = f"rl:{key}:{window}"
        count = await self.redis.incr(rk)
        if count == 1:
            await self.redis.expire(rk, 65)
        return count <= self.per_minute
