"""
SIH26056 — Tests for Festive Spikes & Flight Movers Analysis.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from db.engine import get_database
from engine.festive_and_movers import get_festive_analysis, get_flight_movers


def test_festive_calendar_analysis():
    async def _test():
        db = get_database()
        async with db.session() as session:
            analysis = await get_festive_analysis(session)
            assert "calendar_events" in analysis
            events = analysis["calendar_events"]
            assert len(events) >= 6

            event_ids = [e["id"] for e in events]
            assert "diwali" in event_ids
            assert "chhath" in event_ids
            assert "durga_puja" in event_ids
            assert "new_year_goa" in event_ids
            assert "holi" in event_ids

            diwali = next(e for e in events if e["id"] == "diwali")
            assert diwali["typical_surge_pct"] > 40
            assert "DEL-PAT" in diwali["impacted_corridors"]

    asyncio.run(_test())


def test_flight_movers_empty_or_populated():
    async def _test():
        db = get_database()
        await db.create_schema()
        async with db.session() as session:
            movers = await get_flight_movers(session, source_type="simulated")
            assert "top_surging_flights" in movers
            assert "top_dropping_flights" in movers
            assert "brand_comparison" in movers

    asyncio.run(_test())


def test_api_festive_and_movers_endpoint():
    async def _test():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/analysis/festive-and-movers")
                assert resp.status_code == 200
                data = resp.json()
                assert "festive_spikes" in data
                assert "flight_movers" in data
                assert len(data["festive_spikes"]["calendar_events"]) >= 6

    asyncio.run(_test())
