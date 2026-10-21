"""Contractor Intake System — FastAPI application.

Revenue loop: Lead -> Intake -> Scope -> Proposal -> Payment -> Fulfillment -> Reconciliation

All state changes write to AuditBeacon before returning.
All payment webhooks require signature verification.
Access is enforced by payment status.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import stripe
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import access_control
import audit
import mercury_handler
import proposal_engine
import stripe_handler
from config import Config, get_config
from db import (
    AccountStatus,
    AuditEntry,
    Contractor,
    Lead,
    LeadStatus,
    Proposal,
    ProposalStatus,
    ProjectType,
    get_session,
    init_db,
    shutdown_db,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    await init_db(config.database_url)
    stripe_handler.init_stripe(config)
    yield
    await shutdown_db()


app = FastAPI(
    title="Stephanie.ai Contractor Intake",
    description="AI-powered contractor intake and proposal generation",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Public — Intake form
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def intake_form(request: Request):
    return templates.TemplateResponse(
        "intake.html",
        {
            "request": request,
            "project_types": [
                {"value": pt.value, "label": pt.value.replace("_", " ").title()}
                for pt in ProjectType
            ],
        },
    )


@app.post("/api/intake")
async def submit_intake(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await request.json()

    contractor_id = data.get("contractor_id")
    if not contractor_id:
        raise HTTPException(400, "contractor_id is required")

    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(404, "Contractor not found")

    access = await access_control.check_access(session, contractor_id)
    if not access["has_access"]:
        raise HTTPException(403, f"Account access denied: {access.get('reason')}")

    lead = Lead(
        contractor_id=contractor_id,
        homeowner_name=data["homeowner_name"],
        homeowner_email=data["homeowner_email"],
        homeowner_phone=data["homeowner_phone"],
        property_address=data["property_address"],
        project_type=ProjectType(data["project_type"]),
        project_description=data["project_description"],
        budget_min=data.get("budget_min"),
        budget_max=data.get("budget_max"),
        timeline=data.get("timeline"),
        urgency=data.get("urgency"),
        source=data.get("source", "web_intake"),
    )
    session.add(lead)

    await audit.log(
        session,
        entity_type="lead",
        entity_id=lead.id,
        action="lead.created",
        actor=f"homeowner:{data['homeowner_email']}",
        detail=f"New {data['project_type']} lead from {data['homeowner_name']}",
        metadata={
            "contractor_id": contractor_id,
            "project_type": data["project_type"],
            "property_address": data["property_address"],
        },
    )
    await session.commit()

    return {
        "lead_id": lead.id,
        "status": "received",
        "message": "Your project details have been received. We'll be in touch shortly.",
    }


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------


@app.post("/api/proposals/generate/{lead_id}")
async def generate_proposal(
    lead_id: str,
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
):
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")

    access = await access_control.check_access(session, lead.contractor_id)
    if not access["has_access"]:
        raise HTTPException(403, "Account access denied")

    proposal = await proposal_engine.create_proposal(session, config, lead)

    return {
        "proposal_id": proposal.id,
        "scope_of_work": proposal.scope_of_work,
        "line_items": json.loads(proposal.line_items_json),
        "total_amount": proposal.total_amount,
        "deposit_required": proposal.deposit_required,
        "estimated_duration": proposal.estimated_duration,
        "permit_requirements": proposal.permit_requirements,
    }


@app.get("/api/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "Proposal not found")

    return {
        "id": proposal.id,
        "lead_id": proposal.lead_id,
        "scope_of_work": proposal.scope_of_work,
        "line_items": json.loads(proposal.line_items_json),
        "total_amount": proposal.total_amount,
        "deposit_required": proposal.deposit_required,
        "estimated_duration": proposal.estimated_duration,
        "terms_and_conditions": proposal.terms_and_conditions,
        "permit_requirements": proposal.permit_requirements,
        "material_specifications": proposal.material_specifications,
        "status": proposal.status.value,
        "created_at": proposal.created_at.isoformat(),
    }


@app.post("/api/proposals/{proposal_id}/send")
async def send_proposal(
    proposal_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Proposal).where(Proposal.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "Proposal not found")

    proposal.status = ProposalStatus.SENT
    proposal.sent_at = datetime.now(timezone.utc)

    await audit.log(
        session,
        entity_type="proposal",
        entity_id=proposal_id,
        action="proposal.sent",
        actor="contractor",
        detail=f"Proposal sent to homeowner for lead {proposal.lead_id}",
    )
    await session.commit()

    return {"status": "sent", "sent_at": proposal.sent_at.isoformat()}


# ---------------------------------------------------------------------------
# Contractor registration + checkout
# ---------------------------------------------------------------------------


@app.post("/api/contractors/register")
async def register_contractor(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await request.json()

    existing = await session.execute(
        select(Contractor).where(Contractor.email == data["email"])
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    contractor = Contractor(
        email=data["email"],
        company_name=data["company_name"],
        owner_name=data["owner_name"],
        phone=data["phone"],
        license_number=data.get("license_number"),
        service_area=data.get("service_area"),
        specialties=data.get("specialties"),
        status=AccountStatus.TRIAL,
    )
    session.add(contractor)

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor.id,
        action="contractor.registered",
        actor=f"contractor:{data['email']}",
        detail=f"New contractor: {data['company_name']}",
    )
    await session.commit()

    return {"contractor_id": contractor.id, "status": "trial"}


@app.post("/api/checkout")
async def create_checkout(
    request: Request,
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
):
    data = await request.json()
    contractor_id = data.get("contractor_id")

    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(404, "Contractor not found")

    checkout_session = await stripe_handler.create_checkout_session(
        config,
        contractor_email=contractor.email,
        contractor_id=contractor.id,
    )

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="payment.checkout_initiated",
        actor=f"contractor:{contractor.email}",
        detail="Stripe checkout session created",
        metadata={"checkout_session_id": checkout_session.id},
    )
    await session.commit()

    return {"checkout_url": checkout_session.url}


# ---------------------------------------------------------------------------
# Stripe webhook
# ---------------------------------------------------------------------------


@app.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    config = get_config()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe_handler.verify_webhook(
            payload, sig_header, config.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(400, "Invalid webhook signature")
    except ValueError:
        raise HTTPException(400, "Invalid payload")

    handler = stripe_handler.WEBHOOK_HANDLERS.get(event.type)
    if handler:
        await handler(session, event)

    await audit.log(
        session,
        entity_type="system",
        entity_id="stripe_webhook",
        action=f"webhook.{event.type}",
        actor="stripe",
        detail=f"Processed webhook: {event.type}",
        metadata={"event_id": event.id},
    )
    await session.commit()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------


@app.get("/api/account/{contractor_id}")
async def get_account(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(404, "Contractor not found")

    access = await access_control.check_access(session, contractor_id)

    return {
        "id": contractor.id,
        "company_name": contractor.company_name,
        "email": contractor.email,
        "status": contractor.status.value,
        "has_access": access["has_access"],
        "created_at": contractor.created_at.isoformat(),
    }


@app.post("/api/account/{contractor_id}/refund")
async def refund_account(
    contractor_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    data = await request.json()
    reason = data.get("reason", "customer_request")

    refund = await stripe_handler.process_refund(
        session,
        contractor_id=contractor_id,
        reason=reason,
        actor="admin",
    )

    await access_control.revoke_access(
        session, contractor_id, reason=f"Refund: {reason}", actor="admin"
    )

    return {
        "status": "refunded",
        "refund_id": refund.id if refund else None,
        "access_revoked": True,
    }


# ---------------------------------------------------------------------------
# Dashboard data
# ---------------------------------------------------------------------------


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/api/dashboard/{contractor_id}")
async def dashboard_data(
    contractor_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        raise HTTPException(404, "Contractor not found")

    leads_result = await session.execute(
        select(Lead).where(Lead.contractor_id == contractor_id).order_by(Lead.created_at.desc())
    )
    leads = leads_result.scalars().all()

    proposals_result = await session.execute(
        select(Proposal).where(Proposal.contractor_id == contractor_id)
    )
    proposals = proposals_result.scalars().all()

    total_pipeline = sum(p.total_amount for p in proposals)
    accepted_value = sum(
        p.total_amount for p in proposals if p.status == ProposalStatus.ACCEPTED
    )

    return {
        "contractor": {
            "id": contractor.id,
            "company_name": contractor.company_name,
            "status": contractor.status.value,
        },
        "metrics": {
            "total_leads": len(leads),
            "new_leads": sum(1 for l in leads if l.status == LeadStatus.NEW),
            "proposals_sent": sum(
                1
                for p in proposals
                if p.status in (ProposalStatus.SENT, ProposalStatus.VIEWED)
            ),
            "proposals_accepted": sum(
                1 for p in proposals if p.status == ProposalStatus.ACCEPTED
            ),
            "total_pipeline_value": total_pipeline,
            "accepted_value": accepted_value,
        },
        "recent_leads": [
            {
                "id": l.id,
                "homeowner_name": l.homeowner_name,
                "project_type": l.project_type.value,
                "status": l.status.value,
                "created_at": l.created_at.isoformat(),
                "estimated_range_low": l.estimated_range_low,
                "estimated_range_high": l.estimated_range_high,
            }
            for l in leads[:20]
        ],
    }


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


@app.post("/api/reconciliation/run")
async def run_reconciliation(
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
):
    result = await mercury_handler.reconcile(session, config)
    return result


@app.get("/api/reconciliation/status")
async def reconciliation_status(
    session: AsyncSession = Depends(get_session),
):
    return await mercury_handler.get_reconciliation_status(session)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


@app.get("/api/audit/{entity_type}/{entity_id}")
async def get_audit_trail(
    entity_type: str,
    entity_id: str,
    session: AsyncSession = Depends(get_session),
):
    entries = await audit.get_trail(session, entity_type, entity_id)
    return [
        {
            "id": e.id,
            "action": e.action,
            "actor": e.actor,
            "detail": e.detail,
            "metadata": json.loads(e.metadata_json) if e.metadata_json else None,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


@app.get("/api/audit/recent")
async def get_recent_audit(
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    entries = await audit.get_recent(session, limit)
    return [
        {
            "id": e.id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "action": e.action,
            "actor": e.actor,
            "detail": e.detail,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok", "service": "contractor-intake", "version": "1.0.0"}
