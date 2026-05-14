from app.security.validate import is_valid_solana_address


def test_valid_wsol_mint():
    assert is_valid_solana_address("So11111111111111111111111111111111111111112")


def test_rejects_empty():
    assert not is_valid_solana_address("")


def test_rejects_too_short():
    assert not is_valid_solana_address("So1111")


def test_rejects_bad_base58():
    assert not is_valid_solana_address("0OIl" * 10)


def test_rejects_non_string():
    assert not is_valid_solana_address(None)  # type: ignore[arg-type]
