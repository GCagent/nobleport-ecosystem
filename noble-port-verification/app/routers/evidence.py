from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.db import evidence as edb
from app.security.auth import require_role
from app.services.moderation import moderator


router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.post("")
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    verification_id: str | None = Form(default=None),
    note: str | None = Form(default=None),
    user: dict = Depends(require_role("admin", "moderator", "contractor")),
):
    note_verdict = moderator.moderate(note or "").dict() if note else None
    record = await edb.store_upload(
        request.app.state.pg,
        file=file,
        uploaded_by=user["id"],
        verification_id=verification_id,
        note=note,
        moderation=note_verdict,
    )
    await request.app.state.audit.append(
        address="",
        helius_status=None, birdeye_status=None, solscan_status=None,
        final_decision="",
        reason=None,
        kind="evidence_upload",
        actor_id=user["id"],
        details={
            "evidence_id": record["id"],
            "sha256": record["sha256"],
            "verification_id": verification_id,
            "moderation": note_verdict,
        },
    )
    return {**record, "moderation": note_verdict}
