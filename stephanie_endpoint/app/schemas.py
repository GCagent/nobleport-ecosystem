"""Pydantic request/response schemas for the Stephanie endpoint."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    create_job = "create_job"
    update_job = "update_job"
    check_permit = "check_permit"
    sync_crm = "sync_crm"
    get_status = "get_status"


class ExecuteRequest(BaseModel):
    action: ActionType = Field(..., description="Action to execute")
    source: str = Field(..., description="Originating system (e.g. 'openc law')")
    dry_run: bool = Field(False, description="If true, validate without side effects")
    data: dict[str, Any] = Field(
        default_factory=dict, description="Action-specific payload"
    )


class ExecuteResponse(BaseModel):
    request_id: str
    status: str = Field(..., description="ok | error | dry_run")
    action: str
    result: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebhookEvent(BaseModel):
    event_type: str = Field(..., description="Type of webhook event")
    source: str = Field(default="openc law")
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class WebhookResponse(BaseModel):
    received: bool = True
    event_type: str
    request_id: str
    message: str = "Webhook processed"


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "stephanie-endpoint"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
