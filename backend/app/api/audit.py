from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
import asyncpg

from app.core.db import get_rls_conn, get_conn
from app.core.security import require_auth
from app.services.merkle import build_merkle_root, hash_record

router = APIRouter()


@router.get("/anchors")
async def list_anchors(
    source_table: str | None = None,
    limit: int = 100,
    conn: asyncpg.Connection = Depends(get_conn),
):
    """Public audit endpoint. Lists merkle anchors. No auth required."""
    if source_table:
        rows = await conn.fetch(
            """select id, anchor_date, source_table, root_hash, record_count,
                      chain_name, tx_hash, anchored_at, created_at
               from merkle_anchors
               where source_table = $1
               order by anchor_date desc, created_at desc
               limit $2""",
            source_table, limit,
        )
    else:
        rows = await conn.fetch(
            """select id, anchor_date, source_table, root_hash, record_count,
                      chain_name, tx_hash, anchored_at, created_at
               from merkle_anchors
               order by anchor_date desc, created_at desc
               limit $1""",
            limit,
        )
    return [dict(r) for r in rows]


@router.get("/anchors/{anchor_id}")
async def get_anchor(
    anchor_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
):
    row = await conn.fetchrow(
        "select * from merkle_anchors where id = $1", anchor_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Anchor not found")
    return dict(row)


@router.get("/verify/{source_table}/{anchor_date}")
async def verify_anchor(
    source_table: str,
    anchor_date: date,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    """
    Recompute the merkle root for a given table and date,
    then compare against the stored anchor.
    """
    # Fetch the stored anchor
    anchor = await conn.fetchrow(
        """select root_hash, record_count, leaf_hashes
           from merkle_anchors
           where source_table = $1 and anchor_date = $2""",
        source_table, anchor_date,
    )
    if not anchor:
        raise HTTPException(status_code=404, detail="No anchor found for that table/date")

    # Recompute from live data
    if source_table == "projects":
        rows = await conn.fetch(
            """select id, name, status, gc_id, company_id, created_at, updated_at
               from projects where created_at::date = $1
               order by created_at asc""",
            anchor_date,
        )
    elif source_table == "inspections":
        rows = await conn.fetch(
            """select id, project_id, inspector_id, status, inspection_type, scheduled_at, completed_at, created_at
               from inspections where created_at::date = $1
               order by created_at asc""",
            anchor_date,
        )
    elif source_table == "permits":
        rows = await conn.fetch(
            """select id, project_id, permit_type, permit_number, status, issued_by, issued_at, created_at
               from permits where created_at::date = $1
               order by created_at asc""",
            anchor_date,
        )
    elif source_table == "disputes":
        rows = await conn.fetch(
            """select id, project_id, raised_by, assigned_arbiter, status, subject, created_at
               from disputes where created_at::date = $1
               order by created_at asc""",
            anchor_date,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported source table: {source_table}")

    records = [dict(r) for r in rows]
    hashes = [hash_record(r) for r in records]
    computed_root = build_merkle_root(hashes)

    stored_root = anchor["root_hash"]
    match = computed_root == stored_root

    return {
        "source_table": source_table,
        "anchor_date": str(anchor_date),
        "stored_root": stored_root,
        "computed_root": computed_root,
        "match": match,
        "record_count": len(records),
        "stored_record_count": anchor["record_count"],
    }


@router.get("/log")
async def list_audit_log(
    table_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
    user_id: str = Depends(require_auth),
    conn: asyncpg.Connection = Depends(get_rls_conn),
):
    if table_name:
        rows = await conn.fetch(
            """select * from audit_log
               where table_name = $1
               order by created_at desc limit $2 offset $3""",
            table_name, limit, offset,
        )
    else:
        rows = await conn.fetch(
            "select * from audit_log order by created_at desc limit $1 offset $2",
            limit, offset,
        )
    return [dict(r) for r in rows]
