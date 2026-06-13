import asyncio

import pytest


class FakeRedis:
    """Minimal async Redis stand-in for unit tests."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.fail = False

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def incr(self, key):
        self.store[key] = str(int(self.store.get(key, "0")) + 1)
        return int(self.store[key])

    async def expire(self, key, ttl):
        return True


@pytest.fixture
def fake_redis():
    return FakeRedis()
