from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    company_id: UUID | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    status: str
    gc_id: UUID
    company_id: UUID | None
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    created_at: datetime
    updated_at: datetime
