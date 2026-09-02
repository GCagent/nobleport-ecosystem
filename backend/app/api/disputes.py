from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.core.db import get_rls_conn
from app.core.security import require_auth
from app.models.disputes import (
    DisputeCreate,
    DisputeUpdate,
    DisputeOut,
    DisputeCommentCreate,
    DisputeCommentOut,
)

router = APIRouter()


@router.get("", response_model=list[DisputeOut])
async def list_disputes(
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
        f"select * from disputes {where} order by created_at desc limit ${limit_param} offset ${offset_param}",
        *values,
    )
    return [dict(r) for r in rows]


@router.get("/{dispute_id}", response_model=DisputeOut)
async def get_dispute(
    dispute_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow("select * from disputes where id = $1", dispute_id)
    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return dict(row)


@router.post("", response_model=DisputeOut, status_code=201)
async def create_dispute(
    payload: DisputeCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into disputes (project_id, inspection_id, raised_by, subject, description)
           values ($1, $2, $3, $4, $5)
           returning *""",
        payload.project_id,
        payload.inspection_id,
        UUID(user_id),
        payload.subject,
        payload.description,
    )
    return dict(row)


@router.patch("/{dispute_id}", response_model=DisputeOut)
async def update_dispute(
    dispute_id: UUID,
    payload: DisputeUpdate,
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

    values.append(dispute_id)
    idx = len(values)
    set_clauses.append("updated_at = now()")

    row = await conn.fetchrow(
        f"update disputes set {', '.join(set_clauses)} where id = ${idx} returning *",
        *values,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return dict(row)


# --- Dispute Comments ---

@router.get("/{dispute_id}/comments", response_model=list[DisputeCommentOut])
async def list_comments(
    dispute_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    rows = await conn.fetch(
        "select * from dispute_comments where dispute_id = $1 order by created_at asc",
        dispute_id,
    )
    return [dict(r) for r in rows]


@router.post("/{dispute_id}/comments", response_model=DisputeCommentOut, status_code=201)
async def add_comment(
    dispute_id: UUID,
    payload: DisputeCommentCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into dispute_comments (dispute_id, author_id, body)
           values ($1, $2, $3)
           returning *""",
        dispute_id,
        UUID(user_id),
        payload.body,
    )
    return dict(row)
