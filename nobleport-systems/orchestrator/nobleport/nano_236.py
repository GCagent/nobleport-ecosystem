"""Grounded nano-chain run for 236 High Road, Newbury, MA (SITE-236HIGH).

Assessor, zoning class, and lot geometry are ingested from NoblePort's
Patriot Properties record (Account #997 / R26-0-12). Dimensional numbers
are from Newbury Zoning Bylaw Article VI (R-AG table). This is still not
an AHJ determination. The 8-unit (6+2) program fails baseline density;
Stephanie does not authorize acquisition and nothing is labeled permitted.
"""

from __future__ import annotations

from typing import Any

SITE_ID = "SITE-236HIGH"
RUN_ID = "NEWBURY-236HIGH"
ADDRESS = "236 High Road, Newbury, MA 01951"
LOT_SF = 8712
MIN_LOT_SF = 40000
TWO_FAMILY_MIN_SF_PUBLIC_WATER = 60000
TWO_FAMILY_MIN_SF_OTHER = 80000
FRONTAGE_MIN_FT = 125
SETBACK_PROPERTY_FT = 10
SETBACK_STREET_FT = 20
HEIGHT_MAX_FT = 35

DIMENSIONAL = {
    "district": "R-AG",
    "district_name": "Residential-Agricultural",
    "district_alias": "AR / Agricultural-Residential",
    "source": "Newbury Zoning Bylaw, Article VI — Table of Dimensional Requirements",
    "single_family": {
        "lot_sf": MIN_LOT_SF,
        "frontage_ft": FRONTAGE_MIN_FT,
        "setback_property_ft": SETBACK_PROPERTY_FT,
        "setback_street_ft": SETBACK_STREET_FT,
        "height_ft": HEIGHT_MAX_FT,
    },
    "two_family_public_water": {
        "lot_sf": TWO_FAMILY_MIN_SF_PUBLIC_WATER,
        "frontage_ft": FRONTAGE_MIN_FT,
        "setback_property_ft": SETBACK_PROPERTY_FT,
        "setback_street_ft": SETBACK_STREET_FT,
        "height_ft": HEIGHT_MAX_FT,
    },
    "two_family_other": {
        "lot_sf": TWO_FAMILY_MIN_SF_OTHER,
        "frontage_ft": FRONTAGE_MIN_FT,
        "setback_property_ft": SETBACK_PROPERTY_FT,
        "setback_street_ft": SETBACK_STREET_FT,
        "height_ft": HEIGHT_MAX_FT,
    },
    "lot_meets_any_row": False,
}

HISTORIC = {
    "bylaw": "Newbury Chapter 65 — Historic Preservation",
    "delay_months_if_preferably_preserved": 9,
    "existing_structure_year": 2021,
    "existing_structure_likely_significant": False,
    "corridor_scrutiny": True,
    "note": (
        "2021 barn (permit #21-329RB) is modern construction. "
        "High Road streetscape and any new massing still need inventory review."
    ),
}


def is_site_236(payload: dict[str, Any]) -> bool:
    blob = " ".join(
        str(payload.get(k) or "")
        for k in ("site_id", "address", "run_id", "parcel_id")
    ).upper()
    return "236" in blob and any(
        token in blob for token in ("HIGH", "NEWBURY", "R26", "SITE-236")
    )


def site_screen(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "run_id": RUN_ID,
        "address": ADDRESS,
        "market": "Newbury, MA",
        "program": "6-unit infill + 2 ADUs",
        "classification": "CONSTRAINED INFILL",
        "stage": "STAGED",
        "lot_sf": LOT_SF,
        "zoning": "R-AG",
        "min_lot_sf": MIN_LOT_SF,
        "nonconforming": True,
        "dimensional": DIMENSIONAL,
        "historic": HISTORIC,
        "corridor": "Historic First Parish / High Road (Route 1A)",
        "structure": "Barn / outbuilding, LUC 106, permit #21-329RB",
        "advances_to": "feasibility",
        "subject_to": "dimensional gating",
        "acquisition_authorized": False,
        "acquisition_screen": {
            "zoning_use_compatibility": {
                "status": "CAUTION",
                "evidence": "R-AG; accessory barn; no principal dwelling on record",
            },
            "lot_geometry": {
                "status": "HALT",
                "evidence": (
                    f"{LOT_SF} SF vs {MIN_LOT_SF} SF R-AG single-family / "
                    f"{TWO_FAMILY_MIN_SF_PUBLIC_WATER}–{TWO_FAMILY_MIN_SF_OTHER} SF two-family"
                ),
            },
            "utilities": {
                "status": "VERIFY",
                "evidence": "Title 5 vs municipal sewer on Route 1A",
            },
            "access": {
                "status": "CAUTION",
                "evidence": "Route 1A frontage; MassDOT / municipal curb-cut",
            },
            "flood_environmental": {
                "status": "VERIFY",
                "evidence": "Confirm FEMA / conservation overlays on Newbury GIS",
            },
            "comparable_development": {
                "status": "STAGED",
                "evidence": "105 High Road OSRD; 100 High Road subdivision; no 8-unit 0.20-acre R-AG precedent",
            },
            "permitting_complexity": {
                "status": "GATE_LOCKED",
                "evidence": "Historic corridor + c. 40A §6 nonconformity + ADU path",
            },
        },
        "note": (
            "Assessor records ingested. Tagged CONSTRAINED INFILL. "
            "Not an AHJ zoning determination."
        ),
    }


