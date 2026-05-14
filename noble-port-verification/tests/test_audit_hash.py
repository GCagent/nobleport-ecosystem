from app.db.audit import GENESIS_HASH, _row_hash


def test_hash_chain_deterministic():
    payload = {"a": 1, "b": "x"}
    h1 = _row_hash(GENESIS_HASH, payload)
    h2 = _row_hash(GENESIS_HASH, payload)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_chain_links_prev():
    p1 = {"id": "row1"}
    p2 = {"id": "row2"}
    h1 = _row_hash(GENESIS_HASH, p1)
    h2 = _row_hash(h1, p2)
    h2_wrong = _row_hash(GENESIS_HASH, p2)
    assert h2 != h2_wrong
