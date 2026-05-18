from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.db import verifications as vdb
from app.security.auth import current_user, require_role


router = APIRouter(prefix="/admin", tags=["admin"])


class TransitionRequest(BaseModel):
    target: str
    reason: str | None = None


@router.post("/verifications/{vid}/transition")
async def transition(
    vid: str,
    body: TransitionRequest,
    request: Request,
    user: dict = Depends(current_user),
):
    result = await vdb.transition(request.app.state.pg, vid=vid, target=body.target, actor=user)
    v = await vdb.get(request.app.state.pg, vid)
    await request.app.state.audit.append(
        address=v["address"] if v else "",
        helius_status=None, birdeye_status=None, solscan_status=None,
        final_decision=v["final_decision"] if v else "",
        reason=body.reason,
        kind="state_transition",
        actor_id=user["id"],
        details=result,
    )
    return result


@router.get("/verifications/{vid}")
async def get_verification(
    vid: str,
    request: Request,
    user: dict = Depends(require_role("admin", "moderator")),
):
    v = await vdb.get(request.app.state.pg, vid)
    if not v:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    v["id"] = str(v["id"])
    if v.get("created_by"):
        v["created_by"] = str(v["created_by"])
    return v
