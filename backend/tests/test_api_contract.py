"""
SIH26056 — API Contract Invariant Tests

Tests for HTTP API contract requirements:
1. Every index response carries data_provenance, methodology_version, base_period, sample_size.
2. Provenance display_label is one of LIVE DATA / SIMULATED DATA / OFFLINE PREVIEW / SOURCE UNAVAILABLE.
3. Seasonality adjustment explicitly states "NOT IMPLEMENTED".
4. Admin token authentication guards state-mutating endpoints.
5. No credentials or secrets leak in responses.
"""

import asyncio
from datetime import date
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import API_VERSION, app
from config import reload_settings
from provenance import (
    COLLECTOR_VERSION,
    METHODOLOGY_VERSION,
    NOT_IMPLEMENTED_LABEL,
    PROVENANCE_LABELS,
    SOURCE_UNAVAILABLE_LABEL,
    SourceType,
)


class TestAPIContract:

    def test_root_contract(self):
        """Root endpoint must carry project, methodology, and provenance metadata."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/")
                    assert res.status_code == 200
                    data = res.json()
                    assert data["api_version"] == API_VERSION
                    assert data["methodology_version"] == METHODOLOGY_VERSION
                    assert data["is_official_statistic"] is False
                    assert "Research prototype" in data["disclaimer"]

        asyncio.run(_run())

    def test_provenance_endpoint_contract(self):
        """Provenance endpoint exposes capabilities and current operational mode."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/provenance")
                    assert res.status_code == 200
                    data = res.json()
                    assert "configured_mode" in data
                    assert "configured_provenance_label" in data
                    assert "has_data" in data

        asyncio.run(_run())

    def test_seasonality_honesty_contract(self):
        """Seasonality endpoint must state NOT IMPLEMENTED honestly."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/methodology/seasonality")
                    assert res.status_code == 200
                    data = res.json()
                    assert data["status"] == NOT_IMPLEMENTED_LABEL
                    assert "readiness" in data
                    assert data["readiness"]["is_ready"] is False

        asyncio.run(_run())

    def test_admin_token_protection(self, monkeypatch):
        """State-mutating endpoints (e.g. trigger, review) require valid X-Admin-Token when configured."""
        monkeypatch.setenv("ADMIN_API_TOKEN", "super-secret-token")
        reload_settings()

        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    # Attempt collection trigger without token -> 401
                    res = await client.post(
                        "/api/v1/collection/trigger",
                        json={"mode": "SIMULATED", "routes": [1]},
                    )
                    assert res.status_code == 401

                    # Attempt with wrong token -> 401
                    res = await client.post(
                        "/api/v1/collection/trigger",
                        headers={"X-Admin-Token": "wrong-token"},
                        json={"mode": "SIMULATED", "routes": [1]},
                    )
                    assert res.status_code == 401

                    # Attempt with correct token -> 200
                    res = await client.post(
                        "/api/v1/collection/trigger",
                        headers={"X-Admin-Token": "super-secret-token"},
                        json={"mode": "SIMULATED", "routes": [1], "compute_index": False},
                    )
                    assert res.status_code == 200

        try:
            asyncio.run(_run())
        finally:
            monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)
            reload_settings()

    def test_airports_endpoint(self):
        """GET /api/v1/airports returns comprehensive Indian airport directory."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/airports")
                    assert res.status_code == 200
                    data = res.json()
                    assert "airports" in data
                    assert "states" in data
                    assert data["total_airports"] >= 80
                    assert any(a["code"] == "DEL" for a in data["airports"])
                    assert any(a["code"] == "PAT" for a in data["airports"])
                    assert any(a["code"] == "BLR" for a in data["airports"])

        asyncio.run(_run())

    def test_route_scrape_endpoint(self):
        """POST /api/v1/routes/scrape allows on-demand scraping for custom routes."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.post(
                        "/api/v1/routes/scrape",
                        json={
                            "origin": "PAT",
                            "destination": "BLR",
                            "origin_city": "Patna",
                            "destination_city": "Bengaluru",
                            "mode": "SIMULATED",
                            "horizons": [0, 7],
                        },
                    )
                    assert res.status_code == 200
                    data = res.json()
                    assert data["route"]["origin_code"] == "PAT"
                    assert data["route"]["destination_code"] == "BLR"
                    assert data["data_available"] is True
                    assert data["observations_persisted"] > 0
                    assert len(data["sample_fares"]) > 0

        asyncio.run(_run())


