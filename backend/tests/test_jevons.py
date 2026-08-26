"""
SIH26056 — Jevons Index Unit Tests

Validates the core statistical computation against known results.
"""

import numpy as np
import pytest
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.jevons import JevonsIndexCalculator, CarliIndex, DutotIndex


@pytest.fixture
def calculator():
    return JevonsIndexCalculator(
        winsorize_lower_pct=1.0,
        winsorize_upper_pct=99.0,
        min_observations=3,
    )


class TestJevonsIndex:
    """Test the Jevons price index computation."""
    
    def test_identical_prices_yield_100(self, calculator):
        """If prices haven't changed, index should be 1.0 (=100 base)."""
        base = np.array([5000.0, 6000.0, 4500.0, 5500.0, 7000.0])
        current = np.array([5000.0, 6000.0, 4500.0, 5500.0, 7000.0])
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert abs(result.jevons_index - 1.0) < 1e-6
    
    def test_uniform_increase(self, calculator):
        """10% uniform increase → index should be 1.10."""
        base = np.array([5000.0, 6000.0, 4500.0, 5500.0, 7000.0])
        current = base * 1.10
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert abs(result.jevons_index - 1.10) < 1e-4
    
    def test_uniform_decrease(self, calculator):
        """15% decrease → index should be 0.85."""
        base = np.array([5000.0, 6000.0, 4500.0, 5500.0])
        current = base * 0.85
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=2,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert abs(result.jevons_index - 0.85) < 1e-4
    
    def test_geometric_mean_property(self, calculator):
        """Jevons should compute geometric mean of price relatives."""
        base = np.array([1000.0, 2000.0, 4000.0])
        current = np.array([1200.0, 1800.0, 4400.0])
        
        # Expected: (1.2 × 0.9 × 1.1)^(1/3)
        expected = (1.2 * 0.9 * 1.1) ** (1/3)
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert abs(result.jevons_index - expected) < 1e-6
    
    def test_time_reversal(self, calculator):
        """Jevons should satisfy the time-reversal test: I(0,t) × I(t,0) = 1."""
        base = np.array([5000.0, 6000.0, 4500.0, 5500.0])
        current = np.array([5500.0, 5800.0, 5000.0, 6000.0])
        
        forward = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        reverse = calculator.compute_jevons(
            current_prices=base,
            base_prices=current,
            route_id=1,
            index_date=date(2026, 8, 1),
            base_period_start=date(2026, 8, 25),
            base_period_end=date(2026, 8, 25),
        )
        
        assert forward is not None and reverse is not None
        product = forward.jevons_index * reverse.jevons_index
        assert abs(product - 1.0) < 1e-6, (
            f"Time reversal failed: {forward.jevons_index:.6f} × "
            f"{reverse.jevons_index:.6f} = {product:.6f}"
        )
    
    def test_insufficient_observations(self, calculator):
        """Should return None when below minimum observations."""
        base = np.array([5000.0, 6000.0])
        current = np.array([5500.0, 6500.0])
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is None
    
    def test_zero_prices_filtered(self, calculator):
        """Zero prices should be filtered out, not crash."""
        base = np.array([5000.0, 0.0, 4500.0, 5500.0, 7000.0])
        current = np.array([5500.0, 6000.0, 0.0, 6000.0, 7500.0])
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert result.jevons_index > 0
    
    def test_extreme_relative_capped(self, calculator):
        """Extreme price relatives should be capped."""
        base = np.array([5000.0, 6000.0, 4500.0, 100.0])  # 100 is suspiciously low
        current = np.array([5500.0, 6500.0, 5000.0, 5000.0])  # 50x jump on last item
        
        result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        # Should be reasonable, not blown up by the 50x outlier
        assert result.jevons_index < 5.0
    
    def test_from_prices_only(self, calculator):
        """Test the ratio-of-geometric-means alternative."""
        current = np.array([5500.0, 6500.0, 5000.0, 6000.0])
        base_geo_mean = np.exp(np.mean(np.log(np.array([5000.0, 6000.0, 4500.0, 5500.0]))))
        
        result = calculator.compute_from_prices_only(
            current_prices=current,
            base_geometric_mean=base_geo_mean,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        assert result is not None
        assert result.jevons_index > 0


class TestCarliVsJevons:
    """Demonstrate why Carli has upward bias vs Jevons."""
    
    def test_carli_upward_bias(self, calculator):
        """Carli should give higher index than Jevons for same data."""
        base = np.array([5000.0, 6000.0, 4500.0, 5500.0, 7000.0])
        # Mix of increases and decreases
        current = np.array([6000.0, 5000.0, 5500.0, 5000.0, 8000.0])
        
        jevons_result = calculator.compute_jevons(
            current_prices=current,
            base_prices=base,
            route_id=1,
            index_date=date(2026, 8, 25),
            base_period_start=date(2026, 8, 1),
            base_period_end=date(2026, 8, 7),
        )
        
        carli_index = CarliIndex.compute(current, base)
        
        assert jevons_result is not None
        assert carli_index is not None
        
        # Carli should be >= Jevons (AM-GM inequality)
        assert carli_index >= jevons_result.jevons_index - 1e-10, (
            f"Carli ({carli_index:.6f}) should be >= Jevons ({jevons_result.jevons_index:.6f})"
        )


class TestDutotIndex:
    """Test the Dutot index for comparison."""
    
    def test_dutot_basic(self):
        base = np.array([5000.0, 6000.0, 4500.0])
        current = np.array([5500.0, 6600.0, 4950.0])
        
        dutot = DutotIndex.compute(current, base)
        assert dutot is not None
        # 10% uniform increase
        assert abs(dutot - 1.10) < 1e-4
