"""Mercury reconciliation — verifies Stripe settlements arrive in the bank.

The reconciliation loop:
1. Stripe charges → payout to Mercury bank account
2. This service polls Mercury for recent transactions
3. Matches Stripe payment intents to Mercury deposits
4. Flags discrepancies
5. Writes results to AuditBeacon

Runs as a periodic task, not on every request.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import audit
from config import Config
from db import ReconciliationRecord

MERCURY_API_BASE = "https://api.mercury.com/api/v1"


async def fetch_recent_transactions(
    config: Config,
    *,
    days: int = 7,
) -> list[dict]:
    if not config.mercury_api_key or not config.mercury_account_id:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{MERCURY_API_BASE}/account/{config.mercury_account_id}/transactions",
            headers={"Authorization": f"Bearer {config.mercury_api_key}"},
            params={"limit": 100, "offset": 0},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("transactions", [])


async def reconcile(
    session: AsyncSession,
    config: Config,
) -> dict:
    unreconciled = await session.execute(
        select(ReconciliationRecord).where(
            ReconciliationRecord.reconciled == False  # noqa: E712
        )
    )
    pending = list(unreconciled.scalars().all())
    if not pending:
        return {"status": "nothing_to_reconcile", "matched": 0, "unmatched": 0}

    transactions = await fetch_recent_transactions(config)

    mercury_by_amount: dict[int, list[dict]] = {}
    for txn in transactions:
        amt = abs(int(round(txn.get("amount", 0) * 100)))
        mercury_by_amount.setdefault(amt, []).append(txn)

    matched = 0
    unmatched = 0

    for record in pending:
        candidates = mercury_by_amount.get(record.stripe_amount_cents, [])
        if candidates:
            txn = candidates.pop(0)
            record.mercury_transaction_id = txn.get("id")
            record.mercury_amount_cents = abs(int(round(txn.get("amount", 0) * 100)))
            record.discrepancy_cents = (
                record.stripe_amount_cents - record.mercury_amount_cents
            )
            record.reconciled = True
            record.reconciled_at = datetime.now(timezone.utc)

            await audit.log(
                session,
                entity_type="reconciliation",
                entity_id=record.id,
                action="reconciliation.matched",
                actor="mercury_reconciler",
                detail=f"Stripe {record.stripe_payment_intent_id} matched to Mercury {record.mercury_transaction_id}",
                metadata={
                    "stripe_amount": record.stripe_amount_cents,
                    "mercury_amount": record.mercury_amount_cents,
                    "discrepancy": record.discrepancy_cents,
                },
            )
            matched += 1
        else:
            unmatched += 1

    await session.commit()

    if unmatched > 0:
        await audit.log(
            session,
            entity_type="system",
            entity_id="reconciliation",
            action="reconciliation.unmatched_found",
            actor="mercury_reconciler",
            detail=f"{unmatched} Stripe payments without matching Mercury deposit",
        )
        await session.commit()

    return {"status": "completed", "matched": matched, "unmatched": unmatched}


async def get_reconciliation_status(session: AsyncSession) -> dict:
    all_records = await session.execute(select(ReconciliationRecord))
    records = list(all_records.scalars().all())

    total = len(records)
    reconciled = sum(1 for r in records if r.reconciled)
    pending = total - reconciled
    total_discrepancy = sum(
        r.discrepancy_cents or 0 for r in records if r.reconciled
    )

    return {
        "total_records": total,
        "reconciled": reconciled,
        "pending": pending,
        "total_discrepancy_cents": total_discrepancy,
    }
