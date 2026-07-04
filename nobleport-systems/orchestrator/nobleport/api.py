"""Orchestrator HTTP/WebSocket API.

Sits behind the Rust gateway (which handles TLS termination, rate limiting,
and routing for nobleportsystem.io / *.kuzo.io). Endpoints:

  GET  /health                         liveness
  GET  /modules                        module catalog + health
  GET  /modules/{name}                 single module
  GET  /workflows                      workflow definitions
  POST /workflows/{name}/start         start a run
  GET  /runs/{run_id}                  run state
  GET  /approvals                      pending human-gate requests
  POST /approvals/{id}/resolve         approve/reject (resumes the run)
  WS   /ws/avatar                      Stephanie.ai live avatar session
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from nobleport import __version__
from nobleport.agents import build_agents
from nobleport.human_gate import AlreadyResolvedError, HumanGate
from nobleport.registry import ModuleRegistry, UnknownModuleError
from nobleport.workflows import WORKFLOWS, WorkflowEngine


class StartRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ResolveRequest(BaseModel):
    approved: bool
    actor: str = Field(min_length=1)
    note: str | None = None


def create_app() -> FastAPI:
    app = FastAPI(title="NoblePort Systems Orchestrator", version=__version__)

    registry = ModuleRegistry()
    gate = HumanGate()
    agents = build_agents()
    engine = WorkflowEngine(registry, gate, agents)

    app.state.registry = registry
    app.state.gate = gate
    app.state.agents = agents
    app.state.engine = engine

    # -- health ---------------------------------------------------------------

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "version": __version__,
                "modules": len(registry.all()),
                "agents": sorted(agents)}

    # -- modules ----------------------------------------------------------------

    @app.get("/modules")
    async def list_modules(cluster: str | None = None,
                           agent: str | None = None) -> dict[str, Any]:
        mods = registry.all()
        if cluster:
            mods = [m for m in mods if m.cluster == cluster]
        if agent:
            mods = [m for m in mods if m.agent == agent]
        return {
            "count": len(mods),
            "modules": [
                {"name": m.name, "cluster": m.cluster, "agent": m.agent,
                 "status": m.status.value, "risk": m.risk.value,
                 "description": m.description,
                 "healthy": registry.health(m.name).healthy}
                for m in mods
            ],
        }

    @app.get("/modules/{name}")
    async def get_module(name: str) -> dict[str, Any]:
        try:
            m = registry.get(name)
        except UnknownModuleError:
            raise HTTPException(404, detail="unknown_module")
        h = registry.health(name)
        return {"name": m.name, "cluster": m.cluster, "agent": m.agent,
                "status": m.status.value, "risk": m.risk.value,
                "description": m.description,
                "human_gate": registry.requires_human_gate(name),
                "autonomous_execution_blocked":
                    registry.is_hard_blocked_autonomous(name),
                "health": {"healthy": h.healthy, "breaker_tripped": h.tripped}}

    # -- workflows ---------------------------------------------------------------

    @app.get("/workflows")
    async def list_workflows() -> dict[str, Any]:
        return {
            "workflows": [
                {"name": w.name, "description": w.description,
                 "steps": [{"name": s.name, "module": s.module} for s in w.steps]}
                for w in WORKFLOWS.values()
            ]
        }

    @app.post("/workflows/{name}/start")
    async def start_workflow(name: str, req: StartRequest) -> dict[str, Any]:
        if name not in WORKFLOWS:
            raise HTTPException(404, detail="unknown_workflow")
        run = await engine.start(name, req.payload)
        return run.to_dict()

    @app.get("/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        try:
            return engine.get_run(run_id).to_dict()
        except KeyError:
            raise HTTPException(404, detail="unknown_run")

    # -- human gate -----------------------------------------------------------------

    @app.get("/approvals")
    async def pending_approvals() -> dict[str, Any]:
        return {
            "pending": [
                {"id": r.id, "workflow_id": r.workflow_id, "step": r.step,
                 "module": r.module, "risk": r.risk, "summary": r.summary}
                for r in gate.pending()
            ]
        }

    @app.post("/approvals/{request_id}/resolve")
    async def resolve_approval(request_id: str, req: ResolveRequest) -> dict[str, Any]:
        try:
            approval = gate.get(request_id)
        except KeyError:
            raise HTTPException(404, detail="unknown_approval")
        try:
            run = await engine.resolve_approval(
                approval.workflow_id, request_id,
                approved=req.approved, actor=req.actor, note=req.note)
        except AlreadyResolvedError:
            raise HTTPException(409, detail="already_resolved")
        return run.to_dict()

    # -- avatar ------------------------------------------------------------------------

    @app.websocket("/ws/avatar")
    async def avatar_ws(ws: WebSocket) -> None:
        await ws.accept()
        stephanie = agents["stephanie"]
        try:
            while True:
                message = await ws.receive_text()
                await ws.send_json({"persona": "stephanie",
                                    "reply": stephanie.avatar_reply(message)})
        except WebSocketDisconnect:
            pass

    return app


app = create_app()
