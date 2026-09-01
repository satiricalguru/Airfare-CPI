"""
SIH26056 — Jevons elementary price index: the core arithmetic.

This module holds the formula and its axiomatic guarantees. Product MATCHING —
deciding which observations may legitimately form a price relative — lives in
``engine/matched_jevons.py``, which delegates the arithmetic here so that the
production index and the axiomatic test suite exercise the same code path.

That delegation matters. The audit's finding M1 was that the well-tested
``compute_jevons`` was called only by tests, while production used a ratio of
geometric means that cannot separate price change from product-mix change. Production
now runs through ``compute_jevons``.

Formula:

    I(r,t) = [ prod_i ( p_i,t / p_i,0 ) ] ^ (1/n)

computed in log space for numerical stability:

    ln I(r,t) = (1/n) * sum_i ln( p_i,t / p_i,0 )

Why Jevons rather than Carli or Dutot:

* **Carli** (arithmetic mean of relatives) has a proven upward bias by the AM-GM
  inequality and fails the time-reversal test. The ILO/IMF CPI Manual advises against
  it for elementary aggregates.
* **Dutot** (ratio of arithmetic mean prices) is driven by absolute price level, so on
  a heterogeneous basket the expensive products dominate regardless of their share of
  purchases.
* **Jevons** is scale-invariant, satisfies time reversal, and permits implicit
  substitution. It is the standard recommendation for elementary aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
from loguru import logger


@dataclass
class JevonsResult:
    """Result of a Jevons computation over matched price pairs."""

    route_id: int
    index_date: date
    booking_horizon: Optional[int]  # None = combined across horizons
    jevons_index: float
    observation_count: int
    geometric_mean_price: float
    base_period_start: date
    base_period_end: date
    matched_pairs: int
    unmatched_current: int
    unmatched_base: int

    # Individual log price relatives, retained so uncertainty can be estimated from
    # the observed dispersion rather than assumed (see engine/uncertainty.py).
    log_relatives: tuple[float, ...] = field(default_factory=tuple)
    clipped_relatives: int = 0
    winsorized: bool = False
    base_geometric_mean_price: Optional[float] = None

    @property
    def index_100(self) -> float:
        return self.jevons_index * 100.0


class JevonsIndexCalculator:
    """
    Computes the Jevons elementary index from matched price pairs.

    Safety bounds are applied to price RELATIVES, not to price levels, so an
    intrinsically expensive product is never clipped merely for being expensive —
    only an implausible movement is.
    """

    def __init__(
        self,
        winsorize_lower_pct: float = 1.0,
        winsorize_upper_pct: float = 99.0,
        min_observations: int = 3,
        max_price_relative: float = 10.0,
        min_price_relative: float = 0.1,
    ):
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
        Compute the index from matched arrays.

        Element ``i`` of ``current_prices`` must be the same product as element ``i``
        of ``base_prices``. Returns None when there are too few valid pairs — "not
        computable" is a legitimate answer, and callers must record a missing-data
        reason rather than substitute a value.
        """
        current_prices = np.asarray(current_prices, dtype=float)
        base_prices = np.asarray(base_prices, dtype=float)

        if current_prices.shape != base_prices.shape:
            logger.error(
                f"Route {route_id}: mismatched arrays — current={current_prices.shape}, "
                f"base={base_prices.shape}. Matched-model comparison requires aligned "
                f"pairs."
            )
            return None

        if len(current_prices) < self.min_observations:
            logger.debug(
                f"Route {route_id}: {len(current_prices)} pair(s) < "
                f"{self.min_observations} required"
            )
            return None

        # A non-positive price on either side makes the relative undefined.
        valid_mask = (current_prices > 0) & (base_prices > 0)
        dropped = int(np.sum(~valid_mask))
        current = current_prices[valid_mask]
        base = base_prices[valid_mask]

        if len(current) < self.min_observations:
            logger.debug(
                f"Route {route_id}: {len(current)} valid pair(s) after filtering < "
                f"{self.min_observations} required"
            )
            return None

        relatives = current / base

        clipped = int(
            np.sum((relatives < self.min_price_relative) | (relatives > self.max_price_relative))
        )
        relatives = np.clip(relatives, self.min_price_relative, self.max_price_relative)

        winsorized = False
        if len(relatives) >= 10:
            lower = np.percentile(relatives, self.winsorize_lower_pct)
            upper = np.percentile(relatives, self.winsorize_upper_pct)
            relatives = np.clip(relatives, lower, upper)
            winsorized = True

        log_relatives = np.log(relatives)
        jevons_index = float(np.exp(np.mean(log_relatives)))

        n = len(current)
        logger.debug(
            f"Route {route_id} H={booking_horizon}: Jevons={jevons_index:.4f} n={n}"
        )

        return JevonsResult(
            route_id=route_id,
            index_date=index_date,
            booking_horizon=booking_horizon,
            jevons_index=jevons_index,
            observation_count=n,
            geometric_mean_price=float(np.exp(np.mean(np.log(current)))),
            base_geometric_mean_price=float(np.exp(np.mean(np.log(base)))),
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            matched_pairs=n,
            # Pairs discarded because one side was non-positive.
            unmatched_current=dropped,
            unmatched_base=dropped,
            log_relatives=tuple(float(x) for x in log_relatives),
            clipped_relatives=clipped,
            winsorized=winsorized,
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
        Ratio of geometric means, for use ONLY when product matching is impossible.

        NOT USED IN PRODUCTION, deliberately. This is the method the audit flagged as
        M1: because it compares whatever was sampled now against whatever was sampled
        in the base period, a change in the product mix (a carrier adding a flexible
        fare, a shift toward connecting itineraries) is indistinguishable from a price
        change. It is retained because it is a recognised fallback in the ILO/IMF
        Manual when matched-model tracking is genuinely infeasible, and because the
        test suite compares it against the matched result.

        ``matched_pairs=0`` on the result is the marker that no matching occurred.
        """
        current_prices = np.asarray(current_prices, dtype=float)

        if len(current_prices) < self.min_observations:
            return None

        valid = current_prices[current_prices > 0]
        if len(valid) < self.min_observations:
            return None

        if len(valid) >= 10:
            lower = np.percentile(valid, self.winsorize_lower_pct)
            upper = np.percentile(valid, self.winsorize_upper_pct)
            valid = np.clip(valid, lower, upper)

        if base_geometric_mean <= 0:
            logger.error(
                f"Route {route_id}: invalid base geometric mean {base_geometric_mean}"
            )
            return None

        geo_mean_current = float(np.exp(np.mean(np.log(valid))))
        jevons_index = geo_mean_current / base_geometric_mean

        return JevonsResult(
            route_id=route_id,
            index_date=index_date,
            booking_horizon=booking_horizon,
            jevons_index=float(jevons_index),
            observation_count=len(valid),
            geometric_mean_price=geo_mean_current,
            base_geometric_mean_price=float(base_geometric_mean),
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            # Zero matched pairs: this result carries no product-level matching.
            matched_pairs=0,
            unmatched_current=len(current_prices) - len(valid),
            unmatched_base=0,
            log_relatives=(),
            clipped_relatives=0,
            winsorized=len(valid) >= 10,
        )

    def _winsorize(self, data: np.ndarray) -> np.ndarray:
        """Clip to the configured percentiles."""
        lower = np.percentile(data, self.winsorize_lower_pct)
        upper = np.percentile(data, self.winsorize_upper_pct)
        return np.clip(data, lower, upper)


# ── comparison indices: retained to justify the choice of Jevons, never published ──

class CarliIndex:
    """
    Carli: arithmetic mean of price relatives.

    NOT RECOMMENDED and never published here. Has a proven upward bias (AM-GM
    inequality) and fails the time-reversal test, so a price that rises and returns to
    its starting level leaves Carli above 1. The ILO/IMF CPI Manual advises against it
    for elementary aggregates. Retained so the test suite can demonstrate the bias.
    """

    @staticmethod
    def compute(current_prices: np.ndarray, base_prices: np.ndarray) -> Optional[float]:
        current_prices = np.asarray(current_prices, dtype=float)
        base_prices = np.asarray(base_prices, dtype=float)
        valid = (current_prices > 0) & (base_prices > 0)
        if np.sum(valid) < 3:
            return None
        return float(np.mean(current_prices[valid] / base_prices[valid]))


class DutotIndex:
    """
    Dutot: ratio of arithmetic mean prices.

    NOT RECOMMENDED for airfares and never published here. Sensitive to absolute price
    level, so business-class and long-haul products dominate the index irrespective of
    their share of purchases. Retained for comparison in the test suite.
    """

    @staticmethod
    def compute(current_prices: np.ndarray, base_prices: np.ndarray) -> Optional[float]:
        current_prices = np.asarray(current_prices, dtype=float)
        base_prices = np.asarray(base_prices, dtype=float)
        valid = (current_prices > 0) & (base_prices > 0)
        if np.sum(valid) < 3:
            return None
        mean_base = float(np.mean(base_prices[valid]))
        if mean_base <= 0:
            return None
        return float(np.mean(current_prices[valid])) / mean_base
