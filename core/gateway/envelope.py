"""The MCP call envelope — the contract every internal request must carry.

Mirrors the gateway-rules envelope from the architecture spec. Pydantic does
the schema-validation gate (the first hard requirement) for free: a malformed
envelope never reaches governance, audit, or a tool.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .registry import APPROVAL_LEVELS

TRUTH_LABELS = ("LIVE", "MODELED", "STAGED", "BLOCKED")


class McpEnvelope(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    requesting_agent: str = Field(min_length=1)
    target_agent: str = Field(min_length=1)
    module: str = Field(min_length=1)
    action: str = Field(min_length=1, description="tool name, e.g. gcagent.create_scope")
    truth_label: str = Field(default="STAGED")
    project_id: Optional[str] = None
    customer_id: Optional[str] = None
    approval_level: str = Field(default="L0")
    message: str = Field(default="", description="natural-language payload subject to claim screening")
    payload: dict[str, Any] = Field(default_factory=dict)
    source_refs: list[str] = Field(default_factory=list)
    audit_required: bool = True
    human_approval_required: bool = False
    human_signature: Optional[str] = Field(
        default=None,
        description="Cryptographic token / link validating a human approval for L3/L4 writes",
    )
    requestor_region: Optional[str] = Field(
        default=None, description="ISO region / US state of the requesting party"
    )

    def normalized_level(self) -> str:
        lvl = (self.approval_level or "L0").upper()
        return lvl if lvl in APPROVAL_LEVELS else "L0"


class GateOutcome(BaseModel):
    """Result of the governance gate."""

    decision: str                  # PERMIT | PARK | BLOCK
    level: str                     # the L0-L4 gate that fired
    reason: str
    requires_human: bool = False


class InvokeResult(BaseModel):
    run_id: str
    status: str                    # SUCCESS | PARKED | BLOCKED | FAILED | CACHED
    decision: str
    level: str
    reason: Optional[str] = None
    truth_label: str
    latency_ms: Optional[int] = None
    result: Optional[dict[str, Any]] = None
    audit: Optional[dict[str, Any]] = None
    optimization: Optional[dict[str, Any]] = None