def feasibility_model(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "program_requested": "6-unit infill + 2 ADUs",
        "requested_feasible": False,
        "yields": [
            {
                "id": "requested",
                "program": "6-unit infill + 2 ADUs (8 units)",
                "units": 8,
                "feasible": False,
                "path": "Failed baseline — lot coverage / parking geometry",
            },
            {
                "id": "by_right",
                "program": "Single-family + 1 ADU",
                "units": 2,
                "feasible": True,
                "path": "M.G.L. c. 40A §3 (AHA) subject to a principal dwelling and §6 treatment of the nonconformity",
            },
            {
                "id": "discretionary",
                "program": "Two-family conversion or detached carriage ADU",
                "units": 2,
                "feasible": True,
                "path": (
                    f"ZBA relief for lot area ({TWO_FAMILY_MIN_SF_PUBLIC_WATER}–"
                    f"{TWO_FAMILY_MIN_SF_OTHER} SF table vs {LOT_SF} SF), coverage, setbacks, wastewater"
                ),
            },
        ],
        "acquisition_authorized": False,
        "gate": "DENSITY_GATE_LOCKED",
        "gate_note": (
            "Stephanie does not authorize acquisition. "
            "The 8-unit pipeline is halted; diligence continues on a downscaled program."
        ),
    }


def entitlement_matrix(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [
        ("dimensional_controls", "GATE_LOCKED",
         f"Non-conforming area/frontage vs R-AG {MIN_LOT_SF} SF / {FRONTAGE_MIN_FT} ft (Article VI).",
         "M.G.L. c. 40A §6 finding / special permit — VERIFY with Newbury ZBA counsel."),
        ("density", "FAILED",
         "8-unit (6+2) density fails lot coverage and parking geometry on 8,712 SF.",
         "Downscale to Single+ADU or Two-Family. Do not advance 8-unit drawings."),
        ("parking", "FAILED",
         "8-unit parking demand cannot be met on this footprint without coverage/setback violations.",
         "Re-size parking to the gated program only."),
        ("adu_eligibility", "VERIFY",
         "AHA ADU-by-right is accessory to a principal dwelling. No principal dwelling on record.",
         "Legal opinion on barn-to-ADU vs new principal dwelling + ADU."),
        ("historical_context", "CAUTION",
         "High Road corridor — Chapter 65 nine-month delay if Preferably Preserved. 2021 barn is not itself historic; new massing still needs inventory.",
         "Historic inventory check before exterior alteration or new massing."),
        ("water_wastewater", "VERIFY",
         "Title 5 setbacks on 8,712 SF cap bedroom count if not on sewer.",
         "Verify municipal sewer on Route 1A vs on-site septic."),
        ("mass_stretch_code", "VERIFY",
         "HERS ≤ 42 pathway + all-electric heat-pump infrastructure for any new dwelling/ADU.",
         "Confirm current Newbury Stretch / Specialized Code adoption."),
        ("access_staging", "CAUTION",
         "Route 1A is a high-visibility thoroughfare.",
         "MassDOT / municipal curb-cut and traffic staging plan on the critical path."),
        ("required_municipal_approvals", "STAGED",
         "Building, ZBA, historic/demolition delay if triggered, Board of Health, possibly MassDOT.",
         "Nothing labeled permitted until source evidence supports it."),
    ]
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "jurisdiction": "Town of Newbury",
        "matrix": [
            {
                "surface": surface,
                "status": status,
                "permitted": False,
                "finding": finding,
                "action": action,
            }
            for surface, status, finding, action in rows
        ],
        "anything_labeled_permitted": False,
        "wastewater": {
            "status": "VERIFY",
            "sewer_unknown": True,
            "on_sewer": (
                "Bedroom count still limited by setbacks, parking, and §6 — "
                "sewer removes the Title 5 reserve-area ceiling, not the density gate."
            ),
            "on_title_5": (
                "System, foundation, and reserve-area setbacks on 8,712 SF "
                "create an immediate bedroom ceiling."
            ),
        },
        "note": "Nothing is labeled permitted until source evidence supports it.",
    }


