"""Hypothetical Amesbury/Newburyport nano-chain demonstration.

This is a workflow demonstration, not a live parcel/zoning determination.
Every payload that does not set `verified_parcel=True` is labeled
hypothetical. Stephanie never authorizes acquisition from these helpers.
"""

from __future__ import annotations

from typing import Any

from . import nano_236

DEMO_MARKET = "Amesbury/Newburyport"
DEMO_PROGRAM = "6-unit infill + 2 ADUs"
DEMO_UNITS = 8
DEMO_SITE_ID = "SITE-001"

DEFAULT_COSTS: dict[str, int] = {
    "acquisition": 650_000,
    "hard_construction": 2_100_000,
    "soft_costs": 350_000,
    "financing_carry": 300_000,
    "contingency": 210_000,
}
DEFAULT_UNIT_VALUE = 550_000
HARD_OVERRUN_RATE = 0.10

SEQUENCE_SPINE: tuple[str, ...] = (
    "preconstruction",
    "sitework",
    "foundation",
    "framing_dry_in",
    "mep_rough",
    "inspections",
    "insulation",
    "drywall",
    "finishes",
    "exterior_site_completion",
    "co_closeout",
)

ENTITLEMENT_SURFACES: tuple[str, ...] = (
    "dimensional_requirements",
    "density",
    "parking",
    "adu_eligibility",
    "utilities",
    "fire_access",
    "stormwater",
    "conservation_flood",
    "required_municipal_approvals",
)

EVIDENCE_GRAPH: tuple[str, ...] = (
    "parcel",
    "entitlement",
    "drawings",
    "estimate",
    "subcontractors",
    "schedule",
    "inspections",
    "draws",
    "closeout",
    "tenants",
    "maintenance",
    "asset_performance",
)


def is_hypothetical(payload: dict[str, Any]) -> bool:
    if nano_236.is_site_236(payload):
        return False
    return not bool(payload.get("verified_parcel"))


def is_site_236(payload: dict[str, Any]) -> bool:
    return nano_236.is_site_236(payload)


def site_id(payload: dict[str, Any]) -> str:
    if nano_236.is_site_236(payload):
        return nano_236.SITE_ID
    return str(payload.get("site_id") or DEMO_SITE_ID)


def costs_from(payload: dict[str, Any]) -> dict[str, int]:
    incoming = payload.get("costs") or {}
    merged = dict(DEFAULT_COSTS)
    for key in DEFAULT_COSTS:
        if key in incoming:
            merged[key] = int(incoming[key])
    return merged


def feasibility_model(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.feasibility_model(payload)
    costs = costs_from(payload)
    units = int(payload.get("units") or DEMO_UNITS)
    unit_value = int(payload.get("unit_value") or DEFAULT_UNIT_VALUE)
    total = sum(costs.values())
    gross = units * unit_value
    spread = gross - total
    overrun = int(round(costs["hard_construction"] * HARD_OVERRUN_RATE))
    stressed_spread = spread - overrun
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "market": payload.get("market") or DEMO_MARKET,
        "program": payload.get("program") or DEMO_PROGRAM,
        "units": units,
        "costs": costs,
        "total_modeled_cost": total,
        "unit_value": unit_value,
        "modeled_gross_value": gross,
        "preliminary_spread": spread,
        "hard_cost_overrun": {
            "rate": HARD_OVERRUN_RATE,
            "amount": overrun,
            "stressed_spread": stressed_spread,
        },
        "acquisition_authorized": False,
        "gate": "DUE_DILIGENCE_ONLY",
        "gate_note": (
            "Stephanie does not authorize acquisition. "
            "The model advances only for deeper due diligence."
        ),
    }


