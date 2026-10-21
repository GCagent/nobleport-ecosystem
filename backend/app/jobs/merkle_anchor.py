"""
Daily Merkle anchoring job.

Computes Merkle roots for each anchored table for a given date,
stores them in merkle_anchors, then optionally anchors to chain.

Usage:
    # As a standalone script (cron):
    python -m app.jobs.merkle_anchor

    # Or import and call from scheduler:
    await run_daily_anchor(target_date)
"""

import asyncio
import json
import logging
import sys
from datetime import date, timedelta

import asyncpg

from app.core.config import settings
from app.services.merkle import hash_record, build_merkle_root
from app.services.anchor import anchor_batch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Tables to anchor daily with their column selections
ANCHOR_TABLES = {
    "projects": """
        select id, name, status, gc_id, company_id, created_at, updated_at
        from projects
        where created_at::date = $1
        order by created_at asc
    """,
    "inspections": """
        select id, project_id, inspector_id, inspection_type, status,
               scheduled_at, completed_at, created_at
        from inspections
        where created_at::date = $1
        order by created_at asc
    """,
    "permits": """
        select id, project_id, permit_type, permit_number, status,
               issued_by, issued_at, created_at
        from permits
        where created_at::date = $1
        order by created_at asc
    """,
    "disputes": """
        select id, project_id, raised_by, assigned_arbiter, status,
               subject, created_at
        from disputes
        where created_at::date = $1
        order by created_at asc
    """,
}


async def anchor_table_for_day(
    conn: asyncpg.Connection,
    table_name: str,
    query: str,
    target_date: date,
) -> dict:
    """Compute and store Merkle root for one table for one day."""
    rows = await conn.fetch(query, target_date)
    records = [dict(r) for r in rows]
    hashes = [hash_record(r) for r in records]
    root_hash = build_merkle_root(hashes)

    # Store first N leaf hashes for quick audit reference
    sample_size = min(len(hashes), 50)

    await conn.execute(
        """insert into merkle_anchors (anchor_date, root_hash, record_count, source_table, leaf_hashes, metadata)
           values ($1, $2, $3, $4, $5, $6)
           on conflict (anchor_date, source_table)
           do update set
               root_hash = excluded.root_hash,
               record_count = excluded.record_count,
               leaf_hashes = excluded.leaf_hashes,
               metadata = excluded.metadata""",
        target_date,
        root_hash,
        len(records),
        table_name,
        hashes[:sample_size],
        json.dumps({
            "sample_hashes": hashes[:10],
            "total_hashes": len(hashes),
        }),
    )

    result = {
        "table": table_name,
        "anchor_date": str(target_date),
        "record_count": len(records),
        "root_hash": root_hash,
    }
    logger.info("Anchored %s: %d records, root=%s", table_name, len(records), root_hash[:16])
    return result


async def run_daily_anchor(target_date: date | None = None) -> list[dict]:
    """Run anchoring for all tables for a given date (defaults to yesterday)."""
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    logger.info("Starting daily Merkle anchor for %s", target_date)

    conn = await asyncpg.connect(settings.database_url)
    try:
        results = []
        for table_name, query in ANCHOR_TABLES.items():
            result = await anchor_table_for_day(conn, table_name, query, target_date)
            results.append(result)

        # Attempt on-chain anchoring (no-op if not configured)
        chain_results = await anchor_batch(conn)
        for cr in chain_results:
            logger.info("Chain anchor result: %s", cr)

        logger.info("Daily anchor complete. %d tables processed.", len(results))
        return results
    finally:
        await conn.close()


async def backfill(start_date: date, end_date: date) -> list[dict]:
    """Backfill anchors for a date range."""
    logger.info("Backfilling from %s to %s", start_date, end_date)
    all_results = []
    current = start_date
    while current <= end_date:
        results = await run_daily_anchor(current)
        all_results.extend(results)
        current += timedelta(days=1)
    return all_results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = date.fromisoformat(sys.argv[1])
    else:
        target = date.today() - timedelta(days=1)

    asyncio.run(run_daily_anchor(target))
