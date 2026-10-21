import pytest
from fastapi import HTTPException

from app.engine import esign


# --- envelope state machine --------------------------------------------------
def test_draft_can_send_and_void():
    esign.assert_envelope_transition("DRAFT", "SENT")
    esign.assert_envelope_transition("DRAFT", "VOIDED")


def test_sent_can_complete_decline_void():
    for target in ("COMPLETED", "DECLINED", "VOIDED"):
        esign.assert_envelope_transition("SENT", target)


def test_completed_is_terminal():
    with pytest.raises(HTTPException) as e:
        esign.assert_envelope_transition("COMPLETED", "SENT")
    assert e.value.status_code == 409


def test_cannot_sign_a_draft_directly():
    # DRAFT -> COMPLETED is not a legal edge (must go through SENT).
    with pytest.raises(HTTPException) as e:
        esign.assert_envelope_transition("DRAFT", "COMPLETED")
    assert e.value.status_code == 409


def test_unknown_envelope_state_rejected():
    with pytest.raises(HTTPException) as e:
        esign.assert_envelope_transition("DRAFT", "BANANA")
    assert e.value.status_code == 400


# --- recipient actionability -------------------------------------------------
def test_pending_recipient_is_actionable():
    esign.assert_recipient_actionable("PENDING")


def test_signed_recipient_cannot_act_again():
    with pytest.raises(HTTPException) as e:
        esign.assert_recipient_actionable("SIGNED")
    assert e.value.status_code == 409


# --- signing tokens ----------------------------------------------------------
def test_mint_token_is_prefixed_and_hash_matches():
    raw, h = esign.mint_signing_token()
    assert raw.startswith("sig_")
    assert len(h) == 64
    assert esign.hash_signing_token(raw) == h


def test_tokens_are_unique():
    a, _ = esign.mint_signing_token()
    b, _ = esign.mint_signing_token()
    assert a != b


# --- signature hash ----------------------------------------------------------
def test_signature_hash_deterministic():
    kw = dict(
        document_sha256="a" * 64,
        recipient_id="r1",
        email="Signer@Example.com",
        signed_at_iso="2026-06-02T00:00:00+00:00",
    )
    assert esign.compute_signature_hash(**kw) == esign.compute_signature_hash(**kw)


def test_signature_hash_email_case_insensitive():
    base = dict(
        document_sha256="a" * 64, recipient_id="r1",
        signed_at_iso="2026-06-02T00:00:00+00:00",
    )
    assert (
        esign.compute_signature_hash(email="A@B.com", **base)
        == esign.compute_signature_hash(email="a@b.com", **base)
    )


def test_signature_hash_changes_with_document():
    base = dict(
        recipient_id="r1", email="a@b.com",
        signed_at_iso="2026-06-02T00:00:00+00:00",
    )
    h1 = esign.compute_signature_hash(document_sha256="a" * 64, **base)
    h2 = esign.compute_signature_hash(document_sha256="b" * 64, **base)
    assert h1 != h2


# --- routing / completion ----------------------------------------------------
def _r(order, status_, role="signer"):
    return {"routing_order": order, "status": status_, "role": role}


def test_sequential_blocks_until_prior_signs():
    recips = [_r(1, "PENDING"), _r(2, "PENDING")]
    assert esign.signing_blockers(recips, routing_order=2, mode="sequential")
    assert not esign.signing_blockers(recips, routing_order=1, mode="sequential")


def test_sequential_unblocks_after_prior_signs():
    recips = [_r(1, "SIGNED"), _r(2, "PENDING")]
    assert not esign.signing_blockers(recips, routing_order=2, mode="sequential")


def test_parallel_never_blocks():
    recips = [_r(1, "PENDING"), _r(2, "PENDING")]
    assert esign.signing_blockers(recips, routing_order=2, mode="parallel") == []


def test_viewer_does_not_block_signing():
    recips = [_r(1, "PENDING", role="viewer"), _r(2, "PENDING")]
    assert not esign.signing_blockers(recips, routing_order=2, mode="sequential")


def test_complete_only_when_all_signers_signed():
    assert not esign.envelope_is_complete([_r(1, "SIGNED"), _r(2, "PENDING")])
    assert esign.envelope_is_complete([_r(1, "SIGNED"), _r(2, "SIGNED")])


def test_complete_ignores_viewers():
    recips = [_r(1, "SIGNED"), _r(2, "PENDING", role="viewer")]
    assert esign.envelope_is_complete(recips)


def test_no_signers_is_not_complete():
    assert not esign.envelope_is_complete([_r(1, "PENDING", role="viewer")])


# --- certificate -------------------------------------------------------------
def _envelope():
    return {
        "id": "env-1",
        "subject": "AWO #42 — sign-off",
        "document_name": "awo42.pdf",
        "document_sha256": "c" * 64,
        "status": "COMPLETED",
        "routing": "sequential",
        "created_at": "2026-06-01T00:00:00+00:00",
        "sent_at": "2026-06-01T01:00:00+00:00",
        "completed_at": "2026-06-02T00:00:00+00:00",
    }


def test_certificate_includes_recipients_and_hash():
    recips = [
        {"name": "GC", "email": "gc@x.com", "role": "signer", "routing_order": 1,
         "status": "SIGNED", "consent_given": True, "signature_hash": "d" * 64,
         "signed_at": "2026-06-01T02:00:00+00:00", "signed_ip": "10.0.0.1"},
    ]
    cert = esign.build_certificate(_envelope(), recips)
    assert cert["envelope_id"] == "env-1"
    assert cert["document_sha256"] == "c" * 64
    assert len(cert["recipients"]) == 1
    assert len(cert["certificate_hash"]) == 64
    assert cert["consent_text"] == esign.CONSENT_TEXT


def test_certificate_hash_changes_with_content():
    env = _envelope()
    recips = [
        {"name": "GC", "email": "gc@x.com", "role": "signer", "routing_order": 1,
         "status": "SIGNED", "consent_given": True, "signature_hash": "d" * 64,
         "signed_at": "2026-06-01T02:00:00+00:00", "signed_ip": "10.0.0.1"},
    ]
    h1 = esign.build_certificate(env, recips)["certificate_hash"]
    env["document_sha256"] = "e" * 64
    h2 = esign.build_certificate(env, recips)["certificate_hash"]
    assert h1 != h2
