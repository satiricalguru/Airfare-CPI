"""
SIH26056 — Scrapers Fleet & Observability Health Test Suite.

Verifies:
1. Registration and capability descriptors for all 8 newly enabled portals + FastFlights.
2. GET /api/v1/scrapers/health observability endpoint contracts.
3. POST /api/v1/scrapers/{source_id}/test on-demand probe endpoint with AERA fee decomposition.
4. Scrapy spider specifications and CPIFarePipeline processing.
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
import httpx
import pytest

from api.main import app
from scraper.registry import get_registry
from scraper.spiders.flight_spiders import ScrapedFlightItem
from scraper.spiders.pipelines import CPIFarePipeline


def test_scraper_fleet_registry_membership():
    reg = get_registry()
    expected_sources = [
        "makemytrip",
        "goibibo",
        "cleartrip",
        "indigo",
        "air_india",
        "spicejet",
        "akasa",
        "skyscanner",
        "fast_flights",
        "easemytrip",
        "live_portal",
        "amadeus",
    ]
    for name in expected_sources:
        assert reg.has(name), f"Expected source {name} to be registered in SourceRegistry"
        cap = reg.capability(name)
        assert cap.name == name
        if not cap.requires_credentials:
            assert cap.enabled is True
        assert "INR" in cap.native_currency


def test_api_scrapers_health_endpoint():
    async def _test():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/scrapers/health")
                assert resp.status_code == 200
                data = resp.json()

                assert "scrapers" in data
                assert "summary" in data
                summary = data["summary"]
                assert summary["total_count"] >= 12
                assert summary["active_count"] >= 10
                assert summary["overall_health"] == "OPTIMAL"

                scraper_ids = {s["source_id"] for s in data["scrapers"]}
                assert "makemytrip" in scraper_ids
                assert "indigo" in scraper_ids
                assert "fast_flights" in scraper_ids
                assert "cleartrip" in scraper_ids
                assert "air_india" in scraper_ids
                assert "spicejet" in scraper_ids
                assert "akasa" in scraper_ids
                assert "skyscanner" in scraper_ids

                # Check properties on individual scraper card payload
                mmt = next(s for s in data["scrapers"] if s["source_id"] == "makemytrip")
                assert mmt["status"] == "ACTIVE_WORKING"
                assert mmt["is_active"] is True
                assert "Playwright" in mmt["engine"]
                assert mmt["latency_ms"] > 0
                assert mmt["success_rate_24h"] > 90.0

    asyncio.run(_test())


def test_api_test_single_scraper_probe():
    async def _test():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                for src in ("makemytrip", "indigo", "fast_flights", "cleartrip"):
                    resp = await client.post(f"/api/v1/scrapers/{src}/test")
                    assert resp.status_code == 200
                    data = resp.json()
                    assert data["source_id"] == src
                    assert data["status"] == "SUCCESS"
                    assert data["is_working"] is True
                    assert data["observations_count"] > 0
                    assert len(data["sample_quotes"]) > 0

                    sample = data["sample_quotes"][0]
                    assert sample["fare_total"] > 1000
                    assert sample["fare_base"] is not None
                    assert sample["fare_taxes"] is not None
                    assert sample["fare_udf"] is not None

                # Test unknown scraper 404
                resp_404 = await client.post("/api/v1/scrapers/unknown_portal_xyz/test")
                assert resp_404.status_code == 404

    asyncio.run(_test())


def test_scrapy_pipeline_item_processing():
    pipeline = CPIFarePipeline()
    today = date.today()

    item = ScrapedFlightItem(
        portal="makemytrip",
        airline_code="6E",
        airline_name="IndiGo",
        flight_number="6E-205",
        origin="DEL",
        destination="BOM",
        departure_date=today + timedelta(days=7),
        departure_time="08:30",
        total_fare=4950.0,
        stops=0,
    )

    obs = pipeline.process_item(item, route_id=1, booking_horizon_days=7)
    assert obs is not None
    assert obs.airline_code == "6E"
    assert obs.flight_number == "6E-205"
    assert float(obs.fare_total) == 4950.0
    assert obs.fare_base is not None
    assert obs.fare_taxes is not None
    assert obs.fare_udf is not None
    assert obs.provenance.source_name == "makemytrip"
    assert obs.provenance.acquisition_method.value == "WEB_SCRAPE"
