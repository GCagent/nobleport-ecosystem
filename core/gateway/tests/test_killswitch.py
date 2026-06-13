import pytest

from core.gateway.killswitch import GLOBAL, KillSwitch


@pytest.mark.asyncio
async def test_not_engaged_by_default(fake_redis):
    ks = KillSwitch(fake_redis)
    engaged, scope = await ks.engaged("GCagent.ai")
    assert engaged is False


@pytest.mark.asyncio
async def test_global_engage_blocks_every_agent(fake_redis):
    ks = KillSwitch(fake_redis)
    await ks.engage(GLOBAL, actor="admin", reason="incident")
    engaged, scope = await ks.engaged("Borg.ai")
    assert engaged is True
    assert scope == GLOBAL


@pytest.mark.asyncio
async def test_per_agent_engage_scoped(fake_redis):
    ks = KillSwitch(fake_redis)
    await ks.engage("Cyborg.ai", actor="admin")
    assert (await ks.engaged("Cyborg.ai"))[0] is True
    assert (await ks.engaged("GCagent.ai"))[0] is False


@pytest.mark.asyncio
async def test_release(fake_redis):
    ks = KillSwitch(fake_redis)
    await ks.engage(GLOBAL, actor="admin")
    await ks.release(GLOBAL, actor="admin")
    assert (await ks.engaged("GCagent.ai"))[0] is False


@pytest.mark.asyncio
async def test_fails_closed_when_redis_down(fake_redis):
    fake_redis.fail = True
    ks = KillSwitch(fake_redis)
    engaged, scope = await ks.engaged("GCagent.ai")
    assert engaged is True
    assert scope == "redis_unavailable"
