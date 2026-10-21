from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AccountStatus(str, enum.Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    ESTIMATE_SCHEDULED = "estimate_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ProjectType(str, enum.Enum):
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    ROOFING = "roofing"
    SIDING = "siding"
    ADDITION = "addition"
    DECK_PATIO = "deck_patio"
    BASEMENT = "basement"
    FULL_RENOVATION = "full_renovation"
    PAINTING = "painting"
    FLOORING = "flooring"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    WINDOWS_DOORS = "windows_doors"
    LANDSCAPING = "landscaping"
    OTHER = "other"


class ProposalStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    owner_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32))
    license_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    service_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialties: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus), default=AccountStatus.TRIAL
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    leads: Mapped[list[Lead]] = relationship(back_populates="contractor")
    proposals: Mapped[list[Proposal]] = relationship(back_populates="contractor")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contractor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contractors.id"), index=True
    )

    # Homeowner info
    homeowner_name: Mapped[str] = mapped_column(String(255))
    homeowner_email: Mapped[str] = mapped_column(String(255))
    homeowner_phone: Mapped[str] = mapped_column(String(32))
    property_address: Mapped[str] = mapped_column(Text)

    # Project details
    project_type: Mapped[ProjectType] = mapped_column(Enum(ProjectType))
    project_description: Mapped[str] = mapped_column(Text)
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(64), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # AI-generated scope
    generated_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_range_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_range_high: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus), default=LeadStatus.NEW
    )
    estimate_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_urls: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    contractor: Mapped[Contractor] = relationship(back_populates="leads")
    proposals: Mapped[list[Proposal]] = relationship(back_populates="lead")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contractor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contractors.id"), index=True
    )
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id"), index=True
    )

    # Content
    scope_of_work: Mapped[str] = mapped_column(Text)
    line_items_json: Mapped[str] = mapped_column(Text)
    total_amount: Mapped[float] = mapped_column(Float)
    deposit_required: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_duration: Mapped[str | None] = mapped_column(String(64), nullable=True)
    terms_and_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    permit_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_specifications: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.DRAFT
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signature_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    contractor: Mapped[Contractor] = relationship(back_populates="proposals")
    lead: Mapped[Lead] = relationship(back_populates="proposals")


class AuditEntry(Base):
    """Append-only audit log. No updates or deletes."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


class ReconciliationRecord(Base):
    __tablename__ = "reconciliation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contractor_id: Mapped[str] = mapped_column(String(36), index=True)
    stripe_payment_intent_id: Mapped[str] = mapped_column(String(255))
    stripe_amount_cents: Mapped[int] = mapped_column(Integer)
    mercury_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    mercury_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    discrepancy_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


# ---------------------------------------------------------------------------
# Engine / Session factory
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


async def init_db(database_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    async with _session_factory() as session:
        yield session


async def shutdown_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
