from app.services.moderation import HeuristicModerator


m = HeuristicModerator()


def test_empty_is_ok():
    v = m.moderate("")
    assert v.label == "ok" and v.score == 0.0 and v.hits == {}


def test_clean_text_is_ok():
    v = m.moderate("Excellent contractor, finished on schedule.")
    assert v.label == "ok"


def test_profanity_flags_but_does_not_block():
    v = m.moderate("This was damn slow.")
    assert v.label == "flagged"
    assert "profanity" in v.hits


def test_defamation_blocks():
    v = m.moderate("This contractor is a scammer running a ponzi.")
    assert v.label == "block"
    assert "defamation" in v.hits


def test_pii_email_detected():
    v = m.moderate("Contact me at john.doe@example.com please.")
    assert "pii:email" in v.hits
    assert v.label in {"flagged", "block"}


def test_pii_ssn_detected():
    v = m.moderate("My SSN is 123-45-6789.")
    assert "pii:ssn" in v.hits


def test_score_capped_at_one():
    v = m.moderate("scammer scammer 123-45-6789 fuck shit me@a.co")
    assert 0.0 <= v.score <= 1.0
