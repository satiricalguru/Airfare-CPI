"""
SIH26056 — Tests for Real Web Scraper Components, Time-Band Stratification,
Statutory Fee Breakdown, and Lead-Time Elasticity Econometric Modeling.
"""

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path
import sys

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from engine.elasticity import fit_polynomial_elasticity
from provenance import AcquisitionMethod, DataProvenance, SourceType
from scraper.base import FareObservation, classify_time_band


class TestScraperComponentsAndTimeBands:

    def test_classify_time_band_boundaries(self):
        """Validates correct classification across all 4 time bands."""
        # Band 00:00-05:59
        assert classify_time_band("00:00") == "00:00-05:59"
        assert classify_time_band("03:30") == "00:00-05:59"
        assert classify_time_band("05:59") == "00:00-05:59"

        # Band 06:00-11:59
        assert classify_time_band("06:00") == "06:00-11:59"
        assert classify_time_band("09:45") == "06:00-11:59"
        assert classify_time_band("11:59") == "06:00-11:59"

        # Band 12:00-17:59
        assert classify_time_band("12:00") == "12:00-17:59"
        assert classify_time_band("15:20") == "12:00-17:59"
        assert classify_time_band("17:59") == "12:00-17:59"

        # Band 18:00-23:59
        assert classify_time_band("18:00") == "18:00-23:59"
        assert classify_time_band("21:15") == "18:00-23:59"
        assert classify_time_band("23:59") == "18:00-23:59"

        # Edge cases and fallback
        assert classify_time_band(None) == "UNSPECIFIED"
        assert classify_time_band("") == "UNSPECIFIED"
        assert classify_time_band("invalid") == "UNSPECIFIED"

    def test_product_key_includes_time_band(self):
        """Elementary product key must stratify by departure time band."""
        obs = FareObservation(
            route_id=1,
            origin_code="DEL",
            destination_code="BOM",
            departure_date=date(2026, 9, 15),
            booking_horizon_days=7,
            airline_code="6E",
            airline_name="IndiGo",
            flight_number="6E-201",
            cabin_class="ECONOMY",
            fare_family="saver",
            fare_total=6450.0,
            fare_base=4650.0,
            fare_taxes=780.0,
            fare_udf=670.0,
            fare_convenience=350.0,
            dep_time="08:45",
            dep_time_band="06:00-11:59",
            currency="INR",
            stops=0,
            provenance=DataProvenance(
                source_type=SourceType.SIMULATED,
                source_name="simulator",
                collection_timestamp=datetime.now(timezone.utc),
                request_id="test_req",
            ),
        )
        key = obs.product_key()
        assert "BAND_06:00-11:59" in key
        assert "6E" in key
        assert "H7" in key
        assert "|0|" in key

    def test_statutory_fee_breakdown_balance(self):
        """Fee components must reconcile: Base + Taxes + UDF + Convenience == Total."""
        base = 4200.0
        taxes = 756.0
        udf = 650.0
        convenience = 350.0
        total = round(base + taxes + udf + convenience, 2)

        obs = FareObservation(
            route_id=1,
            origin_code="DEL",
            destination_code="BOM",
            departure_date=date(2026, 9, 20),
            booking_horizon_days=15,
            airline_code="AI",
            airline_name="Air India",
            flight_number="AI-805",
            cabin_class="ECONOMY",
            fare_family="standard",
            fare_total=total,
            fare_base=base,
            fare_taxes=taxes,
            fare_udf=udf,
            fare_convenience=convenience,
            dep_time="14:10",
            dep_time_band="12:00-17:59",
            currency="INR",
            stops=0,
            provenance=DataProvenance(
                source_type=SourceType.SIMULATED,
                source_name="simulator",
                collection_timestamp=datetime.now(timezone.utc),
                request_id="test_req",
            ),
        )
        d = obs.to_dict()
        assert d["fare_udf"] == 650.0
        assert d["fare_convenience"] == 350.0
        assert d["dep_time"] == "14:10"
        assert d["dep_time_band"] == "12:00-17:59"
        reconciled = round(d["fare_base"] + d["fare_taxes"] + d["fare_udf"] + d["fare_convenience"], 2)
        assert abs(reconciled - d["fare_total"]) < 1e-4


class TestEconometricElasticity:

    def test_fit_polynomial_elasticity_standard_curve(self):
        """Tests that standard convex advance purchase fares produce valid econometric parameters."""
        days = [1, 1, 7, 7, 15, 15, 30, 30, 45, 45]
        fares = [9800, 9400, 7100, 6800, 5300, 5100, 4300, 4200, 4100, 4000]

        result = fit_polynomial_elasticity(days, fares)
        assert result is not None
        assert result.r_squared > 0.90
        assert result.sample_size == 10
        assert result.beta_1 < 0
        assert result.beta_2 > 0
        assert "T+1" in result.marginal_elasticities
        assert "T+7" in result.marginal_elasticities
        assert "T+30" in result.marginal_elasticities
        assert result.marginal_elasticities["T+1"] < 0
        assert len(result.predicted_curve) > 0

    def test_elasticity_handles_insufficient_samples(self):
        """Fewer than 3 observations returns None."""
        assert fit_polynomial_elasticity([1, 7], [8000, 6000]) is None
        assert fit_polynomial_elasticity([], []) is None

    def test_elasticity_handles_zero_variance(self):
        """Flat pricing across identical horizon days returns None."""
        assert fit_polynomial_elasticity([7, 7, 7, 7], [5000, 5000, 5000, 5000]) is None


class TestQualityAndElasticityEndpoints:

    def test_quality_endpoint_contract(self):
        """GET /api/v1/quality must report elementary cell coverage, routes, and anomalies."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/quality")
                    assert res.status_code == 200
                    data = res.json()
                    assert "status" in data
                    assert "elementary_cell_coverage" in data
                    cov = data["elementary_cell_coverage"]
                    assert "scheduled_cells" in cov
                    assert "observed_cells" in cov
                    assert "coverage_pct" in cov
                    assert cov["scheduled_cells"] > 0
                    assert "observation_totals" in data
                    assert "routes" in data
                    assert "anomalies" in data
                    assert "sources" in data

        asyncio.run(_run())

    def test_analysis_elasticity_endpoint(self):
        """GET /api/v1/analysis/elasticity returns structured response."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/analysis/elasticity")
                    assert res.status_code == 200
                    data = res.json()
        asyncio.run(_run())

    def test_mospi_backtest_endpoint(self):
        """GET /api/v1/backtest/mospi returns official e-Sankhyiki benchmark metrics."""
        async def _run():
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    res = await client.get("/api/v1/backtest/mospi")
                    assert res.status_code == 200
                    data = res.json()
                    assert "portal_source" in data
                    assert "https://esankhyiki.mospi.gov.in" in data["portal_source"]
                    assert "pearson_correlation_transport" in data
                    assert "pearson_correlation_airfare_item" in data
                    assert data["months_compared"] > 0
                    assert "lead_time_advantage_days" in data
                    assert data["lead_time_advantage_days"] > 0
                    assert "nowcast_projection" in data

        asyncio.run(_run())

