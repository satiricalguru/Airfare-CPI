"""
SIH26056 — Matched-model Jevons elementary index.

This is what the production pipeline uses. The previous production path computed a
ratio of geometric means over whatever fares happened to be present in each period,
which cannot distinguish a price change from a change in WHAT was sampled. If a route
starts selling more flexible fares, or a carrier adds a premium product, that reads
as inflation.

Matched-model fixes it by pairing each product with itself:

    I(t) = geometric_mean over matched products p of ( price_p(t) / price_p(0) )

A product is identified by :meth:`FareObservation.product_key`: origin, destination,
airline, flight number, cabin, fare family, stops, refundability, baggage allowance,
and booking horizon. Two observations only form a price relative when they describe
the same repeatable service specification.

Product churn
-------------
Real markets add and drop products constantly, so the unmatched cases are handled
explicitly rather than ignored:

* **New product** (present now, absent in base) — excluded from this period's index.
  A new product has no base price, so any relative for it would be invented. It
  becomes matchable once it exists in a future base. Counted and reported.
* **Disappeared product** (in base, absent now) — excluded, and counted. Its
  contribution simply leaves the matched set; no last-known price is carried forward,
  because a carried-forward price asserts a price that was not observed.
* **Temporarily unavailable** — indistinguishable from disappeared within a single
  period, so treated identically. Whether it was temporary is only knowable later,
  and :attr:`MatchedJevonsResult.reappeared_products` reports products that return.
* **Fare-family change** — a different fare family is a different product key, so it
  appears as one product disappearing and another arriving. This is deliberate: a
  fare-family substitution is a quality change, not a price change.
* **Route change** — a different origin/destination is a different product key, so
  route substitution can never be read as a price movement.

Elementary aggregate formula, computed in log space for numerical stability:

    ln I(t) = (1/n) * sum_p ln( price_p(t) / price_p(0) )
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Optional

import numpy as np
from loguru import logger

from config import IndexSettings, get_settings
from engine.jevons import JevonsIndexCalculator
from scraper.base import FareObservation


@dataclass(frozen=True)
class ProductPrice:
    """A product's representative price in one period."""

    product_key: str
    price: float
    observation_count: int

    @property
    def is_usable(self) -> bool:
        return self.price > 0


@dataclass
class MatchedJevonsResult:
    """
    Result of a matched-model Jevons computation for one route and horizon.

    Carries the full matching diagnostics because they are what makes the figure
    defensible: a reader can see how many products matched, how many churned, and how
    much of the base sample was retained.
    """

    route_id: int
    index_date: date
    booking_horizon: Optional[int]
    index_value: float                  # ratio form; 1.0 == base period level
    matched_products: int
    observation_count: int
    geometric_mean_price: float
    base_geometric_mean_price: float
    base_period_start: date
    base_period_end: date

    new_products: int = 0
    disappeared_products: int = 0
    reappeared_products: int = 0
    base_products: int = 0
    current_products: int = 0
    clipped_relatives: int = 0
    winsorized: bool = False

    # Individual log relatives, retained so uncertainty can be estimated from the
    # actual dispersion rather than assumed.
    log_relatives: tuple[float, ...] = field(default_factory=tuple)
    matched_keys: tuple[str, ...] = field(default_factory=tuple)

    @property
    def index_100(self) -> float:
        """The index on a base=100 scale."""
        return self.index_value * 100.0

    @property
    def match_rate(self) -> Optional[float]:
        """Share of base-period products still matchable. A churn diagnostic."""
        if not self.base_products:
            return None
        return self.matched_products / self.base_products

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "index_date": self.index_date.isoformat(),
            "booking_horizon": self.booking_horizon,
            "index_value": round(self.index_value, 6),
            "index_100": round(self.index_100, 4),
            "matched_products": self.matched_products,
            "observation_count": self.observation_count,
            "geometric_mean_price": round(self.geometric_mean_price, 2),
            "base_geometric_mean_price": round(self.base_geometric_mean_price, 2),
            "base_period": f"{self.base_period_start.isoformat()} to {self.base_period_end.isoformat()}",
            "product_churn": {
                "base_products": self.base_products,
                "current_products": self.current_products,
                "new_products": self.new_products,
                "disappeared_products": self.disappeared_products,
                "reappeared_products": self.reappeared_products,
                "match_rate": round(self.match_rate, 4) if self.match_rate is not None else None,
            },
            "clipped_relatives": self.clipped_relatives,
            "winsorized": self.winsorized,
        }


def aggregate_product_prices(
    observations: Iterable[FareObservation],
) -> dict[str, ProductPrice]:
    """
    Reduce observations to one representative price per product.

    A product can be quoted several times in a period (multiple departure dates at
    the same horizon, or repeated collections). The geometric mean is used to
    summarise, consistent with the Jevons index itself and less sensitive to a single
    extreme quote than the arithmetic mean.
    """
    grouped: dict[str, list[float]] = defaultdict(list)
    for obs in observations:
        if obs.fare_total > 0:
            grouped[obs.product_key()].append(obs.fare_total)

    prices: dict[str, ProductPrice] = {}
    for key, values in grouped.items():
        arr = np.asarray(values, dtype=float)
        prices[key] = ProductPrice(
            product_key=key,
            price=float(np.exp(np.mean(np.log(arr)))),
            observation_count=len(values),
        )
    return prices


