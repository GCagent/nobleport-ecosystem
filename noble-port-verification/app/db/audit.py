import hashlib
import json
import uuid
from datetime import datetime, timezone

import asyncpg


GENESIS_HASH = "0" * 64


def _row_hash(prev_hash: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(prev_hash.encode() + body).hexdigest()


class AuditLog:
    """Append-only hash-chained decision log.

    Writes commit BEFORE the response returns. If insertion raises,
    the caller fails closed (BLOCK).
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def append(
        self,
        address: str,
        helius_status: str,
        birdeye_status: str,
        solscan_status: str,
        final_decision: str,
        reason: str | None = None,
        kind: str = "verify",
        actor_id: str | None = None,
        details: dict | None = None,
    ) -> dict:
        row_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        details_json = json.dumps(details, sort_keys=True) if details else None
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                prev = await conn.fetchval(
                    "SELECT row_hash FROM audit_log ORDER BY created_at DESC, id DESC LIMIT 1"
                )
                prev_hash = prev or GENESIS_HASH
                payload = {
                    "id": row_id,
                    "kind": kind,
                    "actor_id": actor_id,
                    "address": address,
                    "helius_status": helius_status,
                    "birdeye_status": birdeye_status,
                    "solscan_status": solscan_status,
                    "final_decision": final_decision,
                    "reason": reason,
                    "details": details,
                    "created_at": created_at.isoformat(),
                }
                row_hash = _row_hash(prev_hash, payload)
                await conn.execute(
                    """
                    INSERT INTO audit_log (
                        id, address,
                        helius_status, birdeye_status, solscan_status,
                        final_decision, reason,
                        prev_hash, row_hash, created_at,
                        kind, actor_id, details
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb)
                    """,
                    row_id, address,
                    helius_status, birdeye_status, solscan_status,
                    final_decision, reason,
                    prev_hash, row_hash, created_at,
                    kind, uuid.UUID(actor_id) if actor_id else None, details_json,
                )
        return {"id": row_id, "row_hash": row_hash, "prev_hash": prev_hash}
