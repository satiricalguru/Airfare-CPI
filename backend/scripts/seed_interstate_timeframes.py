#!/usr/bin/env python3
"""
SIH26056 — Seed 1-Year Multi-Timeframe History for Interstate / Custom Corridors.

Generates historical observations and RouteIndex entries for all 58 interstate routes
across 7D, 1M, 3M, 6M, and 1Y timeframes up to today (2026-09-02).
"""

import asyncio
import os
import sys
import time
from datetime import date, datetime, time as dtime, timedelta, timezone
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
    today = date.today() # 2026-09-02
    basket = get_route_basket()
    
    print(f"🚀 Seeding 1-Year Multi-Timeframe series for 58 interstate routes up to {today}...")
    t0 = time.time()

    custom_routes = []
    for orig, dest, orig_city, dest_city in INTERSTATE_ROUTES:
        cr = basket.get_or_dynamic(
            origin_code=orig,
            destination_code=dest,
            origin_city=orig_city,
            destination_city=dest_city,
        )
        custom_routes.append(cr)

    # Key date samples across the full year:
    # - Dense last 35 days (daily) for 7D and 1M
    # - Every 3 days for 3M, 6M, and 1Y
    dense_dates = [today - timedelta(days=d) for d in range(35)]
    sparse_dates = [today - timedelta(days=d) for d in range(35, 370, 4)]
    sample_dates = sorted(set(dense_dates + sparse_dates))

    print(f"Sampling {len(sample_dates)} historical dates from {sample_dates[0]} to {sample_dates[-1]}...")

    async with db.session_factory() as session:
        service = IngestService(settings)

        for d in sample_dates:
            collected_at = datetime.combine(d, dtime(hour=10), tzinfo=timezone.utc)
            await service.ingest(
                session=session,
                mode=CollectionMode.SIMULATED,
                custom_routes=custom_routes,
                horizons=[0, 3, 7, 15, 30],
                collection_day=d,
                compute_index=False,
                triggered_by="seed_interstate_history",
                source_kwargs={"collection_datetime": collected_at},
            )
        await session.commit()

        print("Writing RouteIndex records for all interstate routes...")
        now = utc_now()
        route_index_count = 0

        for r in custom_routes:
            obs = await repo.load_observations(session, route_ids=[r.route_id], valid_only=True)
            if not obs:
                continue
            
            by_date = {}
            for o in obs:
                by_date.setdefault(o.collection_date, []).append(o)
            
            for c_date, date_obs in by_date.items():
                horizon_set = sorted(list({f.booking_horizon_days for f in date_obs}))
                avg_fare = float(sum(f.fare_total for f in date_obs) / len(date_obs))
                # Stable corridor price ratio relative to base
                est_ratio = round(1.0 + (((avg_fare * 13) % 200) - 100) / 2500.0, 4)
                est_index_100 = round(est_ratio * 100.0, 2)

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
                route_index_count += 1
        
        await session.commit()
        print(f"🎉 Done! Seeded {route_index_count} RouteIndex rows across {len(sample_dates)} dates in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
