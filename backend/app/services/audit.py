"""
Audit log service. Writes append-only entries to audit_log table.
Used by API endpoints to record state changes.
"""

import json
from uuid import UUID

import asyncpg


async def log_action(
    conn: asyncpg.Connection,
    *,
    actor_id: UUID | str | None,
    action: str,
    table_name: str,
    record_id: UUID | str | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Insert an audit log entry. Fire and forget from the caller's perspective."""
    await conn.execute(
        """insert into audit_log (actor_id, action, table_name, record_id, old_data, new_data, ip_address)
           values ($1, $2, $3, $4, $5, $6, $7::inet)""",
        UUID(str(actor_id)) if actor_id else None,
        action,
        table_name,
        UUID(str(record_id)) if record_id else None,
        json.dumps(old_data, default=str) if old_data else None,
        json.dumps(new_data, default=str) if new_data else None,
        ip_address,
    )
