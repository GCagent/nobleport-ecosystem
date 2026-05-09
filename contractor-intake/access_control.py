"""Account provisioning and access revocation.

Payment status determines access. No payment = no access. No exceptions.

Flow:
  checkout.completed → provision_access()
  invoice.paid       → (access already active, confirm)
  invoice.failed     → suspend_access()
  subscription.deleted → revoke_access()
  refund.processed   → revoke_access()
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import audit
from db import AccountStatus, Contractor


async def provision_access(
    session: AsyncSession,
    contractor_id: str,
    *,
    actor: str = "system",
) -> bool:
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return False

    contractor.status = AccountStatus.ACTIVE

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="access.provisioned",
        actor=actor,
        detail=f"Access granted to {contractor.company_name}",
    )
    await session.commit()
    return True


async def suspend_access(
    session: AsyncSession,
    contractor_id: str,
    *,
    reason: str,
    actor: str = "system",
) -> bool:
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return False

    contractor.status = AccountStatus.SUSPENDED

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="access.suspended",
        actor=actor,
        detail=f"Access suspended: {reason}",
    )
    await session.commit()
    return True


async def revoke_access(
    session: AsyncSession,
    contractor_id: str,
    *,
    reason: str,
    actor: str = "system",
) -> bool:
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return False

    contractor.status = AccountStatus.CANCELLED

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="access.revoked",
        actor=actor,
        detail=f"Access revoked: {reason}",
    )
    await session.commit()
    return True


async def check_access(
    session: AsyncSession,
    contractor_id: str,
) -> dict:
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return {"has_access": False, "reason": "contractor_not_found"}

    if contractor.status == AccountStatus.ACTIVE:
        return {"has_access": True, "status": contractor.status.value}

    if contractor.status == AccountStatus.TRIAL:
        return {"has_access": True, "status": contractor.status.value}

    return {
        "has_access": False,
        "status": contractor.status.value,
        "reason": f"account_{contractor.status.value}",
    }


def require_active_account(contractor: Contractor) -> None:
    if contractor.status not in (AccountStatus.ACTIVE, AccountStatus.TRIAL):
        raise PermissionError(
            f"Account is {contractor.status.value}. Active subscription required."
        )
