from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DisputeCreate(BaseModel):
    project_id: UUID
    inspection_id: UUID | None = None
    subject: str
    description: str | None = None


class DisputeUpdate(BaseModel):
    status: str | None = None
    assigned_arbiter: UUID | None = None
    resolution: str | None = None


class DisputeOut(BaseModel):
    id: UUID
    project_id: UUID
    inspection_id: UUID | None
    raised_by: UUID
    assigned_arbiter: UUID | None
    status: str
    subject: str
    description: str | None
    resolution: str | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DisputeCommentCreate(BaseModel):
    body: str


class DisputeCommentOut(BaseModel):
    id: UUID
    dispute_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
