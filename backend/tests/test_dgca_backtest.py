"""
Unit tests for the DGCA benchmark validation and back-testing engine.
"""

import pytest
from engine.dgca_backtest import DGCABacktestEngine, evaluate_dgca_backtest_sync


def test_dgca_benchmark_loading():
    engine = DGCABacktestEngine()
    assert len(engine.corridor_benchmarks) == 25
    assert len(engine.thirty_day_series) >= 30
    assert "T+1" in engine.horizon_elasticity
    assert "T+45" in engine.horizon_elasticity
    assert engine.national_benchmark["average_domestic_fare_inr"] > 0


def test_dgca_backtest_evaluation_metrics():
    result = evaluate_dgca_backtest_sync()
    assert result.status == "SUCCESS"
    assert result.days_evaluated >= 30
    assert result.pearson_correlation >= 0.85
    assert result.mape_pct <= 5.0
    assert result.rmse_tracking_error >= 0.0
    assert result.meets_statistical_threshold is True
    assert len(result.time_series) >= 30
    assert len(result.sector_comparisons) == 25


def test_dgca_horizon_elasticity_ordering():
    engine = DGCABacktestEngine()
    el = engine.horizon_elasticity
    # Verify dynamic pricing monotonic slope: T+1 > T+7 > T+15 > T+30 > T+45
    assert el["T+1"]["price_multiplier"] > el["T+7"]["price_multiplier"]
    assert el["T+7"]["price_multiplier"] > el["T+15"]["price_multiplier"]
    assert el["T+15"]["price_multiplier"] > el["T+30"]["price_multiplier"]
    assert el["T+30"]["price_multiplier"] > el["T+45"]["price_multiplier"]
