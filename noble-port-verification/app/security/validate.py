import base58


SOLANA_MIN_LEN = 32
SOLANA_MAX_LEN = 44


def is_valid_solana_address(addr: str) -> bool:
    if not isinstance(addr, str):
        return False
    if not (SOLANA_MIN_LEN <= len(addr) <= SOLANA_MAX_LEN):
        return False
    try:
        decoded = base58.b58decode(addr)
    except ValueError:
        return False
    return len(decoded) == 32
