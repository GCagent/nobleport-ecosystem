"""Persistence + transactional state changes for the e-signature module.

Mirrors the project's other DB modules (``verifications``, ``evidence``):
pure SQL with state-machine guards enforced inside ``FOR UPDATE`` transactions,
failing closed via HTTPException. Signing logic lives in
``app.engine.esign`` and is imported here.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.engine import esign


def _allowed_mimes() -> set[str]:
    return {m.strip() for m in settings.esign_allowed_mime.split(",") if m.strip()}


def _row(record: asyncpg.Record | None) -> dict | None:
    if record is None:
        return None
    d = dict(record)
    for k in ("id", "envelope_id", "created_by"):
        if d.get(k) is not None and isinstance(d[k], uuid.UUID):
            d[k] = str(d[k])
    return d


async def create_envelope(
    pool: asyncpg.Pool,
    *,
    file: UploadFile,
    subject: str,
    message: str | None,
    routing: str,
    created_by: str,
) -> dict:
    if routing not in {"sequential", "parallel"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_routing")
    if file.content_type not in _allowed_mimes():
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"mime_not_allowed:{file.content_type}",
        )

    Path(settings.esign_dir).mkdir(parents=True, exist_ok=True)
    eid = str(uuid.uuid4())
    safe_name = Path(file.filename or "document.pdf").name
    rel_path = f"{eid}_{safe_name}"
    abs_path = os.path.join(settings.esign_dir, rel_path)

    sha = hashlib.sha256()
    size = 0
    with open(abs_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 64)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.esign_max_bytes:
                out.close()
                os.unlink(abs_path)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="document_too_large"
                )
            sha.update(chunk)
            out.write(chunk)

    digest = sha.hexdigest()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO envelopes
                (id, subject, message, document_name, document_mime,
                 document_sha256, document_path, document_bytes,
                 status, routing, created_by, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11, now(), now())
            """,
            uuid.UUID(eid), subject, message, safe_name, file.content_type,
            digest, rel_path, size, esign.DRAFT, routing, uuid.UUID(created_by),
        )
    return {
        "id": eid,
        "subject": subject,
        "status": esign.DRAFT,
        "routing": routing,
        "document_name": safe_name,
        "document_mime": file.content_type,
        "document_sha256": digest,
        "document_bytes": size,
    }


async def add_recipient(
    pool: asyncpg.Pool,
    *,
    envelope_id: str,
    name: str,
    email: str,
    role: str,
    routing_order: int,
) -> dict:
    if role not in esign.RECIPIENT_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_recipient_role")
    rid = str(uuid.uuid4())
    async with pool.acquire() as conn:
        async with conn.transaction():
            env = await conn.fetchrow(
                "SELECT status FROM envelopes WHERE id = $1 FOR UPDATE",
                uuid.UUID(envelope_id),
            )
            if not env:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
            if env["status"] != esign.DRAFT:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="recipients_locked_after_send"
                )
            await conn.execute(
                """
                INSERT INTO envelope_recipients
                    (id, envelope_id, name, email, role, routing_order, status, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7, now())
                """,
                uuid.UUID(rid), uuid.UUID(envelope_id), name, email.strip().lower(),
                role, routing_order, esign.PENDING,
            )
    return {
        "id": rid, "envelope_id": envelope_id, "name": name,
        "email": email.strip().lower(), "role": role,
        "routing_order": routing_order, "status": esign.PENDING,
    }


async def get_envelope(pool: asyncpg.Pool, eid: str) -> dict | None:
    async with pool.acquire() as conn:
        env = await conn.fetchrow("SELECT * FROM envelopes WHERE id = $1", uuid.UUID(eid))
    return _row(env)


async def list_recipients(pool: asyncpg.Pool, eid: str) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM envelope_recipients WHERE envelope_id = $1 "
            "ORDER BY routing_order, email",
            uuid.UUID(eid),
        )
    return [_row(r) for r in rows]


