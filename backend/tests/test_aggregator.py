"""
SIH26056 — Aggregator Unit Tests

Tests for the national CPI aggregation logic using RouteBasket and RouteIndexInput.
"""

from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.aggregator import (
    NationalAggregator,
    RouteContribution,
    RouteIndexInput,
)
from engine.weights import Route, RouteBasket, WeightingMethodology


@pytest.fixture
def sample_basket() -> RouteBasket:
    routes = (
        Route(
            route_id=1,
            origin_code="DEL",
            destination_code="BOM",
            origin_city="Delhi",
            destination_city="Mumbai",
            monthly_pax=1200000,
            weight=0.40,
        ),
        Route(
            route_id=2,
            origin_code="DEL",
            destination_code="BLR",
            origin_city="Delhi",
            destination_city="Bengaluru",
            monthly_pax=1050000,
            weight=0.35,
        ),
        Route(
            route_id=3,
            origin_code="BOM",
            destination_code="BLR",
            origin_city="Mumbai",
            destination_city="Bengaluru",
            monthly_pax=750000,
            weight=0.25,
        ),
    )
    methodology = WeightingMethodology(
        method="passenger_volume",
        status="PROVISIONAL",
        formula="w_r = pax_r / sum(pax)",
        label="DGCA Monthly Passenger Volume",
        is_official_cpi_expenditure_weight=False,
    )
    return RouteBasket(
        basket_id="test_basket",
        basket_version="1.0.0",
        effective_from="2026-01-01",
        currency="INR",
        routes=routes,
        methodology=methodology,
    )


@pytest.fixture
def aggregator(sample_basket) -> NationalAggregator:
    return NationalAggregator(basket=sample_basket, min_coverage_weight=0.50)


def make_route_input(route_id: int, index_value: float, obs_count: int = 20, matched: int = 15) -> RouteIndexInput:
    """Helper: create a RouteIndexInput with given ratio-form index value."""
    return RouteIndexInput(
        route_id=route_id,
        index_value=index_value,
        matched_products=matched,
        observation_count=obs_count,
        horizons_included=[0, 3, 7, 15, 30],
    )


class TestNationalAggregation:

    def test_base_period_equals_100(self, aggregator):
        """If all route indices = 1.0 (no change), national index should be 100.0."""
        inputs = [
            make_route_input(1, 1.0),
            make_route_input(2, 1.0),
            make_route_input(3, 1.0),
        ]
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert abs(res.index_value - 100.0) < 0.01
        assert res.is_publishable is True
        assert res.routes_included == 3
        assert len(res.missing_routes) == 0

    def test_uniform_10pct_increase(self, aggregator):
        """10% increase on all routes → national index = 110.0."""
        inputs = [
            make_route_input(1, 1.10),
            make_route_input(2, 1.10),
            make_route_input(3, 1.10),
        ]
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert abs(res.index_value - 110.0) < 0.01

    def test_weighted_average(self, aggregator):
        """Test that route weights are correctly applied."""
        # Route 1 (w=0.40): +20% -> 1.20
        # Route 2 (w=0.35): -5%  -> 0.95
        # Route 3 (w=0.25): +10% -> 1.10
        inputs = [
            make_route_input(1, 1.20),
            make_route_input(2, 0.95),
            make_route_input(3, 1.10),
        ]
        expected = (0.40 * 1.20 + 0.35 * 0.95 + 0.25 * 1.10) * 100.0

        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert abs(res.index_value - expected) < 0.01

    def test_missing_route_renormalization(self, aggregator):
        """With Route 3 missing (w=0.25), remaining weights (0.40, 0.35 -> sum 0.75) are renormalized."""
        inputs = [
            make_route_input(1, 1.10),  # w=0.40
            make_route_input(2, 1.10),  # w=0.35
            # Route 3 missing
        ]
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert res.routes_included == 2
        assert len(res.missing_routes) == 1
        assert res.missing_routes[0].route_id == 3
        assert res.renormalization_applied is True
        assert abs(res.coverage_weight - 0.75) < 1e-6
        # Both remaining routes are 1.10, so renormalized index should still be 110.0
        assert abs(res.index_value - 110.0) < 0.01
        assert res.is_publishable is True

    def test_insufficient_coverage_marks_not_publishable(self, aggregator):
        """If coverage is below min_coverage_weight, is_publishable is False."""
        # Only Route 3 present: coverage 0.25 < min_coverage 0.50
        inputs = [make_route_input(3, 1.05)]
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert res.is_publishable is False
        assert res.suppression_reason is not None

    def test_contributions_sum_to_100(self, aggregator):
        """Route contributions should sum to 100% of weighted sum."""
        inputs = [
            make_route_input(1, 1.15),
            make_route_input(2, 0.90),
            make_route_input(3, 1.05),
        ]
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        total_pct = sum(c.contribution_pct for c in res.route_contributions)
        assert abs(total_pct - 100.0) < 0.01

    def test_mom_change_calculation(self, aggregator):
        """Month-on-month change should be computed against previous index on base=100 scale."""
        inputs = [
            make_route_input(1, 1.10),
            make_route_input(2, 1.10),
            make_route_input(3, 1.10),
        ]
        # Current index = 110.0. Previous index = 105.0
        res = aggregator.aggregate(
            route_indices=inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
            previous_index=105.0,
        )
        # MoM = (110.0 - 105.0) / 105.0 * 100 = 4.7619%
        assert res.mom_change_pct is not None
        assert abs(res.mom_change_pct - 4.7619) < 0.01
        assert res.mom_status == "available"

    def test_empty_route_indices_returns_suppressed_result(self, aggregator):
        """Empty input should return an honest non-computable result, not raise or invent values."""
        res = aggregator.aggregate(
            route_indices=[],
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        assert res.index_value == 0.0
        assert res.routes_included == 0
        assert res.is_publishable is False
        assert len(res.missing_routes) == 3

    def test_decompose_change(self, aggregator):
        """Test change decomposition between two periods."""
        prev_inputs = [
            make_route_input(1, 1.00),
            make_route_input(2, 1.00),
            make_route_input(3, 1.00),
        ]
        curr_inputs = [
            make_route_input(1, 1.10),  # +10%, w=0.40 -> +4.0 pts
            make_route_input(2, 0.95),  # -5%,  w=0.35 -> -1.75 pts
            make_route_input(3, 1.05),  # +5%,  w=0.25 -> +1.25 pts
        ]
        prev_res = aggregator.aggregate(
            route_indices=prev_inputs,
            index_date=date(2026, 7, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        curr_res = aggregator.aggregate(
            route_indices=curr_inputs,
            index_date=date(2026, 8, 25),
            base_period_label="2026-08-01 to 2026-08-07",
        )
        decomp = aggregator.decompose_change(curr_res, prev_res)
        assert len(decomp) == 3
        # Route 1 has the largest absolute contribution to change (4.0 pts)
        assert decomp[0]["route_id"] == 1
        assert abs(decomp[0]["contribution_to_change_points"] - 4.0) < 0.01
