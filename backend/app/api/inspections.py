from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.core.db import get_rls_conn
from app.core.security import require_auth
from app.models.inspections import (
    InspectionCreate,
    InspectionUpdate,
    InspectionOut,
    InspectionItemCreate,
    InspectionItemOut,
)

router = APIRouter()


@router.get("", response_model=list[InspectionOut])
async def list_inspections(
    project_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    conditions = []
    values: list = []
    idx = 0

    if project_id:
        idx += 1
        conditions.append(f"project_id = ${idx}")
        values.append(project_id)
    if status:
        idx += 1
        conditions.append(f"status = ${idx}")
        values.append(status)

    where = f"where {' and '.join(conditions)}" if conditions else ""
    idx += 1
    limit_param = idx
    idx += 1
    offset_param = idx
    values.extend([limit, offset])

    rows = await conn.fetch(
        f"select * from inspections {where} order by scheduled_at desc nulls last limit ${limit_param} offset ${offset_param}",
        *values,
    )
    return [dict(r) for r in rows]


@router.get("/{inspection_id}", response_model=InspectionOut)
async def get_inspection(
    inspection_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow("select * from inspections where id = $1", inspection_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return dict(row)


@router.post("", response_model=InspectionOut, status_code=201)
async def create_inspection(
    payload: InspectionCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into inspections (project_id, permit_id, inspector_id, inspection_type, scheduled_at, notes)
           values ($1, $2, $3, $4, $5, $6)
           returning *""",
        payload.project_id,
        payload.permit_id,
        UUID(user_id),
        payload.inspection_type,
        payload.scheduled_at,
        payload.notes,
    )
    return dict(row)


@router.patch("/{inspection_id}", response_model=InspectionOut)
async def update_inspection(
    inspection_id: UUID,
    payload: InspectionUpdate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    values = []
    for i, (key, val) in enumerate(updates.items(), start=1):
        set_clauses.append(f"{key} = ${i}")
        values.append(val)

    values.append(inspection_id)
    idx = len(values)
    set_clauses.append("updated_at = now()")

    row = await conn.fetchrow(
        f"update inspections set {', '.join(set_clauses)} where id = ${idx} returning *",
        *values,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return dict(row)


# --- Inspection Items (checklist) ---

@router.get("/{inspection_id}/items", response_model=list[InspectionItemOut])
async def list_inspection_items(
    inspection_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    rows = await conn.fetch(
        "select * from inspection_items where inspection_id = $1 order by sort_order",
        inspection_id,
    )
    return [dict(r) for r in rows]


@router.post("/{inspection_id}/items", response_model=InspectionItemOut, status_code=201)
async def add_inspection_item(
    inspection_id: UUID,
    payload: InspectionItemCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into inspection_items (inspection_id, description, sort_order)
           values ($1, $2, $3)
           returning *""",
        inspection_id,
        payload.description,
        payload.sort_order,
    )
    return dict(row)
