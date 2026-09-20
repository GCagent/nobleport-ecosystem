"""Nano-ecosystem infill chain — demonstration + governance tests."""

import asyncio

from nobleport.modules import CATALOG, Risk, Status, catalog_by_cluster
from nobleport.nano_demo import (
    DEFAULT_COSTS,
    EVIDENCE_GRAPH,
    SEQUENCE_SPINE,
    feasibility_model,
)
from nobleport.workflows import WORKFLOWS, WorkflowState
from nobleport.workflows.definitions import Step

from tests.test_workflows import make_engine

NANO_MODULES = (
    "nano.site_selector",
    "nano.feasibility",
    "nano.entitlement",
    "nano.generative_design",
    "nano.sequence_optimizer",
    "nano.stress_tester",
    "nano.draw_manager",
    "nano.property_ops",
    "nano.orchestrator",
    "nano.five_harness",
)


def test_nano_cluster_is_staged_and_complete():
    cluster = catalog_by_cluster("nano")
    names = {m.name for m in cluster}
    assert names == set(NANO_MODULES)
    assert all(m.status is Status.STAGED for m in cluster)
    draw = next(m for m in cluster if m.name == "nano.draw_manager")
    assert draw.risk is Risk.HIGH
    assert draw.agent == "stephanie"
    entitlement = next(m for m in cluster if m.name == "nano.entitlement")
    assert entitlement.agent == "permitstream"


def test_catalog_still_has_unique_names_after_nano():
    names = [m.name for m in CATALOG]
    assert len(names) == len(set(names))
    assert len(CATALOG) >= 60


def test_feasibility_math_matches_demonstration():
    model = feasibility_model({})
    assert model["total_modeled_cost"] == 3_610_000
    assert model["modeled_gross_value"] == 4_400_000
    assert model["preliminary_spread"] == 790_000
    assert model["hard_cost_overrun"]["amount"] == 210_000
    assert model["hard_cost_overrun"]["stressed_spread"] == 580_000
    assert model["acquisition_authorized"] is False
    assert model["gate"] == "DUE_DILIGENCE_ONLY"
    assert model["hypothetical"] is True
    assert sum(DEFAULT_COSTS.values()) == 3_610_000


def test_nano_infill_chain_definition():
    wf = WORKFLOWS["nano_infill_chain"]
    assert [s.module for s in wf.steps] == [
        "nano.site_selector",
        "nano.feasibility",
        "nano.entitlement",
        "nano.generative_design",
        "nano.sequence_optimizer",
        "nano.stress_tester",
        "nano.draw_manager",
        "nano.property_ops",
        "nano.orchestrator",
        "nano.five_harness",
    ]
    assert all(isinstance(s, Step) for s in wf.steps)


def test_nano_chain_suspends_on_draw_gate():
    engine, _, gate = make_engine()
    run = asyncio.run(engine.start("nano_infill_chain", {
        "market": "Amesbury/Newburyport",
        "program": "6-unit infill + 2 ADUs",
    }))
    # six LOW/MEDIUM steps complete; draw (HIGH) suspends
    assert run.state is WorkflowState.AWAITING_APPROVAL
    assert run.cursor == 6
    assert len(run.results) == 6
    pending = gate.pending_for_workflow(run.id)
    assert len(pending) == 1
    assert pending[0].module == "nano.draw_manager"
    assert all(r.simulated for r in run.results)

    feasibility = next(r for r in run.results if r.module == "nano.feasibility")
    model = feasibility.output["feasibility"]
    assert model["preliminary_spread"] == 790_000
    assert model["acquisition_authorized"] is False

    entitlement = next(r for r in run.results if r.module == "nano.entitlement")
    matrix = entitlement.output["entitlement"]
    assert matrix["anything_labeled_permitted"] is False
    assert all(row["permitted"] is False for row in matrix["matrix"])


def test_nano_chain_completes_after_human_draw_approval():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("nano_infill_chain", {}))
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=True, actor="ops@nobleport"))
    assert run.state is WorkflowState.COMPLETED
    assert [r.module for r in run.results] == list(NANO_MODULES)

    draw = next(r for r in run.results if r.module == "nano.draw_manager")
    pkg = draw.output["draw"]
    assert pkg["status"] == "DRAFT / HUMAN APPROVAL REQUIRED"
    assert pkg["requested"] == 287_500
    assert pkg["evidence_completeness"] == 94
    assert pkg["action"] == "HOLD affected amount"
    assert pkg["funds_released"] is False
    assert draw.output["approved_by"] == "ops@nobleport"

    sequence = next(r for r in run.results if r.module == "nano.sequence_optimizer")
    assert sequence.output["sequence"]["spine"] == list(SEQUENCE_SPINE)

    graph = next(r for r in run.results if r.module == "nano.orchestrator")
    assert graph.output["graph"]["graph"] == list(EVIDENCE_GRAPH)

    harness = run.results[-1].output["control_plane"]
    assert harness["harness"]["execution"] == "PASS"
    assert harness["harness"]["governance"] == "HUMAN GATES ACTIVE"
    assert harness["harness"]["security_compliance"].startswith("PASS")
    assert harness["harness"]["observability_evidence"] == "STAGED"
    assert harness["harness"]["testing_release"] == "NOT VERIFIED"
    assert harness["overall_state"] == "STAGED — DUE DILIGENCE REQUIRED"
    assert harness["acquisition_authorized"] is False


def test_nano_chain_rejection_never_releases_a_draw():
    engine, _, _ = make_engine()
    run = asyncio.run(engine.start("nano_infill_chain", {}))
    run = asyncio.run(engine.resolve_approval(
        run.id, run.pending_approval_id, approved=False, actor="ops@nobleport",
        note="electrical CO still open"))
    assert run.state is WorkflowState.REJECTED
    assert all(r.module != "nano.draw_manager" for r in run.results)
