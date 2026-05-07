from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.core.db import get_rls_conn
from app.core.security import require_auth
from app.models.permits import PermitCreate, PermitUpdate, PermitOut

router = APIRouter()


@router.get("", response_model=list[PermitOut])
async def list_permits(
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
        f"select * from permits {where} order by created_at desc limit ${limit_param} offset ${offset_param}",
        *values,
    )
    return [dict(r) for r in rows]


@router.get("/{permit_id}", response_model=PermitOut)
async def get_permit(
    permit_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow("select * from permits where id = $1", permit_id)
    if not row:
        raise HTTPException(status_code=404, detail="Permit not found")
    return dict(row)


@router.post("", response_model=PermitOut, status_code=201)
async def create_permit(
    payload: PermitCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into permits (project_id, permit_type, permit_number, notes, expires_at)
           values ($1, $2, $3, $4, $5)
           returning *""",
        payload.project_id,
        payload.permit_type,
        payload.permit_number,
        payload.notes,
        payload.expires_at,
    )
    return dict(row)


@router.patch("/{permit_id}", response_model=PermitOut)
async def update_permit(
    permit_id: UUID,
    payload: PermitUpdate,
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

    values.append(permit_id)
    idx = len(values)
    set_clauses.append("updated_at = now()")

    row = await conn.fetchrow(
        f"update permits set {', '.join(set_clauses)} where id = ${idx} returning *",
        *values,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Permit not found")
    return dict(row)
