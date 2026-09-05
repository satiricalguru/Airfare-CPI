"""
SIH26056 — Tests for Structurally Mandatory Acquisition Method and Source Governance.

Verifies:
1. Invariant enforcement in DataProvenance.
2. Source access registry parsing, permission statuses, and governance constraints.
3. Database persistence, index partitioning, and unique constraints for acquisition_method.
4. API serialization and label transparency.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from db.engine import get_database
from db.models import (
    CollectionRun,
    FareObservationRecord,
    NationalIndex,
    RouteIndex,
    HorizonIndex,
)
from db import repository as repo
from provenance import (
    AcquisitionMethod,
    DataProvenance,
    SourceType,
    resolve_display_label,
    METHODOLOGY_VERSION,
)
from scraper.base import FareObservation
from scraper.source_registry import (
    PermissionStatus,
    get_source_registry,
)
from scraper.validator import ValidationAction, ValidationResult
from api import serializers as ser


# ═══════════════════════════════════════════════════════════
# 1. DATA PROVENANCE INVARIANTS
# ═══════════════════════════════════════════════════════════

def test_data_provenance_invariants():
    ts = datetime.now(timezone.utc)

    # Valid combinations
    p_sim = DataProvenance(
        source_type=SourceType.SIMULATED,
        source_name="sim",
        collection_timestamp=ts,
        request_id="req-1",
        acquisition_method=AcquisitionMethod.SIMULATED,
    )
    assert p_sim.acquisition_method == AcquisitionMethod.SIMULATED

    p_off = DataProvenance(
        source_type=SourceType.OFFLINE,
        source_name="fixture",
        collection_timestamp=ts,
        request_id="req-2",
        acquisition_method=AcquisitionMethod.OFFLINE_FIXTURE,
    )
    assert p_off.acquisition_method == AcquisitionMethod.OFFLINE_FIXTURE

    p_live_scrape = DataProvenance(
        source_type=SourceType.LIVE,
        source_name="portal",
        collection_timestamp=ts,
        request_id="req-3",
        acquisition_method=AcquisitionMethod.WEB_SCRAPE,
    )
    assert p_live_scrape.acquisition_method == AcquisitionMethod.WEB_SCRAPE

    p_live_api = DataProvenance(
        source_type=SourceType.LIVE,
        source_name="amadeus",
        collection_timestamp=ts,
        request_id="req-4",
        acquisition_method=AcquisitionMethod.API,
    )
    assert p_live_api.acquisition_method == AcquisitionMethod.API

    # Invalid combinations must raise ValueError
    with pytest.raises(ValueError, match="invariant violation"):
        DataProvenance(
            source_type=SourceType.SIMULATED,
            source_name="sim",
            collection_timestamp=ts,
            request_id="req-bad-1",
            acquisition_method=AcquisitionMethod.WEB_SCRAPE,
        )

    with pytest.raises(ValueError, match="invariant violation"):
        DataProvenance(
            source_type=SourceType.OFFLINE,
            source_name="fixture",
            collection_timestamp=ts,
            request_id="req-bad-2",
            acquisition_method=AcquisitionMethod.API,
        )

    with pytest.raises(ValueError, match="invariant violation"):
        DataProvenance(
            source_type=SourceType.LIVE,
            source_name="live",
            collection_timestamp=ts,
            request_id="req-bad-3",
            acquisition_method=AcquisitionMethod.SIMULATED,
        )


def test_data_provenance_inference_when_omitted():
    ts = datetime.now(timezone.utc)

    p_sim = DataProvenance(
        source_type=SourceType.SIMULATED,
        source_name="sim",
        collection_timestamp=ts,
        request_id="req-1",
    )
    assert p_sim.acquisition_method == AcquisitionMethod.SIMULATED

    p_off = DataProvenance(
        source_type=SourceType.OFFLINE,
        source_name="fixture",
        collection_timestamp=ts,
        request_id="req-2",
    )
    assert p_off.acquisition_method == AcquisitionMethod.OFFLINE_FIXTURE

    p_live = DataProvenance(
        source_type=SourceType.LIVE,
        source_name="live",
        collection_timestamp=ts,
        request_id="req-3",
    )
    assert p_live.acquisition_method == AcquisitionMethod.WEB_SCRAPE


# ═══════════════════════════════════════════════════════════
# 2. SOURCE ACCESS REGISTRY TESTS
# ═══════════════════════════════════════════════════════════

def test_source_access_registry_loading_and_permissions():
    registry = get_source_registry()
    assert len(registry.list_all()) >= 5

    ai = registry.get("air_india")
    assert ai is not None
    assert ai.permission_status == PermissionStatus.PROHIBITED_WITHOUT_PERMISSION
    assert ai.is_permitted_for_network_collection is False
    assert ai.acquisition_method == AcquisitionMethod.WEB_SCRAPE.value

    mmt = registry.get("makemytrip")
    assert mmt is not None
    assert mmt.permission_status == PermissionStatus.PROHIBITED_WITHOUT_PERMISSION
    assert mmt.is_permitted_for_network_collection is False

    indigo = registry.get("indigo")
    assert indigo is not None
    assert indigo.permission_status == PermissionStatus.PENDING_FORMAL_REVIEW
    assert indigo.is_permitted_for_network_collection is False

    amadeus = registry.get("amadeus")
    assert amadeus is not None
    assert amadeus.permission_status == PermissionStatus.AVAILABLE_AFTER_FREE_REGISTRATION
    assert amadeus.is_permitted_for_network_collection is True
    assert amadeus.acquisition_method == AcquisitionMethod.API.value

    sim = registry.get("simulator")
    assert sim is not None
    assert sim.permission_status == PermissionStatus.NON_EMPIRICAL

    as_dict = registry.to_dict()
    assert as_dict["registry_version"] == "1.0.0"
    assert any(s["source_id"] == "air_india" for s in as_dict["sources"])


# ═══════════════════════════════════════════════════════════
# 3. DATABASE PERSISTENCE & PARTITIONING
# ═══════════════════════════════════════════════════════════

def test_db_persistence_and_rehydration_of_acquisition_method():
    async def _test():
        db = get_database()
        await db.create_schema()
        session = db.session()

        obs_time = datetime.now(timezone.utc)
        obs = FareObservation(
            route_id=1,
            origin_code="DEL",
            destination_code="BOM",
            departure_date=date(2026, 9, 20),
            booking_horizon_days=15,
            airline_code="AI",
            airline_name="Air India",
            cabin_class="ECONOMY",
            flight_number="AI-101",
            fare_total=4500.00,
            provenance=DataProvenance.for_api(
                source_name="amadeus",
                source_url="https://test.api.amadeus.com/v2/shopping/flight-offers",
                timestamp=obs_time,
                request_id="req-persist-1",
            ),
        )

        val_res = ValidationResult(is_valid=True, action=ValidationAction.ACCEPTED, flags=())
        row = repo._observation_row(obs, run_db_id=1, result=val_res)
        assert row.acquisition_method == AcquisitionMethod.API.value
        session.add(row)
        await session.commit()

        # Rehydrate
        stmt = select(FareObservationRecord).where(FareObservationRecord.request_id == "req-persist-1")
        result = await session.execute(stmt)
        saved = result.scalar_one()
        assert saved.acquisition_method == AcquisitionMethod.API.value

        rehydrated = repo.record_to_observation(saved)
        assert rehydrated.acquisition_method == AcquisitionMethod.API

        # Observation stats breakdown
        counts = await repo.count_observations_by_acquisition_method(session)
        assert counts[AcquisitionMethod.API.value] >= 1

        await session.close()

    asyncio.run(_test())


def test_unique_constraint_and_partitioning_by_acquisition_method():
    async def _test():
        db = get_database()
        await db.create_schema()
        session = db.session()

        test_date = date(2026, 9, 15)

        # Two national indices on the same date and source_type, but differing acquisition_methods:
        row_scrape = {
            "index_date": test_date,
            "booking_horizon": None,
            "index_value": 105.25,
            "source_type": SourceType.LIVE.value,
            "acquisition_method": AcquisitionMethod.WEB_SCRAPE.value,
            "provenance_label": "PORTAL-SCRAPED DATA",
            "methodology_version": METHODOLOGY_VERSION,
            "validation_rules_version": "1.0.0",
            "base_period_label": "2026-09-01 to 2026-09-07",
            "base_period_start": date(2026, 9, 1),
            "base_period_end": date(2026, 9, 7),
            "weight_basket_id": "TEST-BASKET",
            "weight_basket_version": "1.0.0",
            "weighting_method": "passenger_volume",
            "weighting_status": "official",
            "total_observations": 100,
            "routes_included": 10,
            "routes_in_basket": 10,
            "coverage_weight": 1.0,
            "is_publishable": True,
            "mom_status": "not_available",
            "yoy_status": "not_available",
            "seasonal_adjustment": "none",
            "computed_at": datetime.now(timezone.utc),
        }

        row_api = {
            "index_date": test_date,
            "booking_horizon": None,
            "index_value": 103.80,
            "source_type": SourceType.LIVE.value,
            "acquisition_method": AcquisitionMethod.API.value,
            "provenance_label": "API-COLLECTED DATA",
            "methodology_version": METHODOLOGY_VERSION,
            "validation_rules_version": "1.0.0",
            "base_period_label": "2026-09-01 to 2026-09-07",
            "base_period_start": date(2026, 9, 1),
            "base_period_end": date(2026, 9, 7),
            "weight_basket_id": "TEST-BASKET",
            "weight_basket_version": "1.0.0",
            "weighting_method": "passenger_volume",
            "weighting_status": "official",
            "total_observations": 120,
            "routes_included": 10,
            "routes_in_basket": 10,
            "coverage_weight": 1.0,
            "is_publishable": True,
            "mom_status": "not_available",
            "yoy_status": "not_available",
            "seasonal_adjustment": "none",
            "computed_at": datetime.now(timezone.utc),
        }

        await repo.save_national_index(session, row_scrape, revision_reason="initial publication")
        await repo.save_national_index(session, row_api, revision_reason="initial publication")
        await session.commit()

        # Querying with acquisition_method filter isolates the series
        q_scrape = await repo.get_national_index_on(
            session,
            test_date,
            source_type=SourceType.LIVE,
            acquisition_method=AcquisitionMethod.WEB_SCRAPE,
        )
        assert q_scrape is not None
        assert q_scrape.index_value == 105.25

        q_api = await repo.get_national_index_on(
            session,
            test_date,
            source_type=SourceType.LIVE,
            acquisition_method=AcquisitionMethod.API,
        )
        assert q_api is not None
        assert q_api.index_value == 103.80

        await session.close()

    asyncio.run(_test())


# ═══════════════════════════════════════════════════════════
# 4. API SERIALIZATION AND DISPLAY LABELS
# ═══════════════════════════════════════════════════════════

def test_api_display_labels():
    # Portal Scrape
    b_scrape = ser.provenance_block(SourceType.LIVE, AcquisitionMethod.WEB_SCRAPE)
    assert b_scrape["display_label"] == "PORTAL-SCRAPED DATA"
    assert b_scrape["acquisition_method"] == "WEB_SCRAPE"

    # API
    b_api = ser.provenance_block(SourceType.LIVE, AcquisitionMethod.API)
    assert b_api["display_label"] == "API-COLLECTED DATA"
    assert b_api["acquisition_method"] == "API"

    # Simulated
    b_sim = ser.provenance_block(SourceType.SIMULATED, AcquisitionMethod.SIMULATED)
    assert b_sim["display_label"] == "SIMULATED DATA"
    assert b_sim["acquisition_method"] == "SIMULATED"

    # Offline
    b_off = ser.provenance_block(SourceType.OFFLINE, AcquisitionMethod.OFFLINE_FIXTURE)
    assert b_off["display_label"] == "OFFLINE PREVIEW"
    assert b_off["acquisition_method"] == "OFFLINE_FIXTURE"

    # Direct resolution function
    assert resolve_display_label(SourceType.LIVE, acquisition_method=AcquisitionMethod.WEB_SCRAPE) == "PORTAL-SCRAPED DATA"
    assert resolve_display_label(SourceType.LIVE, acquisition_method=AcquisitionMethod.API) == "API-COLLECTED DATA"
