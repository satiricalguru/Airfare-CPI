#!/usr/bin/env python3
"""
SIH26056 — Seed 1-Year (395-day) Historical Dataset.

Seeds observations and computes Matched-Model Jevons indices from 2025-08-01 to 2026-08-30
across all 25 domestic corridors and 5 advance booking horizons (T+1, T+7, T+15, T+30, T+45).
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from db.engine import get_database
from engine.index_service import IndexService
from engine.ingest_service import IngestService


async def main():
    settings = get_settings()
    db = get_database()

    start_date = date(2025, 8, 1)
    end_date = date.today()

    print(f"🚀 Starting 1-Year History Backfill: {start_date} to {end_date}")
    t0 = time.time()

    async with db.session_factory() as session:
        ingest_service = IngestService(settings)
        print("📦 Generating & persisting observations across all 25 corridors...")
        results = await ingest_service.backfill_simulated_history(
            session=session,
            start_date=start_date,
            end_date=end_date,
            route_ids=list(range(1, 26)),
            horizons=[1, 7, 15, 30, 45],
        )
        await session.commit()
        persisted = sum(r.observations_persisted for r in results)
        print(f"✅ Persisted {persisted} observations across {len(results)} days in {time.time() - t0:.1f}s")

        print("📐 Recomputing Matched-Model Jevons indices...")
        t1 = time.time()
        index_service = IndexService(settings)
        index_result = await index_service.recompute(
            session=session,
            reason=f"1-year history seeding {start_date}..{end_date}",
        )
        await session.commit()
        print(
            f"✅ Computed {len(index_result.dates_computed)} index dates "
            f"({index_result.national_indices_written} national indices, "
            f"{index_result.route_indices_written} route indices) in {time.time() - t1:.1f}s"
        )

    print(f"🎉 Complete 1-Year dataset ready in {time.time() - t0:.1f}s total!")


if __name__ == "__main__":
    asyncio.run(main())
