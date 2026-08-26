"""
SIH26056 — Validator Unit Tests

Tests for fare observation validation logic.
"""

import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.validator import FareValidator


@pytest.fixture
def validator():
    return FareValidator(
        min_fare=500.0,
        max_fare=80000.0,
        iqr_multiplier=3.0,
    )


class TestFareValidator:
    
    def test_valid_fare_accepted(self, validator):
        """Normal fare should be accepted."""
        result = validator.validate(
            fare_total=5500.0,
            fare_base=4400.0,
            fare_taxes=1100.0,
            route_id=1,
            airline_code="6E",
            booking_horizon=7,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is True
        assert result.action == "accepted"
    
    def test_zero_fare_excluded(self, validator):
        """Zero fare should be excluded as scrape error."""
        result = validator.validate(
            fare_total=0,
            fare_base=0,
            fare_taxes=0,
            route_id=1,
            airline_code="6E",
            booking_horizon=7,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is False
        assert result.action == "excluded"
        assert "zero_or_negative_fare" in result.flags
    
    def test_negative_fare_excluded(self, validator):
        """Negative fare should be excluded."""
        result = validator.validate(
            fare_total=-500,
            fare_base=None,
            fare_taxes=None,
            route_id=1,
            airline_code="6E",
            booking_horizon=7,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is False
    
    def test_below_minimum_excluded(self, validator):
        """Fare below ₹500 should be excluded."""
        result = validator.validate(
            fare_total=200,
            fare_base=150,
            fare_taxes=50,
            route_id=1,
            airline_code="6E",
            booking_horizon=30,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is False
        assert result.action == "excluded"
    
    def test_above_maximum_excluded(self, validator):
        """Fare above ₹80,000 should be excluded."""
        result = validator.validate(
            fare_total=150000,
            fare_base=120000,
            fare_taxes=30000,
            route_id=1,
            airline_code="AI",
            booking_horizon=0,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is False
        assert result.action == "excluded"
    
    def test_high_tax_ratio_flagged(self, validator):
        """Tax > 50% of total should be flagged."""
        result = validator.validate(
            fare_total=5000,
            fare_base=2000,
            fare_taxes=3000,  # 60% tax
            route_id=1,
            airline_code="6E",
            booking_horizon=7,
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is True  # Flagged, not excluded
        assert "high_tax_ratio" in result.flags
    
    def test_low_sameday_fare_flagged(self, validator):
        """Same-day fare under ₹1500 should be flagged."""
        result = validator.validate(
            fare_total=1200,
            fare_base=900,
            fare_taxes=300,
            route_id=1,
            airline_code="6E",
            booking_horizon=0,  # Same-day
            departure_date=date(2026, 9, 1),
        )
        assert result.is_valid is True
        assert "suspiciously_low_sameday_fare" in result.flags
    
    def test_batch_validation(self, validator):
        """Batch validation should sort into accepted/flagged/excluded."""
        observations = [
            {"fare_total": 5500, "fare_base": 4400, "fare_taxes": 1100,
             "route_id": 1, "airline_code": "6E", "booking_horizon_days": 7,
             "departure_date": "2026-09-01", "cabin_class": "Economy"},
            {"fare_total": 0, "fare_base": 0, "fare_taxes": 0,
             "route_id": 1, "airline_code": "6E", "booking_horizon_days": 7,
             "departure_date": "2026-09-01", "cabin_class": "Economy"},
            {"fare_total": 100, "fare_base": 80, "fare_taxes": 20,
             "route_id": 1, "airline_code": "6E", "booking_horizon_days": 7,
             "departure_date": "2026-09-01", "cabin_class": "Economy"},
        ]
        
        accepted, flagged, excluded = validator.validate_batch(observations)
        assert len(accepted) == 1
        assert len(excluded) == 2  # zero + below minimum
