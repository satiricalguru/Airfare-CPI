#!/usr/bin/env python3
"""
SIH26056 — Comprehensive Seeding of 1-Year History & Today's Data across ALL Corridors.

Ensures every corridor (both 25 core basket routes + 58 interstate routes) has:
- Today's data (2026-09-02)
- 7D, 1M (30D), 3M (90D), 6M (180D), and 1Y (365D) historical index series
"""

import asyncio
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from config import get_settings
from db.engine import get_database
from db.models import RouteIndex, HorizonIndex
from db import repository as repo
from engine.ingest_service import IngestService
from engine.index_service import IndexService
from engine.weights import get_route_basket
from provenance import CollectionMode, METHODOLOGY_VERSION, utc_now
from scripts.seed_state_routes import INTERSTATE_ROUTES


async def main():
    settings = get_settings()
    db = get_database()
    await db.create_schema()

    today = date.today() # 2026-09-02
    basket = get_route_basket()
    
    print(f"🚀 Seeding Full 1-Year History up to Today ({today}) for all corridors...")
    t0 = time.time()

    # Prepare custom interstate routes
    custom_routes = []
    for orig, dest, orig_city, dest_city in INTERSTATE_ROUTES:
        cr = basket.get_or_dynamic(
            origin_code=orig,
            destination_code=dest,
            origin_city=orig_city,
            destination_city=dest_city,
        )
        custom_routes.append(cr)
    
    print(f"Total custom interstate routes: {len(custom_routes)}")

    async with db.session_factory() as session:
        service = IngestService(settings)

        # 1. Backfill simulated history for all 25 core routes up to today
        print("📦 1/3: Ensuring core basket corridors have daily history up to today...")
        await service.backfill_simulated_history(
            session=session,
            start_date=today - timedelta(days=5),
            end_date=today,
            route_ids=list(range(1, 26)),
            horizons=[0, 3, 7, 15, 30],
        )
        await session.commit()

        # 2. Ingest observations for custom interstate routes across key historical dates & today
        print("📦 2/3: Ingesting observations for 58 interstate corridors across 365 days...")
        
        # Batch ingest interstate routes: dense for past 35 days, then spaced across 365 days
        dense_dates = [today - timedelta(days=d) for d in range(35)]
        sparse_dates = [today - timedelta(days=d) for d in range(35, 370, 3)]
        sample_dates = sorted(set(dense_dates + sparse_dates))

        for d in sample_dates:
            await service.ingest(
                session=session,
                mode=CollectionMode.SIMULATED,
                custom_routes=custom_routes,
                horizons=[0, 3, 7, 15, 30],
                collection_day=d,
                compute_index=False,
                triggered_by="seed_interstate_365d",
            )
        await session.commit()

        # 3. Generate RouteIndex and HorizonIndex for custom routes across all sampled dates
        print("📐 3/3: Recomputing & syncing RouteIndex entries for all routes...")
        now = utc_now()
        
        for r in custom_routes:
            obs = await repo.load_observations(session, route_ids=[r.route_id], valid_only=True)
            if not obs:
                continue
            
            # Group observations by collection_date
            by_date = {}
            for o in obs:
                by_date.setdefault(o.collection_date, []).append(o)
            
            for c_date, date_obs in by_date.items():
                horizon_set = sorted(list({f.booking_horizon_days for f in date_obs}))
                avg_fare = float(sum(f.fare_total for f in date_obs) / len(date_obs))
                est_ratio = round(1.0 + (((avg_fare * 13) % 200) - 100) / 2500.0, 4)
                est_index_100 = round(est_ratio * 100.0, 2)

                # Check if route index exists for this date
                existing = await session.execute(
                    select(RouteIndex).where(
                        RouteIndex.route_id == r.route_id,
                        RouteIndex.index_date == c_date,
                    )
                )
                row = existing.scalar_one_or_none()
                if row:
                    row.index_value = est_ratio
                    row.index_100 = est_index_100
                    row.matched_products = len(date_obs)
                    row.observation_count = len(date_obs)
                    row.horizons_included = horizon_set
                else:
                    session.add(
                        RouteIndex(
                            index_date=c_date,
                            route_id=r.route_id,
                            index_value=est_ratio,
                            index_100=est_index_100,
                            horizons_included=horizon_set,
                            horizons_missing=[],
                            applied_horizon_weights={str(h): 1.0 / len(horizon_set) for h in horizon_set},
                            horizon_weighting_method="equal",
                            horizon_weighting_status="PROVISIONAL",
                            horizon_policy_version="v2.0.0",
                            matched_products=len(date_obs),
                            observation_count=len(date_obs),
                            base_period_start=date(2025, 8, 1),
                            base_period_end=date(2025, 8, 31),
                            is_publishable=True,
                            source_type=date_obs[0].source_type,
                            methodology_version=METHODOLOGY_VERSION,
                            computed_at=now,
                        )
                    )
        
        await session.commit()

        # Recompute national and core route indices
        index_service = IndexService(settings)
        idx_res = await index_service.recompute(session=session, reason="1-year & today comprehensive build")
        await session.commit()

        print(f"🎉 Complete dataset ready in {time.time() - t0:.1f}s!")
        print(f"   Dates computed: {len(idx_res.dates_computed)}")
        print(f"   Route indices written: {idx_res.route_indices_written}")


if __name__ == "__main__":
    asyncio.run(main())
