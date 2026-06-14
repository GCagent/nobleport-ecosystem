import pytest

from core.gateway import subagents
from core.gateway.envelope import McpEnvelope
from core.gateway.executors import StubExecutor
from core.gateway.supervisor import Supervisor


def env(**kw):
    base = dict(requesting_agent="Stephanie.ai", target_agent="GCagent.ai",
                module="Estimate Engine", action="gcagent.price_estimate")
    base.update(kw)
    return McpEnvelope(**base)


def test_every_subagent_has_a_known_parent():
    from core.gateway.registry import AGENT_NAMES
    for s in subagents.SUBAGENTS:
        assert s.parent in AGENT_NAMES


def test_select_prefers_specialist():
    chosen = subagents.select("GCagent.ai", "gcagent.price_estimate")
    names = [s.name for s in chosen]
    assert "estimator" in names          # specialist for this action
    assert "scoper" not in names         # specialist for a different action


def test_select_falls_back_to_generalists():
    chosen = subagents.select("GCagent.ai", "gcagent.unknown_tool")
    names = [s.name for s in chosen]
    assert names == ["scheduler"]        # the only GCagent generalist


def test_select_unknown_agent_empty():
    assert subagents.select("Nobody.ai", "x") == ()


@pytest.mark.asyncio
async def test_supervisor_delegates_and_compresses():
    sup = Supervisor()
    result = await sup.execute(env())
    assert result["delegated_to"]
    assert result["findings"]
    meta = result["_meta"]
    assert meta["subagent_count"] == len(result["delegated_to"])
    assert meta["bytes_packed"] >= 1
    assert meta["bytes_raw"] >= meta["bytes_packed"]


@pytest.mark.asyncio
async def test_supervisor_falls_back_to_inner_when_no_subagents():
    class Marker(StubExecutor):
        async def execute(self, e):
            return {"marker": True, "truth_label": "STAGED"}

    sup = Supervisor(inner=Marker())
    # Stephanie.ai generalists exist, so use an agent with a non-serving action
    # that still has generalists -> instead target an agent and unknown tool.
    result = await sup.execute(env(target_agent="Nobody.ai", action="x"))
    assert result == {"marker": True, "truth_label": "STAGED"}
