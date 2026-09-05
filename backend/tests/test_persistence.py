"""
SIH26056 — Database Persistence & Reproducibility Tests

Tests that:
1. Observations and collection runs survive a database session cycle.
2. Published indices are stored and can be re-queried without recomputation.
3. Validator state is persisted and continuous across process restarts.
"""

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DatabaseSettings
from db import repository as repo
from db.engine import Database
from engine.weights import get_route_basket
from provenance import (
    COLLECTOR_VERSION,
    CollectionMode,
    CollectionStatus,
    DataProvenance,
    SourceType,
    new_request_id,
    utc_now,
)
from scraper.base import CABIN_ECONOMY, FareObservation
from scraper.pipeline import CollectionRunResult
from scraper.validator import (
    FareValidator,
    ValidationAction,
    ValidationBatchResult,
    ValidationResult,
)


@pytest.fixture
def test_db(tmp_path):
    """Provide a fresh SQLite test database."""
    db_file = tmp_path / "test_airfare.db"
    settings = DatabaseSettings(url=f"sqlite+aiosqlite:///{db_file}")
    db = Database(settings=settings)
    asyncio.run(db.create_schema())
    yield db
    asyncio.run(db.close())


def _obs(route_id: int = 1, horizon: int = 7, fare: float = 5200.0) -> FareObservation:
    prov = DataProvenance(
        source_type=SourceType.SIMULATED,
        source_name="test_fixture",
        collection_timestamp=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
        request_id=new_request_id(),
    )
    return FareObservation(
        route_id=route_id,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=date(2026, 8, 22),
        booking_horizon_days=horizon,
        airline_code="6E",
        cabin_class=CABIN_ECONOMY,
        fare_total=fare,
        currency="INR",
        provenance=prov,
    )


class TestPersistence:

    def test_unchanged_national_recomputation_does_not_create_false_revision(self, test_db):
        """Only an actual published-value change belongs in the append-only log."""
        async def _test():
            row = {
                "index_date": date(2026, 8, 15),
                "booking_horizon": None,
                "index_value": 100.0,
                "routes_included": 3,
                "routes_in_basket": 25,
                "total_observations": 30,
                "total_matched_products": 12,
                "coverage_weight": 0.4,
                "renormalization_applied": True,
                "is_publishable": False,
                "suppression_reason": "coverage below release threshold",
                "mom_change_pct": None,
                "mom_status": "insufficient_history",
                "yoy_change_pct": None,
                "yoy_status": "insufficient_history",
                "standard_error": None,
                "confidence_interval_low": None,
                "confidence_interval_high": None,
                "uncertainty_basis": "not estimable",
                "seasonal_adjustment": "NOT IMPLEMENTED",
                "base_period_start": date(2026, 8, 1),
                "base_period_end": date(2026, 8, 7),
                "base_period_label": "2026-08-01 to 2026-08-07",
                "weight_basket_id": "test-basket",
                "weight_basket_version": "test-v1",
                "weighting_method": "passenger_volume_proxy",
                "weighting_status": "PROVISIONAL",
                "source_type": SourceType.SIMULATED.value,
                "provenance_label": "SIMULATED DATA",
                "methodology_version": "test-methodology",
                "validation_rules_version": "test-validation",
                "computed_at": utc_now(),
                "contributing_run_ids": [],
                "route_contributions": [],
                "missing_routes": [],
            }

            async with test_db.session_scope() as session:
                await repo.save_national_index(session, row, "initial computation")

            # A fresh timestamp alone must not become a statistical revision.
            unchanged = {**row, "computed_at": row["computed_at"] + timedelta(minutes=5)}
            async with test_db.session_scope() as session:
                await repo.save_national_index(session, unchanged, "no-op recomputation")

            async with test_db.session() as session:
                assert len(await repo.list_revisions(session, limit=10)) == 1

            changed = {**unchanged, "index_value": 101.0}
            async with test_db.session_scope() as session:
                await repo.save_national_index(session, changed, "late verified data")

            async with test_db.session() as session:
                revisions = await repo.list_revisions(session, limit=10)
                assert len(revisions) == 2
                assert revisions[0].reason == "late verified data"
                assert revisions[0].previous_value == pytest.approx(100.0)
                assert revisions[0].new_value == pytest.approx(101.0)

        asyncio.run(_test())

    def test_collection_run_and_observations_persist(self, test_db):
        """Observations and collection runs are saved and queryable."""
        async def _test():
            obs1 = _obs(route_id=1, fare=5000.0)
            obs2 = _obs(route_id=2, fare=6000.0)

            run_result = CollectionRunResult(
                run_id="test-run-001",
                mode=CollectionMode.SIMULATED,
                status=CollectionStatus.SIMULATED,
                started_at=datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 8, 15, 10, 1, tzinfo=timezone.utc),
                collection_day=date(2026, 8, 15),
                observations=(obs1, obs2),
                routes_requested=2,
                routes_with_data=2,
            )

            val_batch = ValidationBatchResult(
                accepted=[obs1, obs2],
                flagged=[],
                excluded=[],
                results=[
                    ValidationResult(action=ValidationAction.ACCEPTED, is_valid=True),
                    ValidationResult(action=ValidationAction.ACCEPTED, is_valid=True),
                ],
            )
            val_batch.evaluated = list(zip(val_batch.accepted, val_batch.results))

            async with test_db.session_scope() as session:
                run_record = await repo.save_collection_run(
                    session=session,
                    run=run_result,
                    validation=val_batch,
                )
                assert run_record.run_db_id > 0
                assert run_record.observations_persisted == 2

            # Query in a new session (reproducing a new request / restart)
            async with test_db.session() as session:
                stats = await repo.observation_stats(session)
                assert stats["total_observations"] == 2
                assert stats["valid_observations"] == 2
                assert stats["mean_fare"] == pytest.approx(5500.0)
                assert stats["min_fare"] == pytest.approx(5000.0)
                assert stats["max_fare"] == pytest.approx(6000.0)
                assert stats["routes_covered"] == 2
                assert stats["median_fare"] is None
                assert stats["median_status"] == "not_computed"

                runs = await repo.list_collection_runs(session)
                assert len(runs) == 1
                assert runs[0].run_id == "test-run-001"
                assert runs[0].mode == "SIMULATED"

        asyncio.run(_test())

    def test_validator_state_roundtrip(self, test_db):
        """Validator state survives serialization to DB and restoration."""
        async def _test():
            validator = FareValidator()
            # Feed some observations to build distributions
            obs = [_obs(route_id=1, horizon=7, fare=5000.0 + i * 100) for i in range(15)]
            validator.validate_batch(obs)

            exported = validator.export_state()
            assert "stats" in exported
            assert len(exported["stats"]) > 0

            # Save state
            async with test_db.session_scope() as session:
                await repo.save_validator_state(session, exported)

            # Load state in new validator
            async with test_db.session() as session:
                loaded_state = await repo.load_validator_state(session)
                assert loaded_state is not None

            new_validator = FareValidator()
            new_validator.restore_state(loaded_state)

            # Assert reference distributions were restored
            key = (1, 7)
            assert key in new_validator._stats
            assert new_validator._stats[key].count == 15

        asyncio.run(_test())
