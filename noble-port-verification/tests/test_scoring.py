from app.engine.scoring import (
    BLOCK,
    HOLD,
    PASS,
    birdeye_check,
    combine,
    helius_check,
    solscan_check,
)


def test_helius_block_on_mint_authority():
    assert helius_check({"type": "token_account", "mint_authority": "Xyz"}) == BLOCK


def test_helius_hold_on_freeze():
    assert helius_check({"type": "token_account", "freeze_authority": True}) == HOLD


def test_helius_pass_clean():
    assert helius_check({"type": "token_account"}) == PASS


def test_birdeye_block_below_floor():
    assert birdeye_check({"liquidity_usd": 1000, "volume_24h": 0}) == BLOCK


def test_birdeye_hold_thin():
    assert birdeye_check({"liquidity_usd": 75_000, "volume_24h": 30_000}) == HOLD


def test_birdeye_hold_low_volume():
    assert birdeye_check({"liquidity_usd": 200_000, "volume_24h": 10_000}) == HOLD


def test_birdeye_pass():
    assert birdeye_check({"liquidity_usd": 500_000, "volume_24h": 250_000}) == PASS


def test_solscan_block_low_count():
    assert solscan_check([{"from": "a", "to": "b", "amount": 1}] * 3) == BLOCK


def test_solscan_block_on_loop():
    txs = [{"from": "a", "to": "b", "amount": 1}] * 3 + [{"from": "b", "to": "a", "amount": 1}] * 3
    assert solscan_check(txs) == BLOCK


def test_solscan_block_single_source_funding():
    txs = [{"from": "x", "to": "tgt", "amount": 100}] * 6
    assert solscan_check(txs) == BLOCK


def test_solscan_pass_diverse():
    txs = [
        {"from": f"src{i}", "to": "tgt", "amount": 10} for i in range(10)
    ]
    assert solscan_check(txs) == PASS


def test_combine_priority():
    assert combine(PASS, PASS, PASS) == PASS
    assert combine(PASS, HOLD, PASS) == HOLD
    assert combine(PASS, HOLD, BLOCK) == BLOCK
    assert combine(BLOCK, PASS, PASS) == BLOCK
