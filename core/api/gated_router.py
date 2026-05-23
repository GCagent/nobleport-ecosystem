import hashlib
import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/v1/orchestration-core",
    tags=["Operating Spine Guard"],
)

SENSITIVE_SCOPES = frozenset([
    "treasury_movement",
    "securities_action",
    "permit_filing",
    "token_launch",
])


class ExecutionRequest(BaseModel):
    workflow_id: UUID
    action_scope: str
    payload_summary: Dict[str, Any]
    human_signature: Optional[str] = Field(
        None,
        description="Cryptographic token or link validating manual human approval",
    )


class AuditAnchor(BaseModel):
    anchored: bool
    verification_hash: str


class ExecutionResponse(BaseModel):
    execution_status: str
    workflow_id: str
    audit_ledger: AuditAnchor


@router.post("/execute-gate", response_model=ExecutionResponse)
async def process_gated_action(
    payload: ExecutionRequest,
    db_pool=Depends(lambda: router.state.db_pool),
):
    if payload.action_scope.lower() in SENSITIVE_SCOPES and not payload.human_signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Security Violation: Autonomous execution of "
                f"'{payload.action_scope}' is strictly BLOCKED. "
                f"Manual human authorization is required."
            ),
        )

    async with db_pool.acquire() as conn:
        async with conn.transaction():

            wf = await conn.fetchrow(
                "SELECT * FROM workflow_states WHERE id = $1;",
                payload.workflow_id,
            )
            if not wf:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System Error: Target workflow trace not found.",
                )

            if payload.human_signature:
                await conn.execute(
                    """
                    UPDATE workflow_states
                    SET human_approved = TRUE,
                        current_status = 'executed',
                        human_signature_spec = $1,
                        updated_at = NOW()
                    WHERE id = $2;
                    """,
                    payload.human_signature,
                    payload.workflow_id,
                )
                action_result = "HUMAN_APPROVED_AND_EXECUTED"
            else:
                await conn.execute(
                    """
                    UPDATE workflow_states
                    SET current_status = 'pending_human_review',
                        updated_at = NOW()
                    WHERE id = $1;
                    """,
                    payload.workflow_id,
                )
                action_result = "PARKED_PENDING_HUMAN_OVERSIGHT"

            audit_bundle = {
                "workflow_id": str(payload.workflow_id),
                "action_scope": payload.action_scope,
                "resolution": action_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            payload_hash = hashlib.sha256(
                json.dumps(audit_bundle, sort_keys=True).encode()
            ).hexdigest()

            last_audit = await conn.fetchrow(
                "SELECT payload_hash FROM audit_logs ORDER BY timestamp DESC LIMIT 1;"
            )
            previous_hash = last_audit["payload_hash"] if last_audit else None

            await conn.execute(
                """
                INSERT INTO audit_logs
                    (action, entity_type, entity_id, payload_hash, previous_hash, raw_payload)
                VALUES ($1, $2, $3, $4, $5, $6);
                """,
                f"ORCHESTRATOR_TIER_{action_result}",
                "workflow_states",
                payload.workflow_id,
                payload_hash,
                previous_hash,
                json.dumps(audit_bundle),
            )

    return ExecutionResponse(
        execution_status=action_result,
        workflow_id=str(payload.workflow_id),
        audit_ledger=AuditAnchor(anchored=True, verification_hash=payload_hash),
    )
