"""
SIH26056 — Booking-Horizon Stratification Tests

Tests for advance-purchase horizon stratification, composition stability,
and policy-based weight renormalization.
"""

from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.horizon import (
    CombinedRouteIndex,
    HorizonDefinition,
    HorizonIndexInput,
    HorizonPolicy,
    HorizonWeighting,
    combine_horizon_indices,
    get_horizon_policy,
)


@pytest.fixture
def policy() -> HorizonPolicy:
    return get_horizon_policy()


class TestBookingHorizons:

    def test_policy_loads_valid_horizons_and_weights(self, policy):
        """Horizon policy defines [0, 3, 7, 15, 30] with weights summing to 1.0."""
        assert policy.horizon_days == [0, 3, 7, 15, 30]
        weights = policy.weighting.weights
        assert len(weights) == 5
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_composition_stability(self, policy):
        """
        Composition stability: changing the observation COUNT across horizons
        does NOT change the combined route index if underlying prices are unchanged.
        """
        # Scenario A: Mostly same-day bookings (100 obs on T+0, 10 on T+30)
        # All horizon indices = 1.10 (+10%)
        inputs_a = [
            HorizonIndexInput(booking_horizon=0, index_value=1.10, matched_products=20, observation_count=100),
            HorizonIndexInput(booking_horizon=3, index_value=1.10, matched_products=15, observation_count=50),
            HorizonIndexInput(booking_horizon=7, index_value=1.10, matched_products=15, observation_count=30),
            HorizonIndexInput(booking_horizon=15, index_value=1.10, matched_products=10, observation_count=20),
            HorizonIndexInput(booking_horizon=30, index_value=1.10, matched_products=10, observation_count=10),
        ]
        res_a = combine_horizon_indices(route_id=1, horizon_indices=inputs_a, policy=policy)

        # Scenario B: Mostly 30-day advance bookings (10 obs on T+0, 200 on T+30)
        # All horizon indices still = 1.10 (+10%)
        inputs_b = [
            HorizonIndexInput(booking_horizon=0, index_value=1.10, matched_products=5, observation_count=10),
            HorizonIndexInput(booking_horizon=3, index_value=1.10, matched_products=10, observation_count=20),
            HorizonIndexInput(booking_horizon=7, index_value=1.10, matched_products=15, observation_count=40),
            HorizonIndexInput(booking_horizon=15, index_value=1.10, matched_products=20, observation_count=80),
            HorizonIndexInput(booking_horizon=30, index_value=1.10, matched_products=25, observation_count=200),
        ]
        res_b = combine_horizon_indices(route_id=1, horizon_indices=inputs_b, policy=policy)

        assert abs(res_a.index_value - 1.10) < 1e-9
        assert abs(res_b.index_value - 1.10) < 1e-9
        assert res_a.index_value == pytest.approx(res_b.index_value)

    def test_missing_horizon_renormalization(self, policy):
        """
        When a horizon has insufficient data, remaining present horizons
        have their policy weights renormalized to sum to 1.0.
        """
        # T+0 (w=0.2), T+7 (w=0.2), T+30 (w=0.2) present; T+3, T+15 missing
        inputs = [
            HorizonIndexInput(booking_horizon=0, index_value=1.20, matched_products=10, observation_count=20),
            HorizonIndexInput(booking_horizon=7, index_value=1.00, matched_products=10, observation_count=20),
            HorizonIndexInput(booking_horizon=30, index_value=1.10, matched_products=10, observation_count=20),
        ]
        res = combine_horizon_indices(route_id=1, horizon_indices=inputs, policy=policy)

        assert res.is_publishable is True
        assert res.horizons_included == [0, 7, 30]
        assert res.horizons_missing == [3, 15]

        # Present horizons equal weights (0.2, 0.2, 0.2 -> renormalized to 1/3 each)
        assert abs(sum(res.applied_weights.values()) - 1.0) < 1e-9
        expected = (1.20 + 1.00 + 1.10) / 3.0
        assert res.index_value == pytest.approx(expected)

    def test_insufficient_horizons_suppressed(self, policy):
        """If fewer than min_horizons_for_route_index horizons are present, route is not publishable."""
        # Only 1 horizon present (policy requires at least 2)
        inputs = [
            HorizonIndexInput(booking_horizon=7, index_value=1.05, matched_products=10, observation_count=20),
        ]
        res = combine_horizon_indices(route_id=1, horizon_indices=inputs, policy=policy)
        assert res.is_publishable is False
        assert "insufficient_horizons" in (res.suppression_reason or "")
