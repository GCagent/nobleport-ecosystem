from app.services.solscan import detect_single_source_funding, detect_wallet_loops


PASS, HOLD, BLOCK = "PASS", "HOLD", "BLOCK"


def helius_check(data: dict) -> str:
    if data.get("type") not in {"wallet", "token_account", "V1_TOKEN", "FungibleToken", "FungibleAsset"}:
        return BLOCK
    if data.get("mint_authority"):
        return BLOCK
    if data.get("freeze_authority"):
        return HOLD
    return PASS


def birdeye_check(data: dict) -> str:
    liquidity = float(data.get("liquidity_usd") or 0)
    volume = float(data.get("volume_24h") or 0)
    if liquidity < 50_000:
        return BLOCK
    if liquidity < 150_000:
        return HOLD
    if volume < liquidity * 0.2:
        return HOLD
    return PASS


def solscan_check(txs: list[dict]) -> str:
    if len(txs) < 5:
        return BLOCK
    if detect_wallet_loops(txs):
        return BLOCK
    if detect_single_source_funding(txs):
        return BLOCK
    return PASS


def combine(h: str, b: str, s: str) -> str:
    if BLOCK in (h, b, s):
        return BLOCK
    if HOLD in (h, b, s):
        return HOLD
    return PASS