def design_concepts(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "pipeline_halted": "8-unit multifamily",
        "concepts": [
            {
                "id": "eight_unit",
                "name": "Maximum yield (6+2)",
                "intent": "Halted. Density fails lot coverage and parking.",
                "status": "halted",
            },
            {
                "id": "historic_sf_adu",
                "name": "Historic preservation + high-performance ADU",
                "intent": "Quiet principal dwelling + one ADU; Stretch Code / heat pump; barn language retained where lawful.",
                "status": "active",
            },
            {
                "id": "zba_two_family",
                "name": "ZBA two-family / carriage pathway",
                "intent": "Discretionary two-family or detached carriage, contingent on coverage, setback, and wastewater relief.",
                "status": "active",
            },
        ],
        "selected_concept": payload.get("selected_concept") or "historic_sf_adu",
        "selection_authority": "human",
        "stamped_drawings": False,
        "pivot": True,
        "historic": HISTORIC,
    }


def construction_sequence(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "selected_concept": payload.get("selected_concept") or "historic_sf_adu",
        "spine": [
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
        ],
        "critical_path_inputs": [
            "historic_inventory",
            "section_6_finding",
            "title5_or_sewer",
            "route_1a_traffic_plan",
            "massdot_curb_cut",
            "stretch_code_heat_pump",
        ],
        "route_1a_constraints": [
            "traffic_management",
            "curb_cut",
            "delivery_buffer",
            "historic_predecessor",
        ],
    }


def draw_package(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "draw": None,
        "status": "DRAFT NOT OPENED / HUMAN APPROVAL REQUIRED",
        "requested": 0,
        "evidence_completeness": 0,
        "exception": "requested 8-unit density failed baseline",
        "action": "HOLD entire 8-unit amount; no SOV assembled",
        "funds_released": False,
    }


def stress_tests(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "binding_constraints": [
            "dimensional_nonconformity",
            "wastewater",
            "historic_review",
        ],
        "scenarios": [
            {"driver": "density", "shock": "8-unit program", "result": "FAILED BASELINE"},
            {"driver": "permitting", "shock": "§6 finding denied or ADU path fails without a principal dwelling"},
            {"driver": "wastewater", "shock": "Title 5 reserve area consumes the lot; bedroom count collapses"},
            {"driver": "historic", "shock": "Chapter 65 delay / corridor design review extends preconstruction"},
            {"driver": "cost_escalation", "note": "Do not underwrite a 10% overrun on an 8-unit model that cannot be built"},
        ],
        "base_case_is_not_the_plan": True,
        "acquisition_authorized": False,
    }


def property_ops(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "phase": "current_lawful_use",
        "surfaces": [
            "accessory_storage_barn",
            "no_occupied_units",
        ],
        "note": "Barn remains NoblePort contractor storage. Occupied-unit ops do not start until a dwelling exists.",
        "attached_to_graph": True,
    }


def evidence_graph(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "graph": [
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
        ],
        "superseded": ["8-unit drawings", "8-unit estimate", "8-unit draws"],
        "next_evidence": [
            "Title 5 vs sewer",
            "historic inventory",
            "§6 legal opinion",
        ],
        "value": (
            "One project becomes a reusable evidence graph — including the halt."
        ),
    }


def five_harness(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "hypothetical": False,
        "grounded": True,
        "site_id": SITE_ID,
        "run_id": RUN_ID,
        "harness": {
            "execution": "PASS",
            "governance": "GATE LOCKED",
            "security_compliance": "CAUTION",
            "observability_evidence": "STAGED",
            "testing_release": "FAILED BASELINE",
        },
        "harness_notes": {
            "execution": "Registry/assessor records ingested",
            "governance": "Density must downscale from 6+2 to Single+ADU or Two-Family",
            "security_compliance": "Non-conforming lot expansion under Section 6",
            "observability_evidence": "Awaiting Title 5 / sewer verification and historic inventory check",
            "testing_release": "8-unit density fails lot coverage/parking geometry",
        },
        "overall_state": "STAGED — DENSITY GATE LOCKED",
        "verdict": (
            "The ecosystem halts the 8-unit multi-family pipeline and prompts "
            "Generative Design to pivot to a Historic Preservation + Single Family / "
            "High-Performance ADU model, or to initiate a formal ZBA variance pathway."
        ),
        "next_level": (
            "Title 5 vs sewer verification, historic inventory check, and a "
            "c. 40A §6 legal opinion before any downscaled scheme is drawn as entitled."
        ),
        "acquisition_authorized": False,
    }
