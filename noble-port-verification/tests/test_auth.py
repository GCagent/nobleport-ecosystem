from app.security.auth import hash_api_key, mint_api_key


def test_mint_returns_prefixed_key_and_matching_hash():
    raw, h = mint_api_key()
    assert raw.startswith("np_")
    assert len(h) == 64
    assert hash_api_key(raw) == h


def test_hash_is_deterministic_and_different_per_key():
    a, _ = mint_api_key()
    b, _ = mint_api_key()
    assert a != b
    assert hash_api_key(a) != hash_api_key(b)
    assert hash_api_key(a) == hash_api_key(a)
