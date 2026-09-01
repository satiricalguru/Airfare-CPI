"""
SIH26056 — Validator Unit Tests

Tests for fare observation validation logic.
Updated to test the current FareValidator and FareObservation models.
"""

from datetime import date, datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ValidationSettings
from provenance import DataProvenance, SourceType, new_request_id
from scraper.base import CABIN_ECONOMY, FareObservation
from scraper.validator import FareValidator, ValidationAction


def _settings(**overrides) -> ValidationSettings:
    """Build a ValidationSettings with test defaults."""
    defaults = dict(
        min_fare_inr=500.0,
        max_fare_inr=80000.0,
        iqr_multiplier=3.0,
        max_daily_change_pct=300.0,
        min_observations_for_iqr=10,
        route_history_window=500,
    )
    defaults.update(overrides)
    return ValidationSettings(**defaults)


def _obs(
    fare: float,
    route_id: int = 1,
    horizon: int = 7,
    departure: str = "2026-09-01",
    fare_base: float | None = None,
    fare_taxes: float | None = None,
    collection_ts: str = "2026-08-15T10:00:00+00:00",
) -> FareObservation:
    """Build a FareObservation for testing."""
    prov = DataProvenance(
        source_type=SourceType.SIMULATED,
        source_name="test_fixture",
        collection_timestamp=datetime.fromisoformat(collection_ts),
        request_id=new_request_id(),
    )
    return FareObservation(
        route_id=route_id,
        origin_code="DEL",
        destination_code="BOM",
        departure_date=date.fromisoformat(departure),
        booking_horizon_days=horizon,
        airline_code="6E",
        airline_name="IndiGo",
        cabin_class=CABIN_ECONOMY,
        fare_total=fare,
        fare_base=fare_base if fare_base is not None else round(fare * 0.8, 2),
        fare_taxes=fare_taxes if fare_taxes is not None else round(fare * 0.2, 2),
        currency="INR",
        provenance=prov,
    )


@pytest.fixture
def validator():
    return FareValidator(settings=_settings())


class TestFareValidator:

    def test_valid_fare_accepted(self, validator):
        """Normal fare should be accepted."""
        result = validator.validate(_obs(5500.0))
        assert result.is_valid is True
        assert result.action is ValidationAction.ACCEPTED

    def test_zero_or_negative_fare_rejected_at_construction(self):
        """Zero or negative fare cannot even form a FareObservation."""
        with pytest.raises(ValueError, match="must be positive"):
            _obs(0)
        with pytest.raises(ValueError, match="must be positive"):
            _obs(-500)

    def test_below_minimum_excluded(self, validator):
        """Fare below ₹500 should be excluded."""
        result = validator.validate(_obs(200.0))
        assert result.is_valid is False
        assert result.action is ValidationAction.EXCLUDED
        assert any("below_minimum_fare" in f for f in result.flags)

    def test_above_maximum_excluded(self, validator):
        """Fare above ₹80,000 should be excluded."""
        result = validator.validate(_obs(150000.0))
        assert result.is_valid is False
        assert result.action is ValidationAction.EXCLUDED
        assert any("above_maximum_fare" in f for f in result.flags)

    def test_high_tax_ratio_flagged(self, validator):
        """Tax > 50% of total should be flagged."""
        result = validator.validate(_obs(5000.0, fare_base=2000.0, fare_taxes=3000.0))
        assert result.is_valid is True
        assert result.action is ValidationAction.FLAGGED
        assert "high_tax_ratio" in result.flags

    def test_low_sameday_fare_flagged(self, validator):
        """Same-day fare under ₹1500 should be flagged."""
        result = validator.validate(_obs(1200.0, horizon=0))
        assert result.is_valid is True
        assert result.action is ValidationAction.FLAGGED
        assert "suspiciously_low_same_day_fare" in result.flags

    def test_batch_validation(self, validator):
        """Batch validation should sort into accepted/flagged/excluded."""
        observations = [
            _obs(5500.0),           # valid / accepted
            _obs(200.0),            # excluded: below min (500)
            _obs(95000.0),          # excluded: above max (80000)
            _obs(1200.0, horizon=0), # flagged: low same-day fare
        ]
        batch_result = validator.validate_batch(observations)
        assert len(batch_result.accepted) == 1
        assert len(batch_result.flagged) == 1
        assert len(batch_result.excluded) == 2
