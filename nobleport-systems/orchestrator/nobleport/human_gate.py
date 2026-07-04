"""HumanGate: approval routing for high-risk workflow steps.

Every HIGH-risk step suspends its workflow and creates an ApprovalRequest that
a human must resolve. CRITICAL steps (treasury/securities) additionally never
execute in-platform even when approved — approval only unlocks preparing the
artifact (e.g. a multi-sig transaction proposal) for off-platform signing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class ApprovalState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ApprovalRequest:
    workflow_id: str
    step: str
    module: str
    risk: str
    summary: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state: ApprovalState = ApprovalState.PENDING
    resolved_by: str | None = None
    resolution_note: str | None = None


class AlreadyResolvedError(RuntimeError):
    pass


class HumanGate:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def request(self, *, workflow_id: str, step: str, module: str, risk: str,
                summary: str) -> ApprovalRequest:
        req = ApprovalRequest(workflow_id=workflow_id, step=step, module=module,
                              risk=risk, summary=summary)
        self._requests[req.id] = req
        return req

    def get(self, request_id: str) -> ApprovalRequest:
        return self._requests[request_id]

    def pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values()
                if r.state is ApprovalState.PENDING]

    def pending_for_workflow(self, workflow_id: str) -> list[ApprovalRequest]:
        return [r for r in self.pending() if r.workflow_id == workflow_id]

    def resolve(self, request_id: str, *, approved: bool, actor: str,
                note: str | None = None) -> ApprovalRequest:
        req = self.get(request_id)
        if req.state is not ApprovalState.PENDING:
            raise AlreadyResolvedError(request_id)
        req.state = ApprovalState.APPROVED if approved else ApprovalState.REJECTED
        req.resolved_by = actor
        req.resolution_note = note
        return req
