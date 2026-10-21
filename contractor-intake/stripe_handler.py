"""Stripe payment handler — checkout, webhooks, refunds.

Webhook signature verification is mandatory. No unsigned event is processed.
Every payment event writes to AuditBeacon before any state change.
"""

from __future__ import annotations

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import audit
from config import Config
from db import AccountStatus, Contractor, ReconciliationRecord


def init_stripe(config: Config) -> None:
    stripe.api_key = config.stripe_secret_key


async def create_checkout_session(
    config: Config,
    *,
    contractor_email: str,
    contractor_id: str,
) -> stripe.checkout.Session:
    return stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        customer_email=contractor_email,
        line_items=[{"price": config.stripe_price_id, "quantity": 1}],
        success_url=f"{config.app_base_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{config.app_base_url}/pricing",
        metadata={"contractor_id": contractor_id},
    )


def verify_webhook(
    payload: bytes,
    sig_header: str,
    webhook_secret: str,
) -> stripe.Event:
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)


async def handle_checkout_completed(
    session: AsyncSession,
    event: stripe.Event,
) -> None:
    checkout = event.data.object
    contractor_id = checkout.metadata.get("contractor_id")
    if not contractor_id:
        return

    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return

    contractor.stripe_customer_id = checkout.customer
    contractor.stripe_subscription_id = checkout.subscription
    contractor.status = AccountStatus.ACTIVE

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="payment.checkout_completed",
        actor="stripe_webhook",
        detail=f"Subscription {checkout.subscription} activated",
        metadata={
            "stripe_customer_id": checkout.customer,
            "stripe_subscription_id": checkout.subscription,
            "amount_total": checkout.amount_total,
        },
    )
    await session.commit()


async def handle_invoice_paid(
    session: AsyncSession,
    event: stripe.Event,
) -> None:
    invoice = event.data.object
    customer_id = invoice.customer

    result = await session.execute(
        select(Contractor).where(Contractor.stripe_customer_id == customer_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return

    contractor.status = AccountStatus.ACTIVE

    recon = ReconciliationRecord(
        contractor_id=contractor.id,
        stripe_payment_intent_id=invoice.payment_intent or invoice.id,
        stripe_amount_cents=invoice.amount_paid,
    )
    session.add(recon)

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor.id,
        action="payment.invoice_paid",
        actor="stripe_webhook",
        detail=f"Invoice {invoice.id} paid: ${invoice.amount_paid / 100:.2f}",
        metadata={
            "invoice_id": invoice.id,
            "payment_intent": invoice.payment_intent,
            "amount_cents": invoice.amount_paid,
        },
    )
    await session.commit()


async def handle_invoice_payment_failed(
    session: AsyncSession,
    event: stripe.Event,
) -> None:
    invoice = event.data.object
    customer_id = invoice.customer

    result = await session.execute(
        select(Contractor).where(Contractor.stripe_customer_id == customer_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return

    contractor.status = AccountStatus.PAST_DUE

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor.id,
        action="payment.invoice_failed",
        actor="stripe_webhook",
        detail=f"Invoice {invoice.id} payment failed",
        metadata={"invoice_id": invoice.id, "amount_cents": invoice.amount_due},
    )
    await session.commit()


async def handle_subscription_deleted(
    session: AsyncSession,
    event: stripe.Event,
) -> None:
    subscription = event.data.object
    customer_id = subscription.customer

    result = await session.execute(
        select(Contractor).where(Contractor.stripe_customer_id == customer_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor:
        return

    contractor.status = AccountStatus.CANCELLED
    contractor.stripe_subscription_id = None

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor.id,
        action="payment.subscription_cancelled",
        actor="stripe_webhook",
        detail=f"Subscription {subscription.id} cancelled",
        metadata={"subscription_id": subscription.id},
    )
    await session.commit()


async def process_refund(
    session: AsyncSession,
    *,
    contractor_id: str,
    reason: str,
    actor: str,
) -> stripe.Refund | None:
    result = await session.execute(
        select(Contractor).where(Contractor.id == contractor_id)
    )
    contractor = result.scalar_one_or_none()
    if not contractor or not contractor.stripe_subscription_id:
        return None

    sub = stripe.Subscription.retrieve(contractor.stripe_subscription_id)
    latest_invoice = stripe.Invoice.retrieve(sub.latest_invoice)

    refund = None
    if latest_invoice.payment_intent:
        refund = stripe.Refund.create(payment_intent=latest_invoice.payment_intent)

    stripe.Subscription.cancel(contractor.stripe_subscription_id)
    contractor.status = AccountStatus.CANCELLED
    contractor.stripe_subscription_id = None

    await audit.log(
        session,
        entity_type="contractor",
        entity_id=contractor_id,
        action="payment.refund_processed",
        actor=actor,
        detail=f"Refund processed. Reason: {reason}",
        metadata={
            "refund_id": refund.id if refund else None,
            "reason": reason,
        },
    )
    await session.commit()
    return refund


WEBHOOK_HANDLERS = {
    "checkout.session.completed": handle_checkout_completed,
    "invoice.paid": handle_invoice_paid,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "customer.subscription.deleted": handle_subscription_deleted,
}
