import asyncio

from nobleport.agents import build_agents
from nobleport.human_gate import HumanGate
from nobleport.registry import ModuleRegistry
from nobleport.workflows import WORKFLOWS, WorkflowEngine, WorkflowState
from nobleport.workflows.definitions import Step


def make_engine():
    registry = ModuleRegistry()
    gate = HumanGate()
    return WorkflowEngine(registry, gate, build_agents()), registry, gate


def test_all_workflow_steps_target_catalog_modules():
    registry = ModuleRegistry()
    for wf in WORKFLOWS.values():
        for step in wf.steps:
            registry.get(step.module)  # raises if unknown


def test_workflow_runs_until_human_gate():
    engine, _, gate = make_engine()
    run = asyncio.run(engine.start("lead_to_estimate", {
        "lead": {"name": "Ada", "scope_hint": "kitchen remodel"},
        "line_items": [{"amount": 1000.0}, {"amount": 250.5}],
    }))
    # bid step (estimating.bid_package, HIGH) must suspend the run
    assert run.state is WorkflowState.AWAITING_APPROVAL
    assert run.cursor == 5  # five low/medium steps completed
    assert len(run.results) == 5
    pending = gate.pending_for_workflow(run.id)
    assert len(pending) == 1
    assert pending[0].module == "estimating.bid_package"
    # cost model ran with real math
    cost = next(r for r in run.results if r.module == "estimating.cost_model")
    assert cost.output["cost_model"]["total"] == 1375.55


def test_approval_resumes_and_completes():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("lead_to_estimate", {"lead": {}}))
    assert run.state is WorkflowState.AWAITING_APPROVAL
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=True, actor="ops@nobleport"))
    assert run.state is WorkflowState.COMPLETED
    bid = run.results[-1]
    assert bid.module == "estimating.bid_package"
    assert bid.output["approved_by"] == "ops@nobleport"


def test_rejection_terminates_run():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("lead_to_estimate", {"lead": {}}))
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=False, actor="ops@nobleport",
        note="pricing off"))
    assert run.state is WorkflowState.REJECTED
    # the gated step never executed
    assert all(r.module != "estimating.bid_package" for r in run.results)


def test_critical_step_never_executes_even_when_approved():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("subcontractor_payout", {}))
    # first HIGH gate: payment_reconcile
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=True, actor="cfo@nobleport"))
    # second HIGH gate: lien_waiver
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=True, actor="counsel@nobleport"))
    # third gate: CRITICAL payout_release
    assert run.state is WorkflowState.AWAITING_APPROVAL
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=True, actor="cfo@nobleport"))
    assert run.state is WorkflowState.COMPLETED
    release = run.results[-1]
    assert release.module == "finance.payout_release"
    assert release.simulated is True
    assert release.output["status"] == "PREPARED_FOR_MULTISIG"


def test_staged_modules_run_simulated():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("permit_submission",
                                   {"jurisdiction": "Essex County, MA",
                                    "permit_types": ["building", "electrical"]}))
    for result in run.results:
        assert result.simulated is True


def test_failure_trips_breaker_and_fails_run():
    engine, registry, _ = make_engine()

    class Exploding:
        name = "stephanie"

        async def handle(self, module, action, payload, *, simulate):
            raise RuntimeError("boom")

    engine.agents["stephanie"] = Exploding()
    for _ in range(ModuleRegistry.BREAKER_THRESHOLD):
        run = asyncio.run(engine.start("daily_operations", {}))
        assert run.state is WorkflowState.FAILED
        assert "boom" in run.error
    assert registry.health("jobs.daily_log").tripped
