import pytest
from fastapi import HTTPException

from app.db.verifications import assert_transition


def test_verified_to_disputed_by_moderator():
    assert_transition("VERIFIED", "DISPUTED", "moderator")


def test_verified_to_legal_hold_requires_admin():
    assert_transition("VERIFIED", "LEGAL_HOLD", "admin")
    with pytest.raises(HTTPException) as e:
        assert_transition("VERIFIED", "LEGAL_HOLD", "moderator")
    assert e.value.status_code == 403


def test_removed_is_terminal():
    with pytest.raises(HTTPException) as e:
        assert_transition("REMOVED", "DISPUTED", "admin")
    assert e.value.status_code == 409


def test_contractor_can_dispute_but_not_verify():
    assert_transition("VERIFIED", "DISPUTED", "contractor")
    with pytest.raises(HTTPException) as e:
        assert_transition("DISPUTED", "VERIFIED", "contractor")
    assert e.value.status_code == 403


def test_unknown_target_rejected():
    with pytest.raises(HTTPException) as e:
        assert_transition("VERIFIED", "BANANA", "admin")
    assert e.value.status_code == 400


def test_legal_hold_cannot_go_back_to_verified():
    with pytest.raises(HTTPException) as e:
        assert_transition("LEGAL_HOLD", "VERIFIED", "admin")
    assert e.value.status_code == 409
