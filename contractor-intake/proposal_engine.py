"""AI proposal engine — generates scope of work and proposals from intake data.

Uses Claude API to produce:
1. Structured scope of work from free-text project description
2. Line-item cost estimates with material and labor breakdown
3. Timeline estimate
4. Permit/code requirements
5. Full proposal document

Falls back to template-based generation if API is unavailable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import audit
from config import Config
from db import Lead, Proposal, ProposalStatus

SCOPE_PROMPT = """You are an expert construction estimator and proposal writer.
Given the following project intake information, generate a detailed scope of work.

Project Type: {project_type}
Description: {description}
Property Address: {address}
Budget Range: ${budget_min:,.0f} - ${budget_max:,.0f}
Timeline Preference: {timeline}

Generate a JSON response with these fields:
{{
  "scope_of_work": "Detailed scope of work text with numbered items",
  "line_items": [
    {{"description": "item", "category": "labor|material|permit|other", "amount": 0.00}}
  ],
  "total_estimate_low": 0.00,
  "total_estimate_high": 0.00,
  "estimated_duration": "X weeks",
  "permit_requirements": "List of required permits",
  "material_specifications": "Key material specs and recommendations",
  "code_considerations": "Relevant building code requirements",
  "deposit_percentage": 0.0
}}

Be specific and realistic. Use current market rates for the Northeast US.
"""

FALLBACK_TEMPLATES: dict[str, dict] = {
    "kitchen": {
        "scope_of_work": (
            "Kitchen renovation including:\n"
            "1. Demolition of existing cabinetry and countertops\n"
            "2. Electrical updates to meet current code\n"
            "3. Plumbing rough-in for new layout\n"
            "4. Cabinet installation\n"
            "5. Countertop fabrication and installation\n"
            "6. Backsplash installation\n"
            "7. Flooring installation\n"
            "8. Painting and trim\n"
            "9. Fixture installation\n"
            "10. Final inspection and punch list"
        ),
        "estimated_duration": "6-8 weeks",
        "permit_requirements": "Building permit, electrical permit, plumbing permit",
        "deposit_percentage": 25.0,
    },
    "bathroom": {
        "scope_of_work": (
            "Bathroom renovation including:\n"
            "1. Demolition of existing fixtures and finishes\n"
            "2. Plumbing rough-in\n"
            "3. Electrical updates (GFCI outlets, ventilation fan)\n"
            "4. Waterproofing and substrate preparation\n"
            "5. Tile installation (floor and walls)\n"
            "6. Vanity and countertop installation\n"
            "7. Fixture installation (toilet, shower/tub, faucets)\n"
            "8. Glass enclosure installation\n"
            "9. Painting and trim\n"
            "10. Final inspection and punch list"
        ),
        "estimated_duration": "3-5 weeks",
        "permit_requirements": "Building permit, plumbing permit, electrical permit",
        "deposit_percentage": 30.0,
    },
    "roofing": {
        "scope_of_work": (
            "Roof replacement including:\n"
            "1. Removal of existing roofing material\n"
            "2. Inspection of roof deck and repair as needed\n"
            "3. Installation of ice and water shield\n"
            "4. Installation of synthetic underlayment\n"
            "5. Installation of drip edge and flashing\n"
            "6. Shingle installation (architectural grade)\n"
            "7. Ridge vent installation\n"
            "8. Cleanup and debris removal\n"
            "9. Final inspection"
        ),
        "estimated_duration": "3-5 days",
        "permit_requirements": "Building permit",
        "deposit_percentage": 33.0,
    },
}

DEFAULT_TEMPLATE: dict = {
    "scope_of_work": (
        "General construction project including:\n"
        "1. Site preparation and protection\n"
        "2. Demolition as required\n"
        "3. Structural modifications per plan\n"
        "4. Mechanical/electrical/plumbing as required\n"
        "5. Finish work\n"
        "6. Cleanup and final inspection"
    ),
    "estimated_duration": "4-8 weeks",
    "permit_requirements": "Building permit (verify with local authority)",
    "deposit_percentage": 25.0,
}


async def generate_scope(
    config: Config,
    lead: Lead,
) -> dict:
    if config.anthropic_api_key:
        try:
            return await _generate_with_claude(config, lead)
        except Exception:
            pass

    return _generate_fallback(lead)


async def _generate_with_claude(config: Config, lead: Lead) -> dict:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)

    prompt = SCOPE_PROMPT.format(
        project_type=lead.project_type.value,
        description=lead.project_description,
        address=lead.property_address,
        budget_min=lead.budget_min or 0,
        budget_max=lead.budget_max or 0,
        timeline=lead.timeline or "flexible",
    )

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    start = response_text.find("{")
    end = response_text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(response_text[start:end])

    return _generate_fallback(lead)


def _generate_fallback(lead: Lead) -> dict:
    template = FALLBACK_TEMPLATES.get(lead.project_type.value, DEFAULT_TEMPLATE)
    budget_mid = ((lead.budget_min or 10000) + (lead.budget_max or 50000)) / 2
    deposit_pct = template.get("deposit_percentage", 25.0)

    return {
        "scope_of_work": template["scope_of_work"],
        "line_items": [
            {
                "description": "Labor",
                "category": "labor",
                "amount": round(budget_mid * 0.45, 2),
            },
            {
                "description": "Materials",
                "category": "material",
                "amount": round(budget_mid * 0.40, 2),
            },
            {
                "description": "Permits and fees",
                "category": "permit",
                "amount": round(budget_mid * 0.05, 2),
            },
            {
                "description": "Overhead and profit",
                "category": "other",
                "amount": round(budget_mid * 0.10, 2),
            },
        ],
        "total_estimate_low": round(budget_mid * 0.85, 2),
        "total_estimate_high": round(budget_mid * 1.15, 2),
        "estimated_duration": template["estimated_duration"],
        "permit_requirements": template["permit_requirements"],
        "material_specifications": "Standard grade materials. Upgrade options available.",
        "code_considerations": "All work to comply with current building code.",
        "deposit_percentage": deposit_pct,
    }


async def create_proposal(
    session: AsyncSession,
    config: Config,
    lead: Lead,
) -> Proposal:
    scope_data = await generate_scope(config, lead)

    lead.generated_scope = scope_data.get("scope_of_work", "")
    lead.estimated_range_low = scope_data.get("total_estimate_low")
    lead.estimated_range_high = scope_data.get("total_estimate_high")

    total = sum(item["amount"] for item in scope_data.get("line_items", []))
    deposit_pct = scope_data.get("deposit_percentage", 25.0)

    proposal = Proposal(
        contractor_id=lead.contractor_id,
        lead_id=lead.id,
        scope_of_work=scope_data.get("scope_of_work", ""),
        line_items_json=json.dumps(scope_data.get("line_items", [])),
        total_amount=total,
        deposit_required=round(total * deposit_pct / 100, 2),
        estimated_duration=scope_data.get("estimated_duration"),
        terms_and_conditions=(
            "1. Payment schedule: deposit due at signing, progress payments per milestone, final payment at completion.\n"
            "2. Change orders require written approval and may adjust price and timeline.\n"
            "3. Contractor maintains liability insurance and workers compensation.\n"
            "4. Warranty: 1 year workmanship, manufacturer warranty on materials.\n"
            "5. Permits are the responsibility of the contractor unless otherwise noted."
        ),
        permit_requirements=scope_data.get("permit_requirements"),
        material_specifications=scope_data.get("material_specifications"),
        status=ProposalStatus.DRAFT,
    )
    session.add(proposal)

    await audit.log(
        session,
        entity_type="proposal",
        entity_id=proposal.id,
        action="proposal.created",
        actor="proposal_engine",
        detail=f"Proposal generated for lead {lead.id}: ${total:,.2f}",
        metadata={
            "lead_id": lead.id,
            "contractor_id": lead.contractor_id,
            "total_amount": total,
            "line_item_count": len(scope_data.get("line_items", [])),
        },
    )
    await session.commit()
    return proposal
