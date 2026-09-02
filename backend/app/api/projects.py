from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.core.db import get_rls_conn
from app.core.security import require_auth
from app.models.projects import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    if status:
        rows = await conn.fetch(
            """select * from projects where status = $1
               order by created_at desc limit $2 offset $3""",
            status, limit, offset,
        )
    else:
        rows = await conn.fetch(
            "select * from projects order by created_at desc limit $1 offset $2",
            limit, offset,
        )
    return [dict(r) for r in rows]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow("select * from projects where id = $1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    payload: ProjectCreate,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    row = await conn.fetchrow(
        """insert into projects (name, description, gc_id, company_id, address, city, state, zip_code)
           values ($1, $2, $3, $4, $5, $6, $7, $8)
           returning *""",
        payload.name,
        payload.description,
        UUID(user_id),
        payload.company_id,
        payload.address,
        payload.city,
        payload.state,
        payload.zip_code,
    )
    return dict(row)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
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

    values.append(project_id)
    idx = len(values)
    set_clauses.append(f"updated_at = now()")

    query = f"update projects set {', '.join(set_clauses)} where id = ${idx} returning *"
    row = await conn.fetchrow(query, *values)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    result = await conn.execute("delete from projects where id = $1", project_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Project not found")