def site_screen(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.site_screen(payload)
    hypothetical = is_hypothetical(payload)
    status = "VERIFY" if hypothetical else payload.get("screen_status", "VERIFY")
    surfaces = {
        name: {"status": status, "evidence": "unverified_hypothetical" if hypothetical else "source_pending"}
        for name in (
            "zoning_use_compatibility",
            "lot_geometry",
            "utilities",
            "access",
            "flood_environmental",
            "comparable_development",
            "permitting_complexity",
        )
    }
    return {
        "hypothetical": hypothetical,
        "site_id": site_id(payload),
        "market": payload.get("market") or DEMO_MARKET,
        "program": payload.get("program") or DEMO_PROGRAM,
        "stage": "STAGED",
        "advances_to": "feasibility",
        "subject_to": "verified parcel and municipal data",
        "acquisition_authorized": False,
        "acquisition_screen": surfaces,
        "note": (
            "Workflow demonstration, not a live parcel/zoning determination."
            if hypothetical else
            "Screen remains STAGED until each surface cites current municipal source evidence."
        ),
    }


def entitlement_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.entitlement_matrix(payload)
    hypothetical = is_hypothetical(payload)
    matrix = [
        {
            "surface": surface,
            "status": "UNVERIFIED",
            "permitted": False,
            "source": None,
            "action": "VERIFY against current adopting authority / AHJ",
        }
        for surface in ENTITLEMENT_SURFACES
    ]
    return {
        "hypothetical": hypothetical,
        "site_id": site_id(payload),
        "jurisdiction": payload.get("jurisdiction") or DEMO_MARKET,
        "matrix": matrix,
        "anything_labeled_permitted": False,
        "note": "Nothing is labeled permitted until source evidence supports it.",
    }


def design_concepts(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.design_concepts(payload)
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "concepts": [
            {
                "id": "max_yield",
                "name": "Maximum yield",
                "intent": "Most units/GFA the surviving entitlement assumptions allow.",
            },
            {
                "id": "lower_cost",
                "name": "Lower-cost construction",
                "intent": "Simpler structure, repeated bays, fewer unique conditions.",
            },
            {
                "id": "balanced",
                "name": "Balanced yield / community fit",
                "intent": "Massing, parking, and open space that reads as a neighbor.",
            },
        ],
        "selected_concept": payload.get("selected_concept") or "balanced",
        "selection_authority": "human",
        "stamped_drawings": False,
    }


def construction_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.construction_sequence(payload)
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "selected_concept": payload.get("selected_concept") or "balanced",
        "spine": list(SEQUENCE_SPINE),
        "critical_path_inputs": [
            "supplier_availability",
            "inspection_dependencies",
            "weather_exposure",
            "long_lead_items",
        ],
    }


def draw_package(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.draw_package(payload)
    requested = int(payload.get("draw_requested") or 287_500)
    evidence = int(payload.get("evidence_completeness") or 94)
    exception = payload.get("draw_exception") or (
        "electrical change order lacks final approval"
    )
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "draw": "04",
        "status": "DRAFT / HUMAN APPROVAL REQUIRED",
        "requested": requested,
        "evidence_completeness": evidence,
        "exception": exception,
        "action": "HOLD affected amount",
        "funds_released": False,
    }


def stress_tests(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.stress_tests(payload)
    model = feasibility_model(payload)
    overrun = model["hard_cost_overrun"]
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "base_spread": model["preliminary_spread"],
        "scenarios": [
            {
                "driver": "cost_escalation",
                "shock": "10% hard-cost overrun",
                "delta": overrun["amount"],
                "stressed_spread": overrun["stressed_spread"],
            },
            {
                "driver": "schedule_delay",
                "shock": "inspection/weather/long-lead slip → extra carry",
                "note": "carry increases; spread compresses",
            },
            {
                "driver": "rate",
                "shock": "+200 bps construction-loan rate",
                "note": "financing/carry line rises",
            },
            {
                "driver": "absorption",
                "shock": "slower sale/lease-up; hold period extends",
                "note": "cash trough deepens",
            },
            {
                "driver": "permitting",
                "shock": "longer review / extra condition / ADU path fails",
                "note": "entitlement UNVERIFIED rows remain binding",
            },
        ],
        "base_case_is_not_the_plan": True,
        "acquisition_authorized": False,
    }


def property_ops(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.property_ops(payload)
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "phase": "post_closeout",
        "surfaces": [
            "maintenance",
            "vendor_coordination",
            "operating_cost_tracking",
            "recurring_problem_detection",
        ],
        "attached_to_graph": True,
    }


def evidence_graph(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.evidence_graph(payload)
    return {
        "hypothetical": is_hypothetical(payload),
        "site_id": site_id(payload),
        "graph": list(EVIDENCE_GRAPH),
        "value": (
            "One project becomes a reusable evidence graph instead of "
            "disappearing into PDFs, emails, spreadsheets and people's heads."
        ),
    }


def five_harness(payload: dict[str, Any]) -> dict[str, Any]:
    if nano_236.is_site_236(payload):
        return nano_236.five_harness(payload)
    verified = bool(payload.get("verified_parcel"))
    testing_verified = bool(payload.get("testing_verified"))
    return {
        "hypothetical": not verified,
        "site_id": site_id(payload),
        "harness": {
            "execution": "PASS",
            "governance": "HUMAN GATES ACTIVE",
            "security_compliance": "PASS pending project-specific validation",
            "observability_evidence": "STAGED" if not verified else "PASS",
            "testing_release": "PASS" if testing_verified else "NOT VERIFIED",
        },
        "overall_state": (
            "LIVE" if verified and testing_verified
            else "STAGED — DUE DILIGENCE REQUIRED"
        ),
        "next_level": (
            "Run this same chain against a real Amesbury/Newburyport parcel, "
            "pulling current parcel, zoning and market evidence rather than "
            "using hypothetical numbers."
        ),
        "acquisition_authorized": False,
    }
