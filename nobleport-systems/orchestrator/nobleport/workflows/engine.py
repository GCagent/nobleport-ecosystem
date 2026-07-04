"""Workflow engine.

Runs declarative workflows step by step, dispatching each step to the agent
that owns the step's module. Enforcement lives here, not in the agents:

- HIGH/CRITICAL-risk steps suspend the run and open a HumanGate request.
- CRITICAL steps never execute in-platform even after approval; the engine
  records a PREPARED_FOR_MULTISIG result instead of dispatching.
- STAGED modules run in simulation (the agent is invoked with simulate=True).
- READ_ONLY modules are invoked with simulate=True unconditionally.
- Module failures feed the registry's circuit breaker.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from nobleport.human_gate import ApprovalState, HumanGate
from nobleport.modules import Status
from nobleport.registry import ModuleRegistry
from nobleport.workflows.definitions import WORKFLOWS, WorkflowDef


class Agent(Protocol):
    name: str

    async def handle(self, module: str, action: str, payload: dict[str, Any],
                     *, simulate: bool) -> dict[str, Any]: ...


class WorkflowState(str, Enum):
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


@dataclass
class StepResult:
    step: str
    module: str
    agent: str
    simulated: bool
    output: dict[str, Any]


@dataclass
class WorkflowRun:
    definition: WorkflowDef
    payload: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: WorkflowState = WorkflowState.RUNNING
    cursor: int = 0
    results: list[StepResult] = field(default_factory=list)
    pending_approval_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "workflow": self.definition.name,
            "state": self.state.value,
            "cursor": self.cursor,
            "steps_total": len(self.definition.steps),
            "pending_approval_id": self.pending_approval_id,
            "error": self.error,
            "results": [
                {"step": r.step, "module": r.module, "agent": r.agent,
                 "simulated": r.simulated, "output": r.output}
                for r in self.results
            ],
        }


class WorkflowEngine:
    def __init__(self, registry: ModuleRegistry, gate: HumanGate,
                 agents: dict[str, Agent]):
        self.registry = registry
        self.gate = gate
        self.agents = agents
        self.runs: dict[str, WorkflowRun] = {}

    def get_run(self, run_id: str) -> WorkflowRun:
        return self.runs[run_id]

    async def start(self, workflow_name: str,
                    payload: dict[str, Any] | None = None) -> WorkflowRun:
        definition = WORKFLOWS[workflow_name]
        run = WorkflowRun(definition=definition, payload=payload or {})
        self.runs[run.id] = run
        await self._advance(run)
        return run

    async def resolve_approval(self, run_id: str, request_id: str, *,
                               approved: bool, actor: str,
                               note: str | None = None) -> WorkflowRun:
        run = self.get_run(run_id)
        req = self.gate.resolve(request_id, approved=approved, actor=actor,
                                note=note)
        if run.pending_approval_id != request_id:
            return run
        run.pending_approval_id = None
        if req.state is ApprovalState.REJECTED:
            run.state = WorkflowState.REJECTED
            return run
        run.state = WorkflowState.RUNNING
        await self._execute_current_step(run, approved_by=actor)
        if run.state is WorkflowState.RUNNING:
            run.cursor += 1
            await self._advance(run)
        return run

    # -- internals -------------------------------------------------------------

    async def _advance(self, run: WorkflowRun) -> None:
        while run.state is WorkflowState.RUNNING:
            if run.cursor >= len(run.definition.steps):
                run.state = WorkflowState.COMPLETED
                return
            step = run.definition.steps[run.cursor]
            if self.registry.requires_human_gate(step.module):
                spec = self.registry.get(step.module)
                req = self.gate.request(
                    workflow_id=run.id, step=step.name, module=step.module,
                    risk=spec.risk.value,
                    summary=step.summary or spec.description,
                )
                run.pending_approval_id = req.id
                run.state = WorkflowState.AWAITING_APPROVAL
                return
            await self._execute_current_step(run)
            if run.state is WorkflowState.RUNNING:
                run.cursor += 1

    async def _execute_current_step(self, run: WorkflowRun,
                                    approved_by: str | None = None) -> None:
        step = run.definition.steps[run.cursor]
        spec = self.registry.get(step.module)
        agent = self.agents[spec.agent]

        if self.registry.is_hard_blocked_autonomous(step.module):
            # Treasury/securities surface: approval unlocks preparation only.
            run.results.append(StepResult(
                step=step.name, module=step.module, agent=spec.agent,
                simulated=True,
                output={
                    "status": "PREPARED_FOR_MULTISIG",
                    "detail": "Execution requires human multi-sig off-platform; "
                              "platform prepared and recorded the artifact only.",
                    "approved_by": approved_by,
                },
            ))
            return

        simulate = (spec.status is not Status.LIVE
                    or not self.registry.may_execute_effects(step.module))
        try:
            output = await agent.handle(step.module, step.name, run.payload,
                                        simulate=simulate)
        except Exception as exc:  # breaker feed + terminal failure
            self.registry.record_failure(step.module)
            run.state = WorkflowState.FAILED
            run.error = f"{step.module}: {exc}"
            return
        self.registry.record_success(step.module)
        if approved_by is not None:
            output = {**output, "approved_by": approved_by}
        run.results.append(StepResult(
            step=step.name, module=step.module, agent=spec.agent,
            simulated=simulate, output=output,
        ))
