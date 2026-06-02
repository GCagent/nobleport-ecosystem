"""HTTP surface for the open-source e-signature ("Seal") module.

Senders (admin / moderator / contractor) create a draft envelope, attach a
document and recipients, then send it — which mints one-time signing tokens.
Recipients sign or decline using only their token (no account required), the
DocuSign-style model. Every state change appends an ``esign_*`` row to the
shared, hash-chained audit log.
"""
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.db import envelopes as edb
from app.engine import esign
from app.security.auth import current_user, require_role


router = APIRouter(prefix="/esign", tags=["esign"])

_SENDER_ROLES = ("admin", "moderator", "contractor")
_VIEW_ROLES = ("admin", "moderator", "contractor", "viewer")

# Columns never exposed over the API.
_REDACT = {"access_token_hash", "document_path"}


def _public(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in _REDACT}


class RecipientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    role: str = Field(default="signer")
    routing_order: int = Field(default=1, ge=1)


class SignIn(BaseModel):
    token: str = Field(min_length=8)
    consent_given: bool = False


class DeclineIn(BaseModel):
    token: str = Field(min_length=8)
    reason: str | None = None


class VoidIn(BaseModel):
    reason: str | None = None


async def _audit(request: Request, *, kind: str, eid: str, actor_id: str | None, details: dict):
    await request.app.state.audit.append(
        address="",
        helius_status=None, birdeye_status=None, solscan_status=None,
        final_decision="",
        kind=kind,
        actor_id=actor_id,
        details={"envelope_id": eid, **details},
    )


@router.post("/envelopes")
async def create_envelope(
    request: Request,
    file: UploadFile = File(...),
    subject: str = Form(...),
    message: str | None = Form(default=None),
    routing: str = Form(default="sequential"),
    user: dict = Depends(require_role(*_SENDER_ROLES)),
):
    env = await edb.create_envelope(
        request.app.state.pg,
        file=file, subject=subject, message=message,
        routing=routing, created_by=user["id"],
    )
    await _audit(
        request, kind="esign_create", eid=env["id"], actor_id=user["id"],
        details={"document_sha256": env["document_sha256"], "routing": env["routing"]},
    )
    return env


@router.post("/envelopes/{eid}/recipients")
async def add_recipient(
    eid: str,
    body: RecipientIn,
    request: Request,
    user: dict = Depends(require_role(*_SENDER_ROLES)),
):
    rec = await edb.add_recipient(
        request.app.state.pg,
        envelope_id=eid, name=body.name, email=str(body.email),
        role=body.role, routing_order=body.routing_order,
    )
    await _audit(
        request, kind="esign_add_recipient", eid=eid, actor_id=user["id"],
        details={"recipient_id": rec["id"], "email": rec["email"], "role": rec["role"]},
    )
    return rec


@router.post("/envelopes/{eid}/send")
async def send_envelope(
    eid: str,
    request: Request,
    user: dict = Depends(require_role(*_SENDER_ROLES)),
):
    result = await edb.send_envelope(request.app.state.pg, eid=eid)
    await _audit(
        request, kind="esign_send", eid=eid, actor_id=user["id"],
        details={"recipient_count": len(result["recipients"])},
    )
    return result


@router.post("/envelopes/{eid}/sign")
async def sign_envelope(eid: str, body: SignIn, request: Request):
    client_ip = request.client.host if request.client else None
    result = await edb.sign(
        request.app.state.pg,
        eid=eid, token=body.token, consent_given=body.consent_given, signed_ip=client_ip,
    )
    await _audit(
        request, kind="esign_sign", eid=eid, actor_id=None,
        details={
            "recipient_id": result["recipient_id"],
            "signature_hash": result["signature_hash"],
            "envelope_status": result["envelope_status"],
        },
    )
    return result


@router.post("/envelopes/{eid}/decline")
async def decline_envelope(eid: str, body: DeclineIn, request: Request):
    client_ip = request.client.host if request.client else None
    result = await edb.decline(
        request.app.state.pg,
        eid=eid, token=body.token, reason=body.reason, signed_ip=client_ip,
    )
    await _audit(
        request, kind="esign_decline", eid=eid, actor_id=None,
        details={"recipient_id": result["recipient_id"], "reason": body.reason},
    )
    return result


@router.post("/envelopes/{eid}/void")
async def void_envelope(
    eid: str,
    body: VoidIn,
    request: Request,
    user: dict = Depends(require_role(*_SENDER_ROLES)),
):
    result = await edb.void(request.app.state.pg, eid=eid, reason=body.reason)
    await _audit(
        request, kind="esign_void", eid=eid, actor_id=user["id"],
        details={"reason": body.reason, "from": result["from"]},
    )
    return result


@router.get("/envelopes/{eid}")
async def get_envelope(
    eid: str,
    request: Request,
    user: dict = Depends(require_role(*_VIEW_ROLES)),
):
    env = await edb.get_envelope(request.app.state.pg, eid)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
    recips = await edb.list_recipients(request.app.state.pg, eid)
    return {"envelope": _public(env), "recipients": [_public(r) for r in recips]}


@router.get("/envelopes/{eid}/certificate")
async def certificate(
    eid: str,
    request: Request,
    user: dict = Depends(require_role(*_VIEW_ROLES)),
):
    env = await edb.get_envelope(request.app.state.pg, eid)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
    recips = await edb.list_recipients(request.app.state.pg, eid)
    return esign.build_certificate(env, recips)


@router.get("/envelopes/{eid}/document")
async def download_document(eid: str, request: Request, token: str | None = None):
    """Fetch the source document. Authorized either by a valid recipient
    signing token (query param) or by a sender API key with a view role."""
    env = await edb.get_envelope(request.app.state.pg, eid)
    if not env:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")

    authorized = False
    if token:
        recips = await edb.list_recipients(request.app.state.pg, eid)
        wanted = esign.hash_signing_token(token)
        authorized = any(r.get("access_token_hash") == wanted for r in recips)
    if not authorized:
        # No / invalid token → require an authenticated sender role.
        user = await current_user(request, request.headers.get("X-API-Key"))
        if user["role"] not in _VIEW_ROLES:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="insufficient_role")

    abs_path = os.path.join(settings.esign_dir, env["document_path"])
    if not os.path.exists(abs_path):
        raise HTTPException(status.HTTP_410_GONE, detail="document_missing")
    return FileResponse(abs_path, media_type=env["document_mime"], filename=env["document_name"])