async def send_envelope(pool: asyncpg.Pool, *, eid: str) -> dict:
    """DRAFT -> SENT. Mints one-time signing tokens; raw tokens returned once."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            env = await conn.fetchrow(
                "SELECT status FROM envelopes WHERE id = $1 FOR UPDATE",
                uuid.UUID(eid),
            )
            if not env:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
            esign.assert_envelope_transition(env["status"], esign.SENT)

            recips = await conn.fetch(
                "SELECT id, name, email, role FROM envelope_recipients WHERE envelope_id = $1",
                uuid.UUID(eid),
            )
            signers = [r for r in recips if r["role"] in esign.SIGNING_ROLES]
            if not signers:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="no_signing_recipients"
                )

            issued = []
            for r in recips:
                raw, token_hash = esign.mint_signing_token()
                await conn.execute(
                    "UPDATE envelope_recipients SET access_token_hash = $1 WHERE id = $2",
                    token_hash, r["id"],
                )
                issued.append({
                    "recipient_id": str(r["id"]),
                    "name": r["name"],
                    "email": r["email"],
                    "role": r["role"],
                    "signing_token": raw,  # shown once; deliver out-of-band
                })

            await conn.execute(
                "UPDATE envelopes SET status = $1, sent_at = now(), updated_at = now() "
                "WHERE id = $2",
                esign.SENT, uuid.UUID(eid),
            )
    return {"id": eid, "status": esign.SENT, "recipients": issued}


async def _recipient_by_token(conn, eid: str, token: str) -> asyncpg.Record:
    rec = await conn.fetchrow(
        """
        SELECT * FROM envelope_recipients
         WHERE envelope_id = $1 AND access_token_hash = $2
         FOR UPDATE
        """,
        uuid.UUID(eid), esign.hash_signing_token(token),
    )
    if not rec:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid_signing_token")
    return rec


async def sign(
    pool: asyncpg.Pool,
    *,
    eid: str,
    token: str,
    consent_given: bool,
    signed_ip: str | None,
) -> dict:
    """Record a signature, then complete the envelope if all signers are done."""
    if not consent_given:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="consent_required")

    async with pool.acquire() as conn:
        async with conn.transaction():
            env = await conn.fetchrow(
                "SELECT * FROM envelopes WHERE id = $1 FOR UPDATE", uuid.UUID(eid)
            )
            if not env:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
            if env["status"] != esign.SENT:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail=f"envelope_not_signable:{env['status']}"
                )

            recip = await _recipient_by_token(conn, eid, token)
            esign.assert_recipient_actionable(recip["status"])

            all_recips = await conn.fetch(
                "SELECT role, routing_order, status FROM envelope_recipients "
                "WHERE envelope_id = $1",
                uuid.UUID(eid),
            )
            blockers = esign.signing_blockers(
                [dict(r) for r in all_recips], recip["routing_order"], env["routing"]
            )
            if blockers:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="awaiting_prior_signers"
                )

            signed_at = datetime.now(timezone.utc)
            sig_hash = esign.compute_signature_hash(
                document_sha256=env["document_sha256"],
                recipient_id=str(recip["id"]),
                email=recip["email"],
                signed_at_iso=signed_at.isoformat(),
            )
            await conn.execute(
                """
                UPDATE envelope_recipients
                   SET status = $1, consent_given = TRUE, signature_hash = $2,
                       signed_ip = $3, signed_at = $4
                 WHERE id = $5
                """,
                esign.SIGNED, sig_hash, signed_ip, signed_at, recip["id"],
            )

            after = await conn.fetch(
                "SELECT role, status FROM envelope_recipients WHERE envelope_id = $1",
                uuid.UUID(eid),
            )
            completed = esign.envelope_is_complete([dict(r) for r in after])
            if completed:
                await conn.execute(
                    "UPDATE envelopes SET status = $1, completed_at = now(), "
                    "updated_at = now() WHERE id = $2",
                    esign.COMPLETED, uuid.UUID(eid),
                )
    return {
        "envelope_id": eid,
        "recipient_id": str(recip["id"]),
        "email": recip["email"],
        "signature_hash": sig_hash,
        "signed_at": signed_at.isoformat(),
        "envelope_status": esign.COMPLETED if completed else esign.SENT,
    }


async def decline(
    pool: asyncpg.Pool,
    *,
    eid: str,
    token: str,
    reason: str | None,
    signed_ip: str | None,
) -> dict:
    """A recipient declines; the envelope becomes DECLINED (terminal)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            env = await conn.fetchrow(
                "SELECT status FROM envelopes WHERE id = $1 FOR UPDATE", uuid.UUID(eid)
            )
            if not env:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
            if env["status"] != esign.SENT:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail=f"envelope_not_signable:{env['status']}"
                )
            recip = await _recipient_by_token(conn, eid, token)
            esign.assert_recipient_actionable(recip["status"])
            await conn.execute(
                "UPDATE envelope_recipients SET status = $1, decline_reason = $2, "
                "signed_ip = $3, signed_at = now() WHERE id = $4",
                esign.RECIPIENT_DECLINED, reason, signed_ip, recip["id"],
            )
            esign.assert_envelope_transition(env["status"], esign.DECLINED)
            await conn.execute(
                "UPDATE envelopes SET status = $1, updated_at = now() WHERE id = $2",
                esign.DECLINED, uuid.UUID(eid),
            )
    return {
        "envelope_id": eid,
        "recipient_id": str(recip["id"]),
        "email": recip["email"],
        "envelope_status": esign.DECLINED,
    }


async def void(pool: asyncpg.Pool, *, eid: str, reason: str | None) -> dict:
    """Sender voids a DRAFT or SENT envelope (terminal)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            env = await conn.fetchrow(
                "SELECT status FROM envelopes WHERE id = $1 FOR UPDATE", uuid.UUID(eid)
            )
            if not env:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="envelope_not_found")
            esign.assert_envelope_transition(env["status"], esign.VOIDED)
            await conn.execute(
                "UPDATE envelopes SET status = $1, voided_reason = $2, updated_at = now() "
                "WHERE id = $3",
                esign.VOIDED, reason, uuid.UUID(eid),
            )
    return {"id": eid, "status": esign.VOIDED, "from": env["status"]}
