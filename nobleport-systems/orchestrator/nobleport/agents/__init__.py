from nobleport.agents.base import BaseAgent
from nobleport.agents.stephanie import StephanieAgent
from nobleport.agents.gcagent import GCAgent
from nobleport.agents.permitstream import PermitStreamAgent
from nobleport.agents.cyborg import CyborgAgent


def build_agents() -> dict[str, BaseAgent]:
    agents = (StephanieAgent(), GCAgent(), PermitStreamAgent(), CyborgAgent())
    return {a.name: a for a in agents}


__all__ = ["BaseAgent", "StephanieAgent", "GCAgent", "PermitStreamAgent",
           "CyborgAgent", "build_agents"]
