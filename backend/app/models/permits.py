from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PermitCreate(BaseModel):
    project_id: UUID
    permit_type: str
    permit_number: str | None = None
    notes: str | None = None
    expires_at: datetime | None = None


class PermitUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    expires_at: datetime | None = None


class PermitOut(BaseModel):
    id: UUID
    project_id: UUID
    permit_type: str
    permit_number: str | None
    status: str
    issued_by: UUID | None
    issued_at: datetime | None
    expires_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
