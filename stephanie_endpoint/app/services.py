"""Service layer — action dispatcher and business logic stubs.

`dispatch_action()` is the routing seam. Replace the stub handlers
with your actual GCagent, PermitStream, and CRM adapters.
"""

import logging
from typing import Any

from .schemas import ActionType

logger = logging.getLogger("stephanie.services")


async def dispatch_action(
    action: ActionType,
    data: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Route an action to the appropriate handler."""
    handlers = {
        ActionType.create_job: _handle_create_job,
        ActionType.update_job: _handle_update_job,
        ActionType.check_permit: _handle_check_permit,
        ActionType.sync_crm: _handle_sync_crm,
        ActionType.get_status: _handle_get_status,
    }
    handler = handlers.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    if dry_run:
        logger.info("Dry run for action=%s data=%s", action, data)
        return {"dry_run": True, "action": action, "validated": True, "data": data}

    return await handler(data)


async def _handle_create_job(data: dict[str, Any]) -> dict[str, Any]:
    """Stub: create a new job in the system.

    TODO: Wire to actual job creation pipeline —
    GCagent dispatch, CRM record, permit pre-check.
    """
    logger.info("Creating job: %s", data)
    return {
        "job_id": "job_stub_001",
        "client": data.get("client", "unknown"),
        "address": data.get("address", ""),
        "scope": data.get("scope", ""),
        "status": "created",
        "message": "Stub: replace with real job creation logic",
    }


async def _handle_update_job(data: dict[str, Any]) -> dict[str, Any]:
    """Stub: update an existing job."""
    logger.info("Updating job: %s", data)
    return {
        "job_id": data.get("job_id", "unknown"),
        "status": "updated",
        "message": "Stub: replace with real update logic",
    }


async def _handle_check_permit(data: dict[str, Any]) -> dict[str, Any]:
    """Stub: check permit status via PermitStream.

    TODO: Wire to PermitStream / municipal API adapter.
    """
    logger.info("Checking permit: %s", data)
    return {
        "address": data.get("address", ""),
        "permit_status": "pending_review",
        "message": "Stub: replace with PermitStream integration",
    }


async def _handle_sync_crm(data: dict[str, Any]) -> dict[str, Any]:
    """Stub: sync data to CRM.

    TODO: Wire to HubSpot / CRM adapter.
    """
    logger.info("Syncing CRM: %s", data)
    return {
        "crm_record_id": "crm_stub_001",
        "status": "synced",
        "message": "Stub: replace with CRM sync logic",
    }


async def _handle_get_status(data: dict[str, Any]) -> dict[str, Any]:
    """Stub: retrieve status of a job or system component."""
    logger.info("Getting status: %s", data)
    return {
        "job_id": data.get("job_id", "unknown"),
        "status": "in_progress",
        "message": "Stub: replace with real status lookup",
    }


async def process_webhook_event(
    event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Handle an incoming webhook event.

    TODO: Route to appropriate handler based on event_type.
    """
    logger.info("Webhook event_type=%s payload=%s", event_type, payload)
    return {
        "event_type": event_type,
        "processed": True,
        "message": "Stub: replace with real webhook event processing",
    }