class MatchedJevonsCalculator:
    """
    Computes the matched-model Jevons elementary index.

    Winsorization and relative clipping are safety measures against a single
    corrupted quote dominating a geometric mean, applied to price RELATIVES rather
    than to price levels so that a genuinely expensive product is not clipped merely
    for being expensive.
    """

    def __init__(self, settings: Optional[IndexSettings] = None):
        cfg = settings or get_settings().index
        self.min_matched_products = cfg.min_matched_products
        self.min_price_relative = cfg.min_price_relative
        self.max_price_relative = cfg.max_price_relative
        self.winsorize_lower_pct = cfg.winsorize_lower_pct
        self.winsorize_upper_pct = cfg.winsorize_upper_pct

        # The arithmetic is delegated to the axiomatically tested calculator in
        # engine/jevons.py rather than reimplemented here. This module's job is
        # MATCHING — deciding which observations may legitimately be compared — and
        # the formula itself has one implementation, exercised by both the production
        # path and the time-reversal/geometric-mean test suite.
        self._calculator = JevonsIndexCalculator(
            winsorize_lower_pct=self.winsorize_lower_pct,
            winsorize_upper_pct=self.winsorize_upper_pct,
            min_observations=self.min_matched_products,
            max_price_relative=self.max_price_relative,
            min_price_relative=self.min_price_relative,
        )

    def compute(
        self,
        current_observations: list[FareObservation],
        base_prices: dict[str, ProductPrice],
        route_id: int,
        index_date: date,
        base_period_start: date,
        base_period_end: date,
        booking_horizon: Optional[int] = None,
        previously_seen_keys: Optional[set[str]] = None,
    ) -> Optional[MatchedJevonsResult]:
        """
        Compute the index for one route and horizon.

        Returns None when fewer than ``min_matched_products`` products matched. None
        means "not computable", and callers must record a
        :class:`MissingDataReason`, never substitute a value.

        ``previously_seen_keys`` lets the caller distinguish a genuinely new product
        from one that had disappeared and has now returned.
        """
        current_prices = aggregate_product_prices(current_observations)

        base_keys = {k for k, v in base_prices.items() if v.is_usable}
        current_keys = {k for k, v in current_prices.items() if v.is_usable}

        matched_keys = sorted(base_keys & current_keys)
        new_keys = current_keys - base_keys
        disappeared_keys = base_keys - current_keys

        reappeared = 0
        if previously_seen_keys:
            reappeared = len(new_keys & previously_seen_keys)

        if len(matched_keys) < self.min_matched_products:
            logger.debug(
                f"Route {route_id} H={booking_horizon} {index_date}: only "
                f"{len(matched_keys)} matched product(s) < {self.min_matched_products} "
                f"required; index not computed"
            )
            return None

        # Aligned arrays: element i of each is the SAME product. This alignment is
        # the whole point of matched-model comparison, and it is what lets the
        # arithmetic be delegated to the tested calculator.
        current_matched = np.array([current_prices[k].price for k in matched_keys], dtype=float)
        base_matched = np.array([base_prices[k].price for k in matched_keys], dtype=float)

        jevons = self._calculator.compute_jevons(
            current_prices=current_matched,
            base_prices=base_matched,
            route_id=route_id,
            index_date=index_date,
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            booking_horizon=booking_horizon,
        )

        if jevons is None:
            logger.debug(
                f"Route {route_id} H={booking_horizon} {index_date}: calculator "
                f"declined {len(matched_keys)} matched pair(s); index not computed"
            )
            return None

        observation_count = sum(current_prices[k].observation_count for k in matched_keys)

        result = MatchedJevonsResult(
            route_id=route_id,
            index_date=index_date,
            booking_horizon=booking_horizon,
            index_value=jevons.jevons_index,
            matched_products=jevons.matched_pairs,
            observation_count=observation_count,
            geometric_mean_price=jevons.geometric_mean_price,
            base_geometric_mean_price=(
                jevons.base_geometric_mean_price
                if jevons.base_geometric_mean_price is not None
                else float(np.exp(np.mean(np.log(base_matched))))
            ),
            base_period_start=base_period_start,
            base_period_end=base_period_end,
            new_products=len(new_keys),
            disappeared_products=len(disappeared_keys),
            reappeared_products=reappeared,
            base_products=len(base_keys),
            current_products=len(current_keys),
            clipped_relatives=jevons.clipped_relatives,
            winsorized=jevons.winsorized,
            log_relatives=jevons.log_relatives,
            matched_keys=tuple(matched_keys),
        )

        logger.debug(
            f"Route {route_id} H={booking_horizon} {index_date}: "
            f"index={result.index_value:.4f} matched={result.matched_products} "
            f"new={len(new_keys)} gone={len(disappeared_keys)}"
        )
        return result


# ── comparison indices, retained for methodological justification ──

def carli_index(
    current_prices: dict[str, ProductPrice], base_prices: dict[str, ProductPrice]
) -> Optional[float]:
    """
    Carli: arithmetic mean of price relatives.

    NOT used for publication. Retained so the test suite can demonstrate its upward
    bias, which is the reason the ILO/IMF CPI Manual advises against it: by the
    AM-GM inequality Carli >= Jevons for any non-constant set of relatives, and it
    fails the time-reversal test.
    """
    matched = sorted(set(current_prices) & set(base_prices))
    if len(matched) < 3:
        return None
    relatives = [current_prices[k].price / base_prices[k].price for k in matched]
    return float(np.mean(relatives))


def dutot_index(
    current_prices: dict[str, ProductPrice], base_prices: dict[str, ProductPrice]
) -> Optional[float]:
    """
    Dutot: ratio of arithmetic mean prices.

    NOT used for publication. Sensitive to absolute price level, so on a
    heterogeneous basket (economy alongside business, non-stop alongside connecting)
    the expensive products dominate the index regardless of their share of purchases.
    """
    matched = sorted(set(current_prices) & set(base_prices))
    if len(matched) < 3:
        return None
    current_mean = float(np.mean([current_prices[k].price for k in matched]))
    base_mean = float(np.mean([base_prices[k].price for k in matched]))
    if base_mean <= 0:
        return None
    return current_mean / base_mean
