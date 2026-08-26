"""
SIH26056 — Aggregator Unit Tests

Tests for the national CPI aggregation logic.
"""

import numpy as np
import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.jevons import JevonsResult
from engine.aggregator import NationalAggregator, RouteWeight


@pytest.fixture
def sample_weights():
    return [
        RouteWeight(route_id=1, origin_code="DEL", destination_code="BOM", weight=0.40, monthly_pax=1200000),
        RouteWeight(route_id=2, origin_code="DEL", destination_code="BLR", weight=0.35, monthly_pax=950000),
        RouteWeight(route_id=3, origin_code="BOM", destination_code="BLR", weight=0.25, monthly_pax=870000),
    ]


@pytest.fixture
def aggregator(sample_weights):
    return NationalAggregator(sample_weights)


def make_jevons(route_id, index_value):
    """Helper: create a JevonsResult with given index value."""
    return JevonsResult(
        route_id=route_id,
        index_date=date(2026, 8, 25),
        booking_horizon=None,
        jevons_index=index_value,
        observation_count=20,
        geometric_mean_price=5000.0,
        base_period_start=date(2026, 8, 1),
        base_period_end=date(2026, 8, 7),
        matched_pairs=20,
        unmatched_current=0,
        unmatched_base=0,
    )


class TestNationalAggregation:
    
    def test_base_period_equals_100(self, aggregator):
        """If all route indices = 1.0 (no change), CPI should be 100."""
        results = [
            make_jevons(1, 1.0),
            make_jevons(2, 1.0),
            make_jevons(3, 1.0),
        ]
        
        national = aggregator.compute_national_cpi(results)
        assert abs(national.airfare_cpi - 100.0) < 0.01
    
    def test_uniform_10pct_increase(self, aggregator):
        """10% increase on all routes → CPI = 110."""
        results = [
            make_jevons(1, 1.10),
            make_jevons(2, 1.10),
            make_jevons(3, 1.10),
        ]
        
        national = aggregator.compute_national_cpi(results)
        assert abs(national.airfare_cpi - 110.0) < 0.01
    
    def test_weighted_average(self, aggregator):
        """Test that weights are correctly applied."""
        # Route 1 (w=0.40): +20%
        # Route 2 (w=0.35): -5%
        # Route 3 (w=0.25): +10%
        results = [
            make_jevons(1, 1.20),  # w=0.40
            make_jevons(2, 0.95),  # w=0.35
            make_jevons(3, 1.10),  # w=0.25
        ]
        
        # Expected: (0.40×1.20 + 0.35×0.95 + 0.25×1.10) × 100
        expected = (0.40 * 1.20 + 0.35 * 0.95 + 0.25 * 1.10) * 100
        
        national = aggregator.compute_national_cpi(results)
        assert abs(national.airfare_cpi - expected) < 0.5
    
    def test_missing_route_rescaling(self, aggregator):
        """With one route missing, remaining weights should be rescaled."""
        results = [
            make_jevons(1, 1.10),  # w=0.40
            make_jevons(2, 1.10),  # w=0.35
            # Route 3 missing
        ]
        
        national = aggregator.compute_national_cpi(results)
        # Should still compute, rescaled to available routes
        assert national.airfare_cpi > 0
        assert national.routes_included == 2
        assert 3 in national.missing_routes
    
    def test_contributions_sum_to_100(self, aggregator):
        """Route contributions should sum to ~100%."""
        results = [
            make_jevons(1, 1.15),
            make_jevons(2, 0.90),
            make_jevons(3, 1.05),
        ]
        
        national = aggregator.compute_national_cpi(results)
        total_pct = sum(c.contribution_pct for c in national.route_contributions)
        assert abs(total_pct - 100.0) < 0.1
    
    def test_mom_change_calculation(self, aggregator):
        """Month-on-month change should be computed correctly."""
        results = [
            make_jevons(1, 1.10),
            make_jevons(2, 1.10),
            make_jevons(3, 1.10),
        ]
        
        # Previous CPI: 1.05 (scaled back from 105)
        national = aggregator.compute_national_cpi(
            results,
            previous_cpi=1.05,  # ratio form
        )
        
        # MoM should be ~(110/105 - 1)×100 ≈ 4.76%
        assert national.mom_change_pct is not None
        assert abs(national.mom_change_pct - 4.76) < 0.5
    
    def test_empty_indices_raises(self, aggregator):
        """Should raise when no route indices provided."""
        with pytest.raises(ValueError):
            aggregator.compute_national_cpi([])
    
    def test_decompose_change(self, aggregator):
        """Test change decomposition between two periods."""
        prev_results = [
            make_jevons(1, 1.00),
            make_jevons(2, 1.00),
            make_jevons(3, 1.00),
        ]
        curr_results = [
            make_jevons(1, 1.10),
            make_jevons(2, 0.95),
            make_jevons(3, 1.05),
        ]
        
        prev_national = aggregator.compute_national_cpi(prev_results)
        curr_national = aggregator.compute_national_cpi(curr_results)
        
        decomp = aggregator.decompose_change(curr_national, prev_national)
        assert len(decomp) == 3
        
        # Route 1 should be the largest contributor (highest weight + biggest change)
        assert decomp[0]["route_id"] == 1
