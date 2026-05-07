from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InspectionCreate(BaseModel):
    project_id: UUID
    permit_id: UUID | None = None
    inspection_type: str = "general"
    scheduled_at: datetime | None = None
    notes: str | None = None


class InspectionUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    result_notes: str | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None


class InspectionOut(BaseModel):
    id: UUID
    project_id: UUID
    permit_id: UUID | None
    inspector_id: UUID | None
    inspection_type: str
    status: str
    notes: str | None
    result_notes: str | None
    scheduled_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InspectionItemCreate(BaseModel):
    description: str
    sort_order: int = 0


class InspectionItemOut(BaseModel):
    id: UUID
    inspection_id: UUID
    description: str
    passed: bool | None
    notes: str | None
    sort_order: int
    created_at: datetime
