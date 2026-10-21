"""Open-source e-signature ("Seal") engine.

A from-scratch, audit-first signing core — the open-source counterpart to a
hosted e-signature service. All logic here is pure (no DB, no network) so it
can be unit-tested in isolation and reused by the DB / router layers.

Design notes
------------
* Envelopes and recipients each run an explicit, fail-closed state machine.
* Every signature commits to the document digest, the signer's identity, the
  signing timestamp and an explicit ESIGN/UETA consent string. The resulting
  ``signature_hash`` is tamper-evident: changing the document or any field
  invalidates it.
* Signing tokens follow the same "hash-at-rest, raw-shown-once" pattern as the
  project's API keys (see ``app/security/auth.py``).
* A Certificate of Completion can be derived deterministically from an envelope
  and its recipients, and is itself hashed for integrity.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime

from fastapi import HTTPException, status


# --- Consent (ESIGN Act 15 U.S.C. ch. 96 / UETA) ----------------------------
CONSENT_TEXT = (
    "I agree to use electronic records and electronic signatures, and I agree "
    "that my electronic signature is the legal equivalent of my handwritten "
    "signature on this document (ESIGN Act, 15 U.S.C. ch. 96 / UETA)."
)


# --- Envelope state machine --------------------------------------------------
DRAFT, SENT, COMPLETED, DECLINED, VOIDED = (
    "DRAFT", "SENT", "COMPLETED", "DECLINED", "VOIDED",
)
ENVELOPE_STATES = {DRAFT, SENT, COMPLETED, DECLINED, VOIDED}

# COMPLETED / DECLINED / VOIDED are terminal.
_ENVELOPE_ALLOWED = {
    DRAFT:     {SENT, VOIDED},
    SENT:      {COMPLETED, DECLINED, VOIDED},
    COMPLETED: set(),
    DECLINED:  set(),
    VOIDED:    set(),
}


def assert_envelope_transition(current: str, target: str) -> None:
    if target not in ENVELOPE_STATES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="invalid_envelope_state")
    if target not in _ENVELOPE_ALLOWED.get(current, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"envelope_transition_not_allowed:{current}->{target}",
        )


# --- Recipient state machine -------------------------------------------------
PENDING, SIGNED, RECIPIENT_DECLINED = "PENDING", "SIGNED", "DECLINED"
RECIPIENT_STATES = {PENDING, SIGNED, RECIPIENT_DECLINED}

# Roles that must act for an envelope to complete. Viewers are non-blocking.
SIGNING_ROLES = {"signer", "approver"}
RECIPIENT_ROLES = SIGNING_ROLES | {"viewer"}


def assert_recipient_actionable(current: str) -> None:
    """A recipient may only sign / decline while PENDING."""
    if current != PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"recipient_not_actionable:{current}"
        )


# --- Signing tokens (hash-at-rest, raw shown once) ---------------------------
def hash_signing_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def mint_signing_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Persist only the hash."""
    raw = "sig_" + secrets.token_urlsafe(32)
    return raw, hash_signing_token(raw)


# --- Tamper-evident signature hash -------------------------------------------
def compute_signature_hash(
    *,
    document_sha256: str,
    recipient_id: str,
    email: str,
    signed_at_iso: str,
    consent_text: str = CONSENT_TEXT,
) -> str:
    """Bind a signature to the exact document + signer + moment + consent.

    Any later change to the document bytes, the signer, the timestamp or the
    consent string yields a different hash, so a stored signature is
    self-verifying against the recorded inputs.
    """
    msg = "|".join(
        [document_sha256, recipient_id, email.strip().lower(), signed_at_iso, consent_text]
    )
    return hashlib.sha256(msg.encode()).hexdigest()


# --- Routing / completion ----------------------------------------------------
def signing_blockers(recipients: list[dict], routing_order: int, mode: str) -> list[dict]:
    """Earlier-order signers still PENDING that block a given routing order.

    In ``sequential`` mode a recipient cannot sign until everyone with a lower
    routing order has signed. ``parallel`` mode never blocks.
    """
    if mode == "parallel":
        return []
    return [
        r for r in recipients
        if r["role"] in SIGNING_ROLES
        and r["routing_order"] < routing_order
        and r["status"] == PENDING
    ]


def envelope_is_complete(recipients: list[dict]) -> bool:
    """True once every signing-role recipient has SIGNED (viewers ignored)."""
    signers = [r for r in recipients if r["role"] in SIGNING_ROLES]
    return bool(signers) and all(r["status"] == SIGNED for r in signers)


# --- Certificate of Completion -----------------------------------------------
def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _certificate_hash(cert: dict) -> str:
    body = json.dumps(cert, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def build_certificate(envelope: dict, recipients: list[dict]) -> dict:
    """Deterministic Certificate of Completion for an envelope.

    The returned dict carries a ``certificate_hash`` computed over every other
    field, so the certificate is itself tamper-evident.
    """
    ordered = sorted(recipients, key=lambda r: (r["routing_order"], r["email"]))
    cert = {
        "envelope_id": str(envelope["id"]),
        "subject": envelope["subject"],
        "document_name": envelope["document_name"],
        "document_sha256": envelope["document_sha256"],
        "status": envelope["status"],
        "routing": envelope["routing"],
        "consent_text": CONSENT_TEXT,
        "created_at": _iso(envelope.get("created_at")),
        "sent_at": _iso(envelope.get("sent_at")),
        "completed_at": _iso(envelope.get("completed_at")),
        "recipients": [
            {
                "name": r["name"],
                "email": r["email"],
                "role": r["role"],
                "routing_order": r["routing_order"],
                "status": r["status"],
                "consent_given": bool(r.get("consent_given")),
                "signature_hash": r.get("signature_hash"),
                "signed_at": _iso(r.get("signed_at")),
                "signed_ip": r.get("signed_ip"),
            }
            for r in ordered
        ],
    }
    cert["certificate_hash"] = _certificate_hash(cert)
    return cert
