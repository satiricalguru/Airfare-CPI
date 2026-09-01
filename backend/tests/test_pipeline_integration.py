"""
SIH26056 — End-to-End Pipeline Integration Tests

Tests the end-to-end workflow:
1. Data collection via simulator
2. Data validation & anomaly filtering via FareValidator
3. Base price extraction & Matched-model Jevons computation per horizon
4. Booking-horizon combination with policy weights
5. National aggregation with passenger-volume weights
6. HTTP API endpoints verification against running FastAPI instance with lifespan
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import httpx
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from config import get_settings
from engine.aggregator import NationalAggregator, RouteIndexInput
from engine.horizon import (
    CombinedRouteIndex,
    HorizonIndexInput,
    combine_horizon_indices,
    get_horizon_policy,
)
from engine.matched_jevons import MatchedJevonsCalculator
from engine.rebase import BasePeriod, compute_base_prices
from engine.weights import get_route_basket
from scraper.sources.simulator import SimulatorFareSource
from scraper.validator import FareValidator


def test_full_engine_pipeline_integration():
    """Test data generation -> validation -> base prices -> matched Jevons -> horizon combination -> national aggregation."""
    simulator = SimulatorFareSource(seed=42)
    validator = FareValidator()
    jevons_calc = MatchedJevonsCalculator()
    horizon_policy = get_horizon_policy()
    basket = get_route_basket()
    aggregator = NationalAggregator(basket=basket)

    base_period = BasePeriod(start=date(2026, 8, 1), days=7)
    target_date = date(2026, 8, 15)

    # 1. Generate base period observations (for all 25 routes, 5 horizons)
    base_observations = []
    for day_offset in range(base_period.days):
        coll_day = base_period.start + timedelta(days=day_offset)
        coll_dt = datetime(coll_day.year, coll_day.month, coll_day.day, 10, 0, tzinfo=timezone.utc)
        for route in basket.routes[:5]:  # Use top 5 routes for fast test execution
            for h in [0, 3, 7, 15, 30]:
                dep_date = coll_day + timedelta(days=h)
                obs_list = simulator.generate(
                    route_id=route.route_id,
                    origin=route.origin_code,
                    destination=route.destination_code,
                    departure_date=dep_date,
                    booking_horizon_days=h,
                    collection_datetime=coll_dt,
                )
                base_observations.extend(obs_list)

    # Validate base observations
    base_batch = validator.validate_batch(base_observations)
    valid_base = [obs for obs in base_batch.accepted if obs.is_valid]
    assert len(valid_base) > 0

    # Extract base prices
    base_prices = compute_base_prices(valid_base, base_period=base_period)
    assert len(base_prices) > 0

    # 2. Generate current period observations
    curr_observations = []
    target_dt = datetime(target_date.year, target_date.month, target_date.day, 10, 0, tzinfo=timezone.utc)
    for route in basket.routes[:5]:
        for h in [0, 3, 7, 15, 30]:
            dep_date = target_date + timedelta(days=h)
            obs_list = simulator.generate(
                route_id=route.route_id,
                origin=route.origin_code,
                destination=route.destination_code,
                departure_date=dep_date,
                booking_horizon_days=h,
                collection_datetime=target_dt,
            )
            curr_observations.extend(obs_list)

    curr_batch = validator.validate_batch(curr_observations)
    valid_curr = [obs for obs in curr_batch.accepted if obs.is_valid]
    assert len(valid_curr) > 0

    # Group current observations by (route_id, horizon)
    curr_by_route_h: dict[tuple[int, int], list] = {}
    for obs in valid_curr:
        curr_by_route_h.setdefault((obs.route_id, obs.booking_horizon_days), []).append(obs)

    # 3. Compute matched-model Jevons per horizon, then combine across horizons for each route
    route_index_inputs: list[RouteIndexInput] = []
    for route in basket.routes[:5]:
        horizon_inputs: list[HorizonIndexInput] = []
        for h in [0, 3, 7, 15, 30]:
            key = (route.route_id, h)
            if key not in base_prices or key not in curr_by_route_h:
                continue
            base_set = base_prices[key]
            jev_res = jevons_calc.compute(
                current_observations=curr_by_route_h[key],
                base_prices=base_set.product_prices,
                route_id=route.route_id,
                index_date=target_date,
                base_period_start=base_period.start,
                base_period_end=base_period.end,
                booking_horizon=h,
            )
            if jev_res is not None:
                horizon_inputs.append(
                    HorizonIndexInput(
                        booking_horizon=h,
                        index_value=jev_res.index_value,
                        matched_products=jev_res.matched_products,
                        observation_count=jev_res.observation_count,
                    )
                )

        combined_route = combine_horizon_indices(
            route_id=route.route_id,
            horizon_indices=horizon_inputs,
            policy=horizon_policy,
        )
        if combined_route.is_publishable:
            route_index_inputs.append(
                RouteIndexInput(
                    route_id=route.route_id,
                    index_value=combined_route.index_value,
                    matched_products=combined_route.total_matched_products,
                    observation_count=combined_route.total_observations,
                    horizons_included=combined_route.horizons_included,
                    horizons_missing=combined_route.horizons_missing,
                )
            )

    assert len(route_index_inputs) > 0

    # 4. National aggregation
    national_res = aggregator.aggregate(
        route_indices=route_index_inputs,
        index_date=target_date,
        base_period_label=base_period.label,
    )

    assert national_res is not None
    assert national_res.index_value > 0
    assert national_res.routes_included == len(route_index_inputs)
    assert national_res.renormalization_applied is True  # Because only 5 of 25 routes were provided


def test_api_endpoints_live(monkeypatch):
    """Test all primary FastAPI endpoints with ASGI transport and lifespan context."""
    monkeypatch.setenv("COLLECTION_MODE", "SIMULATED")
    monkeypatch.setenv("INDEX_BASE_PERIOD_START", "2026-08-01")
    from config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None

    async def _run():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                # 1. Root
                res = await client.get("/")
                assert res.status_code == 200
                data = res.json()
                assert "SIH26056" in data["project"]
                assert "provenance_label" in data
                assert "collection_mode" in data

                # 2. Routes
                res = await client.get("/api/v1/routes")
                assert res.status_code == 200
                data = res.json()
                assert data["total_routes"] == 25
                assert len(data["routes"]) == 25

                # 3. Route Weights
                res = await client.get("/api/v1/weights")
                assert res.status_code == 200
                data = res.json()
                assert abs(data["weight_sum"] - 1.0) < 1e-9

                # 4. Health
                res = await client.get("/api/v1/health")
                assert res.status_code == 200
                assert res.json()["status"] in {"healthy", "degraded"}

                # 5. Provenance metadata
                res = await client.get("/api/v1/provenance")
                assert res.status_code == 200
                assert "configured_mode" in res.json()

                # 6. Methodology
                res = await client.get("/api/v1/methodology")
                assert res.status_code == 200
                assert "elementary_aggregate" in res.json()

                # 7. Sources
                res = await client.get("/api/v1/sources")
                assert res.status_code == 200
                assert "sources" in res.json()

                # 8. Collection status
                res = await client.get("/api/v1/collection/status")
                assert res.status_code == 200
                assert "configured_mode" in res.json()

                # 9. Monthly bulletin check
                res_monthly = await client.get("/api/v1/reports/monthly")
                assert res_monthly.status_code in {200, 404}

                # 10. Seed simulated history
                res_backfill = await client.post(
                    "/api/v1/collection/backfill-simulated",
                    json={
                        "start_date": "2026-08-01",
                        "end_date": "2026-08-10",
                        "routes": [1, 2, 3],
                        "horizons": [0, 7],
                    },
                )
                assert res_backfill.status_code == 200
                assert res_backfill.json()["days_seeded"] == 10

                # 11. Now Monthly bulletin returns 200
                res = await client.get("/api/v1/reports/monthly")
                assert res.status_code == 200
                report = res.json()
                assert "headline_index" in report

                res_html = await client.get("/api/v1/reports/monthly/html")
                assert res_html.status_code == 200
                assert "PROTOTYPE" in res_html.text.upper()
                assert "NOT AN OFFICIAL STATISTICAL RELEASE" in res_html.text.upper()

    asyncio.run(_run())


def test_scraper_trigger_endpoint():
    """Test collection trigger endpoint via AsyncClient."""
    async def _run():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                res = await client.post(
                    "/api/v1/collection/trigger",
                    json={
                        "mode": "SIMULATED",
                        "routes": [1, 2],
                        "horizons": [0, 7],
                        "compute_index": True,
                    },
                )
                assert res.status_code == 200
                data = res.json()
                assert data["collection"]["status"] in {"simulated", "success"}
                assert data["collection"]["observation_count"] > 0
                assert data["observations_persisted"] > 0

    asyncio.run(_run())
