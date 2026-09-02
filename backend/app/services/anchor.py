"""
Arbitrum anchoring stub.

Phase 1: Store roots in merkle_anchors table (done by merkle_anchor job).
Phase 2: Anchor batch root to Arbitrum, store tx_hash back.

This module provides the Phase 2 interface. It is a stub until
the on-chain contract and RPC credentials are configured.
"""

import json
import logging
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# -- Configuration (set these when ready for on-chain anchoring) --
ARBITRUM_RPC_URL: str | None = None  # e.g. "https://arb1.arbitrum.io/rpc"
ANCHOR_CONTRACT_ADDRESS: str | None = None
ANCHOR_PRIVATE_KEY: str | None = None  # Never hardcode. Load from env/vault.


async def anchor_to_chain(
    conn: asyncpg.Connection,
    anchor_id: UUID,
    root_hash: str,
) -> dict:
    """
    Anchor a merkle root to Arbitrum.

    Returns:
        dict with chain_name, tx_hash, anchored_at if successful.
        dict with status="stub" if chain config is not set.
    """
    if not all([ARBITRUM_RPC_URL, ANCHOR_CONTRACT_ADDRESS, ANCHOR_PRIVATE_KEY]):
        logger.info(
            "Chain anchoring not configured. Storing root locally only. "
            "Set ARBITRUM_RPC_URL, ANCHOR_CONTRACT_ADDRESS, ANCHOR_PRIVATE_KEY to enable."
        )
        return {
            "status": "stub",
            "message": "On-chain anchoring not configured. Root stored locally.",
            "anchor_id": str(anchor_id),
            "root_hash": root_hash,
        }

    # ---------------------------------------------------------------
    # Phase 2 implementation goes here.
    #
    # Pseudocode:
    #
    #   from web3 import Web3
    #   w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))
    #   contract = w3.eth.contract(address=ANCHOR_CONTRACT_ADDRESS, abi=ANCHOR_ABI)
    #   tx = contract.functions.anchorRoot(
    #       bytes.fromhex(root_hash)
    #   ).build_transaction({
    #       "from": account.address,
    #       "nonce": w3.eth.get_transaction_count(account.address),
    #       "gas": 100000,
    #   })
    #   signed = account.sign_transaction(tx)
    #   tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    #   receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    #
    #   await conn.execute("""
    #       update merkle_anchors
    #       set chain_name = 'arbitrum',
    #           tx_hash = $1,
    #           anchored_at = now()
    #       where id = $2
    #   """, receipt.transactionHash.hex(), anchor_id)
    #
    #   return {
    #       "status": "anchored",
    #       "chain_name": "arbitrum",
    #       "tx_hash": receipt.transactionHash.hex(),
    #       "anchored_at": datetime.utcnow().isoformat(),
    #   }
    # ---------------------------------------------------------------

    return {"status": "stub", "message": "Implement Phase 2 anchor logic"}


async def get_unanchored_roots(conn: asyncpg.Connection, limit: int = 50) -> list[dict]:
    """Fetch merkle anchors that have not yet been anchored on-chain."""
    rows = await conn.fetch(
        """select id, anchor_date, source_table, root_hash, record_count
           from merkle_anchors
           where tx_hash is null
           order by anchor_date asc
           limit $1""",
        limit,
    )
    return [dict(r) for r in rows]


async def anchor_batch(conn: asyncpg.Connection) -> list[dict]:
    """Anchor all pending roots. Returns results per anchor."""
    pending = await get_unanchored_roots(conn)
    results = []
    for row in pending:
        result = await anchor_to_chain(conn, row["id"], row["root_hash"])
        results.append(result)
    return results
