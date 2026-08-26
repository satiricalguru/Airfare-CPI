"""
SIH26056 — Jevons Price Index Calculator

Computes route-level elementary price indices using the Jevons formula
(geometric mean of price relatives), as recommended by the ILO/IMF
Consumer Price Index Manual for elementary aggregates.

Formula:
    I(r,t) = [Π (pᵢ,t / pᵢ,₀)]^(1/n)

Where:
    - pᵢ,t  = fare observation i in current period t
    - pᵢ,₀  = matched fare observation i in base period 0
    - n      = number of matched observations

Why Jevons:
    - Geometric mean allows implicit substitution → lower bias than Carli
    - Satisfies the time-reversal test (Carli does not)
    - Less sensitive to extreme airfare observations than arithmetic mean
    - Recommended by ILO, IMF, Statistics Canada, UK ONS, ABS for elementary CPI
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional
from datetime import date
from loguru import logger


@dataclass
class JevonsResult:
    """Result of a Jevons index computation."""
    route_id: int
    index_date: date
    booking_horizon: Optional[int]  # None = combined across all horizons
    jevons_index: float
    observation_count: int
    geometric_mean_price: float
    base_period_start: date
    base_period_end: date
    matched_pairs: int              # Number of successfully matched price pairs
    unmatched_current: int          # Current-period obs without base match
    unmatched_base: int             # Base-period obs without current match


class JevonsIndexCalculator:
    """
    Computes the Jevons elementary price index for a route.
    
    The Jevons index is the geometric mean of price relatives.
    For matched observations between base and current period:
    
        I(r,t) = [Π (pᵢ,t / pᵢ,₀)]^(1/n)
    
    Equivalently (using log-space for numerical stability):
    
        ln I(r,t) = (1/n) × Σ ln(pᵢ,t / pᵢ,₀)
    """
    
    def __init__(
        self,
        winsorize_lower_pct: float = 1.0,
        winsorize_upper_pct: float = 99.0,
        min_observations: int = 3,
        max_price_relative: float = 10.0,  # Cap individual price relatives at 10x
        min_price_relative: float = 0.1,   # Floor at 0.1x
    ):
        """
        Args:
            winsorize_lower_pct: Lower percentile for Winsorization
            winsorize_upper_pct: Upper percentile for Winsorization  
            min_observations: Minimum obs required for valid index
            max_price_relative: Maximum allowed price relative (safety cap)
            min_price_relative: Minimum allowed price relative (safety floor)
        """
        self.winsorize_lower_pct = winsorize_lower_pct
        self.winsorize_upper_pct = winsorize_upper_pct
        self.min_observations = min_observations
        self.max_price_relative = max_price_relative
        self.min_price_relative = min_price_relative
    
    def compute_jevons(
        self,
        current_prices: np.ndarray,
        base_prices: np.ndarray,
        route_id: int,
        index_date: date,
        base_period_start: date,
        base_period_end: date,
        booking_horizon: Optional[int] = None,
    ) -> Optional[JevonsResult]:
        """
        Compute the Jevons index from matched current and base prices.
        
        Both arrays must be the same length, with element i in current_prices
        corresponding to element i in base_prices (matched pair).
        
        Args:
            current_prices: Array of current-period fares (matched)
            base_prices: Array of base-period fares (matched)
            route_id: Route identifier
            index_date: Date of the current index computation
            base_period_start: Start of base period
            base_period_end: End of base period
            booking_horizon: Booking horizon (None for combined)
            
        Returns:
            JevonsResult or None if insufficient data
        """
        if len(current_prices) != len(base_prices):
            logger.error(
                f"Route {route_id}: Mismatched arrays — "
                f"current={len(current_prices)}, base={len(base_prices)}"
            )
            return None
        
        if len(current_prices) < self.min_observations:
            logger.warning(
                f"Route {route_id}: Insufficient observations "
                f"({len(current_prices)} < {self.min_observations})"
            )
            return None
        
        # Filter out zero or negative prices (invalid)
        valid_mask = (current_prices > 0) & (base_prices > 0)
        current = current_prices[valid_mask]
        base = base_prices[valid_mask]
        
        if len(current) < self.min_observations:
            logger.warning(
                f"Route {route_id}: Insufficient valid observations after filtering "
                f"({len(current)} < {self.min_observations})"
            )
            return None
        
        # Compute price relatives
        price_relatives = current / base
        
        # Cap extreme price relatives (safety guard)
        price_relatives = np.clip(
            price_relatives,
            self.min_price_relative,
            self.max_price_relative
        )
        
        # Optional: Winsorize price relatives for robustness
        if len(price_relatives) >= 10:
            price_relatives = self._winsorize(price_relatives)
        
        # Jevons Index = geometric mean of price relatives
        # Computed in log-space for numerical stability:
        #   ln(I) = (1/n) × Σ ln(pᵢ,t / pᵢ,₀)
        #   I = exp(mean(ln(price_relatives)))
        log_relatives = np.log(price_relatives)
        log_jevons = np.mean(log_relatives)
        jevons_index = np.exp(log_jevons)
        
        # Geometric mean of current prices (for reference)
        geo_mean_price = np.exp(np.mean(np.log(current)))
        
        n = len(current)
        
        logger.info(
            f"Route {route_id} | Horizon={booking_horizon} | "
            f"Jevons={jevons_index:.4f} | n={n} | "
            f"GeoMean=₹{geo_mean_price:.0f}"
        )
        
        return JevonsResult(
            route_id=route_id,
            index_date=index_date,
            booking_horizon=booking_horizon,
            jevons_index=float(jevons_index),
            observation_count=n,
            geometric_mean_price=float(geo_mean_price),
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            matched_pairs=n,
            unmatched_current=int(np.sum(~valid_mask[:len(current_prices)])),
            unmatched_base=0,
        )
    
    def compute_from_prices_only(
        self,
        current_prices: np.ndarray,
        base_geometric_mean: float,
        route_id: int,
        index_date: date,
        base_period_start: date,
        base_period_end: date,
        booking_horizon: Optional[int] = None,
    ) -> Optional[JevonsResult]:
        """
        Alternative computation when individual matching isn't possible.
        Uses the ratio of geometric means:
        
            I(r,t) = geometric_mean(current_prices) / geometric_mean(base_prices)
        
        This is equivalent to Jevons when the same items appear in both periods
        but pairing is not feasible (e.g., different flight numbers).
        
        The ILO/IMF Manual notes this is an acceptable alternative for
        elementary aggregates where matched-model tracking isn't practical.
        """
        if len(current_prices) < self.min_observations:
            return None
        
        # Filter valid prices
        valid = current_prices[current_prices > 0]
        if len(valid) < self.min_observations:
            return None
        
        # Winsorize if enough observations
        if len(valid) >= 10:
            valid = self._winsorize(valid)
        
        # Geometric mean of current prices
        geo_mean_current = np.exp(np.mean(np.log(valid)))
        
        # Index = ratio of geometric means
        if base_geometric_mean <= 0:
            logger.error(f"Route {route_id}: Invalid base geometric mean: {base_geometric_mean}")
            return None
        
        jevons_index = geo_mean_current / base_geometric_mean
        
        logger.info(
            f"Route {route_id} | Horizon={booking_horizon} | "
            f"Jevons (ratio)={jevons_index:.4f} | n={len(valid)} | "
            f"GeoMean=₹{geo_mean_current:.0f} / ₹{base_geometric_mean:.0f}"
        )
        
        return JevonsResult(
            route_id=route_id,
            index_date=index_date,
            booking_horizon=booking_horizon,
            jevons_index=float(jevons_index),
            observation_count=len(valid),
            geometric_mean_price=float(geo_mean_current),
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            matched_pairs=0,
            unmatched_current=len(current_prices) - len(valid),
            unmatched_base=0,
        )
    
    def _winsorize(self, data: np.ndarray) -> np.ndarray:
        """
        Winsorize data at the configured percentiles.
        Replaces values below/above thresholds with the threshold value.
        Preserves genuine market movements while limiting extreme outliers.
        """
        lower = np.percentile(data, self.winsorize_lower_pct)
        upper = np.percentile(data, self.winsorize_upper_pct)
        return np.clip(data, lower, upper)


# ============================================================
# Comparison: Why not Carli or Dutot?
# ============================================================
class CarliIndex:
    """
    Carli index: arithmetic mean of price relatives.
    
    I = (1/n) × Σ (pᵢ,t / pᵢ,₀)
    
    NOT RECOMMENDED — included only for comparison/validation.
    Known to have upward bias (fails time-reversal test).
    ILO/IMF CPI Manual explicitly warns against using Carli.
    """
    
    @staticmethod
    def compute(current_prices: np.ndarray, base_prices: np.ndarray) -> Optional[float]:
        valid = (current_prices > 0) & (base_prices > 0)
        if np.sum(valid) < 3:
            return None
        relatives = current_prices[valid] / base_prices[valid]
        return float(np.mean(relatives))


class DutotIndex:
    """
    Dutot index: ratio of arithmetic means.
    
    I = mean(pᵢ,t) / mean(pᵢ,₀)
    
    NOT RECOMMENDED for heterogeneous products like airfares.
    Sensitive to the level of prices — inappropriate when products 
    differ in quality (direct vs connecting, business vs economy).
    """
    
    @staticmethod
    def compute(current_prices: np.ndarray, base_prices: np.ndarray) -> Optional[float]:
        valid = (current_prices > 0) & (base_prices > 0)
        if np.sum(valid) < 3:
            return None
        mean_current = np.mean(current_prices[valid])
        mean_base = np.mean(base_prices[valid])
        if mean_base <= 0:
            return None
        return float(mean_current / mean_base)
