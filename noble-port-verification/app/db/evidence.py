import hashlib
import json
import os
import uuid
from pathlib import Path

import asyncpg
from fastapi import HTTPException, UploadFile, status

from app.config import settings


def _allowed_mimes() -> set[str]:
    return {m.strip() for m in settings.evidence_allowed_mime.split(",") if m.strip()}


async def store_upload(
    pool: asyncpg.Pool,
    *,
    file: UploadFile,
    uploaded_by: str,
    verification_id: str | None,
    note: str | None,
    moderation: dict | None,
) -> dict:
    if file.content_type not in _allowed_mimes():
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"mime_not_allowed:{file.content_type}")

    Path(settings.evidence_dir).mkdir(parents=True, exist_ok=True)
    eid = str(uuid.uuid4())
    safe_name = Path(file.filename or "evidence.bin").name
    rel_path = f"{eid}_{safe_name}"
    abs_path = os.path.join(settings.evidence_dir, rel_path)

    sha = hashlib.sha256()
    size = 0
    with open(abs_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 64)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.evidence_max_bytes:
                out.close()
                os.unlink(abs_path)
                raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="evidence_too_large")
            sha.update(chunk)
            out.write(chunk)

    digest = sha.hexdigest()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO evidence
                (id, verification_id, uploaded_by, filename, mime,
                 size_bytes, sha256, path, note, moderation, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb, now())
            """,
            uuid.UUID(eid),
            uuid.UUID(verification_id) if verification_id else None,
            uuid.UUID(uploaded_by),
            safe_name, file.content_type,
            size, digest, rel_path, note,
            json.dumps(moderation) if moderation else None,
        )
    return {
        "id": eid, "sha256": digest, "size_bytes": size,
        "mime": file.content_type, "filename": safe_name,
    }
