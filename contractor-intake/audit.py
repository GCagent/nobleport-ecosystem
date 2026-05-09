"""AuditBeacon — append-only audit log service.

Every state change in the system writes here. No updates. No deletes.
This is the reconciliation and compliance source of truth.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import AuditEntry


async def log(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    detail: str | None = None,
    metadata: dict | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        detail=detail,
        metadata_json=json.dumps(metadata) if metadata else None,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()
    return entry


async def get_trail(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> list[AuditEntry]:
    result = await session.execute(
        select(AuditEntry)
        .where(
            AuditEntry.entity_type == entity_type,
            AuditEntry.entity_id == entity_id,
        )
        .order_by(AuditEntry.id)
    )
    return list(result.scalars().all())


async def get_recent(
    session: AsyncSession,
    limit: int = 50,
) -> list[AuditEntry]:
    result = await session.execute(
        select(AuditEntry).order_by(AuditEntry.id.desc()).limit(limit)
    )
    return list(result.scalars().all())
