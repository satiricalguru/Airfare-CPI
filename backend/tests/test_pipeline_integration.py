"""
SIH26056 — End-to-End Pipeline Integration Tests

Tests the end-to-end workflow:
1. Data collection & mock extraction
2. Data validation & anomaly filtering
3. Route-level Jevons geometric mean computation
4. Upper-level DGCA-weighted national CPI aggregation
5. HTTP API endpoints verification against running instance or direct handlers
"""

import pytest
import httpx
import numpy as np
from datetime import date, datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.jevons import JevonsIndexCalculator
from engine.aggregator import NationalAggregator, RouteWeight
from scraper.scrapers.mock_scraper import MockFareGenerator, observations_to_dicts
from scraper.validator import FareValidator
from reports.generator import MoSPIReportGenerator, MonthlyBulletin
from api.main import app
import asyncio


def test_full_engine_pipeline_integration():
    """Test data generation -> validation -> Jevons -> national aggregation."""
    generator = MockFareGenerator(seed=101)
    validator = FareValidator()
    jevons_calc = JevonsIndexCalculator()

    routes = [
        {"route_id": 1, "origin_code": "DEL", "destination_code": "BOM", "weight": 0.6, "dgca_monthly_pax": 1200000},
        {"route_id": 2, "origin_code": "DEL", "destination_code": "BLR", "weight": 0.4, "dgca_monthly_pax": 800000},
    ]

    base_date = date(2026, 8, 1)
    target_date = date(2026, 8, 15)

    # 1. Base period observations
    base_obs = generator.generate_day(routes, target_date=base_date, booking_horizons=[7, 30])
    base_dicts = observations_to_dicts(base_obs)
    acc_base, _, _ = validator.validate_batch(base_dicts)
    assert len(acc_base) > 0

    # 2. Current period observations
    curr_obs = generator.generate_day(routes, target_date=target_date, booking_horizons=[7, 30])
    curr_dicts = observations_to_dicts(curr_obs)
    acc_curr, _, _ = validator.validate_batch(curr_dicts)
    assert len(acc_curr) > 0

    # 3. Compute route Jevons
    route_weights = [
        RouteWeight(
            route_id=r["route_id"],
            origin_code=r["origin_code"],
            destination_code=r["destination_code"],
            weight=r["weight"],
            monthly_pax=r["dgca_monthly_pax"],
        )
        for r in routes
    ]
    aggregator = NationalAggregator(route_weights)

    jevons_results = []
    for r in routes:
        b_fares = [o["fare_total"] for o in acc_base if o["route_id"] == r["route_id"]]
        c_fares = [o["fare_total"] for o in acc_curr if o["route_id"] == r["route_id"]]
        base_gm = float(np.exp(np.mean(np.log(np.array(b_fares)))))
        res = jevons_calc.compute_from_prices_only(
            current_prices=np.array(c_fares),
            base_geometric_mean=base_gm,
            route_id=r["route_id"],
            index_date=target_date,
            base_period_start=base_date,
            base_period_end=base_date + timedelta(days=6),
        )
        assert res is not None
        assert res.jevons_index > 0
        jevons_results.append(res)

    # 4. Compute national CPI
    national_res = aggregator.compute_national_cpi(jevons_results)
    assert national_res is not None
    assert national_res.airfare_cpi > 0
    assert national_res.routes_included == 2
    assert len(national_res.route_contributions) == 2


import asyncio


def test_api_endpoints_live():
    """Test all primary FastAPI endpoints with ASGI transport and lifespan context."""
    async def _run():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                # Test Root Info
                res = await client.get("/")
                assert res.status_code == 200
                assert "SIH26056" in res.json()["project"]

                # Test Routes
                res = await client.get("/api/v1/routes")
                assert res.status_code == 200
                data = res.json()
                assert data["total_routes"] == 25

                # Test National Index
                res = await client.get("/api/v1/index/national")
                assert res.status_code == 200
                assert "airfare_cpi" in res.json()

                # Test National History
                res = await client.get("/api/v1/index/national/history?days=30")
                assert res.status_code == 200
                assert len(res.json()["data"]) > 0

                # Test Route Indices
                res = await client.get("/api/v1/index/routes")
                assert res.status_code == 200
                assert len(res.json()["routes"]) > 0

                # Test Fare Stats
                res = await client.get("/api/v1/fares/stats")
                assert res.status_code == 200
                assert res.json()["total_observations"] > 0

                # Test Booking Horizons Analysis
                res = await client.get("/api/v1/analysis/booking-horizons")
                assert res.status_code == 200
                assert len(res.json()["horizons"]) == 5

                # Test Health
                res = await client.get("/api/v1/health")
                assert res.status_code == 200
                assert res.json()["status"] == "healthy"

                # Test Monthly Report JSON & HTML
                res = await client.get("/api/v1/reports/monthly")
                assert res.status_code == 200
                assert "national_cpi" in res.json()

                res_html = await client.get("/api/v1/reports/monthly/html")
                assert res_html.status_code == 200
                assert "MoSPI" in res_html.text

    asyncio.run(_run())


def test_scraper_trigger_endpoint():
    """Test manual scrape trigger pipeline via AsyncClient."""
    async def _run():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                res = await client.post("/api/v1/scraper/trigger", json={"routes": [1, 2], "horizons": [0, 7]})
                assert res.status_code == 200
                data = res.json()
                assert data["status"] == "success"
                assert data["observations_generated"] > 0

    asyncio.run(_run())
